"""
jira_upload.py — uploads markdown content to a Jira ticket description (ADF format)
Usage: py jira_upload.py <ticket_id> <source_file> <base_url> <email> <token>

If the source file contains <!-- SUBTASK:<KEY> --> ... <!-- /SUBTASK:<KEY> --> blocks
(produced by enrich-us.md when the HU has Jira subtasks), each block is uploaded to
its own subtask issue and stripped out of the content applied to <ticket_id>.
"""
import re
import sys
import json
import base64
import urllib.request
import urllib.error

ticket_id, source_file, base_url, email, token = sys.argv[1:6]

with open(source_file, encoding="utf-8") as f:
    raw = f.read()

SUBTASK_RE = re.compile(
    r"<!--\s*SUBTASK:(\S+)\s*-->(.*?)<!--\s*/SUBTASK:\1\s*-->",
    re.DOTALL,
)

subtask_updates = [(key, body.strip()) for key, body in SUBTASK_RE.findall(raw)]
main_content = SUBTASK_RE.sub("", raw).strip()


def text_to_adf(text):
    """Convert a simple markdown string to Atlassian Document Format (ADF)."""
    content = []
    for line in text.split("\n"):
        line = line.rstrip()
        if line.startswith("# "):
            content.append({"type": "heading", "attrs": {"level": 1},
                            "content": [{"type": "text", "text": line[2:]}]})
        elif line.startswith("## "):
            content.append({"type": "heading", "attrs": {"level": 2},
                            "content": [{"type": "text", "text": line[3:]}]})
        elif line.startswith("### "):
            content.append({"type": "heading", "attrs": {"level": 3},
                            "content": [{"type": "text", "text": line[4:]}]})
        elif line.startswith(("- ", "* ")):
            content.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": line[2:]}]}
                ]}
            ]})
        elif line.strip():
            content.append({"type": "paragraph",
                            "content": [{"type": "text", "text": line}]})

    return {
        "type": "doc",
        "version": 1,
        "content": content or [{"type": "paragraph",
                                 "content": [{"type": "text", "text": text}]}],
    }


creds = base64.b64encode(f"{email}:{token}".encode()).decode()


def update_issue(issue_key, content):
    body = json.dumps({"fields": {"description": text_to_adf(content)}}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/rest/api/3/issue/{issue_key}",
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"Updated ticket {issue_key} - HTTP {resp.status}")
            return True
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} updating {issue_key} - {e.read().decode()}", file=sys.stderr)
        return False


ok = update_issue(ticket_id, main_content)

for subtask_key, subtask_content in subtask_updates:
    ok = update_issue(subtask_key, subtask_content) and ok

sys.exit(0 if ok else 1)

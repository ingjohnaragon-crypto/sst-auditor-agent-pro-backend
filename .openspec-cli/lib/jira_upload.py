"""
jira_upload.py — uploads markdown content to a Jira ticket description (ADF format)
Usage: py jira_upload.py <ticket_id> <source_file> <base_url> <email> <token>
"""
import sys
import json
import base64
import urllib.request
import urllib.error

ticket_id, source_file, base_url, email, token = sys.argv[1:6]

with open(source_file, encoding="utf-8") as f:
    raw = f.read()


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


body = json.dumps({"fields": {"description": text_to_adf(raw)}}).encode("utf-8")
creds = base64.b64encode(f"{email}:{token}".encode()).decode()
req = urllib.request.Request(
    f"{base_url}/rest/api/3/issue/{ticket_id}",
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
        print(f"Updated ticket {ticket_id} - HTTP {resp.status}")
        sys.exit(0)
except urllib.error.HTTPError as e:
    print(f"Error: HTTP {e.code} - {e.read().decode()}", file=sys.stderr)
    sys.exit(1)

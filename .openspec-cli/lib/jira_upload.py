"""
jira_upload.py — uploads markdown content to a Jira ticket description (ADF format)
Usage: py jira_upload.py <ticket_id> <source_file> <base_url> <email> <token>

If the source file contains <!-- SUBTASK:<KEY> --> ... <!-- /SUBTASK:<KEY> --> blocks
(produced by enrich-us.md when the HU has Jira subtasks), each block is uploaded to
its own subtask issue and stripped out of the content applied to <ticket_id>.

Blocks wrapped in <!-- jira-skip --> ... <!-- /jira-skip --> are removed before upload
(local archive only — e.g. original description).

<!-- STORY_POINTS:<N> --> markers set the Story Points field when JIRA_STORY_POINTS_FIELD
is configured (default: customfield_10016 — override via env).
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

ticket_id, source_file, base_url, email, token = sys.argv[1:6]

with open(source_file, encoding="utf-8") as f:
    raw = f.read()

SUBTASK_RE = re.compile(
    r"<!--\s*SUBTASK:(\S+)\s*-->(.*?)<!--\s*/SUBTASK:\1\s*-->",
    re.DOTALL,
)
JIRA_SKIP_RE = re.compile(
    r"<!--\s*jira-skip\s*-->.*?<!--\s*/jira-skip\s*-->",
    re.DOTALL | re.IGNORECASE,
)
STORY_POINTS_RE = re.compile(
    r"<!--\s*STORY_POINTS:(\d+(?:\.\d+)?)\s*-->",
    re.IGNORECASE,
)
# Also strip the closing marker if present
STORY_POINTS_CLOSE_RE = re.compile(r"<!--\s*/STORY_POINTS\s*-->", re.IGNORECASE)

STORY_POINTS_FIELD = os.environ.get("JIRA_STORY_POINTS_FIELD", "customfield_10016")


def strip_jira_skip(text: str) -> str:
    return JIRA_SKIP_RE.sub("", text).strip()


def extract_story_points(text: str) -> float | None:
    match = STORY_POINTS_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def clean_markers(text: str) -> str:
    text = STORY_POINTS_RE.sub("", text)
    text = STORY_POINTS_CLOSE_RE.sub("", text)
    return text.strip()


subtask_updates = [(key, body.strip()) for key, body in SUBTASK_RE.findall(raw)]
main_content = SUBTASK_RE.sub("", raw).strip()


def inline_marks(text: str) -> list[dict]:
    """Parse simple **bold**, *italic*, and `code` into ADF text nodes."""
    nodes: list[dict] = []
    pattern = re.compile(
        r"(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)",
    )
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            nodes.append({"type": "text", "text": text[pos:m.start()]})
        if m.group(2) is not None:
            nodes.append({
                "type": "text",
                "text": m.group(2),
                "marks": [{"type": "strong"}],
            })
        elif m.group(3) is not None:
            nodes.append({
                "type": "text",
                "text": m.group(3),
                "marks": [{"type": "em"}],
            })
        else:
            nodes.append({
                "type": "text",
                "text": m.group(4),
                "marks": [{"type": "code"}],
            })
        pos = m.end()
    if pos < len(text):
        nodes.append({"type": "text", "text": text[pos:]})
    return nodes or [{"type": "text", "text": text}]


def paragraph(text: str) -> dict:
    return {"type": "paragraph", "content": inline_marks(text)}


def heading(level: int, text: str) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": min(max(level, 1), 6)},
        "content": inline_marks(text),
    }


def list_item(text: str) -> dict:
    # Strip checkbox prefixes for cleaner Jira bullets
    cleaned = re.sub(r"^\[([ xX])\]\s*", "", text).strip()
    return {
        "type": "listItem",
        "content": [paragraph(cleaned)],
    }


def text_to_adf(text: str) -> dict:
    """Convert markdown (headings, lists, code fences, tables, HR) to ADF."""
    text = strip_jira_skip(text)
    text = clean_markers(text)
    content: list[dict] = []
    lines = text.split("\n")
    i = 0
    bullet_buffer: list[dict] = []
    ordered_buffer: list[dict] = []

    def flush_bullets() -> None:
        nonlocal bullet_buffer
        if bullet_buffer:
            content.append({"type": "bulletList", "content": bullet_buffer})
            bullet_buffer = []

    def flush_ordered() -> None:
        nonlocal ordered_buffer
        if ordered_buffer:
            content.append({"type": "orderedList", "content": ordered_buffer})
            ordered_buffer = []

    def flush_lists() -> None:
        flush_bullets()
        flush_ordered()

    while i < len(lines):
        line = lines[i].rstrip()

        # Fenced code block
        if line.startswith("```"):
            flush_lists()
            lang = line[3:].strip() or None
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].rstrip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_text = "\n".join(code_lines)
            block: dict = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": code_text or " "}],
            }
            if lang:
                block["attrs"] = {"language": lang}
            content.append(block)
            i += 1
            continue

        # Markdown table → codeBlock (readable monospace in Jira)
        if "|" in line and line.strip().startswith("|"):
            flush_lists()
            table_lines = [line]
            i += 1
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i].rstrip())
                i += 1
            # Drop separator row |---|---|
            rendered = [
                tl for tl in table_lines
                if not re.match(r"^\|[\s\-:|]+\|$", tl.strip())
            ]
            content.append({
                "type": "codeBlock",
                "attrs": {"language": "text"},
                "content": [{"type": "text", "text": "\n".join(rendered) or " "}],
            })
            continue

        if not line.strip():
            flush_lists()
            i += 1
            continue

        if line.startswith("---") and set(line.strip()) <= {"-"}:
            flush_lists()
            content.append({"type": "rule"})
            i += 1
            continue

        if line.startswith("# "):
            flush_lists()
            content.append(heading(1, line[2:].strip()))
        elif line.startswith("## "):
            flush_lists()
            content.append(heading(2, line[3:].strip()))
        elif line.startswith("### "):
            flush_lists()
            content.append(heading(3, line[4:].strip()))
        elif line.startswith("#### "):
            flush_lists()
            content.append(heading(4, line[5:].strip()))
        elif re.match(r"^[-*]\s+", line):
            flush_ordered()
            bullet_buffer.append(list_item(re.sub(r"^[-*]\s+", "", line)))
        elif re.match(r"^\d+\.\s+", line):
            flush_bullets()
            ordered_buffer.append(list_item(re.sub(r"^\d+\.\s+", "", line)))
        else:
            flush_lists()
            content.append(paragraph(line))

        i += 1

    flush_lists()

    return {
        "type": "doc",
        "version": 1,
        "content": content
        or [{"type": "paragraph", "content": [{"type": "text", "text": "(sin contenido)"}]}],
    }


creds = base64.b64encode(f"{email}:{token}".encode()).decode()


def jira_request(method: str, path: str, payload: dict) -> tuple[bool, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        return False, f"HTTP {e.code} - {err}"


def update_issue(issue_key: str, content: str) -> bool:
    prepared = strip_jira_skip(content)
    points = extract_story_points(prepared)
    fields: dict = {"description": text_to_adf(prepared)}

    if points is not None and STORY_POINTS_FIELD:
        # Jira Software story points are usually a number
        fields[STORY_POINTS_FIELD] = points

    ok, msg = jira_request("PUT", f"/rest/api/3/issue/{issue_key}", {"fields": fields})
    if ok:
        extra = f" (story points={points})" if points is not None else ""
        print(f"Updated ticket {issue_key} - {msg}{extra}")
        return True

    # Retry without story points if the custom field is wrong/unavailable
    if points is not None and STORY_POINTS_FIELD in fields:
        print(
            f"Warning: story points field '{STORY_POINTS_FIELD}' failed for {issue_key}; "
            f"retrying description only. Detail: {msg}",
            file=sys.stderr,
        )
        ok2, msg2 = jira_request(
            "PUT",
            f"/rest/api/3/issue/{issue_key}",
            {"fields": {"description": text_to_adf(prepared)}},
        )
        if ok2:
            print(f"Updated ticket {issue_key} - {msg2} (description only)")
            return True
        print(f"Error: {msg2} updating {issue_key}", file=sys.stderr)
        return False

    print(f"Error: {msg} updating {issue_key}", file=sys.stderr)
    return False


ok = update_issue(ticket_id, main_content)

for subtask_key, subtask_content in subtask_updates:
    ok = update_issue(subtask_key, subtask_content) and ok

sys.exit(0 if ok else 1)

#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def load_env(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get(path: str) -> tuple[int, dict]:
    base = os.environ["JIRA_BASE_URL"].rstrip("/")
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_TOKEN"]
    req = urllib.request.Request(base + path)
    req.add_header("Accept", "application/json")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def adf_to_text(node: object) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(n) for n in node)
    if not isinstance(node, dict):
        return str(node)
    t = node.get("type")
    content = node.get("content", [])
    text = node.get("text", "")
    if t == "text":
        return text
    if t == "hardBreak":
        return "\n"
    if t in {"paragraph", "heading", "blockquote", "listItem"}:
        return adf_to_text(content) + "\n"
    if t in {"bulletList", "orderedList", "doc"}:
        return adf_to_text(content)
    return adf_to_text(content)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    load_env(repo / ".env")
    print("PROJECT", os.environ.get("JIRA_PROJECT_KEY"))
    print("BASE", os.environ.get("JIRA_BASE_URL"))

    for key in ("SP-192", "SP-145", "SP-191", "SP-190"):
        code, data = get(
            f"/rest/api/3/issue/{key}?fields=summary,status,issuetype,parent,description,subtasks,customfield_10016"
        )
        if code != 200:
            print(key, "HTTP", code, data.get("errorMessages"))
            continue
        fields = data["fields"]
        print(
            key,
            "OK",
            fields.get("summary"),
            "|",
            (fields.get("status") or {}).get("name"),
            "| parent",
            (fields.get("parent") or {}).get("key"),
        )
        if key == "SP-192":
            out = {
                "key": data["key"],
                "summary": fields.get("summary"),
                "status": (fields.get("status") or {}).get("name"),
                "type": (fields.get("issuetype") or {}).get("name"),
                "assignee": ((fields.get("assignee") or {}) or {}).get("displayName"),
                "parent": (fields.get("parent") or {}).get("key"),
                "story_points": fields.get("customfield_10016"),
                "description": adf_to_text(fields.get("description")).strip(),
                "subtasks": [
                    {
                        "key": s.get("key"),
                        "summary": (s.get("fields") or {}).get("summary"),
                        "status": ((s.get("fields") or {}).get("status") or {}).get("name"),
                    }
                    for s in (fields.get("subtasks") or [])
                ],
            }
            out_path = Path(
                r"c:\desarollo\innova\sst-auditor-agent-pro-frontend\.openspec-cli\.ticket-SP-192.json"
            )
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print("SAVED", out_path)

    jql = 'project = SP AND text ~ "planilla" ORDER BY key ASC'
    code, data = get(
        "/rest/api/3/search/jql?jql="
        + urllib.parse.quote(jql)
        + "&maxResults=20&fields=summary,status,parent"
    )
    print("SEARCH_HTTP", code)
    issues = data.get("issues") or data.get("values") or []
    for issue in issues:
        fields = issue.get("fields", {})
        print(
            issue.get("key"),
            fields.get("summary"),
            (fields.get("status") or {}).get("name"),
            (fields.get("parent") or {}).get("key"),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Diagnose/transition Jira issue without printing secrets."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_env(repo: Path) -> None:
    env_path = repo / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list | None]:
    base = os.environ["JIRA_BASE_URL"].rstrip("/")
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_TOKEN"]
    url = f"{base}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    import base64

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return exc.code, payload


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    load_env(repo)
    ticket = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"BASE={os.environ.get('JIRA_BASE_URL')}")
    print(f"PROJECT={os.environ.get('JIRA_PROJECT_KEY')}")
    print(f"EMAIL_SET={'yes' if os.environ.get('JIRA_EMAIL') else 'no'}")
    print(f"TOKEN_SET={'yes' if os.environ.get('JIRA_TOKEN') else 'no'}")

    code, issue = request("GET", f"/rest/api/3/issue/{ticket}?fields=summary,status,issuetype,parent")
    print(f"ISSUE_HTTP={code}")
    if not isinstance(issue, dict) or "fields" not in issue:
        print(json.dumps(issue, ensure_ascii=False, indent=2))
        return 1

    fields = issue["fields"]
    parent = fields.get("parent") or {}
    print(f"KEY={issue.get('key')}")
    print(f"SUMMARY={fields.get('summary')}")
    print(f"STATUS={fields.get('status', {}).get('name')}")
    print(f"TYPE={fields.get('issuetype', {}).get('name')}")
    print(f"PARENT={parent.get('key')}")

    code, transitions = request("GET", f"/rest/api/3/issue/{ticket}/transitions")
    print(f"TRANSITIONS_HTTP={code}")
    items = (transitions or {}).get("transitions", []) if isinstance(transitions, dict) else []
    for t in items:
        print(f"TRANSITION={t['id']}|{t['name']}")

    if not target:
        return 0

    match = next((t for t in items if target.lower() in t["name"].lower()), None)
    if match is None:
        print(f"ERROR=transition_not_found:{target}")
        return 1

    code, _ = request("POST", f"/rest/api/3/issue/{ticket}/transitions", {"transition": {"id": match["id"]}})
    print(f"TRANSITION_HTTP={code}")
    print(f"MOVED_TO={match['name']}")
    return 0 if code in (204, 200) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
parse_config.py — reads the active stack block from openspec/config.yaml
Usage:  py parse_config.py <config_path>
Output: KEY=VALUE lines for shell eval
"""
import sys
import re

if len(sys.argv) < 2:
    sys.exit(1)

config_path = sys.argv[1]

with open(config_path, encoding="utf-8") as f:
    lines = f.readlines()

# Read active stack name from the top-level "stack:" key
stack = None
for line in lines:
    m = re.match(r'^stack:\s*["\']?([a-zA-Z0-9_-]+)["\']?\s*$', line)
    if m:
        stack = m.group(1).strip()
        break

if not stack:
    sys.exit(1)

# Find the 2-space-indented entry for this stack under "stacks:"
start = None
for i, line in enumerate(lines):
    if re.match(r'^  ' + re.escape(stack) + r':\s*$', line):
        start = i
        break

if start is None:
    sys.exit(1)

# Collect 4-space-indented key: value fields until the block ends
fields = {}
for line in lines[start + 1:]:
    if line.strip() and not line.startswith('    '):
        break
    m = re.match(r'^    ([a-zA-Z0-9_]+):\s*(.+?)\s*$', line.rstrip())
    if m:
        key = m.group(1)
        val = m.group(2).strip().strip('"').strip("'")
        fields[key] = val

for k, v in fields.items():
    print(f"{k}={v}")

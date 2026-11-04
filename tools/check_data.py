#!/usr/bin/env python3
"""Pre-deploy check: every run the site's index names must exist and be tracked by git.

Usage: python3 site/tools/check_data.py   (from the repository root; exit 1 on any miss)
"""
import json, pathlib, subprocess, sys
root = pathlib.Path(__file__).resolve().parents[2]
idx = json.loads((root / 'site/data/runs/index.json').read_text())
tracked = set(subprocess.run(['git', 'ls-files', 'site/data/runs'], cwd=root, capture_output=True, text=True, check=True).stdout.split())
missing = []
for r in idx.get('runs', []):
    rel = f"site/data/runs/{r['id']}.json"
    if not (root / rel).exists(): missing.append(rel + ' (no file)')
    elif rel not in tracked: missing.append(rel + ' (not tracked by git)')
if missing:
    print('MISSING:'); print('\n'.join('  ' + m for m in missing)); sys.exit(1)
print(f"ok: {len(idx.get('runs', []))} runs in index.json, all present and tracked")

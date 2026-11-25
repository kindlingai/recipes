#!/usr/bin/env python3
"""Refresh the kindling.json of each external recipe (status external) from the repo it lives in.

  python3 tools/sync_external.py

Fetches source.repo's source.path (default kindling.json) at source.ref (default: its default branch) through the
GitHub contents API, and writes it over the local copy, keeping this repo's own keys: version, id, status,
source and site. Prints one line per recipe; exit 1 when a fetch fails. Set GITHUB_TOKEN to read private repos.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OURS = ('version', 'id', 'status', 'source', 'site')


def fetch(repo, path, ref):
    url = f'https://api.github.com/repos/{repo}/contents/{path}' + (f'?ref={ref}' if ref else '')
    req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github.raw+json',
                                               'User-Agent': 'kindlingai-recipes'})
    if os.environ.get('GITHUB_TOKEN'):
        req.add_header('Authorization', f'Bearer {os.environ["GITHUB_TOKEN"]}')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    failed = False
    for f in sorted(ROOT.glob('*/*/*/*/kindling.json')):
        k = json.loads(f.read_text())
        if k.get('status') != 'external':
            continue
        src = k['source']
        try:
            theirs = fetch(src['repo'], src.get('path', 'kindling.json'), src.get('ref'))
        except Exception as x:  # noqa: BLE001 - report every failure and go on to the next recipe
            print(f'sync_external: {f.parent.relative_to(ROOT)}: {src["repo"]}: {x}', file=sys.stderr)
            failed = True
            continue
        new = {key: k[key] for key in OURS if key in k}
        new.update({key: v for key, v in theirs.items() if key not in OURS})
        text = json.dumps(new, indent=1, ensure_ascii=False) + '\n'
        changed = f.read_text() != text
        if changed:
            f.write_text(text)
        print(f'sync_external: {f.parent.relative_to(ROOT)}: {"updated" if changed else "unchanged"}')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Pick the recipes a CI run covers, as a JSON list.

  python3 tools/changed_recipes.py --base REV   recipes with a file changed since REV (git diff REV...HEAD)
  python3 tools/changed_recipes.py --all        every recipe
  python3 tools/changed_recipes.py --id ID      the recipe whose kindling.json id is ID (a dispatch)

Prints a check=<json> line (append it to $GITHUB_OUTPUT) listing the folders of non-external, non-retired recipes.
A change to tools/, schema/, template/, hardware.json or recipes.yml selects every active recipe for check.
"""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ('tools/', 'schema/', 'template/', 'hardware.json', '.github/workflows/recipes.yml')


def recipes():
    out = {}
    for f in sorted(ROOT.glob('*/*/*/*/kindling.json')):
        rel = f.parent.relative_to(ROOT).as_posix()
        if rel.split('/')[0] in ('tools', 'schema', 'cli') or rel.startswith('.'):
            continue
        out[rel] = json.loads(f.read_text())
    return out


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--base')
    g.add_argument('--all', action='store_true')
    g.add_argument('--id')
    args = ap.parse_args()

    all_recipes = recipes()
    if args.all:
        check_dirs = set(all_recipes)
    elif args.id:
        check_dirs = {d for d, k in all_recipes.items() if k.get('id') == args.id}
        if not check_dirs:
            raise SystemExit(f'changed_recipes: no recipe has id {args.id}')
    else:
        changed = subprocess.run(['git', 'diff', '--name-only', f'{args.base}...HEAD'], cwd=ROOT, check=True,
                                 capture_output=True, text=True).stdout.split()
        touched = {'/'.join(p.split('/')[:4]) for p in changed if p.count('/') >= 4}
        shared = any(p.startswith(SHARED) for p in changed)
        check_dirs = set(all_recipes) if shared else (touched & set(all_recipes))
    check = sorted(d for d in check_dirs if all_recipes[d]['status'] not in ('external', 'retired'))
    print(f'check={json.dumps(check)}')


if __name__ == '__main__':
    main()

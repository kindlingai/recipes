#!/usr/bin/env python3
"""Validate every recipe and write index.json and the README's recipe tables from them.

  python3 tools/build_index.py                  validate, then write index.json and the README block
  python3 tools/build_index.py --check          validate; exit 1 when index.json or the README block is out of date
  python3 tools/build_index.py --summary FILE   also append the rendered tables to FILE (a job summary)

A recipe is a folder <model>/<hardware>/<count>x/<variant>/ holding a kindling.json (schema/kindling.v1.json). Exit 1,
with one line per problem, when any recipe is invalid; nothing is written then.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = 'kindlingai/recipes'
INDEX = ROOT / 'index.json'
README = ROOT / 'README.md'
START = '<!-- recipes:index:start -->'
END = '<!-- recipes:index:end -->'
SLUG = re.compile(r'^[a-z0-9][a-z0-9.-]*$')
COUNT = re.compile(r'^([1-9][0-9]*)x$')
NOT_RECIPES = {'tools', 'schema', 'cli'}


def load_validator():
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        sys.exit('build_index: needs jsonschema (pip install -r tools/requirements.txt)')
    schema = json.loads((ROOT / 'schema' / 'kindling.v1.json').read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def updated_at(rel):
    out = subprocess.run(['git', 'log', '-1', '--format=%cI', '--', rel], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.strip() or None


def default_config(k):
    configs = k.get('configs') or []
    for c in configs:
        if c.get('id') == k.get('default_config'):
            return c
    return configs[0] if configs else {}


def check_recipe(rel, k, hardware, validator):
    """Problems with one recipe, as strings."""
    bad = [f'{"/".join(str(p) for p in e.absolute_path) or "(root)"}: {e.message}'
           for e in sorted(validator.iter_errors(k), key=lambda e: list(e.absolute_path))]
    if bad:
        return bad
    model, hw, count, variant = rel.split('/')
    for name, part in (('model', model), ('variant', variant)):
        if not SLUG.match(part):
            bad.append(f'{name} folder {part!r} is not lowercase letters, digits, dots and dashes')
    if '-' not in variant:
        bad.append(f'variant folder {variant!r} is not <quant>[-<tag>]-<engine>')
    if hw not in hardware:
        bad.append(f'hardware folder {hw!r} is not a key of hardware.json ({", ".join(sorted(hardware))})')
    m = COUNT.match(count)
    if not m:
        bad.append(f'count folder {count!r} is not <n>x')
    ids = [c['id'] for c in k['configs']]
    if 'default_config' in k and k['default_config'] not in ids:
        bad.append(f'default_config {k["default_config"]!r} names no config ({", ".join(ids)})')
    elif m and default_config(k)['nodes'] != int(m.group(1)):
        bad.append(f'the default config runs on {default_config(k)["nodes"]}, the folder says {count}')
    if len(set(ids)) != len(ids):
        bad.append('config ids repeat')
    d = ROOT / rel
    if k['status'] != 'external':
        if variant.endswith('-gr8') and 'engine' not in k:
            bad.append('a gr8 recipe needs an engine pin')
        if (d / 'Dockerfile').exists() and 'image' not in k:
            bad.append('the recipe has a Dockerfile but no image')
        if 'build' in k:
            for f in ('Dockerfile', 'smoke.sh'):
                if not (d / f).exists():
                    bad.append(f'build is set but {f} is missing')
            if 'image' not in k:
                bad.append('build is set but image is not')
    return bad


def entry(rel, k, hardware):
    model, hw, count, variant = rel.split('/')
    url = (f'https://github.com/{k["source"]["repo"]}' if k['status'] == 'external'
           else f'https://github.com/{REPO}/tree/main/{rel}')
    return {
        'id': k['id'],
        'path': rel,
        'url': url,
        'model': model,
        'hardware': hw,
        'hardware_name': hardware[hw]['name'],
        'count': int(count[:-1]),
        'variant': variant,
        'status': k['status'],
        'updated_at': updated_at(rel),
        'kindling': k,
    }


def collect():
    hardware = json.loads((ROOT / 'hardware.json').read_text())
    validator = load_validator()
    entries, problems = [], []
    for f in sorted(ROOT.glob('*/*/*/*/kindling.json')):
        rel = f.parent.relative_to(ROOT).as_posix()
        if rel.split('/')[0] in NOT_RECIPES or rel.startswith('.'):
            continue
        try:
            k = json.loads(f.read_text())
        except ValueError as x:
            problems.append(f'{rel}/kindling.json: not JSON: {x}')
            continue
        bad = check_recipe(rel, k, hardware, validator)
        problems += [f'{rel}/kindling.json: {b}' for b in bad]
        if not bad:
            entries.append(entry(rel, k, hardware))
    for key in ('id', 'image'):
        seen = Counter(e['kindling'].get(key) for e in entries if e['kindling'].get(key))
        problems += [f'{key} {v!r} is used by {n} recipes' for v, n in seen.items() if n > 1]
    big = 1 << 31
    entries.sort(key=lambda e: ((e['kindling'].get('site') or {}).get('order', big), place(e)))
    return hardware, entries, problems


def place(e):
    """Sort key: model, hardware, count (as a number), variant."""
    return e['model'], e['hardware'], e['count'], e['variant']


def fmt_int(n):
    return f'{n:,}' if isinstance(n, int) else '–'


def fmt_tps(n):
    return f'{n:,.1f}'.rstrip('0').rstrip('.') if isinstance(n, (int, float)) else '–'


def engine_label(e):
    eng = e['kindling'].get('engine')
    if not eng:
        return e['variant'].rsplit('-', 1)[1]
    name = eng['repo'].split('/')[-1]
    if eng['ref'] == 'main' and eng.get('commit'):
        return f'{name} main@{eng["commit"][:7]}'
    return f'{name} {eng["ref"]}'


def row(e, unit_names):
    k = e['kindling']
    c = default_config(k)
    decode = c.get('decode') or {}
    if 'code' in decode:
        dec = fmt_tps(decode['code'])
    elif decode:
        key = next(iter(decode))
        dec = f'{fmt_tps(decode[key])} ({key})'
    else:
        dec = '–'
    prefill = c.get('prefill') or []
    p8k = next((p for p in prefill if p['context'] == 8192), None)
    hw = f'{e["count"]}× {unit_names[e["hardware"]]}'
    cells = [f'[`{e["id"]}`]({e["path"]})', hw, (k.get('variant') or '').replace('|', '\\|'), engine_label(e), dec,
             fmt_tps(p8k['tps']) if p8k else '–', fmt_int(c.get('max_context')), e['status']]
    return '| ' + ' | '.join(cells) + ' |'


def render(hardware, entries):
    unit_names = {k: v['name'] for k, v in hardware.items()}
    shown = [e for e in entries if e['status'] != 'retired']
    lines = [START,
             '<!-- Written by tools/build_index.py from each recipe\'s kindling.json. Edits here are overwritten. -->',
             '',
             f'{len(shown)} recipes. Numbers are the default config\'s: single-request decode on code, cold prefill of an '
             '8K prompt (tok/s), longest request (tokens).',
             '']
    by_model = {}
    for e in sorted(shown, key=place):
        by_model.setdefault(e['model'], []).append(e)
    for model, es in by_model.items():
        title = Counter(e['kindling']['title'] for e in es).most_common(1)[0][0]
        lines += [f'### {title}', '',
                  '| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |',
                  '|---|---|---|---|---|---|---|---|']
        lines += [row(e, unit_names) for e in es]
        lines.append('')
    lines.append(END)
    return '\n'.join(lines)


def index_text(hardware, entries):
    doc = {'version': 1, 'repo': REPO, 'hardware': hardware, 'recipes': entries}
    return json.dumps(doc, indent=2, ensure_ascii=False) + '\n'


def readme_text(block):
    text = README.read_text()
    a, b = text.find(START), text.find(END)
    if a < 0 or b < a:
        sys.exit(f'build_index: README.md has no {START} ... {END} block')
    return text[:a] + block + text[b + len(END):]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='write nothing; exit 1 when the outputs are out of date')
    ap.add_argument('--summary', metavar='FILE', help='append the rendered tables to FILE')
    args = ap.parse_args()

    hardware, entries, problems = collect()
    for p in problems:
        print(f'build_index: {p}', file=sys.stderr)
    if problems:
        sys.exit(1)
    block = render(hardware, entries)
    want = {INDEX: index_text(hardware, entries), README: readme_text(block)}
    if args.summary:
        with open(args.summary, 'a') as f:
            f.write(block + '\n')
    stale = [p.name for p, t in want.items() if not p.exists() or p.read_text() != t]
    if args.check:
        if stale:
            print(f'build_index: out of date: {", ".join(stale)} (run python3 tools/build_index.py)', file=sys.stderr)
            sys.exit(1)
    else:
        for p, t in want.items():
            if p.name in stale:
                p.write_text(t)
    print(f'build_index: {len(entries)} recipes ok' + (f', wrote {", ".join(stale)}' if stale and not args.check else ''))


if __name__ == '__main__':
    main()

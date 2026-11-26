#!/usr/bin/env python3
"""Lint recipes against the standard (template/, CONTRIBUTING.md "The recipe standard").

  python3 tools/lint_recipe.py [DIR ...] [--strict]

Without DIRs, every non-external recipe. Without --strict (the mode CI runs until issue #2's conversions land),
findings print as `::warning` annotations and the exit code is 0; --strict prints `::error` annotations and exits 1.

Checks:
  required files   README.md, AGENTS.md, kindling.json, compose.yaml, .env.example, docs/card.png, .gitignore
  README           title line and card first; H2 order Results, Quickstart, What you need, Settings, Other sizes,
                   Help, Engine pin, License; extra H2 sections only between Settings and Other sizes
  compose          one service on the host network running a published engine image pinned by digest, the OpenAI API
                   on port 8100, no `build:` key; every ${VAR} it references is documented in .env.example
  no builds        no Dockerfile in the folder, no `build` object in kindling.json
  benchmarks       default config has standard decode keys (code, prose, structured; extra workloads in decode_extra),
                   cold prefill points (8K/32K/128K within max_context), concurrency points (1/2/4/8 within
                   max_concurrent), and Needle recall (when max_context >= 132072)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = ('README.md', 'AGENTS.md', 'kindling.json', 'compose.yaml', '.env.example', 'docs/card.png', '.gitignore')
H2_ORDER = ('Results', 'Quickstart', 'What you need', 'Settings', 'Other sizes', 'Help', 'Engine pin', 'License')
STD_DECODE = ('code', 'prose', 'structured')
STD_PREFILL = (8192, 32768, 131072)
STD_CONCURRENCY = (1, 2, 4, 8)
NEEDLE_MIN_CONTEXT = 131072 + 1000
DIGEST = re.compile(r'@sha256:[0-9a-f]{40,}')
VAR = re.compile(r'\$(?!\$)\{([A-Za-z_][A-Za-z0-9_]*)(?::?[-=+?][^}]*)?\}')


def _default_config(kindling):
    configs = kindling.get('configs') or []
    for c in configs:
        if isinstance(c, dict) and c.get('id') == kindling.get('default_config'):
            return c
    return configs[0] if configs and isinstance(configs[0], dict) else None


def _check_benchmarks(kindling, add):
    if kindling.get('status') in ('external', 'retired'):
        return
    cfg = _default_config(kindling)
    if not cfg:
        return
    cid = cfg.get('id', '(default)')

    decode = cfg.get('decode') if isinstance(cfg.get('decode'), dict) else {}
    missing_decode = [k for k in STD_DECODE if k not in decode]
    if missing_decode:
        add('kindling.json', f'default config `{cid}` decode is missing standard key(s): '
                             f'{", ".join(missing_decode)} (measure with gr8 bench/bench.py)')
    extra_decode = sorted(k for k in decode if k not in STD_DECODE)
    if extra_decode:
        add('kindling.json', f'default config `{cid}` decode has non-standard key(s): '
                             f'{", ".join(extra_decode)} (move extra workloads to decode_extra)')

    max_ctx = cfg.get('max_context') if isinstance(cfg.get('max_context'), int) else None
    expected_pf = [s for s in STD_PREFILL if not max_ctx or s + 1000 <= max_ctx]
    have_pf = {p.get('context') for p in (cfg.get('prefill') or []) if isinstance(p, dict)}
    missing_pf = [f'{s // 1024}K ({s})' for s in expected_pf if s not in have_pf]
    if missing_pf:
        add('kindling.json', f'default config `{cid}` prefill is missing standard cold point(s): '
                             f'{", ".join(missing_pf)}')

    max_conc = cfg.get('max_concurrent') if isinstance(cfg.get('max_concurrent'), int) else None
    expected_cc = [s for s in STD_CONCURRENCY if not max_conc or s <= max_conc]
    have_cc = {c.get('streams') for c in (cfg.get('concurrency') or []) if isinstance(c, dict)}
    missing_cc = [str(s) for s in expected_cc if s not in have_cc]
    if missing_cc:
        add('kindling.json', f'default config `{cid}` concurrency is missing standard stream count(s): '
                             f'{", ".join(missing_cc)}')

    if not max_ctx or max_ctx >= NEEDLE_MIN_CONTEXT:
        qual = cfg.get('quality') or []
        has_needle = any(isinstance(q, dict) and 'needle' in (q.get('name') or '').lower() for q in qual)
        if not has_needle:
            add('kindling.json', f'default config `{cid}` quality has no Needle recall entry '
                                 '(bench/bench.py default level runs 128K needle)')


def findings_for(rel):
    """All findings for the recipe folder rel, as (file, message) pairs; empty when it meets the standard."""
    d = ROOT / rel
    out = []
    add = lambda f, m: out.append((f, m))

    for name in REQUIRED:
        f = d / name
        if not f.is_file() or (name == 'docs/card.png' and f.stat().st_size == 0):
            add(name, 'missing (the standard files are listed in template/)')

    kindling = {}
    if (d / 'kindling.json').is_file():
        try:
            kindling = json.loads((d / 'kindling.json').read_text())
        except (OSError, json.JSONDecodeError) as e:
            add('kindling.json', f'does not parse: {e}')
    if kindling.get('build') is not None:
        add('kindling.json', 'has a "build" object; the standard runs the published engine image, no local build')
    _check_benchmarks(kindling, add)

    readme = (d / 'README.md')
    if readme.is_file():
        lines = readme.read_text().splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines or not lines[0].startswith('# '):
            add('README.md', 'first line must be the `# <Model> <variant> on <count>× <hardware>` title')
        h2 = [l[3:].strip() for l in lines if l.startswith('## ')]
        card = readme.read_text().split('## ')[0]
        if 'docs/card.png' not in card:
            add('README.md', 'the card (![...](docs/card.png)) comes right after the title line, before Results')
        seen = 0
        s_idx = H2_ORDER.index('Settings')
        o_idx = H2_ORDER.index('Other sizes')
        for h in h2:
            if seen < len(H2_ORDER) and h == H2_ORDER[seen]:
                seen += 1
            elif not (s_idx < seen <= o_idx) and h not in H2_ORDER:
                add('README.md', f'unexpected H2 section `{h}`; recipe-specific sections go between Settings and '
                                 'Other sizes')
        if seen < len(H2_ORDER):
            add('README.md', 'missing or out-of-order H2 sections, expected order: ' + ', '.join(H2_ORDER))

    compose = (d / 'compose.yaml')
    if compose.is_file():
        text = compose.read_text()
        if not re.search(r'^\s*network_mode:\s*host\s*$', text, re.M):
            add('compose.yaml', 'must run with `network_mode: host` (the OpenAI API is a host port, 8100)')
        images = re.findall(r'^\s*image:\s*(.+?)\s*$', text, re.M)
        if not images:
            add('compose.yaml', 'no image: line; the engine runs as a published image, pinned by digest')
        for img in images:
            if not DIGEST.search(img):
                add('compose.yaml', f'image `{img}` is not pinned by digest (`...@sha256:<digest>`)')
            if re.search(r':latest($|@)', img):
                add('compose.yaml', f'image `{img}` uses the `latest` tag')
        if re.search(r'^\s*build\s*:', text, re.M):
            add('compose.yaml', 'has a `build:` key; the standard runs the published engine image, no local build')
        if '8100' not in text:
            add('compose.yaml', 'does not mention the OpenAI API port 8100 (say where it serves, even in a comment)')
        env = (d / '.env.example')
        if env.is_file():
            envtext = env.read_text()
            for var in sorted(set(VAR.findall(text))):
                if not re.search(r'\b' + re.escape(var) + r'\b', envtext):
                    add('.env.example', f'documents nothing about `{var}`, which compose.yaml references')

    if list(d.glob('Dockerfile*')):
        add('Dockerfile', 'present; the standard runs the published engine image, no local build')

    return out


def recipes():
    out = {}
    for f in sorted(ROOT.glob('*/*/*/*/kindling.json')):
        rel = f.parent.relative_to(ROOT).as_posix()
        try:
            k = json.loads(f.read_text())
        except json.JSONDecodeError:
            k = {}
        if k.get('status') != 'external':
            out[rel] = k
    return out


def main():
    args = [a for a in sys.argv[1:]]
    strict = '--strict' in args
    dirs = [a for a in args if not a.startswith('--')]
    for a in args:
        if a.startswith('--') and a != '--strict':
            raise SystemExit(f'lint_recipe: unknown option {a}')
    if not dirs:
        dirs = sorted(recipes())

    total = 0
    for rel in dirs:
        if not (ROOT / rel / 'kindling.json').is_file():
            raise SystemExit(f'lint_recipe: {rel} has no kindling.json')
        found = findings_for(rel)
        total += len(found)
        tag = 'error' if strict else 'warning'
        for f, msg in found:
            print(f'::{tag} file={rel}/{f}::{msg}')
        state = 'ok' if not found else f'{len(found)} finding(s)'
        print(f'lint: {rel}: {state}')

    if not total:
        print(f'lint: {len(dirs)} recipe(s), all meet the standard')
    if strict and total:
        sys.exit(1)


if __name__ == '__main__':
    main()

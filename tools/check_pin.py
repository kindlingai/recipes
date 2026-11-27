#!/usr/bin/env python3
"""Check that a recipe's engine and weight pins agree across kindling.json, compose.yaml and .env.example.

  python3 tools/check_pin.py DIR...           exit 0 when every DIR agrees, 1 with the reasons when not
  python3 tools/check_pin.py --strict DIR...  also refuse a pending pin (no engine commit and digest yet)

engine.pin image:  every compose file's ${<ENGINE>_IMAGE:-...} default (e.g. GR8_IMAGE, VLLM_IMAGE, ENGINE_IMAGE) is
                   engine.image@engine.image_digest. A pin may be pending (commit and digest both empty) while its
                   release is unpublished; --strict refuses that.
weights_commit:    when set, agrees with MODEL_REVISION=<commit> in .env.example.
A recipe without an engine pin passes with a note.
"""
import json
import re
import sys
from pathlib import Path

SHA = re.compile(r'[0-9a-f]{40}')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}')
REF = re.compile(r'v\d+\.\d+(\.\d+)?(?:[-.][A-Za-z0-9._-]+)?|nightly(?:-[0-9a-f]{7,40})?|stable|main')
IMAGE_VAR = re.compile(r'\$\{([A-Z][A-Z0-9_]*IMAGE):-([^}\s]+)\}')


def check(d, strict):
    if not (d / 'kindling.json').exists():
        return ['no kindling.json'], 'not a recipe'
    k = json.loads((d / 'kindling.json').read_text())
    e = k.get('engine')
    if not e:
        return [], 'no engine pin'
    env_example = (d / '.env.example').read_text() if (d / '.env.example').exists() else ''
    bad = []
    for f in ('repo', 'ref', 'pin'):
        if not e.get(f):
            bad.append(f'engine.{f} is missing')
    if e.get('ref') and not REF.fullmatch(e['ref']):
        bad.append(f'engine.ref {e["ref"]} is not a release tag, nightly, stable or main')
    commit, digest = e.get('commit') or '', e.get('image_digest') or ''
    if commit and not SHA.fullmatch(commit):
        bad.append('engine.commit is not a full commit hash')
    if digest and not DIGEST.fullmatch(digest):
        bad.append('engine.image_digest is not sha256:<64 hex>')
    if (d / '.gitmodules').exists():
        bad.append('.gitmodules: the engine is pinned by engine.commit, not a submodule')

    pin = e.get('pin')
    if pin == 'image':
        pending = not commit and not digest
        if pending and strict:
            bad.append('engine.commit and engine.image_digest are pending (--strict)')
        elif not pending:
            if not commit:
                bad.append('engine.commit is missing')
            if not digest:
                bad.append('engine.image_digest is missing')
        if not e.get('image'):
            bad.append('engine.image is missing')
        want = e.get('image') if pending else f'{e.get("image")}@{digest}'
        compose_files = sorted(d.glob('compose.yaml')) + sorted(d.glob('compose.*.yaml'))
        if not compose_files:
            bad.append('compose.yaml is missing')
        for cf in compose_files:
            images = re.findall(r'^\s*image:\s*(.+?)\s*$', cf.read_text(), re.M)
            if not images:
                bad.append(f'{cf.name} has no ${"{<ENGINE>_IMAGE:-...}"} default image')
            for img_expr in images:
                m = IMAGE_VAR.fullmatch(img_expr)
                if not m:
                    bad.append(f'{cf.name} image `{img_expr}` is not a ${"{<ENGINE>_IMAGE:-...}"} default image')
                elif m.group(2) != want:
                    bad.append(f'{cf.name} pins {m.group(2)}, kindling.json says {want}')
    elif pin:
        bad.append(f'engine.pin {pin} is not image')

    if k.get('weights_commit'):
        me = re.search(r'^MODEL_REVISION=([0-9a-f]{40})\s*$', env_example, re.M)
        if me and me.group(1) != k['weights_commit']:
            bad.append(f'.env.example pins MODEL_REVISION {me.group(1)[:8]}, weights_commit is {k["weights_commit"][:8]}')
    tag = f'{e.get("ref")} {commit[:7]}' if commit else f'{e.get("ref")} (pending)'
    return bad, f'engine {tag}, pin {pin}'


def main():
    args = sys.argv[1:]
    strict = '--strict' in args
    dirs = [Path(a) for a in args if a != '--strict']
    if not dirs:
        sys.exit(__doc__)
    failed = False
    for d in dirs:
        bad, note = check(d, strict)
        for b in bad:
            print(f'check_pin: {d}: {b}', file=sys.stderr)
        print(f'check_pin: {"FAIL" if bad else "ok"}: {d}: {note}')
        failed |= bool(bad)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()

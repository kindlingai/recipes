#!/usr/bin/env python3
"""Check that a recipe's engine and weight pins agree across kindling.json, compose.yaml and the Dockerfile.

  python3 tools/check_pin.py DIR...           exit 0 when every DIR agrees, 1 with the reasons when not
  python3 tools/check_pin.py --strict DIR...  also refuse a pending pin (no engine commit and digest yet)

engine.pin image:  compose.yaml's ${GR8_IMAGE:-...} default is engine.image@engine.image_digest. A pin may be pending
                   (commit and digest both empty) while its release is unpublished; --strict refuses that.
engine.pin source: the Dockerfile builds the engine from engine.commit (tools/engine.sh checks it out); compose.yaml's
                   ${IMAGE:-...} default is the recipe's own image; engine.image, when set, is the engine's image of
                   that commit or ref.
weights_commit:    when set and the Dockerfile pins MODEL=https://huggingface.co/<model>@<commit>, they agree.
A recipe without an engine pin passes with a note.
"""
import json
import re
import sys
from pathlib import Path

SHA = re.compile(r'[0-9a-f]{40}')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}')
REF = re.compile(r'v\d+\.\d+(\.\d+)?|stable|main')


def check(d, strict):
    if not (d / 'kindling.json').exists():
        return ['no kindling.json'], 'not a recipe'
    k = json.loads((d / 'kindling.json').read_text())
    e = k.get('engine')
    if not e:
        return [], 'no engine pin'
    compose = (d / 'compose.yaml').read_text() if (d / 'compose.yaml').exists() else ''
    dockerfile = (d / 'Dockerfile').read_text() if (d / 'Dockerfile').exists() else ''
    bad = []
    for f in ('repo', 'ref', 'pin'):
        if not e.get(f):
            bad.append(f'engine.{f} is missing')
    if e.get('ref') and not REF.fullmatch(e['ref']):
        bad.append(f'engine.ref {e["ref"]} is not a release tag, stable or main')
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
        m = re.search(r'image: \$\{GR8_IMAGE:-([^}\s]+)\}', compose)
        want = e.get('image') if pending else f'{e.get("image")}@{digest}'
        if not m:
            bad.append('compose.yaml has no ${GR8_IMAGE:-...} default image')
        elif m.group(1) != want:
            bad.append(f'compose.yaml pins {m.group(1)}, kindling.json says {want}')
    elif pin == 'source':
        if not commit:
            bad.append('engine.commit is missing: a source pin builds that commit')
        if not dockerfile:
            bad.append('a source pin needs a Dockerfile')
        img = e.get('image')
        if img and commit and not (img.endswith(':sha-' + commit[:7]) or img.endswith(':' + e.get('ref', ''))):
            bad.append(f'engine.image {img} is not the engine at {commit[:7]} or {e.get("ref")}')
        m = re.search(r'image: \$\{IMAGE:-([^}:\s]+)(:[^}\s]*)?\}', compose)
        if not k.get('image'):
            bad.append('image is missing: a source pin builds the recipe\'s own image')
        elif not m:
            bad.append('compose.yaml has no ${IMAGE:-...} default image')
        elif m.group(1) != k['image']:
            bad.append(f'compose.yaml runs {m.group(1)}, kindling.json image is {k["image"]}')
    elif pin:
        bad.append(f'engine.pin {pin} is not image or source')

    if k.get('weights_commit'):
        m = re.search(r'MODEL=https://huggingface\.co/([^@\s]+)@([0-9a-f]{40})', dockerfile)
        if m:
            if m.group(1) != k.get('model'):
                bad.append(f'the Dockerfile boots {m.group(1)}, kindling.json model is {k.get("model")}')
            if m.group(2) != k['weights_commit']:
                bad.append(f'the Dockerfile pins weights {m.group(2)[:8]}, weights_commit is {k["weights_commit"][:8]}')
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

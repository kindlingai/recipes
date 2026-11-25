#!/usr/bin/env python3
"""Check this recipe's pin: kindling.json's engine field and compose.yaml's image name the same gr8 image.

  python3 check.py           exit 0 when they agree (allows pending commit/digest before v1.2.0 publishes)
  python3 check.py --strict  also require a full 40-char engine.commit and sha256 image_digest pin
"""
import json
import re
import sys

strict = '--strict' in sys.argv[1:]
k = json.load(open('kindling.json'))
e = k.get('engine') or {}
bad = []
for f in ('repo', 'ref', 'pin', 'image'):
    if not e.get(f):
        bad.append(f'kindling.json engine.{f} is missing')

commit = e.get('commit') or ''
digest = e.get('image_digest') or ''
pending = not commit and not digest

if pending:
    if strict:
        bad.append('kindling.json engine.commit is missing (--strict)')
        bad.append('kindling.json engine.image_digest is missing (--strict)')
else:
    if not commit:
        bad.append('kindling.json engine.commit is missing')
    elif not re.fullmatch(r'[0-9a-f]{40}', commit):
        bad.append('engine.commit is not a full commit hash')
    if not digest:
        bad.append('kindling.json engine.image_digest is missing')
    elif not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        bad.append('engine.image_digest is not a sha256:<64 hex> digest')

if e.get('ref') and not re.fullmatch(r'v\d+\.\d+(\.\d+)?|stable|main', e['ref']):
    bad.append('engine.ref is not a release tag, stable or main')

m = re.search(r'image: \$\{GR8_IMAGE:-([^}\s]+)\}', open('compose.yaml').read())
want = e.get('image') if pending else f"{e.get('image')}@{digest}"
if not m:
    bad.append('compose.yaml has no pinned default image')
elif m.group(1) != want:
    bad.append(f'compose.yaml pins {m.group(1)}, kindling.json says {want}')

ids = [c['id'] for c in k.get('configs') or []]
if k.get('default_config') not in ids:
    bad.append('default_config names no config')

for b in bad:
    print('check: ' + b, file=sys.stderr)
tag = f"{e.get('ref')} {commit[:7]}" if commit else f"{e.get('ref')} (pending digest)"
print(f"check: {'FAIL' if bad else 'ok'}: engine {tag}, {len(ids)} config(s)")
sys.exit(1 if bad else 0)

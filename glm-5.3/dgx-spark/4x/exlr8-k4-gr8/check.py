#!/usr/bin/env python3
"""Check this recipe's pins: kindling.json's engine field names the gr8 commit the gr8/ submodule is at, and its
weights_commit is the Hugging Face commit the Dockerfile's MODEL line boots.

  python3 check.py        exit 0 when they agree, 1 with the reason when not
"""
import json
import re
import subprocess
import sys

k = json.load(open('kindling.json'))
e = k.get('engine') or {}
bad = []
for f in ('repo', 'ref', 'commit', 'pin', 'image', 'image_digest'):
    if not e.get(f):
        bad.append(f'kindling.json engine.{f} is missing')
if e.get('commit') and not re.fullmatch(r'[0-9a-f]{40}', e['commit']):
    bad.append('engine.commit is not a full commit hash')
if e.get('image_digest') and not re.fullmatch(r'sha256:[0-9a-f]{64}', e['image_digest']):
    bad.append('engine.image_digest is not a sha256 digest')
if e.get('image') and e.get('commit'):
    ok_img = (
        e['image'].endswith(':sha-' + e['commit'][:7])
        or (e.get('ref') and e['image'].endswith(':' + e['ref']))
    )
    if not ok_img:
        bad.append(f"engine.image {e['image']} does not match ref {e.get('ref')} or commit {e['commit'][:7]}")
try:
    sub = subprocess.run(['git', 'ls-tree', 'HEAD', 'gr8'], capture_output=True, text=True, check=True).stdout.split()
    if len(sub) < 3 or sub[1] != 'commit':
        bad.append('the gr8/ submodule is not in HEAD')
    elif sub[2] != e.get('commit'):
        bad.append(f'the gr8/ submodule is at {sub[2]}, kindling.json says {e.get("commit")}')
except (OSError, subprocess.CalledProcessError) as x:
    bad.append(f'git ls-tree HEAD gr8: {x}')
df = open('Dockerfile').read()
m = re.search(r'MODEL=https://huggingface\.co/([^@\s]+)@([0-9a-f]{40})', df)
if not m:
    bad.append('the Dockerfile has no pinned MODEL')
else:
    if m.group(1) != k.get('model'):
        bad.append(f'the Dockerfile boots {m.group(1)}, kindling.json says {k.get("model")}')
    if m.group(2) != k.get('weights_commit'):
        bad.append(f'the Dockerfile pins {m.group(2)}, kindling.json weights_commit says {k.get("weights_commit")}')
if 'MOE_UNION_CAP=0' not in df:
    bad.append('Dockerfile must explicitly set MOE_UNION_CAP=0 to keep K4 uncapped')
ids = [c['id'] for c in k['configs']]
if k.get('default_config') not in ids:
    bad.append('default_config names no config')
for b in bad:
    print('check: ' + b, file=sys.stderr)
print(f"check: {'FAIL' if bad else 'ok'}: engine {e.get('ref')} {str(e.get('commit'))[:7]}, weights {str(k.get('weights_commit'))[:8]}, "
      f"{len(ids)} config(s)")
sys.exit(1 if bad else 0)

#!/usr/bin/env bash
# Recipe-specific invariants for glm-5.3/dgx-spark/4x/exlr8-k4-gr8:
#   1. .env.example pins MOE_UNION_CAP=0 (uncapped pure-quality K4 routing).
#   2. manifests/exlr8-manifest-bit387.json exists, is mounted read-only at /etc/gr8, and matches VARIANT.
#   3. .env.example MODEL agrees with kindling.json model and weights_commit.
set -euo pipefail
dir="$(cd "$(dirname "$0")" && pwd)"

grep -Eq '^MOE_UNION_CAP=0([[:space:]]|$)' "$dir/.env.example" || {
  echo "check.sh: .env.example must explicitly set MOE_UNION_CAP=0 to keep K4 routing uncapped" >&2
  exit 1
}

[ -f "$dir/manifests/exlr8-manifest-bit387.json" ] || {
  echo "check.sh: manifests/exlr8-manifest-bit387.json is missing" >&2
  exit 1
}

grep -Eq '^\s*-\s*\./manifests:/etc/gr8:ro([[:space:]]|$)' "$dir/compose.yaml" || {
  echo "check.sh: compose.yaml must bind-mount ./manifests:/etc/gr8:ro" >&2
  exit 1
}

grep -Eq '^VARIANT=/etc/gr8/exlr8-manifest-bit387\.json([[:space:]]|$)' "$dir/.env.example" || {
  echo "check.sh: .env.example must set VARIANT=/etc/gr8/exlr8-manifest-bit387.json" >&2
  exit 1
}

python3 - "$dir" <<'PY'
import json, re, sys
from pathlib import Path

d = Path(sys.argv[1])
k = json.loads((d / 'kindling.json').read_text())
env = (d / '.env.example').read_text()
m = re.search(r'^MODEL=https://huggingface\.co/([^@\s]+)@([0-9a-f]{40})\s*$', env, re.M)
if not m:
    sys.exit('check.sh: .env.example MODEL is not pinned to https://huggingface.co/<model>@<40-hex commit>')
if m.group(1) != k.get('model'):
    sys.exit(f'check.sh: .env.example MODEL boots {m.group(1)}, kindling.json model is {k.get("model")}')
if m.group(2) != k.get('weights_commit'):
    sys.exit(f'check.sh: .env.example MODEL pins {m.group(2)[:8]}, kindling.json weights_commit is {k.get("weights_commit", "")[:8]}')
PY

echo "check.sh: glm-5.3/dgx-spark/4x/exlr8-k4-gr8 ok"

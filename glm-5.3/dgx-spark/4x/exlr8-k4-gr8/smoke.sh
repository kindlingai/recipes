#!/usr/bin/env bash
# Usage: smoke.sh IMAGE
#
# The no-GPU smoke test CI runs on the recipe's image after each build (.github/workflows/recipe-image.yml, from the
# recipe folder): the binaries link, and the launcher resolves the recipe's options
set -euo pipefail
img=${1:?usage: smoke.sh IMAGE}
# The recipe keeps K4 routing uncapped: the Dockerfile must say so (was check.py's).
grep -q 'MOE_UNION_CAP=0' "$(dirname "$0")/Dockerfile" || { echo 'Dockerfile must explicitly set MOE_UNION_CAP=0 to keep K4 uncapped'; exit 1; }
docker image ls "$img"
docker run --rm --entrypoint bash "$img" -c '
  set -eu
  for b in bin/g6m4-int4 bin/g6front-rs bin/g6load; do
    [ -x "$b" ] || { echo "$b: not in the image"; exit 1; }
    if ldd "$b" | grep "not found"; then echo "$b: missing libraries"; exit 1; fi
  done
  bin/g6front-rs --help > /dev/null
  echo binaries OK'
docker run --rm "$img" show-config --no-check | grep -E "^  (TP|PEERS|VARIANT|DISPRAM|KV_FORMAT) "
want() {  # want NAME=VALUE [docker run options]: show-config with these options has this cluster option
  # show-config prints "  NAME  VALUE  scope  (origin)" in aligned columns
  docker run --rm "${@:2}" "$img" show-config --no-check | awk -v n="${1%%=*}" -v v="${1#*=}" '$1 == n && $2 == v { f = 1 } END { exit !f }' \
    || { echo "want $1 with ${*:2}"; exit 1; }
}
want TP=4
want VARIANT=/etc/gr8/exlr8-manifest-bit387.json
want DISPRAM=1
want CAP=442368
want S2_ADAPT=0
want DEC_BK=16384
want DEC_BK_MAX=32768
want SHARE_LIMIT=16384
echo smoke OK

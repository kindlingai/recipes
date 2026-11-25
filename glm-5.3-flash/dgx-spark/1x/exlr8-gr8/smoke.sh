#!/usr/bin/env bash
# Usage: smoke.sh IMAGE
#
# The no-GPU smoke test CI runs on the recipe's image after each build (.github/workflows/recipe-image.yml, from the
# recipe folder): the binaries link, the launcher resolves the recipe's options with MENTAT 0 and 1, and the knobs are
# refused when wrong
set -euo pipefail
img=${1:?usage: smoke.sh IMAGE}
docker image ls "$img"
docker run --rm --entrypoint bash "$img" -c '
  set -eu
  for b in bin/g6m4_flash-int4 bin/g6front-rs bin/g6load; do
    [ -x "$b" ] || { echo "$b: not in the image"; exit 1; }
    if ldd "$b" | grep "not found"; then echo "$b: missing libraries"; exit 1; fi
  done
  bin/g6front-rs --help > /dev/null
  echo binaries OK'
docker run --rm "$img" show-config --no-check | grep -E "^  (TP|PEERS|CAP|MAX_MODEL_LEN|DFLASH|KV_FORMAT|VARIANT|SESS) "
want() {  # want NAME=VALUE [docker run options]: show-config with these options has this cluster option
  # show-config prints "  NAME  VALUE  scope  (origin)" in aligned columns; newer gr8 no longer repeats them as
  # "  NAME=VALUE" in its cluster options
  docker run --rm "${@:2}" "$img" show-config --no-check | awk -v n="${1%%=*}" -v v="${1#*=}" '$1 == n && $2 == v { f = 1 } END { exit !f }' \
    || { echo "want $1 with ${*:2}"; exit 1; }
}
want MAX_MODEL_LEN=262144
want MAX_MODEL_LEN=262144 -e TUNE=quality
want MAX_MODEL_LEN=700018 -e TUNE=context
want MAX_MODEL_LEN=300000 -e TUNE=context -e MAX_MODEL_LEN=300000
docker run --rm -e MENTAT=1 "$img" show-config --no-check | grep -E "^  (MENTAT|GROUP) "
rc=0; err=$(docker run --rm -e MENTAT=2 "$img" show-config --no-check 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want 0" || { echo "MENTAT=2: exit $rc: $err"; exit 1; }
rc=0; err=$(docker run --rm -e TUNE=fast "$img" show-config --no-check 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want speed" || { echo "TUNE=fast: exit $rc: $err"; exit 1; }
rc=0; err=$(docker run --rm -e TUNE=context -e CAP=262208 "$img" show-config --no-check 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "more than CAP" || { echo "TUNE=context CAP=262208: exit $rc: $err"; exit 1; }
echo smoke OK

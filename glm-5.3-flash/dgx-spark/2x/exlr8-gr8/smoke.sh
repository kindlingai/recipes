#!/usr/bin/env bash
# Usage: smoke.sh IMAGE
#
# The no-GPU smoke test CI runs on the recipe's image after each build (.github/workflows/recipe-image.yml, from the
# recipe folder): the binaries link, the launcher resolves the recipe's options with MENTAT 0 (PEERS) and 1, and the
# knobs are refused when wrong
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
docker run --rm -e PEERS=10.9.0.1,10.9.0.2 "$img" show-config --no-check | grep -E "^  (TP|PEERS|CAP|DFLASH|KV_FORMAT|VARIANT|SESS) "
rc=0; err=$(docker run --rm "$img" show-config --no-check 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want the two boxes" || { echo "no PEERS: exit $rc: $err"; exit 1; }
docker run --rm -e MENTAT=1 "$img" show-config --no-check | grep -E "^  (MENTAT|GROUP) "
rc=0; err=$(docker run --rm -e MENTAT=2 "$img" show-config --no-check 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want 0" || { echo "MENTAT=2: exit $rc: $err"; exit 1; }
# each TUNE sets its options (knobs.sh), and an option set on its own keeps its value
want() {  # want "ENV..." "LINE...": show-config with ENV prints each LINE
  local out; out=$(docker run --rm -e PEERS=10.9.0.1,10.9.0.2 $(printf -- '-e %s ' $1) "$img" show-config --no-check)
  for l in "${@:2}"; do grep -qE "$l" <<< "$out" || { echo "$1: no line matching '$l'"; exit 1; }; done
}
d=$(docker run --rm -e PEERS=10.9.0.1,10.9.0.2 "$img" show-config --no-check | grep "^digest")
[ "$(docker run --rm -e PEERS=10.9.0.1,10.9.0.2 -e TUNE=speed "$img" show-config --no-check | grep "^digest")" = "$d" ] \
  || { echo "TUNE=speed: not the default's cluster options"; exit 1; }
want TUNE=speed '^  VARIANT +[^ ]*/manifests/exlr8-manifest-bit349\.json' '^  SESS +4 ' '^  CAP +2097152 ' '^  MAX_MODEL_LEN +262144 '
want TUNE=context '^  VARIANT +[^ ]*/manifests/exlr8-manifest-bit349\.json' '^  SESS +8 ' '^  CAP +2097152 ' '^  MAX_MODEL_LEN +1048576 ' 'GR8_CP=1'
want TUNE=quality '^  VARIANT +k4' '^  SESS +4 ' '^  CAP +262208 ' '^  MAX_MODEL_LEN +262144 '
want "TUNE=quality CAP=131136 MAX_MODEL_LEN=131072" '^  CAP +131136 ' '^  MAX_MODEL_LEN +131072 '
rc=0; err=$(docker run --rm -e PEERS=10.9.0.1,10.9.0.2 -e TUNE=fast "$img" show-config --no-check 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want speed" || { echo "TUNE=fast: exit $rc: $err"; exit 1; }
echo smoke OK

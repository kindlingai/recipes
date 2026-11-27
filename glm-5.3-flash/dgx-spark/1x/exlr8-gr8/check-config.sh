#!/usr/bin/env bash
# No-GPU configuration check for glm-5.3-flash-exlr8-1x-spark against gr8's published image.
# Verifies compose.yaml + .env.example parse cleanly, the pinned gr8 image has the required binaries,
# knobs.sh resolves each TUNE / MENTAT mode cleanly, and invalid knob combinations fail with exit 2.
set -euo pipefail
cd "$(dirname "$0")"

docker compose --env-file .env.example config --quiet
img=$(docker compose --env-file .env.example config --images | head -n 1)
echo "compose OK; image: $img"

docker run --rm --entrypoint bash "$img" -c '
  set -eu
  for b in bin/g6m4_flash-int4 bin/g6front-rs bin/g6load; do
    [ -x "$b" ] || { echo "$b: not in the image"; exit 1; }
    if ldd "$b" | grep "not found"; then echo "$b: missing libraries"; exit 1; fi
  done
  bin/g6front-rs --help > /dev/null
  echo binaries OK'

run_cfg() {
  docker run --rm --read-only \
    --tmpfs /tmp:size=1g,mode=1777 \
    -v "$PWD/entrypoint.sh:/opt/glm53f-1x/entrypoint.sh:ro" \
    -v "$PWD/knobs.sh:/opt/glm53f-1x/knobs.sh:ro" \
    -v "$PWD/bin/gr8:/opt/glm53f-1x/bin/gr8:ro" \
    -v "$PWD/kv-store.yaml:/etc/gr8/kv-store.yaml:ro" \
    -v /var/lib/gr8/home \
    -v /var/lib/gr8/cache \
    --env-file .env.example \
    -e GR8_WORK_DIR=/var/lib/gr8/home \
    -e MODEL_CACHE=/var/lib/gr8/cache \
    -e PY=/usr/bin/python3 \
    -e FRONT_BIN=/opt/gr8/bin/g6front-rs \
    --entrypoint /opt/glm53f-1x/entrypoint.sh \
    "$@" "$img" show-config --no-check
}

run_cfg | grep -E "^  (TP|PEERS|CAP|MAX_MODEL_LEN|DFLASH|KV_FORMAT|VARIANT|SESS) "

want() {  # want NAME=VALUE [docker run options]
  run_cfg "${@:2}" | awk -v n="${1%%=*}" -v v="${1#*=}" '$1 == n && $2 == v { f = 1 } END { exit !f }' \
    || { echo "want $1 with ${*:2}"; exit 1; }
}

want MAX_MODEL_LEN=262144
want MAX_MODEL_LEN=262144 -e TUNE=quality
want MAX_MODEL_LEN=700018 -e TUNE=context
want MAX_MODEL_LEN=300000 -e TUNE=context -e MAX_MODEL_LEN=300000
run_cfg -e MENTAT=1 | grep -E "^  (MENTAT|GROUP) "
rc=0; err=$(run_cfg -e MENTAT=2 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want 0" || { echo "MENTAT=2: exit $rc: $err"; exit 1; }
rc=0; err=$(run_cfg -e TUNE=fast 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want speed" || { echo "TUNE=fast: exit $rc: $err"; exit 1; }
rc=0; err=$(run_cfg -e TUNE=context -e CAP=262208 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "more than CAP" || { echo "TUNE=context CAP=262208: exit $rc: $err"; exit 1; }
echo "check-config OK"

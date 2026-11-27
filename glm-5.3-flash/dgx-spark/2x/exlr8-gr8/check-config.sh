#!/usr/bin/env bash
# No-GPU configuration check for glm-5.3-flash-exlr8-2x-spark against gr8's published image.
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
    -v "$PWD/entrypoint.sh:/opt/glm53f-2x/entrypoint.sh:ro" \
    -v "$PWD/knobs.sh:/opt/glm53f-2x/knobs.sh:ro" \
    -v "$PWD/bin/gr8:/opt/glm53f-2x/bin/gr8:ro" \
    -v "$PWD/kv-store.yaml:/etc/gr8/kv-store.yaml:ro" \
    -v /var/lib/gr8/home \
    -v /var/lib/gr8/cache \
    --env-file .env.example \
    -e GR8_WORK_DIR=/var/lib/gr8/home \
    -e MODEL_CACHE=/var/lib/gr8/cache \
    -e PY=/usr/bin/python3 \
    -e FRONT_BIN=/opt/gr8/bin/g6front-rs \
    --entrypoint /opt/glm53f-2x/entrypoint.sh \
    "$@" "$img" show-config --no-check
}

run_cfg -e PEERS=10.9.0.1,10.9.0.2 | grep -E "^  (TP|PEERS|CAP|DFLASH|KV_FORMAT|VARIANT|SESS) "
rc=0; err=$(run_cfg 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want the two boxes" || { echo "no PEERS: exit $rc: $err"; exit 1; }
run_cfg -e MENTAT=1 | grep -E "^  (MENTAT|GROUP) "
rc=0; err=$(run_cfg -e MENTAT=2 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want 0" || { echo "MENTAT=2: exit $rc: $err"; exit 1; }

# each TUNE sets its options (knobs.sh), and an option set on its own keeps its value
want() {  # want "ENV..." "LINE...": show-config with ENV prints each LINE
  local out
  # shellcheck disable=SC2046
  out=$(run_cfg -e PEERS=10.9.0.1,10.9.0.2 $(printf -- '-e %s ' $1))
  for l in "${@:2}"; do grep -qE "$l" <<< "$out" || { echo "$1: no line matching '$l'"; exit 1; }; done
}
d=$(run_cfg -e PEERS=10.9.0.1,10.9.0.2 | grep "^digest")
[ "$(run_cfg -e PEERS=10.9.0.1,10.9.0.2 -e TUNE=speed | grep "^digest")" = "$d" ] \
  || { echo "TUNE=speed: not the default's cluster options"; exit 1; }
want TUNE=speed '^  VARIANT +[^ ]*/manifests/exlr8-manifest-bit349\.json' '^  SESS +4 ' '^  CAP +2097152 ' '^  MAX_MODEL_LEN +262144 ' 'GR8_GLM53F_VISION=1'
want TUNE=context '^  VARIANT +[^ ]*/manifests/exlr8-manifest-bit349\.json' '^  SESS +8 ' '^  CAP +2097152 ' '^  MAX_MODEL_LEN +1048576 ' 'GR8_CP=1' 'GR8_GLM53F_VISION=1'
want TUNE=quality '^  VARIANT +k4' '^  SESS +4 ' '^  CAP +262208 ' '^  MAX_MODEL_LEN +262144 ' 'GR8_GLM53F_VISION=1'
want "TUNE=quality CAP=131136 MAX_MODEL_LEN=131072" '^  CAP +131136 ' '^  MAX_MODEL_LEN +131072 '
rc=0; err=$(run_cfg -e PEERS=10.9.0.1,10.9.0.2 -e TUNE=fast 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want speed" || { echo "TUNE=fast: exit $rc: $err"; exit 1; }
echo "check-config OK"

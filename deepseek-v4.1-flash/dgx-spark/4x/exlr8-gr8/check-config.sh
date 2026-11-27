#!/usr/bin/env bash
# No-GPU configuration check for deepseek-v4.1-flash-exlr8-4x-spark against gr8's published image.
# Verifies compose.yaml + .env.example parse cleanly (both default and fetch profile), the seccomp profile is valid
# JSON allowing io_uring, the gr8 image has the required binaries, knobs.sh resolves every TUNE / override / MENTAT
# mode cleanly without duplicate engine.env keys, and invalid knob combinations or booting without the release fail
# with exit 2.
#
# Usage: ./check-config.sh [GR8_IMAGE]
set -euo pipefail
cd "$(dirname "$0")"

docker compose --env-file .env.example config --quiet
docker compose --profile fetch --env-file .env.example config --quiet
python3 -c '
import json
d = json.load(open("seccomp-iouring.json"))
assert d.get("defaultAction") == "SCMP_ACT_ERRNO"
names = {n for s in d.get("syscalls", []) if s.get("action") == "SCMP_ACT_ALLOW" for n in s.get("names", [])}
for c in ("io_uring_setup", "io_uring_enter", "io_uring_register"):
    assert c in names, f"missing {c}"
print("seccomp-iouring.json OK")
'

img=${1:-$(docker compose --env-file .env.example config --images | head -n 1)}
echo "compose OK; image: $img"

docker run --rm --security-opt "seccomp=$PWD/seccomp-iouring.json" --entrypoint bash "$img" -c '
  set -eu
  for b in bin/g6m4_ds41 bin/g6front-rs bin/g6load; do
    [ -x "$b" ] || { echo "$b: not in the image"; exit 1; }
    if ldd "$b" | grep "not found"; then echo "$b: missing libraries"; exit 1; fi
  done
  bin/g6front-rs --help > /dev/null
  echo binaries OK'

run_cfg() {
  docker run --rm --read-only \
    --tmpfs /tmp:size=1g,mode=1777 \
    --security-opt "seccomp=$PWD/seccomp-iouring.json" \
    -v "$PWD/entrypoint.sh:/opt/ds41-4x/entrypoint.sh:ro" \
    -v "$PWD/knobs.sh:/opt/ds41-4x/knobs.sh:ro" \
    -v "$PWD/fetch-release.sh:/opt/ds41-4x/fetch-release.sh:ro" \
    -v /var/lib/gr8/home \
    -v /var/lib/gr8/cache \
    --env-file .env.example \
    -e GR8_WORK_DIR=/var/lib/gr8/home \
    -e MODEL_CACHE=/var/lib/gr8/cache \
    -e MODEL=/var/lib/gr8/cache/deepseek-v4.1-flash-exlr8-native \
    -e ENGRAM_PREFIX=/var/lib/gr8/home/engram/ds41 \
    -e PY=/usr/bin/python3 \
    -e FRONT_BIN=/opt/gr8/bin/g6front-rs \
    --entrypoint /opt/ds41-4x/entrypoint.sh \
    "$@" "$img" show-config --no-check
}

peers=PEERS=10.9.0.1,10.9.0.2,10.9.0.3,10.9.0.4
run_cfg -e "$peers" | grep -E "^  (TP|PEERS|CAP|SESS|MODEL|EXTRA_ENV) "

no_dup_keys() {
  local dups
  dups=$(echo "$1" | sed -n 's/^  engine\.env=//p' | tr ' ' '\n' | cut -d= -f1 | sort | uniq -d)
  [ -z "$dups" ] || { echo "$2: duplicate engine.env keys: $dups"; exit 1; }
}

want() { # TUNE, then patterns its show-config must hold
  local t=$1 out p; shift
  out=$(run_cfg -e "$peers" -e TUNE="$t")
  echo "$out" | grep -E "^  (CAP|SESS|EXACT|EXTRA_ENV) "
  no_dup_keys "$out" "TUNE=$t"
  for p in "$@"; do echo "$out" | grep -qE -- "$p" || { echo "TUNE=$t: show-config has no $p"; exit 1; }; done
}

want speed "^  CAP +327680 " "^  SESS +32 " "GR8_DS_ENGRAM=1" "GR8_DS_ENGRAM_PREFIX=/var/lib/gr8/home/engram/ds41" "GR8_DS_RELAXED_ACCEPT=" "GR8_DS_MOE_TOPK_DECODE=4" "GR8_DS41_HEAD_MX=1" "GR8_DS_ATTN_TC_MF=2" "GR8_DS_CACHE_MIB=1024" "GR8_DS_ENGRAM_CACHE_MIB=2048" "GR8_DS_PF_V2=1" "GR8_DS_PREFILL_W=12288" "GR8_DS_ATTN_PW=12288" "GR8_DS41_IDX_PW=12288" "GR8_DS_PF_V2_W16K=1" "GR8_DS_PF_V2_L20_TAIL=1" "GR8_DS_PF_V2_SEND_FFN_OPT=3" "GR8_DS_PF_V2_BF16_TC=0" "GR8_DS_PF_V2_ATTN_PIPE=1" "GR8_DS_ATTN_TC_TILE=2" "GR8_S2_ADMIT_HOLD=1" "GR8_S2_TAIL_FIRST=1" "GR8_DS_SESS_DRAFTS=1"
if run_cfg -e "$peers" | grep -qE "GR8_DS_PREFILL_W=8192|GR8_DS_MHC_ROW_SHARD=1|GR8_DS_ATTN_TC_TILE=1"; then
  echo "TUNE=speed: unexpected 8192, row-shard, or tile-1 word is set"; exit 1
fi
want context "^  CAP +1048576 " "^  SESS +16 " "GR8_DS_RELAXED_ACCEPT=" "GR8_DS_CACHE_MIB=2048" "GR8_DS_MHC_ROW_SHARD=1" "GR8_DS_ATTN_TC_TILE=1" "GR8_DS_PREFILL_W=4096"
if run_cfg -e "$peers" -e TUNE=context | grep -qE "GR8_DS_PF_V2=1|GR8_DS_PF_V2_W16K=1|GR8_DS_PF_V2_BF16_TC=|GR8_DS_ENGRAM_CACHE_MIB="; then
  echo "TUNE=context: v2 prefill or speed cache words leaked onto context"; exit 1
fi
want quality "^  CAP +262144 " "^  SESS +5 " "^  EXACT +1 " "GR8_DS_PREFILL_W=4096" "GR8_DS_PF_LANES=2"
if run_cfg -e "$peers" -e TUNE=quality | grep -qE "GR8_DS_RELAXED_ACCEPT|GR8_DS_PF_V2=1|GR8_DS_PF_V2_BF16_TC=|GR8_DS_SH_TC=1|GR8_DS_CACHE_MIB=|GR8_DS_ENGRAM_CACHE_MIB="; then
  echo "TUNE=quality: fast mode, v2, or speed cache switches are on"; exit 1
fi

q10=$(run_cfg -e "$peers" -e TUNE=quality -e SESS=10)
echo "$q10" | grep -q "GR8_DS_SESS_DRAFTS=1" || { echo "TUNE=quality SESS=10: missing GR8_DS_SESS_DRAFTS=1"; exit 1; }
w8k=$(run_cfg -e "$peers" -e EXTRA_ENV=GR8_DS_PF_V2_W16K=0)
no_dup_keys "$w8k" "W16K=0"
echo "$w8k" | grep -q "GR8_DS_PREFILL_W=8192" && ! echo "$w8k" | grep -q "GR8_DS_PF_V2_W16K=1" || { echo "W16K=0 rollback failed"; exit 1; }
bf16tc7=$(run_cfg -e "$peers" -e EXTRA_ENV=GR8_DS_PF_V2_BF16_TC=7)
no_dup_keys "$bf16tc7" "BF16_TC=7"
echo "$bf16tc7" | grep -q "GR8_DS_PF_V2_BF16_TC=7" && ! echo "$bf16tc7" | grep -q "GR8_DS_PF_V2_BF16_TC=0" || { echo "BF16_TC=7 override failed"; exit 1; }
topk6=$(run_cfg -e "$peers" -e EXTRA_ENV=GR8_DS_MOE_TOPK_DECODE=6)
no_dup_keys "$topk6" "TOPK=6"
echo "$topk6" | grep -q "GR8_DS_MOE_TOPK_DECODE=6" && ! echo "$topk6" | grep -q "GR8_DS_MOE_TOPK_DECODE=4" || { echo "TOPK=6 override failed"; exit 1; }
cmib=$(run_cfg -e "$peers" -e EXTRA_ENV="GR8_DS_CACHE_MIB=2048 GR8_DS_ENGRAM_CACHE_MIB=4096")
no_dup_keys "$cmib" "CACHE_MIB"
echo "$cmib" | grep -q "GR8_DS_CACHE_MIB=2048" && echo "$cmib" | grep -q "GR8_DS_ENGRAM_CACHE_MIB=4096" && ! echo "$cmib" | grep -qE "GR8_DS_CACHE_MIB=1024|GR8_DS_ENGRAM_CACHE_MIB=2048" || { echo "cache MiB override failed"; exit 1; }
lcmib=$(run_cfg -e "$peers" -e EXTRA_ENV=G6_DS41_CACHE_MIB=2048)
no_dup_keys "$lcmib" "G6_DS41_CACHE_MIB"
echo "$lcmib" | grep -q "GR8_DS_CACHE_MIB=2048" && ! echo "$lcmib" | grep -qE "GR8_DS_CACHE_MIB=1024|DS41_CACHE_MIB=" || { echo "legacy G6_DS41_CACHE_MIB override failed"; exit 1; }

rc=0; err=$(run_cfg 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want the four boxes" || { echo "no PEERS: exit $rc: $err"; exit 1; }
run_cfg -e MENTAT=1 | grep -E "^  (MENTAT|GROUP) "
rc=0; err=$(run_cfg -e MENTAT=2 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want 0" || { echo "MENTAT=2: exit $rc: $err"; exit 1; }
rc=0; err=$(run_cfg -e "$peers" -e TUNE=fast 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "want speed" || { echo "TUNE=fast: exit $rc: $err"; exit 1; }
rc=0; err=$(run_cfg -e "$peers" -e EXACT=1 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "TUNE=quality" || { echo "EXACT=1: exit $rc: $err"; exit 1; }
rc=0; err=$(run_cfg -e "$peers" -e EXACT=0 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "TUNE=speed" || { echo "EXACT=0: exit $rc: $err"; exit 1; }

rc=0
err=$(docker run --rm --read-only \
  --tmpfs /tmp:size=1g,mode=1777 \
  -v "$PWD/entrypoint.sh:/opt/ds41-4x/entrypoint.sh:ro" \
  -v "$PWD/knobs.sh:/opt/ds41-4x/knobs.sh:ro" \
  -v "$PWD/fetch-release.sh:/opt/ds41-4x/fetch-release.sh:ro" \
  -v /var/lib/gr8/home -v /var/lib/gr8/cache \
  --env-file .env.example \
  -e GR8_WORK_DIR=/var/lib/gr8/home -e MODEL_CACHE=/var/lib/gr8/cache \
  -e MODEL=/var/lib/gr8/cache/deepseek-v4.1-flash-exlr8-native \
  -e ENGRAM_PREFIX=/var/lib/gr8/home/engram/ds41 \
  -e "$peers" \
  --entrypoint /opt/ds41-4x/entrypoint.sh \
  "$img" 2>&1) || rc=$?
[ "$rc" = 2 ] && echo "$err" | grep -q "run the fetch first" || { echo "up without the release: exit $rc: $err"; exit 1; }
echo "check-config OK"

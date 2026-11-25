#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

GR8_DIR="${GR8_DIR:-$SCRIPT_DIR/gr8}"
MODEL_DIR="${MODEL_DIR:-$SCRIPT_DIR/models/Qwen3.8-Flash-Next-exlr8}"
WIDTHS="${WIDTHS:-$MODEL_DIR/manifests/exlr8-manifest-bit300.json}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8100}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen3.8-flash-next}"
CAP="${CAP:-40960}"
PREFILL="${PREFILL:-13312}"
MTP="${MTP:-4}"
VRAM_RESERVE_MIB="${VRAM_RESERVE_MIB:-1920}"
PLE_PATH="${PLE_PATH:-}"
EXPERT_PROFILE="${EXPERT_PROFILE:-}"

G6M4="$GR8_DIR/bin/g6m4_qw38"
SHIM="$GR8_DIR/frontend/g6s2shim.py"
G6FRONT="$GR8_DIR/frontend/g6front-rs/target/release/g6front-rs"

for f in "$G6M4" "$SHIM" "$G6FRONT" "$WIDTHS"; do
    if [ ! -e "$f" ]; then
        echo "Missing required file: $f" >&2
        exit 1
    fi
done

RUN_DIR="$SCRIPT_DIR/run"
S2_DIR="$RUN_DIR/s2"
SOCK="$RUN_DIR/engine.sock"
rm -rf "$RUN_DIR"
mkdir -p "$S2_DIR"

ENG_PID=""
SHIM_PID=""
FRONT_PID=""
cleanup() {
    [ -n "$FRONT_PID" ] && kill "$FRONT_PID" 2>/dev/null || true
    [ -n "$SHIM_PID" ] && kill "$SHIM_PID" 2>/dev/null || true
    touch "$S2_DIR/quit" 2>/dev/null || true
    sleep 0.5
    [ -n "$ENG_PID" ] && kill -TERM "$ENG_PID" 2>/dev/null || true
    wait "$FRONT_PID" 2>/dev/null || true
    wait "$SHIM_PID" 2>/dev/null || true
    wait "$ENG_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

EXTRA_ARGS=()
[ -n "$PLE_PATH" ] && EXTRA_ARGS+=(--ple "$PLE_PATH")
[ -n "$EXPERT_PROFILE" ] && EXTRA_ARGS+=(--expert-profile "$EXPERT_PROFILE")

echo "Starting g6m4_qw38 (K3 hybrid GPU + host RAM, MTP=$MTP, cap=$CAP, reserve=${VRAM_RESERVE_MIB}MiB)..."
GR8_LOAD_THREADS="${GR8_LOAD_THREADS:-8}" \
GR8_LOAD_CHUNK_MB="${GR8_LOAD_CHUNK_MB:-32}" \
GR8_LOAD_MERGE_KB="${GR8_LOAD_MERGE_KB:-0}" \
"$G6M4" \
    --rank 0 --ips 127.0.0.1 \
    --packs "$MODEL_DIR" \
    --widths "$WIDTHS" \
    --strata \
    --vram-reserve-mib "$VRAM_RESERVE_MIB" \
    --mtp "$MTP" \
    --prefill "$PREFILL" \
    --cap "$CAP" \
    --s2-sessions 1 \
    --s2-epoch 1 \
    --reuse-prefix \
    --serve "$S2_DIR" \
    "${EXTRA_ARGS[@]}" \
    >"$RUN_DIR/engine.log" 2>&1 &
ENG_PID=$!

for _ in $(seq 1 300); do
    if ! kill -0 "$ENG_PID" 2>/dev/null; then
        echo "Engine exited early. Tail of $RUN_DIR/engine.log:" >&2
        tail -n 40 "$RUN_DIR/engine.log" >&2
        exit 1
    fi
    [ -f "$S2_DIR/ready.s2" ] && break
    sleep 1
done
[ -f "$S2_DIR/ready.s2" ] || { echo "Engine ready timeout." >&2; exit 1; }

python3 "$SHIM" \
    --dir "$S2_DIR" \
    --sock "$SOCK" \
    --model-name "$SERVED_MODEL_NAME" \
    --model-dir "$MODEL_DIR" \
    --vocab-size 248320 \
    --eos-ids 248046,248044 \
    --sessions 1 \
    --max-model-len "$CAP" \
    >"$RUN_DIR/shim.log" 2>&1 &
SHIM_PID=$!

for _ in $(seq 1 30); do
    [ -S "$SOCK" ] && break
    sleep 0.5
done
[ -S "$SOCK" ] || { echo "Shim socket timeout." >&2; exit 1; }

"$G6FRONT" \
    --model-dir "$MODEL_DIR" \
    --engine-sock "$SOCK" \
    --dialect qwen \
    --served-model-name "$SERVED_MODEL_NAME" \
    --max-model-len "$CAP" \
    --allow-thinking-off \
    --host "$HOST" \
    --port "$PORT" \
    >"$RUN_DIR/front.log" 2>&1 &
FRONT_PID=$!

for _ in $(seq 1 30); do
    if curl -fsS "http://${HOST}:${PORT}/v1/models" >/dev/null 2>&1; then
        echo "Ready: http://${HOST}:${PORT}/v1/chat/completions (model: $SERVED_MODEL_NAME)"
        wait "$FRONT_PID"
        exit 0
    fi
    sleep 1
done

echo "Frontend health timeout. Tail of $RUN_DIR/front.log:" >&2
tail -n 30 "$RUN_DIR/front.log" >&2
exit 1

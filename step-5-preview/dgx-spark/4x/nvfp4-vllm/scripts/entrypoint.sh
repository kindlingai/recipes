#!/usr/bin/env bash
# Container entrypoint for Step-5 Preview NVFP4 on 4x DGX Spark.
# Expands PROFILE (b5-fp8, b4-fp8, b4-bf16-192k, b4-bf16-256k, custom), verifies the read-only
# FP8 KV overlay manifest when STEP5_FP8KV=1, and execs `vllm serve` for rank 0 (API) or 1..3 (--headless).
set -euo pipefail

NODE_RANK=${NODE_RANK:-0}
[[ $NODE_RANK =~ ^[0-3]$ ]] || { echo "Expected NODE_RANK in 0..3, got: $NODE_RANK" >&2; exit 2; }

STEP5_ROOT=${STEP5_ROOT:-/srv/step5}
MODEL_DIR=${MODEL_DIR:-$STEP5_ROOT/model}
FP8KV_BUNDLE=${FP8KV_BUNDLE:-/opt/step5-fp8kv-bundle}
API_PORT=${API_PORT:-8100}
MASTER_PORT=${MASTER_PORT:-29511}
BATCH_TOKENS=${BATCH_TOKENS:-4096}
MAXSEQ=${MAXSEQ:-8}
STEP5_DENSE=${STEP5_DENSE:-1}
LMONLY=${LMONLY:-1}
SPEC_TOKENS=${SPEC_TOKENS:-3}
PROFILE=${PROFILE:-b5-fp8}

NODE0=${NODE0:-192.168.50.11}
NODE1=${NODE1:-192.168.50.12}
NODE2=${NODE2:-192.168.50.13}
NODE3=${NODE3:-192.168.50.14}
NODES=("$NODE0" "$NODE1" "$NODE2" "$NODE3")

if [[ -z ${VLLM_HOST_IP:-} ]]; then
  VLLM_HOST_IP=${NODES[$NODE_RANK]}
fi
export VLLM_HOST_IP

case "$PROFILE" in
  b5-fp8)
    P_FP8KV=1; P_KV=fp8_e4m3; P_MAXLEN=589824; P_BLOCKS=40000; P_GMU=0.86; P_EST=0 ;;
  b4-fp8)
    P_FP8KV=1; P_KV=fp8_e4m3; P_MAXLEN=442368; P_BLOCKS=30000; P_GMU=0.85; P_EST=1 ;;
  b4-bf16-192k)
    P_FP8KV=0; P_KV=auto;     P_MAXLEN=196608; P_BLOCKS=;      P_GMU=0.85; P_EST=1 ;;
  b4-bf16-256k)
    P_FP8KV=0; P_KV=auto;     P_MAXLEN=262144; P_BLOCKS=;      P_GMU=0.86; P_EST=1 ;;
  custom)
    P_FP8KV=;  P_KV=;         P_MAXLEN=;       P_BLOCKS=;      P_GMU=;     P_EST= ;;
  *)
    echo "Unknown PROFILE '$PROFILE' (expected b5-fp8, b4-fp8, b4-bf16-192k, b4-bf16-256k, or custom)" >&2
    exit 2 ;;
esac

STEP5_FP8KV=${STEP5_FP8KV:-$P_FP8KV}
KV_DTYPE=${KV_DTYPE:-$P_KV}
MAXLEN=${MAXLEN:-$P_MAXLEN}
FP8KV_BLOCKS=${FP8KV_BLOCKS:-$P_BLOCKS}
GMU=${GMU:-$P_GMU}
VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=${VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS:-$P_EST}

: "${STEP5_FP8KV:?Set STEP5_FP8KV (0 or 1) or pick a named PROFILE}"
: "${KV_DTYPE:?Set KV_DTYPE (fp8_e4m3 or auto) or pick a named PROFILE}"
: "${MAXLEN:?Set MAXLEN for the selected profile}"
: "${GMU:?Set GMU for the selected profile}"
: "${VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS:?Set VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS (0 or 1)}"

[[ -s $MODEL_DIR/config.json && -s $MODEL_DIR/model.safetensors.index.json ]] || {
  echo "Model view is missing under $MODEL_DIR; complete storage and NFS setup first" >&2
  exit 2
}

FP8KV_VLLM_ARGS=()
if [[ $STEP5_FP8KV == 1 ]]; then
  : "${FP8KV_BLOCKS:?Set FP8KV_BLOCKS for the selected FP8 profile}"
  [[ $FP8KV_BLOCKS =~ ^[1-9][0-9]*$ ]] || { echo "FP8KV_BLOCKS must be a positive integer" >&2; exit 2; }
  [[ $KV_DTYPE == fp8_e4m3 && $STEP5_DENSE == 1 ]] || {
    echo "STEP5_FP8KV=1 requires KV_DTYPE=fp8_e4m3 and STEP5_DENSE=1" >&2; exit 2
  }
  [[ -d $FP8KV_BUNDLE/overlay/step5_fp8kv && -f $FP8KV_BUNDLE/overlay.sha256 ]] || {
    echo "FP8 KV overlay bundle is missing under $FP8KV_BUNDLE" >&2; exit 2
  }
  if command -v sha256sum >/dev/null 2>&1; then
    (cd -- "$FP8KV_BUNDLE" && sha256sum -c overlay.sha256)
  else
    (cd -- "$FP8KV_BUNDLE" && shasum -a 256 -c overlay.sha256)
  fi
  export STEP5_FP8KV=1
  export PYTHONPATH="$FP8KV_BUNDLE/overlay${PYTHONPATH:+:$PYTHONPATH}"
  FP8KV_VLLM_ARGS=(--block-size 16 --num-gpu-blocks-override "$FP8KV_BLOCKS")
else
  export STEP5_FP8KV=0
fi

export VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS

HEAD_ARGS=()
[[ $NODE_RANK == 0 ]] || HEAD_ARGS=(--headless)

DENSE_ARGS=()
[[ $STEP5_DENSE != 1 ]] || DENSE_ARGS=(--hf-overrides '{"text_config":{"sparse_config":{"enabled":false}}}')

LM_ARGS=()
[[ $LMONLY != 1 ]] || LM_ARGS=(--language-model-only)

SPEC_ARGS=()
if (( SPEC_TOKENS > 0 )); then
  SPEC_ARGS=(--spec-method mtp --spec-tokens "$SPEC_TOKENS")
fi

exec "${VLLM_BIN:-vllm}" serve "$MODEL_DIR" \
  ${HEAD_ARGS[@]+"${HEAD_ARGS[@]}"} \
  --served-model-name step5 \
  --host 0.0.0.0 \
  --port "$API_PORT" \
  --tensor-parallel-size 4 \
  --nnodes 4 \
  --node-rank "$NODE_RANK" \
  --master-addr "$NODE0" \
  --master-port "$MASTER_PORT" \
  --distributed-executor-backend mp \
  --disable-custom-all-reduce \
  --max-model-len "$MAXLEN" \
  --max-num-batched-tokens "$BATCH_TOKENS" \
  --max-num-seqs "$MAXSEQ" \
  --gpu-memory-utilization "$GMU" \
  --enable-prefix-caching \
  --kv-cache-dtype "$KV_DTYPE" \
  --trust-remote-code \
  ${SPEC_ARGS[@]+"${SPEC_ARGS[@]}"} \
  --reasoning-parser step5 \
  --enable-auto-tool-choice \
  --tool-call-parser step5 \
  ${DENSE_ARGS[@]+"${DENSE_ARGS[@]}"} \
  ${LM_ARGS[@]+"${LM_ARGS[@]}"} \
  ${FP8KV_VLLM_ARGS[@]+"${FP8KV_VLLM_ARGS[@]}"} \
  "$@"

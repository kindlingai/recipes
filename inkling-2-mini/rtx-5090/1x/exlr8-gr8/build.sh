#!/usr/bin/env bash
# Build gr8 (g6m4_ink2 TP=1 for sm_120a / RTX 5090 + g6front-rs) on x86_64 Linux with CUDA 13.
# Requirements: CUDA 13 toolkit (nvcc with sm_120a), g++ (C++20), libibverbs-dev, cmake, clang, libclang-dev, rust/cargo.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="${ENGINE_DIR:-$HERE/gr8}"
OUT_DIR="${OUT_DIR:-$HERE/bin}"
ENGINE_REPO="${ENGINE_REPO:-https://github.com/kindlingai/gr8.git}"
ENGINE_COMMIT="${ENGINE_COMMIT:-6b8748038bc74cd746c2f83075b0fbb6ba5aa99e}"
JOBS="${JOBS:-$(nproc)}"

for cuda_bin in /usr/local/cuda/bin /usr/local/cuda-13.1/bin /usr/local/cuda-13.0/bin; do
  if [ -x "$cuda_bin/nvcc" ]; then
    export PATH="$cuda_bin:$PATH"
    break
  fi
done
[ -d "$HOME/.cargo/bin" ] && export PATH="$HOME/.cargo/bin:$PATH"

command -v nvcc >/dev/null 2>&1 || { echo "nvcc (CUDA 13+) not found in PATH" >&2; exit 1; }
command -v cargo >/dev/null 2>&1 || { echo "cargo (Rust toolchain) not found in PATH" >&2; exit 1; }

if [ ! -d "$ENGINE_DIR/.git" ]; then
  echo "Cloning $ENGINE_REPO at pinned commit ${ENGINE_COMMIT:0:8} into $ENGINE_DIR..."
  git clone --no-checkout "$ENGINE_REPO" "$ENGINE_DIR"
  git -C "$ENGINE_DIR" checkout --detach "$ENGINE_COMMIT"
else
  echo "Using existing gr8 checkout at $ENGINE_DIR ($(git -C "$ENGINE_DIR" rev-parse --short HEAD))"
fi

mkdir -p "$OUT_DIR"

echo "Building g6m4_ink2 for sm_120a (TP=1, JOBS=$JOBS)..."
(
  cd "$ENGINE_DIR"
  ARCH=120a GR8_WIDTHS=1 MODEL=ink2 JOBS="$JOBS" bash scripts/build.sh "$OUT_DIR"
)

echo "Building g6front-rs..."
(
  cd "$ENGINE_DIR/frontend/g6front-rs"
  cargo build --release --locked
  cp target/release/g6front-rs "$OUT_DIR/g6front-rs"
)

echo "Built binaries in $OUT_DIR:"
ls -lh "$OUT_DIR/g6m4_ink2" "$OUT_DIR/g6front-rs"

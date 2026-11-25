# For agents: boot Qwen3.8-Flash-Next EXLR8 on one Blackwell GPU

You are booting this recipe for someone. Follow the steps in order and stop if a check fails.

## 1. Check the box

- 1× NVIDIA Blackwell GPU (`sm_120a` such as RTX 5090 / RTX PRO 6000, or `sm_121a` GB10): check `nvidia-smi`.
- At least 96–128 GB host RAM (`free -h`) and ~165 GB free on local NVMe (`df -h`).
- CUDA 13 (`nvcc --version`), `g++`, `cargo`, and `python3` are installed.

## 2. Build `gr8`

Clone `https://github.com/kindlingai/gr8` and build TP=1 Qwen 3.8 + `g6front-rs`:

```bash
MODEL=qw38 GR8_NR=1 ARCH=120a GR8_TESTS=0 scripts/build.sh bin
cargo build --release --locked --manifest-path frontend/g6front-rs/Cargo.toml
```

## 3. Download K3 (`bit300`) weights

Download `kindlingai/Qwen3.8-Flash-Next-exlr8` excluding `k2` and `k4` expert shards so only `bit300` (K3) is fetched.

## 4. Configure and start

Copy `.env.example` to `.env`, set `GR8_DIR` and `MODEL_DIR`, and run `./serve.sh`.

## 5. Check

- `curl -s http://127.0.0.1:8100/v1/models` returns `qwen3.8-flash-next`.
- A short `/v1/chat/completions` request returns coherent text with HTTP 200.

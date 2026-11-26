# For agents: boot Inkling-2-Mini on one RTX 5090 (32 GB)

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and tell
the person what failed. This recipe is the folder `inkling-2-mini/rtx-5090/1x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes) (also published standalone at
[kindlingai/inkling-2-mini-exlr8-rtx5090](https://github.com/kindlingai/inkling-2-mini-exlr8-rtx5090)).

## 1. Check the box

- 1× NVIDIA Blackwell GPU with 32 GB VRAM (`sm_120a`, e.g. RTX 5090): check `nvidia-smi`.
  - On a dedicated 32 GB GPU (~30 GiB available), the defaults fit with ~2 GiB free (`bit325`: `65536 × 4` = 262K KV pool).
  - If other GPU services occupy VRAM (e.g. ~7 GiB), lower `CAP` in `.env` (for example `CAP=16384`, `SESSIONS=4`, `PREFILL=256`).
- Local NVMe disk: at least 35 GB free for `kindlingai/inkling-2-mini-exlr8-k2-k3-k4` (`~31 GB` on disk).
- Build toolchain: CUDA 13 (`nvcc --version` with `sm_120a`), `g++` (C++20), `cmake`, `clang`, `libclang-dev`, `libibverbs-dev`, Rust 1.85+ (`cargo --version`), and `python3`.

## 2. Build `gr8` (pinned commit)

Run `./build.sh`. It clones `kindlingai/gr8` at the pinned commit (`6b8748038bc74cd746c2f83075b0fbb6ba5aa99e`), compiles `g6m4_ink2` for `ARCH=120a GR8_WIDTHS=1 MODEL=ink2`, and compiles `g6front-rs` into `./bin/`.

## 3. Download weights & write `.env`

```bash
hf download kindlingai/inkling-2-mini-exlr8-k2-k3-k4 \
  --local-dir ./models/inkling-2-mini-exlr8-k2-k3-k4
cp .env.example .env
```

Default is `VARIANT=bit325` (`65536 × 4` = 262K KV pool, `MTP=7` DFlash auto-discovered). Ask the person before switching to `VARIANT=k4` (higher quality / graduate-level science, `49152 × 4` = 196K KV pool), `./serve.sh bit225-fast` (fast 2.25-bit tier, `81920 × 4` = 327K KV pool), or `./serve.sh long` (single-stream long context up to `303K` on `bit325` / `385K` on `bit225`).

## 4. Boot & check

Run `./serve.sh`. Boot from local NVMe takes ~4–5 s.

- `curl -s http://127.0.0.1:8100/v1/models` returns `200` and lists `inkling-2-mini`.
- Run one short `/v1/chat/completions` request and verify a coherent reply.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, GPU, and `gr8` commit.
- `README.md` and `kindling.json` must agree; redraw `docs/card.png` from a `gr8` checkout via `python3 bench/gif.py card kindling.json --out docs/card.png`.
- From the `kindlingai/recipes` root, run `python3 tools/check_pin.py --strict inkling-2-mini/rtx-5090/1x/exlr8-gr8` and `python3 tools/build_index.py --check` before committing.

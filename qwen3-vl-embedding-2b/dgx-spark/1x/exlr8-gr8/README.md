# Qwen3-VL-Embedding-2B exlr8 K4 on 1× DGX Spark (GB10)

![Qwen3-VL-Embedding-2B exlr8 K4 on one DGX Spark](docs/card.png)

If you are an agent booting this for someone, read [AGENTS.md](AGENTS.md) first, then the Quickstart.

Qwen3-VL-Embedding-2B on **one DGX Spark** (GB10, 128 GB) at `TP=1`, served natively by [gr8](https://github.com/kindlingai/gr8) (`g6embed` + `g6front-rs`) from [kindlingai/Qwen3-VL-Embedding-2B-exlr8-k4](https://huggingface.co/kindlingai/Qwen3-VL-Embedding-2B-exlr8-k4): calibrated 4-bit trellis quantization (`1.33 GB` on disk, `2.61 GiB` GPU peak — `4.41×` smaller than BF16 vLLM) with full multimodal text + image DeepStack vision, last-token pooling, and Matryoshka dimensions (`64..2048`) on OpenAI-compatible `/v1/embeddings`. This recipe is the published `gr8` image and one `.env` file. Nothing is compiled.

## Results

**2B exlr8 K4 (`TP=1`):** **10.6 ms** instructed query p50 (**10.4 ms** raw text, **15.5 ms** 32-item multimodal suite p50 — `3.90×`–`5.08×` faster than BF16 vLLM) · **14,568 tok/s** at 8 concurrent streams (**14,188 tok/s** at 16 streams, **4,782 tok/s** single-item `batch_1`) · **-0.0030** mean 15-task Δ vs BF16 (**0.9906** text / **0.9776** image held-out cosine) · **2.61 GiB** GPU peak · **1.45 s** cold boot.

Measured 2026-11-26 on one NVIDIA DGX Spark (GB10, 128 GB unified LPDDR5X, ARM64 64 KiB page kernel, 2200 MHz SM clock cap) running `gr8` (`g6embed` + `g6front-rs`, `CAP=16384`, `MAX_MODEL_LEN=16384`, full 54-file XXH64 checksum verification enabled). Throughput is in tokens per second (tok/s).

### Throughput & latency (`/v1/embeddings`)

| Workload | Requests | Median latency | Items/s | Throughput (tok/s) |
|---|---:|---:|---:|---:|
| Text `batch_1` (52 tok) | 1 | **10.9 ms** | **92.0** | **4,782** |
| Concurrent HTTP (`1` client, 52 tok) | 1 | **12.5 ms** | 80.1 | **4,167** |
| Concurrent HTTP (`8` clients, 2,800 tok) | 8 | **192.2 ms** | 41.6 | **14,568** |
| Concurrent HTTP (`16` clients, 3,327 tok) | 16 | **234.5 ms** | 68.2 | **14,188** |

### Multimodal latency breakdown (32-item suite vs BF16 vLLM)

| Modality | BF16 vLLM p50 | 2B exlr8 K4 (`gr8`) p50 | Speedup |
|---|---:|---:|---:|
| Unprefixed raw text | 52.84 ms | **10.40 ms** (p95 `13.80 ms`) | **5.08×** |
| Instructed query | 53.53 ms | **10.59 ms** (p95 `13.70 ms`) | **5.05×** |
| Instructed document | 56.79 ms | **15.60 ms** (2,371-tok doc `165.57 ms`) | **3.64×** |
| Overall 32-item suite | 60.54 ms | **15.51 ms** (`min 9.30 ms`) | **3.90×** |
| Image-only (`64×64` / `256×256` / `1024×512` / `2048×1536`) | 59.0 / 78.7 / 171.5 / 365.4 ms | **13.1 / 29.0 / 115.2 / 324.7 ms** | **1.13×–4.49×** |

### Quality & footprint

| Check | Result |
|---|---|
| 15-task eval (BEIR, XPQA, CSN, STS-B, ViDoRe) | **-0.0030** mean Δ vs BF16 · **89.1%** mean Top-10 overlap |
| 660-row held-out cosine (`d2048`) | **0.9880** all (`0.9906` text · `0.9776` image · `0.9797` image+text) · `86.8%` Top-10 neighbour overlap |
| Live serving parity vs BF16 vLLM | **0.9911** text / **0.9848** image+text · exact `6/6` query-doc Top-1 · MRL `d1536` cos `1.0000` |
| Weight size on disk | **1.33 GB** (`1.24 GiB`, `3.21×` smaller than `4.26 GB` BF16) |
| GPU memory peak (`nvidia-smi`) | **2.61 GiB** (`1,173 MiB` weights + `1,154 MiB` workspace; `4.41×` smaller than `11.50 GiB` BF16 vLLM) |
| Cold boot → `/health` | **1.45 s** (`0.55 s` engine load w/ full checksums; `27.6×`–`121×` faster than vLLM) |

[kindling.json](kindling.json) holds these numbers in machine-readable form; [docs/card.png](docs/card.png) is drawn from it.

## Quickstart

```bash
npx @kindlingai/recipe qwen3-vl-embedding-2b-exlr8-1x-spark && cd qwen3-vl-embedding-2b-exlr8-1x-spark
# the CLI already copied .env.example to .env; edit it if you need to
docker compose up -d       # pulls the pinned gr8 image; first boot fetches 1.33 GB
docker compose logs -f     # ready at "serving: http://127.0.0.1:8100/v1" (~1.5 s once cached)
```

Once serving, run the built-in 5-part smoke check and query `/v1/embeddings`:

```bash
docker compose exec gr8 /opt/gr8/gr8 embed smoke
curl -s localhost:8100/v1/models
curl -s localhost:8100/v1/embeddings -H 'Content-Type: application/json' -d '{
  "model": "qwen3-vl-embedding-2b",
  "input": ["A dog running in a sunny park.", "TCP congestion control window size."],
  "dimensions": 1024
}'
```

Stop the server cleanly with:

```bash
docker compose exec gr8 /opt/gr8/gr8 embed down
docker compose down
```

## What you need

- One DGX Spark or other GB10 box (128 GB unified memory); only ~2.6 GiB GPU memory is used, so it coexists effortlessly alongside large LLM serving workloads.
- Docker with the NVIDIA container toolkit (DGX OS has both).
- **Disk:** about **2 GB** free for the cached `exlr8 K4` release (`1.33 GB`) and logs.
- Internet access to `huggingface.co` on the first boot (cached locally for offline restarts thereafter).

## Settings

`cp .env.example .env` (the CLI already did). Every knob is documented in [.env.example](.env.example); the active lines match the measured Results above.

| knob | default | what it does |
|---|---|---|
| `GR8_MODEL` | `embed` | Selects `g6embed` (TP=1 dense multimodal embedding engine) |
| `MODEL` | pinned HF URL | Hugging Face repo `@commit` (or a local release directory) |
| `PORT` | `8100` | OpenAI-compatible HTTP API port (`/v1/embeddings`, `/v1/models`, `/health`) |
| `CAP` / `MAX_MODEL_LEN` | `16384` / `16384` | Max batched tokens per forward pass and max input sequence length |
| `NOHASH` | `0` | Set `1` to skip load-time XXH64 checksum verification (default `0`: full verification) |
| `EXTRA_ARGS` | unset | Extra `g6embed` flags (e.g. `--weight-mode bf16`) |
| `GR8_CACHE` / `GR8_HOME` | named volumes | Optional host directories (owned by uid 1000) for model cache and logs/state |
| `GR8_STOP_GRACE` / `GR8_IMAGE` | unset | Optional container stop grace or image override |

## Multimodal & Matryoshka usage

- **Matryoshka Representation Learning (MRL):** pass `"dimensions": 256|512|1024|2048` (any `1..2048`) to truncate and re-normalize embeddings on GPU with zero extra compute; pass `"encoding_format": "base64"` for compact little-endian FP32 output.
- **Multimodal images (`messages`):** pass OpenAI/vLLM-style `messages` with `image_url` data URIs (`min_pixels=4096`, `max_pixels=1310720`, `4..1,280` merged visual tokens per image). Pass `"add_generation_prompt": true` to match the official `chat_template.jinja` convention or `false` to match vLLM's default; pre-formatted strings passed via `"input"` are unaffected.

## Other sizes

- **Higher quality (8B, `4.66 GB` on disk, `6.73 GiB` GPU peak, `-0.0010` 15-task Δ, `0.9942` text cosine):** [qwen3-vl-embedding-8b-exlr8-1x-spark](../../../../qwen3-vl-embedding-8b/dgx-spark/1x/exlr8-gr8)

## Help

Ask on Discord (https://discord.gg/8EAvYPV2rE) or open an issue in the recipes repo
(https://github.com/kindlingai/recipes/issues) with `qwen3-vl-embedding-2b-exlr8-1x-spark` in the title. Say which step failed and include the end of `docker compose logs` before you remove the container. Remove addresses and hostnames before you post.

## Engine pin

This recipe has no engine code. It runs one published `gr8` image, named in [compose.yaml](compose.yaml) and in the `engine` field of [kindling.json](kindling.json):

| | |
|---|---|
| engine | [kindlingai/gr8](https://github.com/kindlingai/gr8) `v1.5.0` ([`dd253a4f12a5f6eb46dd6229c5bbba839f5e981c`](https://github.com/kindlingai/gr8/commit/dd253a4f12a5f6eb46dd6229c5bbba839f5e981c)) |
| image | `ghcr.io/kindlingai/gr8:v1.5.0` |
| digest | `sha256:6d40ab08ad3de8c51571b6ab55ea20df5865e7e2adee0c3be259b5b814f50c16` |
| weights | [kindlingai/Qwen3-VL-Embedding-2B-exlr8-k4](https://huggingface.co/kindlingai/Qwen3-VL-Embedding-2B-exlr8-k4/commit/7f98ec7913b7bd4844b8e7da8015f1a77a13ba1f) (`7f98ec79`) |

`python3 tools/check_pin.py --strict qwen3-vl-embedding-2b/dgx-spark/1x/exlr8-gr8`, run from the monorepo root, verifies that `compose.yaml` and `kindling.json` agree on the immutable image digest.

## License

MIT, see [LICENSE](../../../../LICENSE). The Qwen3-VL-Embedding-2B weights are licensed under Apache-2.0 (see the model page).

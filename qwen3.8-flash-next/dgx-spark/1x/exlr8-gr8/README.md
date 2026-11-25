# KindlingAI: Qwen3.8-Flash-Next EXLR8 on one DGX Spark (K3 & K4)

If you are an agent booting this for someone, read [AGENTS.md](AGENTS.md) first, then the Quickstart.

_**Join our discord to learn more about KindlingAI and `gr8`: https://discord.gg/8EAvYPV2rE**_

Qwen3.8-Flash-Next on **one DGX Spark** (GB10, 128 GB) at `TP=1`, served by [gr8](https://github.com/kindlingai/gr8) `v1.2.0` from
[kindlingai/Qwen3.8-Flash-Next-exlr8](https://huggingface.co/kindlingai/Qwen3.8-Flash-Next-exlr8/tree/4943478fdd54d8a59f2f9824b2389799e79f564b) (`v0.2`):
both **`bit300` (K3, 3.00 bpw)** and **`bit400` (K4, 4.00 bpw)** fit on a single 128 GB box with **8 dedicated 139,200-token** chats (`1,114,112` total KV rows), Layer-48 `MTP=3` speculative decoding, Blackwell MXFP8 dense kernels, async `O_DIRECT` NVMe streaming for the 102.4 GB Layer-1 PLE rowstore, and an opt-in BF16 vision tower (`GR8_QW38_VISION=1`).
This recipe is the published `gr8` image and one `.env` file. Nothing is compiled.

![Qwen3.8-Flash-Next K3 (bit300) on one DGX Spark: decode, prefill and concurrency](docs/card.png)

**K3 (`bit300`, default):** **83.0 tok/s** code · **61.5 tok/s** prose · **87.4 tok/s** structured · **88.8 tok/s** counting · **2,269 tok/s** 32K prefill · **155.2 tok/s** at 8 streams · 128K needle recall PASS · 16 s boot from local NVMe
**K4 (`bit400`, 1-line switch):** **78.4 tok/s** code · **55.1 tok/s** prose · **81.2 tok/s** structured · **82.0 tok/s** counting · **2,215 tok/s** 8K prefill · **140.6 tok/s** at 8 streams · near-lossless `0.0046` mean KL (`97.70%` top-1) · 18 s boot from local NVMe

## Results

One DGX Spark (GB10, 128 GB) with local NVMe release storage, `TP=1`, measured 2026-11-23 on the `gr8 v1.2.0` candidate ([PR #599](https://github.com/kindlingai/gr8/pull/599)) with `gr8`'s live S2 serving path and benchmark (`bench/bench.py`, `--runs 3`, `SESS=8`, `CAP=139,264`, `MAX_MODEL_LEN=139,200`, `MTP=3`, `GR8_QW38_PLE_CACHE_MIB=4096`), one fresh boot per manifest. GPU clocks were uncapped in the timed stages. Every speed is in tokens per second (tok/s).

### One request, short prompts (`MTP=3`, 78–87 prompt tokens, 3 runs each)

| manifest | code (95% CI) | prose (95% CI) | structured (95% CI) | counting (95% CI) | tok/step (code / prose) | ms/step | TTFT |
|---|---:|---:|---:|---:|---:|---:|---:|
| **`bit300` (K3, default)** | **83.0** (79.9–84.8) | **61.5** (60.8–62.3) | **87.4** (87.1–88.0) | **88.8** (88.2–89.2) | 3.72 / 2.69 | 43.9 ms | 157 ms |
| **`bit400` (K4)** | **78.4** (77.2–79.1) | **55.1** (53.7–56.6) | **81.2** (80.9–81.5) | **82.0** (81.9–82.0) | 3.76 / 2.59 | 47.0–47.5 ms | 182 ms |

*Optional `MTP=4` on `bit300`:* setting `MTP=4` in `.env` increases code/structured/counting speed to **89.5** code / **97.2** structured / **99.1** counting (`57.7` prose, `c1` `73.1` / `c2` `103.3` / `c4` `117.9` / `c8` `154.8`). `MTP=3` is the default for the best prose/code balance.

### Requests at once (`MTP=3`, mixed prompts, 80–87 tokens)

| manifest | metric | 1 stream | 2 streams | 4 streams | 8 streams |
|---|---|---:|---:|---:|---:|
| **`bit300` (K3, default)** | **total tok/s** | **72.6** | **102.1** | **121.7** | **155.2** |
| `bit300` | tok/s per request | 73.4 | 56.8 | 37.5 | 27.8 |
| `bit300` | first token, median (p90) | 0.17 s (0.17 s) | 0.63 s (0.63 s) | 1.16 s (1.83 s) | 2.51 s (5.06 s) |
| **`bit400` (K4)** | **total tok/s** | **65.5** | **93.9** | **106.7** | **140.6** |
| `bit400` | tok/s per request | 67.4 | 53.1 | 32.4 | 24.1 |
| `bit400` | first token, median (p90) | 0.19 s (0.19 s) | 0.70 s (0.70 s) | 1.28 s (1.99 s) | 2.80 s (5.73 s) |

### Prefill, cold salted prompts (`MTP=3`)

| manifest | 8K prompt (TTFT · decode after) | 32K prompt (TTFT · decode after) |
|---|---:|---:|
| **`bit300` (K3, default)** | **2,258 tok/s** (`3.64 s` · `63.5 tok/s`) | **2,269 tok/s** (`14.44 s` · `55.3 tok/s`) |
| **`bit400` (K4)** | **2,215 tok/s** (`3.71 s` · `55.7 tok/s`) | **2,200 tok/s** (`14.93 s` · `47.1 tok/s`) |

### Choosing K3 (`bit300`) vs K4 (`bit400`)

Both profiles run on one DGX Spark with the exact same `CAP=139,264` (`139,200` max context per chat, 8 slots). Switch by changing one line in `.env` (`VARIANT=bit300` or `VARIANT=bit400`).

| profile | routed bpw | experts on box | total disk (incl. PLE) | model-written KL (mean / median) | model-written top-1 | WikiText-2 PPL (BF16 ref `3.729`) |
|---|---:|---:|---:|---:|---:|---:|
| **`bit300` (K3, default)** | 3.00 | 45.4 GB | ~163 GB | **0.0124 / 0.00157** | 96.34% | 3.737 (+0.23%) |
| **`bit400` (K4)** | 4.00 | 60.5 GB | ~178 GB | **0.0046 / 0.00054** | 97.70% | 3.723 (-0.17%) |

![Qwen3.8-Flash-Next K4 (bit400) on one DGX Spark: decode, prefill and concurrency](docs/card-k4.png)

### How long each chat can be

Qwen3.8-Flash-Next has only 12 full-attention layers (with 2 KV heads, GQA-12; the other 36 layers are fixed-state Gated DeltaNet), so `gr8` gives each of the `SESS=8` concurrent session slots its own dedicated `139,264`-token KV slab (`1,114,112` total KV rows). Concurrent chats do not split each other's context limit:

| active chats | 1 | 2 | 4 | 8 |
|---|---:|---:|---:|---:|
| max tokens per chat (prompt + `max_tokens`) | 139,200 | 139,200 | 139,200 | 139,200 |

The 1-chat limit is measured (the served `max_model_len`, verified up to 131,572 tokens in the 128K needle check); the multi-chat values follow directly from the 8 dedicated per-slot KV slabs.

### Quality checks

Measured on the same 2026-11-23 boots:

| check | `bit300` (K3) | `bit400` (K4) |
|---|---|---|
| smoke test (`./gr8 qw38 smoke`) | 8 of 8 PASS | 8 of 8 PASS |
| fact hidden in a 128K prompt | found (`131,572` tokens) | — |
| count to 200, three times | 3 of 3 clean | — |
| suspect characters | 0 replies | 0 replies |
| `GR8_PTAB=0` vs `GR8_PTAB=2` parity | exact | exact (same path) |
| boot to serving from local NVMe | 16 s | 18 s |

[kindling.json](kindling.json) has both the K3 (`tp1-k3`) and K4 (`tp1-k4`) numbers in a form a program can read. Both cards above are drawn from it.

## Quickstart

First turn off proactive memory compaction on the Spark ([What you need](#what-you-need)). Then:

```bash
git clone https://github.com/kindlingai/qwen3.8-flash-next-exlr8-1x-spark && cd qwen3.8-flash-next-exlr8-1x-spark
cp .env.example .env
# Optional: edit .env to switch VARIANT=bit400 (K4), MTP=4, or add GR8_QW38_VISION=1 to EXTRA_ENV
docker compose up -d       # pulls the pinned gr8 image; the first boot fetches the model (~163 GB)
docker compose logs -f     # ready at "serving: http://127.0.0.1:8100/v1"
```

Once serving, verify the API:

```bash
docker compose exec gr8 /opt/gr8/gr8 qw38 smoke
curl -s localhost:8100/v1/models      # id: qwen3.8-flash-next, max_model_len: 139200
```

Send a chat completion request (the model name is `qwen3.8-flash-next`, alias `qw38`; Qwen XML tool calls and `<think>` reasoning work out of the box):

```bash
curl -s localhost:8100/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "qwen3.8-flash-next",
  "messages": [{"role": "user", "content": "Write a haiku about a small computer."}],
  "max_tokens": 2048
}'
```

Stop the server cleanly with:

```bash
docker compose exec gr8 /opt/gr8/gr8 qw38 down
docker compose down
```

### Multimodal vision (opt-in)

The pinned `v0.2` weights include the unquantized 27-layer BF16 vision tower (`dense/vision-bf16.safetensors`, `898 MB`). To enable OpenAI `image_url` inputs, add `GR8_QW38_VISION=1` to `EXTRA_ENV` in `.env`:

```bash
EXTRA_ENV="GR8_QW38_PLE_CACHE_MIB=4096 GR8_QW38_VISION=1"
```

Then restart (`docker compose up -d`) and verify with `docker compose exec -e GR8_QW38_VISION_SMOKE=1 gr8 /opt/gr8/gr8 qw38 smoke` (9/9 checks).

## What you need

- One DGX Spark or other GB10 box (128 GB unified memory), with no other model running on it.
- Docker with the NVIDIA container toolkit (DGX OS has both).
- **Local NVMe disk:** about **163 GB** free for `bit300` (`45.4 GB` experts + `15.1 GB` dense/vocab/MTP + `102.4 GB` Layer-1 PLE rowstore) or **178 GB** for `bit400` (`60.5 GB` experts), plus `0.9 GB` if enabling vision. Keep Docker's storage (or `GR8_CACHE`) on fast local NVMe — Layer-1 PLE streams per token over async `O_DIRECT` `pread` behind Layer 0 rather than consuming GPU memory.
- Proactive memory compaction off:
  `sudo sysctl -w vm.compaction_proactiveness=0` (`gr8`'s
  [DEPLOY.md](https://github.com/kindlingai/gr8/blob/main/docs/DEPLOY.md#before-you-start) has the permanent form).

`gr8`'s [Qwen3.8-Flash-Next page](https://github.com/kindlingai/gr8/blob/main/docs/QWEN38.md) explains the architecture and every `GR8_QW38_*` rollback knob, and [DEPLOY.md](https://github.com/kindlingai/gr8/blob/main/docs/DEPLOY.md) explains the launcher options.

## Other box counts

- **Two boxes (`TP=2`, full native 256K context/chat, up to 126.8 code / 89.2 prose / 254.5 at 8 streams):** [qwen3.8-flash-next-exlr8-2x-spark](https://github.com/kindlingai/qwen3.8-flash-next-exlr8-2x-spark)

## Help

Ask on Discord (https://discord.gg/8EAvYPV2rE) or open an issue in this repo
(https://github.com/kindlingai/qwen3.8-flash-next-exlr8-1x-spark/issues). Say which step failed, and include:

- the command you ran, and the end of `docker logs qw38-1x-spark`, before you remove the container;
- if it still runs, `docker exec qw38-1x-spark /opt/gr8/gr8 qw38 status`.

Remove addresses and hostnames before you post.

## Engine pin

This recipe has no engine code. It runs one published `gr8` image, named in [compose.yaml](compose.yaml) and in the `engine` field of [kindling.json](kindling.json):

| | |
|---|---|
| engine | [kindlingai/gr8](https://github.com/kindlingai/gr8) [`v1.2.0`](https://github.com/kindlingai/gr8/releases/tag/v1.2.0) *(commit pin pending `v1.2.0` tag)* |
| image | `ghcr.io/kindlingai/gr8:v1.2.0` |
| digest | *pending `v1.2.0` GHCR publish (will be pinned as `@sha256:<digest>` once released)* |

Benchmarks above were measured on 2026-11-23 on the `gr8 v1.2.0` candidate branch ([PR #599](https://github.com/kindlingai/gr8/pull/599)). `python3 check.py` checks that `compose.yaml` and `kindling.json` agree; CI runs it on every pull request and automatically enforces `check.py --strict` plus `docker manifest inspect` once the `v1.2.0` digest is pinned.

## License

MIT, see [LICENSE](LICENSE). Qwen3.8-Flash-Next has its own licence (`qwen-community-1.0`): see the
[model page](https://huggingface.co/kindlingai/Qwen3.8-Flash-Next-exlr8).

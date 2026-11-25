# KindlingAI: GLM-5.3 EXLR8 on three DGX Sparks (384K context, bit273)

If you are an agent booting this for someone, read [AGENTS.md](AGENTS.md) first, then the Quickstart.

_**Join our discord to learn more about KindlingAI and `gr8`: https://discord.gg/8EAvYPV2rE**_

Full GLM-5.3 on three DGX Sparks (GB10, 128 GB each) at TP=3, served by [gr8](https://github.com/kindlingai/gr8) `v1.1.1` from
the high-precision **`bit273`** width profile (`2.73 bpw`) of [kindlingai/glm-5.3-exlr8-k2-k3-k4](https://huggingface.co/kindlingai/glm-5.3-exlr8-k2-k3-k4/tree/3e388b45b26ca4558351d22994afcfc85b99af74) (v0.6):
a **393,216-token** int4 KV pool (`393,210` max context), zero-copy shared prefix pages, MTP=3 drafting with confidence stopping,
distributed `PF_OWN=2` prefill, up to 8 concurrent chats, and ~82 s boots from disk (no QO cache needed).
This recipe is the published gr8 image, pinned by digest, and one `.env` file. Nothing is compiled.

![GLM-5.3 on three DGX Sparks, 384K context: decode, prefill and concurrency](docs/card.png)

51.6 tok/s for one request writing code · 764 tok/s prefill on an 8K prompt (646 at 32K, 562 at 128K) · 8 requests at once, 106.5 tok/s in total (119.1 tok/s in fast mode) · 393,216-token KV pool (`bit273`, 2.73 bpw) · GSM8K-250 98.0% (245/250) · HumanEval-164 91.5% (150/164) · live-proven 12/12 clean from 119K to 359K single-session & 4×87K concurrent · 3.8+ GiB free memory per box after bench

## Results

Three DGX Sparks on a 200G switch, TP=3, `gr8 v1.1.1` (`a3f44a0`), this recipe's `.env` (`bit273` v0.6 experts, int4 KV `CAP=393,216`, `GR8_KV_SHARE_PAGES=1`, MTP=3 with confidence stopping, `PF_OWN=2`, default quality preset `MOE_UNION_CAP=48`), measured 2026-11-21 with gr8's own benchmark (`bench/bench.py`, default level), one fresh boot. GPU clocks were uncapped in the timed stages. Every speed is in tokens per second (tok/s).

One request, short prompts (46-54 tokens, up to 512 tokens out, 6 runs each):

| work | code | prose | structured | counting |
|---|---|---|---|---|
| tok/s, mean | 51.6 | 38.6 | 53.1 | 55.3 |
| lowest - highest run | 49.5 - 53.0 | 37.3 - 41.0 | 51.3 - 55.4 | 54.4 - 55.7 |
| 95% interval | 50.7 - 52.7 | 37.8 - 39.6 | 52.1 - 54.2 | 55.0 - 55.6 |

Prefill, cold prompt (one run each):

| prompt | first token | prefill tok/s | decode after it | first token, same prompt again (cached) |
|---|---|---|---|---|
| 8K tokens | 10.67 s | 764 | 37.5 tok/s | 0.14 s |
| 32K tokens | 50.78 s | 646 | 33.0 tok/s | 0.21 s |
| 128K tokens | 233.19 s | 562 | 30.7 tok/s | 0.62 s |

Requests at once (short mixed prompts, 48-55 tokens, up to 512 tokens out each):

| requests at once | 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| total tok/s (quality default, `MOE_UNION_CAP=48`) | 45.5 | 59.5 | 77.5 | 106.5 |
| tok/s per request (quality default) | 45.1 | 33.8 | 27.4 | 21.3 |
| first token, median | 0.35 s | 0.77 s | 1.50 s | 2.90 s |

### Speed and quality presets (`MOE_UNION_CAP`)

`gr8 v1.1.1` enables seven bit-exact decode and prefill kernels (`KL = 0.00000`), `DEC_BK_MAX=2048`, and a batch-budgeted MoE expert union cap (`MOE_UNION_CAP`):

| preset (`.env`) | code / prose decode | 4 streams total (per req) | 8 streams total (per req) | prefill 8K / 32K / 128K | lowest `MemAvailable` after bench |
|---|---:|---:|---:|---:|---:|
| **Quality (default, `MOE_UNION_CAP=48`)** | 51.6 / 38.6 tok/s | 77.5 (27.4) tok/s | 106.5 (21.3) tok/s | 764 / 646 / 562 tok/s | 3.80 GiB |
| **Fast (`MOE_UNION_CAP=32`)** | 51.2 / 38.5 tok/s | 85.7 (33.2) tok/s | 119.1 (25.1) tok/s | 772 / 646 / 564 tok/s | 3.87 GiB |
| **Uncapped exact (`MOE_UNION_CAP=0`)** | 51.0 / 38.5 tok/s | 68.7 (22.6) tok/s | 81.9 (14.1) tok/s | 771 / 646 / 565 tok/s | 3.74 GiB |

All three presets were measured on fresh boots on 2026-11-21 (`bench/bench.py` default level for Quality, `--quick` for Fast and Uncapped exact, 0 suspect characters across all three runs). Note: in the 8K prefill runs, 8–9 shared chat-template tokens hit the prefix cache (0.1% of the 8K prompt); 32K and 128K were 100% cold (0 cached tokens).

### Why `bit273` (`2.73 bpw`) is the default

The `bit273` profile upgrades the 8 busiest experts per MoE layer to K4 and promotes 10 additional layers' gate/up projections to K3 (`~84 GB` of experts per Spark), cutting held-out KL divergence by **17% mean / 21% median** compared to `bit260` while keeping the same 51.6 tok/s decode speed and **3.80+ GiB** free RAM per box at 384K context.

Want **512K context** (`524,288`-token KV pool, `5.3+ GiB` free RAM per box) instead? Change two lines in `.env` to `VARIANT=bit260` and `CAP=524288`.

### How long each chat can be

The int4 KV pool holds **393,216 tokens** (`2,389` physical pages of 64 tokens per rank), with `max_model_len` **393,210**. The first 32,768 tokens (`SHARE_LIMIT`) of each chat are stored on every box, and the rest is spread across the three boxes. Each active chat reserves its prompt plus `max_tokens`:

| active chats | 1 | 2 | 3 | 4 | 8 |
|---|---:|---:|---:|---:|---:|
| max tokens per chat, equal unshared split | 393,210 | 163,706 | 87,290 | 49,082 | 19,066 |

The 1-chat value is measured (the served `max_model_len`); the multi-chat values are computed from the 2,389-page pool assuming distinct prompts. With `GR8_KV_SHARE_PAGES=1` (on by default), identical system or repository prefixes are stored once across concurrent chats — allowing 4 concurrent sessions to run past **87K tokens each** (live-proven below).

### Quality checks & live long-context proofs

Measured back-to-back on the same `v1.1.1` quality-default boot on 2026-11-21:

| check | result |
|---|---|
| smoke test | 14 of 14 |
| GSM8K-250 (C=4, `MOE_UNION_CAP=48`) | 245 of 250 (98.0%) |
| HumanEval-164 (C=4, `MOE_UNION_CAP=48`) | 150 of 164 (91.5%) |
| fact hidden in a 131,069-token prompt | found |
| count to 200, three times | 3 of 3 clean |
| prompt cache | 419 of 420 cached |
| suspect characters | 0 replies |
| single-session long-context extraction (119K, 191K, 263K, 359K tokens) | 4 of 4 clean (0 anomalies) |
| concurrent multi-session (4 clients × 2 turns @ 82.5K → 87.6K tokens, shared 20K prefix, T=0.7) | 8 of 8 clean (0 anomalies) |
| longest context (`max_model_len`) | 393,210 tokens |
| boot to `/health` 200 from disk | 82 s (81–86 s across 3 fresh boots) |
| lowest `MemAvailable` recorded on any box | 4.38 GiB after boot · 3.80 GiB after bench · 3.73 GiB after GSM8K/HumanEval · 3.64 GiB after 359K & 4×87K stress |

### Why `int4` KV preserves quality while unlocking a 384K-token pool

`KV_FORMAT=int4` is **mixed-precision**, not naive blanket 4-bit quantization — `gr8` compresses each part of the KV cache differently depending on its sensitivity:

- **RoPE positional keys (64 dims) stay full BF16 (128 B/tok)** — positional geometry is never 4-bit quantized.
- **Sparse-attention indexer keys (128 dims) stay FP8 E4M3 (132 B/tok)** — top-K sparse token retrieval stays sharp across 359K+ prompts.
- **Only the 512-dim MLA latent is stored in 4-bit**, after an orthonormal **512-point Sylvester Hadamard rotation** (`H x`) with **per-32-dim FP16 scales** (`288 B` vs `528 B` in FP8). The rotation spreads channel outliers evenly across all 512 dims (+4–6 dB worst-case SQNR in layers 2–3), hitting **20.3 dB median SQNR at 416 B/row** while folding `H` into the decode weights (`KV4_FOLD=1`) for zero extra rotation cost.
- **Combined with context-parallel sharding & shared prefix pages:** Only the first 32,768 tokens (`SHARE_LIMIT`) are replicated per box (everything past that is sharded `1/3` across the 3 Sparks), and `GR8_KV_SHARE_PAGES=1` shares identical system/repo prefixes across concurrent chats with zero duplicate copies. Full math and study: [gr8 KV4.md](https://github.com/kindlingai/gr8/blob/main/docs/KV4.md).

[kindling.json](kindling.json) has these numbers in a form a program can read. The card above is drawn from it.

## Quickstart

On every box, first turn off proactive memory compaction and open TCP ports 7340 and 7341 between the boxes
([What you need](#what-you-need)). Then, on every box:

```bash
git clone https://github.com/kindlingai/glm-5.3-exlr8-3x-spark && cd glm-5.3-exlr8-3x-spark
cp .env.example .env
nano .env                  # PEERS: the three LAN addresses, head first. The same file on every box.
docker compose up -d       # pulls the pinned gr8 image; the first boot fetches this box's part of the model
docker compose logs -f     # this box's supervisor; ready when the cluster serves
```

Then, on the head (the first address in `PEERS`):

```bash
docker compose exec gr8 /opt/gr8/gr8 glm53 smoke
curl -s localhost:8100/v1/models      # max_model_len 393210
```

The head serves an OpenAI-compatible API on port 8100. Stop the cluster with
`docker compose exec gr8 /opt/gr8/gr8 glm53 down` on the head, then `docker compose down` on every box.

## What you need

- Three DGX Sparks or other GB10 boxes (128 GB unified memory), with nothing else holding much memory (3.8+ GiB free
  per box measured after benchmark at `CAP=393,216`).
- A RoCE v2 fabric between the ConnectX-7 ports: one 200G switch (`SHAPE=mesh`), or the three boxes direct-cabled in a
  triangle (`SHAPE=ring`, no switch needed; about 10% slower single-stream decode).
- A LAN between the boxes with TCP ports 7340 and 7341 open.
- Docker with the NVIDIA container toolkit (DGX OS has both).
- About 100 GB of disk a box for the model (`~84 GB` experts + `12.5 GB` dense/vocab). No QO cache is required for `PF_OWN=2`.
- Proactive memory compaction off on every box:
  `sudo sysctl -w vm.compaction_proactiveness=0` (gr8's
  [DEPLOY.md](https://github.com/kindlingai/gr8/blob/main/docs/DEPLOY.md#before-you-start) has the permanent form).

gr8's [GLM-5.3 page](https://github.com/kindlingai/gr8/blob/main/docs/GLM-5.3.md) explains how the engine works, and
[DEPLOY.md](https://github.com/kindlingai/gr8/blob/main/docs/DEPLOY.md) explains every setting.

## Other box counts

- **Four boxes (1M context, `bit325`, DFlash2):** [glm-5.3-exlr8-4x-spark](https://github.com/kindlingai/glm-5.3-exlr8-4x-spark)
- **Four boxes K4 (`bit387`, uncapped routing):** [glm-5.3-exlr8-k4-4x-spark](https://github.com/kindlingai/glm-5.3-exlr8-k4-4x-spark)
- **Five boxes (983K context, `bit325`):** [glm-5.3-exlr8-5x-spark](https://github.com/kindlingai/glm-5.3-exlr8-5x-spark)
- **Six boxes (1M context / 2.18M KV pool, `bit325`):** [glm-5.3-exlr8-6x-spark](https://github.com/kindlingai/glm-5.3-exlr8-6x-spark)

## Help

Ask on Discord (https://discord.gg/8EAvYPV2rE) or open an issue in this repo
(https://github.com/kindlingai/glm-5.3-exlr8-3x-spark/issues). Say which step failed, and include:

- the command you ran, and the end of `docker logs glm53-3x-spark`, before you remove the container;
- if it still runs, `docker exec glm53-3x-spark /opt/gr8/gr8 glm53 status`.

Remove addresses and hostnames before you post.

## Engine pin

This recipe has no engine code. It runs one published gr8 image, named by tag and digest in
[compose.yaml](compose.yaml) and in the `engine` field of [kindling.json](kindling.json):

| | |
|---|---|
| engine | [kindlingai/gr8](https://github.com/kindlingai/gr8) [`v1.1.1`](https://github.com/kindlingai/gr8/releases/tag/v1.1.1) at [`a3f44a0`](https://github.com/kindlingai/gr8/commit/a3f44a075854fc9af0ed56c6d43f7739705bc871) |
| image | `ghcr.io/kindlingai/gr8:v1.1.1` |
| digest | `sha256:fa5c9f66fbfa55d162782578b3262893b782e6365a76562bcab951b54acc6d96` |

`python3 check.py` checks that `compose.yaml` and `kindling.json` name the same image.

## License

MIT, see [LICENSE](LICENSE). GLM-5.3 has its own licence: see the
[model page](https://huggingface.co/kindlingai/glm-5.3-exlr8-k2-k3-k4).

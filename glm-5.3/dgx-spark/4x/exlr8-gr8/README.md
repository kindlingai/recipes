# KindlingAI: GLM-5.3 EXLR8 on four DGX Sparks (1M context)

![GLM-5.3 on four DGX Sparks: decode, prefill and concurrency](docs/card.png)

If you are an agent booting this for someone, read [AGENTS.md](AGENTS.md) first, then the Quickstart.

_**Join our discord to learn more about KindlingAI and `gr8`: https://discord.gg/8EAvYPV2rE**_

Full GLM-5.3 on four DGX Sparks (GB10, 128 GB each) at TP=4, served by [gr8](https://github.com/kindlingai/gr8) `v1.1.1` from
the `bit325` width profile of [kindlingai/glm-5.3-exlr8-k2-k3-k4](https://huggingface.co/kindlingai/glm-5.3-exlr8-k2-k3-k4/tree/3e388b45b26ca4558351d22994afcfc85b99af74) (v0.6):
a full **1,048,576-token** context window (1,130,496-token int4 KV pool), zero-copy shared prefix pages, DFlash2 + MTP=2 drafting,
and up to 8 concurrent chats. This recipe is the published gr8 image, pinned by digest, and one `.env` file. Nothing is compiled.

67.1 tok/s for one request writing code (74.6 tok/s in fast mode) · 1,638 tok/s prefill on a 32K prompt (1,579 tok/s at 128K, +8.5% vs v1.1.1) · 8 requests at once, 123.8 tok/s in total (149.1 tok/s in fast mode) · RealMark 1,356.8 Grade A (C=4 1,546.3, 16/16 all lanes, 99.2% cache hit) · full 1M context (`1,130,496`-token KV pool) · 5.46+ GiB free memory per box

## Results

Four DGX Sparks on a 200G switch, TP=4, `gr8 main` (`530312e6`), this recipe's `.env` (`bit325` v0.6 experts, int4 KV `CAP=1,130,496`, `MAX_MODEL_LEN=1,048,576`, `GR8_KV_SHARE_PAGES=1`, DFlash2 + MTP=2 drafter, default quality preset `MOE_UNION_CAP=48`), measured 2026-11-28 with gr8's own benchmark (`bench/bench.py`, default level) and Official RealMark C=1/2/4 on one fresh boot (73 s warm boot). GPU clocks were uncapped in the timed stages (`0%` throttle across all four boxes). Every speed is in tokens per second (tok/s).

One request, short prompts (46-54 tokens, up to 512 tokens out, 6 runs each):

| work | code | prose | structured | counting |
|---|---|---|---|---|
| tok/s, mean | 67.1 | 39.9 | 81.1 | 85.5 |
| lowest - highest run | 57.7 - 72.9 | 38.6 - 42.4 | 74.4 - 88.0 | 84.2 - 87.1 |
| 95% interval | 62.4 - 71.7 | 39.2 - 40.9 | 77.8 - 84.1 | 84.8 - 86.2 |

Prefill, cold prompt (one run each):

| prompt | first token | prefill tok/s | decode after it | first token, same prompt again (cached) |
|---|---|---|---|---|
| 8K tokens | 5.64 s | 1,448 | 37.3 tok/s | 0.15 s |
| 32K tokens | 20.02 s | 1,638 | 31.2 tok/s | 0.12 s |
| 128K tokens | 82.97 s | 1,579 | 31.7 tok/s | 0.30 s |

Requests at once (short mixed prompts, 48-55 tokens, up to 512 tokens out each):

| requests at once | 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| total tok/s (quality default, `MOE_UNION_CAP=48`) | 53.5 | 66.7 | 89.1 | 123.8 |
| tok/s per request (quality default) | 56.9 | 35.9 | 27.7 | 18.9 |
| first token, median | 0.34 s | 0.60 s | 1.18 s | 2.57 s |

### Official RealMark RIPAL (C=1 / C=2 / C=4)

Measured on the same boot (`--lanes 1 2 4 --probe`, Thinking OFF, server default temperature): **RIPAL Score 1,356.8 Grade A** (`99.23%` prefix cache hit across 11.19M prompt tokens, C=1 prefill floor `1,653 tok/s`, lowest `MemAvailable` `5.46 GiB`):

| lanes | RIPAL score | aggregate decode (per lane) | prefill (per lane) | active context | done | match |
|---|---:|---:|---:|---:|---:|---:|
| **C=1** | **1,179.8** | 38.9 (38.9) tok/s | 1,068 (1,068) tok/s | 97K (97K) | 16/16 | 97.7% (A) |
| **C=2** | **1,369.1** | 49.4 (24.7) tok/s | 755.8 (377.9) tok/s | 166K (83K) | 16/16 | 98.3% (A) |
| **C=4** | **1,546.3** | 61.5 (15.4) tok/s | 851.2 (212.8) tok/s | 305K (76K) | 16/16 | 97.7% (A) |

### Speed and quality presets (`MOE_UNION_CAP`)

`gr8` enables bit-exact decode, prefill, and DFlash2 kernels by default (`KL = 0.00000`), `DEC_BK_MAX=2048` (allowing a 1.13M-token int4 KV pool with over 5.4 GiB free RAM per box), and a batch-budgeted MoE expert union cap (`MOE_UNION_CAP`):

| preset (`.env`) | code decode | 4 streams total (per req) | 8 streams total (per req) | prefill 8K / 32K / 128K | GSM8K-250 (C=4) | HumanEval-164 (C=4) |
|---|---:|---:|---:|---:|---:|---:|
| **Quality (default, `MOE_UNION_CAP=48`)** | 67.1 tok/s | 89.1 (27.7) tok/s | 123.8 (18.9) tok/s | 1,448 / 1,638 / 1,579 tok/s | 246 / 250 (98.4%) | 156 / 164 (95.1%) |
| **Fast (`MOE_UNION_CAP=32`)** | 74.6 tok/s | 101.0 (33.9) tok/s | 149.1 (23.4) tok/s | 1,576 / 1,633 / 1,432 tok/s | 242 / 250 (96.8%) | 153 / 164 (93.3%) |
| **Uncapped exact (`MOE_UNION_CAP=0`)** | exact (`KL=0`) | — | — | — | 244 / 250 (97.6%) | 157 / 164 (95.7%) |

Fast mode (`MOE_UNION_CAP=32`), GSM8K-250, and HumanEval-164 were measured on the same 1M-context recipe on `gr8 v1.1.0` (`cdd1e09`, 2026-11-20). Note: in the 8K prefill run, 8–9 shared chat-template tokens hit the prefix cache (0.1% of the 8K prompt); 32K and 128K were 100% cold (0 cached tokens).

### How long each chat can be

The int4 KV pool holds **1,130,496 tokens** (`4,800` physical pages of 64 tokens per rank), with `MAX_MODEL_LEN=1,048,576` (full 1M context). The first 32,768 tokens (`SHARE_LIMIT`) of each chat are stored on every box, and the rest is spread across the four boxes. Each active chat reserves its prompt plus `max_tokens`:

| active chats | 1 | 2 | 3 | 4 | 8 |
|---|---:|---:|---:|---:|---:|
| max tokens per chat, equal split | 1,048,576 | 516,082 | 311,282 | 208,882 | 55,282 |

The 1-chat value is measured (the served `max_model_len`); the multi-chat values are computed from the 4,800-page pool.

### Live long-context & shared-prefix proofs

Measured back-to-back on the same `v1.1.0` quality-default boot on 2026-11-20 (unique passkey needles per chat, zero evictions):

| live concurrent workload | resident KV tokens | needle recall | turn-2 prefix cache hit | aggregate decode |
|---|---:|---:|---:|---:|
| **3 × 300K** independent chats | 898,902 | 3/3 (T1) & 3/3 (T2) | 99.9 - 100.0% | 26.2 tok/s (T2) |
| **4 × 153K** independent chats | 613,806 | 4/4 (T1) & 4/4 (T2) | 99.9% | 35.1 tok/s (T2) |
| **8 × 26K** shared prefix (`GR8_KV_SHARE_PAGES=1`) | 26K shared | 8/8 | 8/8 (26,080 / 26,101 tok) | 78.3 tok/s |

Checks on the 2026-11-28 `gr8 main` (`530312e6`) default boot:

| check | result |
|---|---|
| smoke test | 14 of 14 |
| fact hidden in a 130,876-token prompt | found |
| count to 200, three times | 3 of 3 clean |
| prompt cache | 423 of 424 cached |
| suspect characters | 0 replies |
| RealMark RIPAL (C=1/2/4) | 1,356.8 Grade A (16/16 all lanes, 99.23% prefix cache hit) |
| GSM8K-250 / HumanEval-164 (C=4, `MOE_UNION_CAP=48`) | 246 of 250 (98.4%) / 156 of 164 (95.1%) (v1.1.0) |
| longest context (`max_model_len`) | 1,048,576 tokens |
| warm boot to `/health` 200 | 73 s |
| lowest `MemAvailable` recorded on any box | 5.61 GiB during bench, 5.46 GiB during RealMark (6.84 - 7.44 GiB after boot) |

### Why `int4` KV preserves quality while unlocking a 1.13M-token pool

`KV_FORMAT=int4` is **mixed-precision**, not naive blanket 4-bit quantization — `gr8` compresses each part of the KV cache differently depending on its sensitivity:

- **RoPE positional keys (64 dims) stay full BF16 (128 B/tok)** — positional geometry is never 4-bit quantized, preserving accuracy past 1M context.
- **Sparse-attention indexer keys (128 dims) stay FP8 E4M3 (132 B/tok)** — top-K sparse token retrieval stays sharp at long context.
- **Only the 512-dim MLA latent is stored in 4-bit**, and only after an orthonormal **512-point Sylvester Hadamard rotation** (`H x`) with **per-32-dim FP16 scales** (`288 B` vs `528 B` in FP8). The rotation spreads channel outliers evenly across all 512 dims (+4–6 dB worst-case SQNR in layers 2–3), hitting **20.3 dB median SQNR at 416 B/row** (beating MXFP4's 18.6 dB and matching NVFP4's 20.4 dB in fewer bytes) while folding `H` into the decode weights (`KV4_FOLD=1`) for zero extra rotation cost.
- **Measured quality:** On full-vocabulary KL vs. BF16, INT4 adds just **+0.010 KL** over FP8 (~6.5% of weight quantization's own KL); head-to-head against FP8 on 4 boxes it hits **97.0%** top-1 agreement (`KL=0.0145`), `qeval` **73/75 vs 74/75** (`p=1.0`), **GSM8K-250 246/250 (98.4%)**, **HumanEval-164 156/164 (95.1%)**, and **100% needle recall** across the 3×300K, 4×153K, and 8×26K live concurrency proofs above.
- **Combined with context-parallel sharding & shared prefix pages:** Only the first 32,768 tokens (`SHARE_LIMIT`) are replicated per box (everything past that is sharded `1/4` across the 4 Sparks), and `GR8_KV_SHARE_PAGES=1` shares identical system/repo prefixes across concurrent chats with zero duplicate copies. Set `KV_FORMAT=fp8` in `.env` anytime to roll back to FP8 KV. Full math and study: [gr8 KV4.md](https://github.com/kindlingai/gr8/blob/main/docs/KV4.md).

[kindling.json](kindling.json) has these numbers in a form a program can read. The card above is drawn from it.

## Quickstart

On every box, first turn off proactive memory compaction and open TCP ports 7340 and 7341 between the boxes
([What you need](#what-you-need)). Then, on every box:

```bash
npx @kindlingai/recipe glm-5.3-exlr8-4x-spark && cd glm-5.3-exlr8-4x-spark
# the CLI already copied .env.example to .env; edit it:
nano .env                  # PEERS: the four LAN addresses, head first. The same file on every box.
docker compose up -d       # pulls the pinned gr8 image; the first boot fetches this box's part of the model
docker compose logs -f     # this box's supervisor; ready when the cluster serves
```

This recipe lives in [kindlingai/recipes](https://github.com/kindlingai/recipes/tree/main/glm-5.3/dgx-spark/4x/exlr8-gr8) at `glm-5.3/dgx-spark/4x/exlr8-gr8`; a [sparse clone](https://github.com/kindlingai/recipes#run-a-recipe) also works.

Then, on the head (the first address in `PEERS`):

```bash
docker compose exec gr8 /opt/gr8/gr8 glm53 smoke
curl -s localhost:8100/v1/models      # max_model_len 1048576
```

The head serves an OpenAI-compatible API on port 8100. Stop the cluster with
`docker compose exec gr8 /opt/gr8/gr8 glm53 down` on the head, then `docker compose down` on every box.

A box that ran the earlier form of this recipe (its own image) has its part of the model in the docker volume
`glm53-4x-cache`. To use that volume again, set `GR8_CACHE` in `.env` to its directory
(`docker volume inspect glm53-4x-cache --format '{{.Mountpoint}}'`). The cache is keyed by Hugging Face commit: the box
reads what the volume holds at the commits pinned in `.env`, and fetches the rest.

## What you need

- Four DGX Sparks or other GB10 boxes (128 GB unified memory), with nothing else holding much memory (5.4+ GiB free
  per box measured at `CAP=1,130,496`).
- A RoCE v2 fabric between the ConnectX-7 ports: one 200G switch, or the four boxes cabled in a ring (`SHAPE=ring`,
  about 10% slower single-stream decode).
- A LAN between the boxes with TCP ports 7340 and 7341 open.
- Docker with the NVIDIA container toolkit (DGX OS has both).
- About 90 GB of disk a box for the model, 200 GB for the SSD KV store as set in `.env.example`, and about 70 GiB
  more if you run `prepare` for the compact copies.
- Proactive memory compaction off on every box:
  `sudo sysctl -w vm.compaction_proactiveness=0` (gr8's
  [DEPLOY.md](https://github.com/kindlingai/gr8/blob/main/docs/DEPLOY.md#before-you-start) has the permanent form).

gr8's [GLM-5.3 page](https://github.com/kindlingai/gr8/blob/main/docs/GLM-5.3.md) explains how the engine works, and
[DEPLOY.md](https://github.com/kindlingai/gr8/blob/main/docs/DEPLOY.md) explains deployment options.

## Settings

`cp .env.example .env` (the CLI already did). Every knob is documented in [.env.example](.env.example); the active
lines are the exact settings the Results numbers were measured with.

| knob | default | what it does |
|---|---|---|
| `PEERS` | `192.0.2.1,...,192.0.2.4` | LAN addresses of the four boxes in rank order (head first) |
| `SHAPE` | unset (`mesh`) | Uncomment `SHAPE=ring` for direct-cabled ring without a switch |
| `DRAFTER` | `GLM-5.3-DFlash2` | Pinned DFlash2 drafter (TP=4 only; remove to draft with MTP only) |
| `KV_FORMAT` / `CAP` / `MAX_MODEL_LEN` / `SESS` | `int4` / `1130496` / `1048576` / `8` | Mixed-precision int4 KV pool with full 1M context across up to 8 concurrent chats |
| `MOE_UNION_CAP` | `48` | Decode speed/quality preset (`48` quality default, `32` fast, `0` uncapped exact) |
| `KV_STORE` / `GR8_STOP_GRACE` | `ssd:...,size=200G` / `150s` | Persistent SSD KV store with matching shutdown grace |
| `EXTRA_ENV` | shared pages + load caches | Enables `GR8_KV_SHARE_PAGES=1`, `GR8_GEN_CACHE`, `GR8_QUIT_FAST=1`, and compact TP=4 load cache |
| `GR8_CACHE` / `GR8_HOME` | named volumes | Optional host directories (owned by uid 1000) for the model cache and logs/state |
| `GR8_IMAGE` | pinned digest | Override the published `gr8` image from `compose.yaml` |

gr8's [SETTINGS.md](https://github.com/kindlingai/gr8/blob/main/docs/SETTINGS.md) explains every launcher option.

## Other sizes

The same image and the same `compose.yaml` serve GLM-5.3 on three, five or six boxes. For other box counts with tuned
settings and expanded context pools, use the dedicated recipes:

- **Three boxes (384K context, `bit273`):** [glm-5.3-exlr8-3x-spark](../../3x/exlr8-gr8)
- **Four boxes K4 (`bit387`, uncapped routing):** [glm-5.3-exlr8-k4-4x-spark](../../4x/exlr8-k4-gr8)
- **Five boxes (`v1.1.0`, 983K context):** [glm-5.3-exlr8-5x-spark](../../5x/exlr8-gr8) — measured 2026-11-20 on `gr8 v1.1.0`.
- **Six boxes (1M context / 2.18M KV pool):** [glm-5.3-exlr8-6x-spark](../../6x/exlr8-gr8) — measured 2026-11-28 on `gr8 main` (`530312e6`, RealMark 1,431.9 A).

| | TP=3 (2026-10-24) | TP=5 (`v1.1.0`, 2026-11-20) | TP=6 (`main`, 2026-11-28) |
|---|---|---|---|
| experts | `bit225`, 2.25 bpw | `bit325`, 3.25 bpw | `bit325`, 3.25 bpw |
| decode, code / prose | 41.1 / 31.7 tok/s | 68.9 / 50.8 tok/s | 78.8 / 57.6 tok/s |
| total, 2 / 4 / 8 requests at once | 50.6 / 63.8 / — tok/s | 81.1 / 104.2 / 141.5 tok/s | 86.7 / 119.5 / 157.8 tok/s |
| prefill, 8K / 32K / 128K prompt | 635 / — / — tok/s | 1,937 / 1,960 / 1,837 tok/s | 2,296 / 2,428 / 2,257 tok/s |
| KV pool (longest context) | 307,136 tokens | 983,040 tokens | 2,179,072 tokens (1M max) |

TP=3 row above is from 2026-10-24 ([RigMark](https://github.com/alexellis/rigmark) 1.0.0, fp8 KV, MTP drafting). TP=5 and TP=6 rows are from 2026-11-20 on `gr8 v1.1.0` (`MOE_UNION_CAP=48`; fast preset `MOE_UNION_CAP=32` reaches 119.6 / 160.5 tok/s at C=4 / C=8 on TP=5, and 128.2 / 180.2 tok/s at C=4 / C=8 on TP=6).

## Help

Ask on Discord (https://discord.gg/8EAvYPV2rE) or open an issue in
[kindlingai/recipes](https://github.com/kindlingai/recipes/issues) with `glm-5.3-exlr8-4x-spark` in the title. Say which step failed, and include:

- the command you ran, and the end of `docker logs glm53-4x-spark`, before you remove the container;
- if it still runs, `docker exec glm53-4x-spark /opt/gr8/gr8 glm53 status`.

Remove addresses and hostnames before you post.

## Engine pin

This recipe has no engine code. It runs one published gr8 image, named by tag and digest in
[compose.yaml](compose.yaml) and in the `engine` field of [kindling.json](kindling.json):

| | |
|---|---|
| engine | [kindlingai/gr8](https://github.com/kindlingai/gr8) [`v1.1.1`](https://github.com/kindlingai/gr8/releases/tag/v1.1.1) at [`a3f44a0`](https://github.com/kindlingai/gr8/commit/a3f44a075854fc9af0ed56c6d43f7739705bc871) |
| image | `ghcr.io/kindlingai/gr8:v1.1.1` |
| digest | `sha256:fa5c9f66fbfa55d162782578b3262893b782e6365a76562bcab951b54acc6d96` |

The TP=4 benchmark tables above were measured on 2026-11-20 on `gr8 v1.1.0` (`cdd1e09`); `v1.1.1` (`a3f44a0`) is a hotfix on top of `v1.1.0` fixing the 150K+ multi-session TP=4 CP staged index ordering bug (verified 24/24 clean across greedy and sampled multi-turn runs with no prefill regression).

After v1.0, the pin moves to a newer gr8 release only after this recipe was booted and measured on it.
`python3 tools/check_pin.py glm-5.3/dgx-spark/4x/exlr8-gr8`, run from the monorepo root, checks that `compose.yaml` and
`kindling.json` name the same image; CI (`.github/workflows/recipes.yml`) runs it on every pull request.

## License

MIT, see [LICENSE](../../../../LICENSE). GLM-5.3 and the DFlash2 drafter have their own licences: see the
[model page](https://huggingface.co/kindlingai/glm-5.3-exlr8-k2-k3-k4) and
[incoai/GLM-5.3-DFlash2](https://huggingface.co/incoai/GLM-5.3-DFlash2) (CC BY-NC-ND).

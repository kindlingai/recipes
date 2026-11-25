# KindlingAI: GLM-5.3 EXLR8 K4 on four DGX Sparks

If you are an agent booting this for someone, read [AGENTS.md](AGENTS.md) first, then the Quickstart.

_**Join our discord to learn more about KindlingAI and `gr8`: https://discord.gg/8EAvYPV2rE**_

Quality-first GLM-5.3 on four DGX Sparks (GB10, 128 GB each), served by [gr8](https://github.com/kindlingai/gr8) `v1.1.1` from the `bit387`
profile of [kindlingai/glm-5.3-exlr8-k2-k3-k4](https://huggingface.co/kindlingai/glm-5.3-exlr8-k2-k3-k4/tree/9e25c28a2e8808d8b2599d780521fd6af24e7558) (0.7): every
routed expert at 4 bits a weight except the first ten MoE layers (3-12) at 3, and the MTP layer at 3, the only width
the release stores for it. `bit387` is statistically identical to the all-K4 `bit400`: full-vocabulary KL against
BF16 of 0.0385 against 0.0381 on model-written text (1.5 standard errors apart), in 12 GB less (89 against 92 GB of
experts per box). The recipe carries a copy of the release's manifest (`manifests/exlr8-manifest-bit387.json`), runs int4 KV, enables all eight bit-exact `gr8 v1.1.0` kernels (`KL = 0.00000`), and explicitly sets **`MOE_UNION_CAP=0`** so routed experts stay 100% uncapped.

![GLM-5.3 K4 on four GB10 boxes: decode, prefill and concurrency](docs/card.png)

60.8 tok/s for one request writing code · 1,570 tok/s prefill on a 32K prompt (1,434 tok/s at 128K) · 8 requests at once, 82.0 tok/s in total · 100% uncapped pure-quality routing (`MOE_UNION_CAP=0`, `KL=0.00000`) · a 442,368-token KV pool · a fact hidden in a 128K prompt found

## Results

Four DGX Sparks on a 200G switch, TP=4, `gr8 v1.1.0` (`cdd1e09`), `bit387` v0.7 experts (`9e25c28a`), int4 KV, DFlash2 + MTP drafter, `MOE_UNION_CAP=0` (uncapped), `DEC_BK=2048 DEC_BK_MAX=2048` (`.env.example`), measured 2026-11-20 with gr8's benchmark (`bench/bench.py`, default level), one fresh boot, GPU clocks uncapped in timed stages. Every speed is in tokens per second (tok/s).

One request, short prompts (46-54 tokens, up to 512 tokens out, 6 runs each):

| work | code | prose | structured | counting |
|---|---|---|---|---|
| tok/s, mean | 60.8 | 36.2 | 72.9 | 76.5 |
| lowest - highest run | 54.5 - 66.2 | 33.5 - 37.7 | 67.3 - 78.7 | 75.5 - 77.0 |

Prefill, cold prompt (one run each):

| prompt | first token | prefill tok/s | decode after it | first token, same prompt again (cached) |
|---|---|---|---|---|
| 8K tokens | 5.34 s | 1,530 | 34.6 tok/s | 0.17 s |
| 32K tokens | 20.90 s | 1,570 | 31.0 tok/s | 0.47 s |
| 128K tokens | 91.44 s | 1,434 | 29.6 tok/s | 0.29 s |

Requests at once (short mixed prompts, 48-55 tokens, up to 512 tokens out each):

| requests at once | 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| total tok/s | 44.2 | 57.1 | 62.3 | 82.0 |
| tok/s per request | 47.1 | 31.1 | 20.4 | 13.0 |
| first token, median | 0.41 s | 0.79 s | 1.72 s | 3.37 s |

Checks on the same boot:

| check | result |
|---|---|
| smoke test | 14 of 14 |
| fact hidden in a 131,475-token prompt | found |
| count to 200, three times | 3 of 3 clean |
| prompt cache | 437 of 438 cached |
| suspect characters | 0 replies |
| quality / routing | `MOE_UNION_CAP=0` (uncapped), 8 bit-exact `v1.1.0` kernels (`KL = 0.00000`) |
| longest context (`max_model_len`) | 442,354 tokens |
| lowest `MemAvailable` recorded on any box | 3.78 GiB (4.32 - 4.72 GiB after boot) |

### Why `int4` KV preserves quality on a quality-first K4 recipe

Even on this quality-first `bit387` (`MOE_UNION_CAP=0`) recipe, `gr8` uses **mixed-precision** `KV_FORMAT=int4` rather than naive blanket 4-bit quantization — compressing each part of the KV cache differently depending on its sensitivity:

- **RoPE positional keys (64 dims) stay full BF16 (128 B/tok)** — positional geometry is never 4-bit quantized.
- **Sparse-attention indexer keys (128 dims) stay FP8 E4M3 (132 B/tok)** — top-K sparse token retrieval stays sharp at long context.
- **Only the 512-dim MLA latent is stored in 4-bit**, after an orthonormal **512-point Sylvester Hadamard rotation** (`H x`) with **per-32-dim FP16 scales** (`288 B` vs `528 B` in FP8). The rotation spreads channel outliers evenly across all 512 dims (+4–6 dB worst-case SQNR in layers 2–3), hitting **20.3 dB median SQNR at 416 B/row** (beating MXFP4 and matching NVFP4 in fewer bytes) while folding `H` directly into the decode weights (`KV4_FOLD=1`).
- **Measured quality:** On full-vocabulary KL vs. BF16, INT4 adds only **+0.010 KL** over FP8 (~6.5% of weight quantization's own KL, at the BF16 microbatch noise floor), with **97.0%** top-1 token agreement vs. FP8 (`KL=0.0145`) and `qeval` **73/75 vs 74/75** (`McNemar p=1.0`). Shrinking each KV page block from 3.50 MB to 2.29 MB lets K4 experts (~89 GB/box) coexist with a 442K-token KV pool and 4.3+ GiB free RAM per box. Set `KV_FORMAT=fp8` in `.env` if you want FP8 KV with a smaller pool. Full math and study: [gr8 KV4.md](https://github.com/kindlingai/gr8/blob/main/docs/KV4.md).

[kindling.json](kindling.json) has these numbers in a form a program can read. The card above is drawn from it.

## What you need

- Four DGX Sparks, or other GB10 boxes such as the ASUS GX10, joined by their ConnectX ports (a switch, or cables
  between the boxes).
- Docker and the NVIDIA container toolkit on each box (both come with DGX OS).
- About 110 GB free on each box for its part of the model.
- Proactive memory compaction off on each box, as root, once:

  ```bash
  echo 'vm.compaction_proactiveness = 0' > /etc/sysctl.d/90-gr8-no-proactive-compaction.conf
  sysctl -w vm.compaction_proactiveness=0
  ```

## Quickstart

On each of the four boxes:

```bash
npx @kindlingai/recipe glm-5.3-exlr8-k4-4x-spark && cd glm-5.3-exlr8-k4-4x-spark
# the CLI already copied .env.example to .env; edit it:
nano .env                   # fill in PEERS (and IPS, IPS2) unless the boxes run mentat; keep DRAFTER + DEC_BK=2048
docker compose up -d
```

The first boot fetches each box's part of the model from Hugging Face. Then the boxes find each other, and the head
(the first address in `PEERS`) serves the OpenAI API on port 8100:

```bash
docker compose logs -f                                  # ready when it says the cluster serves
docker compose exec gr8 /opt/gr8/gr8 glm53 smoke        # on the head
curl http://localhost:8100/v1/models                    # on the head
```

`docker compose up -d --build` builds the image on the box instead. For that, fetch the recipe with
`npx @kindlingai/recipe glm-5.3-exlr8-k4-4x-spark --engine`: it puts the gr8 source in `gr8/` at the commit
`kindling.json` pins (`engine.commit`); without it, compose only pulls the image.

This recipe lives in [kindlingai/recipes](https://github.com/kindlingai/recipes/tree/main/glm-5.3/dgx-spark/4x/exlr8-k4-gr8) at `glm-5.3/dgx-spark/4x/exlr8-k4-gr8`; a [sparse clone](https://github.com/kindlingai/recipes#run-a-recipe) also works.

Stop and update:

```bash
docker compose exec gr8 /opt/gr8/gr8 glm53 down         # on the head: stops every box
docker compose pull && docker compose up -d             # on every box
```

For a newer version of the recipe itself, `git pull` in a clone of kindlingai/recipes, or fetch the folder again with
the CLI and keep your `.env`.

## Knobs

- **`MOE_UNION_CAP=0` (set in `Dockerfile` and `.env.example`):** `gr8 v1.1.0` enables eight bit-exact decode, prefill, and DFlash2 kernels at TP=4 (`KL = 0.00000`) and defaults `MOE_UNION_CAP=48` for the standard 3.25-bpw recipe. This K4 recipe explicitly pins `MOE_UNION_CAP=0` so routed experts stay 100% uncapped and exact.
- **`DEC_BK=2048` and `DEC_BK_MAX=2048` (set in `.env.example`):** Captures three decode graph buckets (2K, 16K, cap) instead of 16K/32K/cap — bit-exact, leaving 4.3+ GiB `MemAvailable` per box after boot (`3.78 GiB` minimum during full benchmark).
- **`CAP=442368`, `SHARE_LIMIT=16384`, `S2_ADAPT=0` (`Dockerfile`):** One session up to 432K tokens (`442,354` `max_model_len`), or four sessions of ~74K tokens sharing the pool.
- **`PEERS`, `IPS`, `IPS2`:** The boxes' addresses (`.env.example`). Unset, the boxes find each other through mentat.
- **`DISPRAM=1`:** Lends each box's 2 GiB display carveout to the KV cache when Kindling OS runs `dispramd` (0 turns it off).

Every other option is gr8's launcher default, listed in
[gr8/KNOBS.md](https://github.com/kindlingai/gr8/blob/a3f44a075854fc9af0ed56c6d43f7739705bc871/KNOBS.md).

## Engine pin

| | |
|---|---|
| engine | [kindlingai/gr8](https://github.com/kindlingai/gr8) [`v1.1.1`](https://github.com/kindlingai/gr8/releases/tag/v1.1.1) at [`a3f44a0`](https://github.com/kindlingai/gr8/commit/a3f44a075854fc9af0ed56c6d43f7739705bc871) (`engine.commit` in `kindling.json`; `--engine` or `tools/engine.sh` puts it in `gr8/`) |
| prebuilt engine image | `ghcr.io/kindlingai/gr8:v1.1.1@sha256:fa5c9f66fbfa55d162782578b3262893b782e6365a76562bcab951b54acc6d96` |
| weights | [kindlingai/glm-5.3-exlr8-k2-k3-k4](https://huggingface.co/kindlingai/glm-5.3-exlr8-k2-k3-k4/tree/9e25c28a2e8808d8b2599d780521fd6af24e7558) (`9e25c28a`, `bit387`) |

`python3 tools/check_pin.py glm-5.3/dgx-spark/4x/exlr8-k4-gr8`, run from the monorepo root, checks that `kindling.json`,
`compose.yaml` and the `Dockerfile` agree. Bumping the engine means editing `engine.commit` (and `engine.ref`) in
`kindling.json`.

## Help

Questions and problems: the Discord above, or an issue on [gr8](https://github.com/kindlingai/gr8/issues).

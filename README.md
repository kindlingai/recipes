# Kindling recipes

Launch recipes for serving large models on DGX Spark (GB10) boxes and single GPUs: each one pins an engine, a
checkpoint and the settings we measured, with the numbers in its `kindling.json`. The tables below and the cards on
[kindlingai.dev](https://www.kindlingai.dev) are both generated from those files.

## Run a recipe

```bash
npx @kindlingai/recipe glm-5.3-exlr8-3x-spark    # writes ./glm-5.3-exlr8-3x-spark with only that recipe, .env ready to edit
npx @kindlingai/recipe --list                     # every recipe id
```

Then follow the recipe's own README (usually: edit `.env`, `docker compose up -d`). `--history` also brings the
recipe's git history (the folder's commits only); `npx @kindlingai/recipe --help` has the rest.

Without Node, a sparse clone fetches one folder:

```bash
git clone --filter=blob:none --sparse https://github.com/kindlingai/recipes && cd recipes
git sparse-checkout set glm-5.3/dgx-spark/3x/exlr8-gr8 && cd glm-5.3/dgx-spark/3x/exlr8-gr8
```

## Scoreboard

<!-- recipes:index:start -->
<!-- Written by tools/build_index.py from each recipe's kindling.json and models.json. Edits here are overwritten. -->

25 recipes across 11 models and 2 hardware targets. Default config per recipe, all speeds in tok/s: **C1 Decode** is single-session decode (code workload), **C4 Decode** is 4-session aggregate decode (per-stream in parentheses when measured, or closest measured concurrency), **Prefill** is cold prefill at 8K (other prompt length noted), and **Max context** is the longest request (tokens).

| Model | Size | Hardware | C1 Decode | C4 Decode | Prefill | Max context | Engine | Build | Recipe | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| [**DeepSeek-V4.1-Flash**](deepseek-v4.1-flash/dgx-spark/4x/exlr8-gr8) | 763B | 4× DGX Spark (GB10) | 137.5 | 202.9 (C8) | 7,720 (32K) | 327,670 | gr8 v1.3.1 | exlr8 native, fp8 KV, fast mode | [`deepseek-v4.1-flash-exlr8-4x-spark`](deepseek-v4.1-flash/dgx-spark/4x/exlr8-gr8) | stable |
| [**GLM-5.3**](glm-5.3/dgx-spark/2x/exlr8-gr8) | 744B | 2× DGX Spark (GB10) | 24.1 | 98.4 (24.6/s) | 323 (32K) | 131,072 | gr8 main@fa5d82d | exlr8 bit225, 4-bit MLA latent KV, INT4 DFlash + 48 GB SSD KV | [`glm-5.3-exlr8-2x-spark`](glm-5.3/dgx-spark/2x/exlr8-gr8) | stable |
| [**GLM-5.3**](glm-5.3/dgx-spark/3x/exlr8-gr8) | 744B | 3× DGX Spark (GB10) | 51.6 | 77.5 (27.4/s) | 764 | 393,210 | gr8 v1.1.1 | exlr8 bit273, int4 KV, 384K context | [`glm-5.3-exlr8-3x-spark`](glm-5.3/dgx-spark/3x/exlr8-gr8) | stable |
| [**GLM-5.3**](glm-5.3/dgx-spark/4x/exlr8-fp8kv-gr8) | 744B | 4× DGX Spark (GB10) | 67.5 | 75.3 (23.1/s) | 1,686 | 655,346 | gr8 v1.2.0 | exlr8 bit325, pure FP8 KV, 640K pool, uncapped exact MoE | [`glm-5.3-exlr8-fp8kv-4x-spark`](glm-5.3/dgx-spark/4x/exlr8-fp8kv-gr8) | stable |
| [**GLM-5.3**](glm-5.3/dgx-spark/4x/exlr8-gr8) | 744B | 4× DGX Spark (GB10) | 66.9 | 89.4 (27.9/s) | 1,534 | 1,048,576 | gr8 v1.1.1 | exlr8 bit325, int4 KV, 1M context, DFlash2 drafter | [`glm-5.3-exlr8-4x-spark`](glm-5.3/dgx-spark/4x/exlr8-gr8) | stable |
| [**GLM-5.3**](glm-5.3/dgx-spark/4x/exlr8-k4-gr8) | 744B | 4× DGX Spark (GB10) | 60.8 | 62.3 (20.4/s) | 1,530 | 442,354 | gr8 v1.1.1 | exlr8 bit387 (K4), int4 KV, pure quality | [`glm-5.3-exlr8-k4-4x-spark`](glm-5.3/dgx-spark/4x/exlr8-k4-gr8) | stable |
| [**GLM-5.3**](glm-5.3/dgx-spark/5x/exlr8-gr8) | 744B | 5× DGX Spark (GB10) | 68.9 | 104.2 (36.6/s) | 1,937 | 983,034 | gr8 v1.1.1 | exlr8 bit325, int4 KV, 983K context | [`glm-5.3-exlr8-5x-spark`](glm-5.3/dgx-spark/5x/exlr8-gr8) | stable |
| [**GLM-5.3**](glm-5.3/dgx-spark/6x/exlr8-fp8kv-gr8) | 744B | 6× DGX Spark (GB10) | 78 | 101.3 (31.9/s) | 2,016 | 1,048,576 | gr8 v1.2.0 | exlr8 bit325, pure FP8 KV, 1.51M pool (1M ctx), uncapped exact MoE | [`glm-5.3-exlr8-fp8kv-6x-spark`](glm-5.3/dgx-spark/6x/exlr8-fp8kv-gr8) | stable |
| [**GLM-5.3**](glm-5.3/dgx-spark/6x/exlr8-gr8) | 744B | 6× DGX Spark (GB10) | 78 | 117.4 (41.6/s) | 2,467 | 1,048,576 | gr8 v1.1.1 | exlr8 bit325, int4 KV, 1M context (2.18M pool) | [`glm-5.3-exlr8-6x-spark`](glm-5.3/dgx-spark/6x/exlr8-gr8) | stable |
| [**GLM-5.3-Flash**](glm-5.3-flash/dgx-spark/1x/exlr8-gr8) | 320B-A18B | 1× DGX Spark (GB10) | 53.8 | 53.4 | 995 | 262,144 | gr8 v1.2.0 | exlr8 bit201, int4 KV | [`glm-5.3-flash-exlr8-1x-spark`](glm-5.3-flash/dgx-spark/1x/exlr8-gr8) | stable |
| [**GLM-5.3-Flash**](glm-5.3-flash/dgx-spark/2x/exlr8-gr8) | 320B-A18B | 2× DGX Spark (GB10) | 76.5 | 82.9 | 1,670 | 262,144 | gr8 v1.2.0 | exlr8 bit349, int4 KV | [`glm-5.3-flash-exlr8-2x-spark`](glm-5.3-flash/dgx-spark/2x/exlr8-gr8) | stable |
| [**GLM-5.3-Flash**](glm-5.3-flash/dgx-spark/4x/exlr8-vllm) | 320B-A18B | 4× DGX Spark (GB10) | 117.3 | 148 | 4,934 (32K) | 524,288 | vllm | NVFP4 | [`glm-5.3-flash-exlr8-gx10`](glm-5.3-flash/dgx-spark/4x/exlr8-vllm) | external |
| [**GLM-5.3-Flash**](glm-5.3-flash/dgx-spark/4x/nvfp4-vllm) | 320B-A18B | 4× DGX Spark (GB10) | 117.3 | 148 | 4,934 (32K) | 524,288 | vllm | NVFP4 | [`glm-5.3-flash-gx10`](glm-5.3-flash/dgx-spark/4x/nvfp4-vllm) | external |
| [**Inkling-2-Mini**](inkling-2-mini/dgx-spark/1x/exlr8-gr8) | 26.4B-A3.4B | 1× DGX Spark (GB10) | 90.6 | 160 (C6) | 3,484 | 147,456 | gr8 main@2c221e9 | exlr8, DFlash, 144K x 8 (1.18M KV) | [`inkling-2-mini-exlr8-1x-spark`](inkling-2-mini/dgx-spark/1x/exlr8-gr8) | stable |
| [**Inkling-2-Mini**](inkling-2-mini/rtx-5090/1x/exlr8-gr8) | 26.4B-A3.4B | 1× RTX 5090 | 328.1 | 777 (213.8/s) | 9,580 | 65,536 | gr8 main@2c221e9 | exlr8, DFlash, 262K KV | [`inkling-2-mini-exlr8-1x-rtx5090`](inkling-2-mini/rtx-5090/1x/exlr8-gr8) | stable |
| [**Nemotron 3.5 Bolt 74B-A9B**](nemotron-3.5-bolt/rtx-5090/1x/nvidia-24gb-vllm) | 74B-A9B | 1× RTX 5090 | 218 (512 tokens) | – | 6,277 | 262,144 | vllm v0.34.0 | NVIDIA 24GB checkpoint, fp8 KV, DFlash drafter | [`nemotron-3.5-bolt-rtx5090`](nemotron-3.5-bolt/rtx-5090/1x/nvidia-24gb-vllm) | stable |
| [**Nemotron 3.5 Super VL 120B-A12B**](nemotron-3.5-super-vl/dgx-spark/1x/nvfp4-vllm) | 120B-A12B | 1× DGX Spark (GB10) | 40.9 (tg128) | – | 3,058 | – | vllm v0.34.0 | NVFP4, DFlash LiLiCorr drafter | [`nemotron-3.5-super-vl-dgx-spark`](nemotron-3.5-super-vl/dgx-spark/1x/nvfp4-vllm) | stable |
| [**Qwen3-VL-Embedding-2B**](qwen3-vl-embedding-2b/dgx-spark/1x/exlr8-gr8) | 2B | 1× DGX Spark (GB10) | 4,167.4 (embed) | 14,567.8 (C8 embed) | – | 16,384 | gr8 v1.5.0 | exlr8 K4, multimodal embeddings | [`qwen3-vl-embedding-2b-exlr8-1x-spark`](qwen3-vl-embedding-2b/dgx-spark/1x/exlr8-gr8) | stable |
| [**Qwen3-VL-Embedding-8B**](qwen3-vl-embedding-8b/dgx-spark/1x/exlr8-gr8) | 8B | 1× DGX Spark (GB10) | 1,563.1 (embed) | 3,544.8 (C8 embed) | – | 16,384 | gr8 v1.5.0 | exlr8 K4, multimodal embeddings | [`qwen3-vl-embedding-8b-exlr8-1x-spark`](qwen3-vl-embedding-8b/dgx-spark/1x/exlr8-gr8) | stable |
| [**Qwen3.8-Flash-Next**](qwen3.8-flash-next/dgx-spark/1x/exlr8-gr8) | 180B-A6B | 1× DGX Spark (GB10) | 114.2 | 120.5 (38.2/s) | 2,204 | 262,144 | gr8 main@fa5d82d | exlr8, DFlash + MTP=3, 256K | [`qwen3.8-flash-next-exlr8-1x-spark`](qwen3.8-flash-next/dgx-spark/1x/exlr8-gr8) | stable |
| [**Qwen3.8-Flash-Next**](qwen3.8-flash-next/dgx-spark/2x/exlr8-gr8) | 180B-A6B | 2× DGX Spark (GB10) | 126.8 | 183.5 (56.6/s) | 3,027 | 262,144 | gr8 v1.2.0 | exlr8, MTP=3, 256K | [`qwen3.8-flash-next-exlr8-2x-spark`](qwen3.8-flash-next/dgx-spark/2x/exlr8-gr8) | stable |
| [**Qwen3.8-Flash-Next**](qwen3.8-flash-next/rtx-5090/1x/exlr8-gr8) | 180B-A6B | 1× RTX 5090 | 171.1 | – | – | 40,960 | gr8 v1.3.1 | exlr8 K3 bit300, hybrid GPU + host RAM, MTP=4 | [`qwen3.8-flash-next-exlr8-1x-gpu`](qwen3.8-flash-next/rtx-5090/1x/exlr8-gr8) | experimental |
| [**Sage-S2.1-Flash**](sage-s2.1-flash/dgx-spark/2x/exlr8-gr8) | 320B-A18B | 2× DGX Spark (GB10) | 55.1 | 79.8 | 1,832 | 262,144 | gr8 v1.2.0 | exlr8 k4, int4 KV | [`sage-s2.1-flash-exlr8-2x-spark`](sage-s2.1-flash/dgx-spark/2x/exlr8-gr8) | stable |
| [**Sage-S2.1-Flash**](sage-s2.1-flash/dgx-spark/4x/exlr8-gr8) | 320B-A18B | 4× DGX Spark (GB10) | 88 | 127.5 | 2,999 | 262,144 | gr8 v1.2.0 | exlr8 k4, int4 KV | [`sage-s2.1-flash-exlr8-4x-spark`](sage-s2.1-flash/dgx-spark/4x/exlr8-gr8) | stable |
| [**Step-5 Preview**](step-5-preview/dgx-spark/4x/nvfp4-vllm) | 600B-A27B | 4× DGX Spark (GB10) | 27.9 | 62.9 (16.3/s) | 1,317.1 | 589,824 | vllm | NVFP4, staged FP8 KV, MTP3, 576K context | [`step5-tp4-gb10-recipe`](step-5-preview/dgx-spark/4x/nvfp4-vllm) | experimental |

<!-- recipes:index:end -->

## Layout

Each recipe is a folder `<model>/<hardware>/<count>x/<variant>/`:

| Level | What | Examples |
|---|---|---|
| model | the upstream model, lowercased | `glm-5.3`, `glm-5.3-flash`, `deepseek-v4.1-flash` |
| hardware | a key of [`hardware.json`](hardware.json) | `dgx-spark` (DGX Spark, ASUS GX10: any GB10), `rtx-5090` |
| count | boxes or GPUs of the default config | `1x` … `6x` |
| variant | `<quant>[-<tag>]-<engine>` | `exlr8-gr8`, `exlr8-k4-gr8`, `nvfp4-vllm` |

A recipe that runs at several sizes lives under its default size; the others are configs in its `kindling.json`, shown
as tabs on its card. Every recipe also has a stable `id` (its old repo name for recipes that had one), used for the
CLI and its tags `<id>/<name>`.

Root files:

| Path | |
|---|---|
| [`index.json`](index.json) | generated: every recipe's `kindling.json` with its path, id, hardware, status and last-change date. The site reads it. |
| [`hardware.json`](hardware.json) | hardware slugs and their display names |
| [`models.json`](models.json) | model slugs and their parameter sizes for the scoreboard |
| [`schema/`](schema/) | `kindling.v1.json` (a recipe) and `index.v1.json` |
| [`tools/`](tools/) | the index builder, the pin checker, the recipe linter, the card drawer, the repo adopter |
| [`cli/`](cli/) | `@kindlingai/recipe`, the npx tool |

## Adding a recipe

Add a folder at its path with a `kindling.json` ([schema](schema/kindling.v1.json)) and open a pull request. CI
validates it and shows the tables it would produce; after the merge a bot commit updates `index.json` and the tables
above, and the site shows the card within about ten minutes. Nothing else changes: no site PR, no new repo.
[CONTRIBUTING.md](CONTRIBUTING.md) has the details (pins, tags, adopting an existing repo).

## License

MIT ([LICENSE](LICENSE)), except folders with their own LICENSE.

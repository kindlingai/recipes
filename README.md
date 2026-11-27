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

## Recipes

<!-- recipes:index:start -->
<!-- Written by tools/build_index.py from each recipe's kindling.json. Edits here are overwritten. -->

22 recipes. Numbers are the default config's: single-request decode on code, cold prefill of an 8K prompt (tok/s), longest request (tokens).

### DeepSeek-V4.1-Flash

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`deepseek-v4.1-flash-exlr8-4x-spark`](deepseek-v4.1-flash/dgx-spark/4x/exlr8-gr8) | 4× DGX Spark (GB10) | exlr8 native, fp8 KV, fast mode | gr8 v1.3.1 | 137.5 | – | 327,670 | stable |

### GLM-5.3

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`glm-5.3-exlr8-3x-spark`](glm-5.3/dgx-spark/3x/exlr8-gr8) | 3× DGX Spark (GB10) | exlr8 bit273, int4 KV, 384K context | gr8 v1.1.1 | 51.6 | 764 | 393,210 | stable |
| [`glm-5.3-exlr8-4x-spark`](glm-5.3/dgx-spark/4x/exlr8-gr8) | 4× DGX Spark (GB10) | exlr8 bit325, int4 KV, 1M context, DFlash2 drafter | gr8 v1.1.1 | 66.9 | 1,534 | 1,048,576 | stable |
| [`glm-5.3-exlr8-k4-4x-spark`](glm-5.3/dgx-spark/4x/exlr8-k4-gr8) | 4× DGX Spark (GB10) | exlr8 bit387 (K4), int4 KV, pure quality | gr8 v1.1.1 | 60.8 | 1,530 | 442,354 | stable |
| [`glm-5.3-exlr8-5x-spark`](glm-5.3/dgx-spark/5x/exlr8-gr8) | 5× DGX Spark (GB10) | exlr8 bit325, int4 KV, 983K context | gr8 v1.1.1 | 68.9 | 1,937 | 983,034 | stable |
| [`glm-5.3-exlr8-6x-spark`](glm-5.3/dgx-spark/6x/exlr8-gr8) | 6× DGX Spark (GB10) | exlr8 bit325, int4 KV, 1M context (2.18M pool) | gr8 v1.1.1 | 78 | 2,467 | 1,048,576 | stable |

### GLM-5.3-Flash

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`glm-5.3-flash-exlr8-1x-spark`](glm-5.3-flash/dgx-spark/1x/exlr8-gr8) | 1× DGX Spark (GB10) | exlr8 bit201, int4 KV | gr8 v1.2.0 | 53.8 | 995 | 262,144 | stable |
| [`glm-5.3-flash-exlr8-2x-spark`](glm-5.3-flash/dgx-spark/2x/exlr8-gr8) | 2× DGX Spark (GB10) | exlr8 bit349, int4 KV | gr8 v1.2.0 | 76.5 | 1,670 | 262,144 | stable |
| [`glm-5.3-flash-exlr8-gx10`](glm-5.3-flash/dgx-spark/4x/exlr8-vllm) | 4× DGX Spark (GB10) | NVFP4 | vllm | 117.3 | – | 524,288 | external |
| [`glm-5.3-flash-gx10`](glm-5.3-flash/dgx-spark/4x/nvfp4-vllm) | 4× DGX Spark (GB10) | NVFP4 | vllm | 117.3 | – | 524,288 | external |

### Inkling-2-Mini

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`inkling-2-mini-exlr8-1x-spark`](inkling-2-mini/dgx-spark/1x/exlr8-gr8) | 1× DGX Spark (GB10) | exlr8, DFlash, 144K x 8 (1.18M KV) | gr8 main@2c221e9 | 90.6 | 3,484 | 147,456 | stable |
| [`inkling-2-mini-exlr8-1x-rtx5090`](inkling-2-mini/rtx-5090/1x/exlr8-gr8) | 1× RTX 5090 | exlr8, DFlash, 262K KV | gr8 v1.3.1 | 328.1 | 3,427 | 65,536 | stable |

### Nemotron 3.5 Bolt 74B-A9B

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`nemotron-3.5-bolt-rtx5090`](nemotron-3.5-bolt/rtx-5090/1x/nvidia-24gb-vllm) | 1× RTX 5090 | NVIDIA 24GB checkpoint, fp8 KV, DFlash drafter | vllm v0.34.0 | 218 (512 tokens) | 6,277 | 262,144 | stable |

### Nemotron 3.5 Super VL 120B-A12B

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`nemotron-3.5-super-vl-dgx-spark`](nemotron-3.5-super-vl/dgx-spark/1x/nvfp4-vllm) | 1× DGX Spark (GB10) | NVFP4, DFlash LiLiCorr drafter | vllm v0.34.0 | 40.9 (tg128) | 3,058 | – | stable |

### Qwen3-VL-Embedding-2B

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`qwen3-vl-embedding-2b-exlr8-1x-spark`](qwen3-vl-embedding-2b/dgx-spark/1x/exlr8-gr8) | 1× DGX Spark (GB10) | exlr8 K4, multimodal embeddings | gr8 v1.5.0 | – | – | 16,384 | stable |

### Qwen3-VL-Embedding-8B

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`qwen3-vl-embedding-8b-exlr8-1x-spark`](qwen3-vl-embedding-8b/dgx-spark/1x/exlr8-gr8) | 1× DGX Spark (GB10) | exlr8 K4, multimodal embeddings | gr8 v1.5.0 | – | – | 16,384 | stable |

### Qwen3.8-Flash-Next

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`qwen3.8-flash-next-exlr8-1x-spark`](qwen3.8-flash-next/dgx-spark/1x/exlr8-gr8) | 1× DGX Spark (GB10) | exlr8, DFlash + MTP=3, 256K | gr8 main@fa5d82d | 114.2 | 2,204 | 262,144 | stable |
| [`qwen3.8-flash-next-exlr8-2x-spark`](qwen3.8-flash-next/dgx-spark/2x/exlr8-gr8) | 2× DGX Spark (GB10) | exlr8, MTP=3, 256K | gr8 v1.2.0 | 126.8 | 3,027 | 262,144 | stable |
| [`qwen3.8-flash-next-exlr8-1x-gpu`](qwen3.8-flash-next/rtx-5090/1x/exlr8-gr8) | 1× RTX 5090 | exlr8 K3 bit300, hybrid GPU + host RAM, MTP=4 | gr8 v1.3.1 | 171.1 | – | 40,960 | experimental |

### Sage-S2.1-Flash

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`sage-s2.1-flash-exlr8-2x-spark`](sage-s2.1-flash/dgx-spark/2x/exlr8-gr8) | 2× DGX Spark (GB10) | exlr8 k4, int4 KV | gr8 v1.2.0 | 55.1 | 1,832 | 262,144 | stable |
| [`sage-s2.1-flash-exlr8-4x-spark`](sage-s2.1-flash/dgx-spark/4x/exlr8-gr8) | 4× DGX Spark (GB10) | exlr8 k4, int4 KV | gr8 v1.2.0 | 88 | 2,999 | 262,144 | stable |

### Step-5 Preview

| Recipe | Hardware | Build | Engine | Decode | Prefill 8K | Max context | Status |
|---|---|---|---|---|---|---|---|
| [`step5-tp4-gb10-recipe`](step-5-preview/dgx-spark/4x/nvfp4-vllm) | 4× DGX Spark (GB10) | NVFP4, staged FP8 KV, MTP3, 576K context | vllm | 27.9 | 1,317.1 | 589,824 | experimental |

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

# For agents: boot Nemotron 3.5 Bolt 74B-A9B on 1× RTX 5090

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person. This recipe is the folder `nemotron-3.5-bolt/rtx-5090/1x/nvidia-24gb-vllm` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe nemotron-3.5-bolt-rtx5090` (or a sparse clone of the monorepo) and run the commands from inside
the folder.

## 1. Check the box

- It is a Linux x86_64 host with an NVIDIA RTX 5090 (32 GB VRAM) and no other model running on it: `docker ps` and
  `nvidia-smi` show none.
- NVIDIA driver supports CUDA 13.0+ (required by `vllm/vllm-openai:v0.34.0`): `nvidia-smi` reports CUDA 13.0 or newer.
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Disk: at least 40 GB free where the model and container cache live
  (`df -h "$(docker info --format '{{.DockerRootDir}}')"`, or `CACHE_DIR` if set).
- Hugging Face answers: `curl -sI https://huggingface.co`.

## 2. Write .env

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did). It is ready to boot `PROFILE=fast` as-is
(DFlash LiLiCorr drafter, 5 tokens, 262K context, 1 sequence). Ask the person before switching `PROFILE` (`long` drops
the drafter for a larger KV pool; `multi` drops the drafter and raises `MAX_NUM_SEQS` to 8 at 32K context) or changing
VRAM/batch knobs (`GPU_MEMORY_UTILIZATION`, `MAX_NUM_BATCHED_TOKENS`).

## 3. Boot

Run `docker compose up -d`. The first boot pulls the digest-pinned `vllm/vllm-openai:v0.34.0` image and fetches the
24 GB checkpoint (and LiLiCorr drafter in `fast` mode) into `CACHE_DIR`; later boots take about 2 minutes. Nothing is
`pip install`ed or kernel-downloaded at container start. Follow progress with `docker compose logs -f`.

## 4. Check

- `docker compose ps` shows the `vllm` service healthy.
- `curl -s localhost:8100/v1/models` lists `nemotron-3.5-bolt` with the expected `max_model_len` (262144 for `fast` /
  `long`, 32768 for `multi`).
- Run `python3 bench/bench.py smoke`: it prints `PASS` (answer contains `391`).

## 5. Stop

Run `docker compose down`.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count and the
  engine build. Do not copy a number from another build without noting which build measured it.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and the card
  (`docs/card.png`) is regenerated from `kindling.json`.
- The engine pin is one exact commit and one image digest (`@sha256:...`). Never a moving tag alone, never a locally
  built image, never an unpinned `pip install` at boot.
- From the monorepo root, run `python3 tools/check_pin.py --strict nemotron-3.5-bolt/rtx-5090/1x/nvidia-24gb-vllm` and
  `python3 tools/lint_recipe.py nemotron-3.5-bolt/rtx-5090/1x/nvidia-24gb-vllm` before you commit.

# For agents: boot Qwen3-VL-Embedding-8B on 1× DGX Spark (GB10)

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person. This recipe is the folder `qwen3-vl-embedding-8b/dgx-spark/1x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe qwen3-vl-embedding-8b-exlr8-1x-spark` (or a sparse clone of the monorepo) and run the commands
from inside the folder.

## 1. Check the box

- It is a DGX Spark or other GB10 box with at least 10 GiB free memory (`free -h` / `nvidia-smi`).
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Disk: at least 6 GB free where the model cache lives
  (`df -h "$(docker info --format '{{.DockerRootDir}}')"`, or `GR8_CACHE` if you set one).
- Hugging Face answers: `curl -sI https://huggingface.co`.

## 2. Write .env

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did). It is ready to boot
`Qwen3-VL-Embedding-8B` (`exlr8 K4`, `TP=1`, `CAP=16384`, `MAX_MODEL_LEN=16384`, port `8100`) as-is. Ask the person
before changing `PORT`, `CAP`, or `MAX_MODEL_LEN`.

## 3. Boot

Run `docker compose up -d`. The first boot downloads the model (`4.66 GB`) and verifies all 65 SHA-256 + XXH64
checksums; later boots take ~2 s. Follow it with `docker compose logs -f`.

## 4. Check

- `docker compose exec gr8 /opt/gr8/gr8 embed health` exits 0.
- `curl -s localhost:8100/v1/models` lists `qwen3-vl-embedding-8b` with `max_model_len` 16384.
- `docker compose exec gr8 /opt/gr8/gr8 embed smoke` passes 5 of 5 checks (single text, batched array + cosine sanity,
  Matryoshka `dimensions=512` + `base64`, and multimodal PNG image+text).

## 5. Stop

Run `docker compose exec gr8 /opt/gr8/gr8 embed down`, then `docker compose down`.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count and the
  engine build. Do not copy a number from another build without its date.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and the card
  (`docs/card.png`) is drawn again with `python3 tools/card.py qwen3-vl-embedding-8b/dgx-spark/1x/exlr8-gr8`.
- The engine pin is one exact commit and one image digest (`@sha256:...`). Never a moving tag alone, never a patched
  engine. An engine change goes to [kindlingai/gr8](https://github.com/kindlingai/gr8) as a pull request; this recipe
  then moves its pin to the merged commit or next release.
- From the monorepo root, run `python3 tools/check_pin.py --strict qwen3-vl-embedding-8b/dgx-spark/1x/exlr8-gr8` and
  `python3 tools/lint_recipe.py qwen3-vl-embedding-8b/dgx-spark/1x/exlr8-gr8` before you commit.

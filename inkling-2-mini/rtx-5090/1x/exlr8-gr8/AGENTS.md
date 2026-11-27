# For agents: boot Inkling-2-Mini on one RTX 5090 (32 GB)

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and tell
the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and tell the
person. This recipe is the folder `inkling-2-mini/rtx-5090/1x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe inkling-2-mini-exlr8-1x-rtx5090` (or a sparse clone of the monorepo) and run the commands from
inside the folder.

## 1. Check the box

- 1× NVIDIA Blackwell GPU with 32 GB VRAM (`sm_120a`, e.g. RTX 5090): check `nvidia-smi` and `docker ps`.
  - On a dedicated 32 GB GPU (~30 GiB available), the defaults fit with ~2 GiB free (`bit325`: `65536 × 4` = 262K KV pool).
  - If other GPU services occupy VRAM (e.g. ~7 GiB), lower `CAP` in `.env` (for example `CAP=16384`, `SESSIONS=4`, `PREFILL=256`).
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Local NVMe disk: at least 35 GB free for `kindlingai/inkling-2-mini-exlr8-k2-k3-k4` (`~31 GB` on disk).
- Hugging Face answers: `curl -sI https://huggingface.co`.

## 2. Download weights & write `.env`

```bash
hf download kindlingai/inkling-2-mini-exlr8-k2-k3-k4 \
  --local-dir ./models/inkling-2-mini-exlr8-k2-k3-k4
cp .env.example .env
```

Default is `VARIANT=bit325` (`65536 × 4` = 262K KV pool, `MTP=7` DFlash auto-discovered). Ask the person before
switching to `VARIANT=k4` (higher quality / graduate-level science, `49152 × 4` = 196K KV pool),
`PROFILE=bit225-fast` (fast 2.25-bit tier, `81920 × 4` = 327K KV pool), or `PROFILE=long` (single-stream long context
up to `303K` on `bit325` / `385K` on `bit225`).

## 3. Boot

Run `docker compose up -d`. Boot from local NVMe takes ~4–5 s once the `gr8` image is pulled. Follow with
`docker compose logs -f`.

## 4. Check

- `curl -s http://127.0.0.1:8100/v1/models` returns `200` and lists `inkling-2-mini`.
- Run one short `/v1/chat/completions` request and verify a coherent reply.

## 5. Stop

Run `docker compose down`.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, GPU, and `gr8` commit.
- `README.md` and `kindling.json` must agree; redraw `docs/card.png` from the monorepo root with
  `python3 tools/card.py inkling-2-mini/rtx-5090/1x/exlr8-gr8`.
- The engine pin is one exact `gr8` commit and one image digest (`@sha256:...`). Never a moving tag alone, never a
  patched engine or host build.
- From the `kindlingai/recipes` root, run `python3 tools/check_pin.py --strict inkling-2-mini/rtx-5090/1x/exlr8-gr8`
  and `python3 tools/lint_recipe.py inkling-2-mini/rtx-5090/1x/exlr8-gr8` before committing.

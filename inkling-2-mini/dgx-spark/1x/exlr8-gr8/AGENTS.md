# For agents: boot Inkling-2-Mini on one DGX Spark (bit325 / K4 / bit225)

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person. This recipe is the folder `inkling-2-mini/dgx-spark/1x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe inkling-2-mini-exlr8-1x-spark` (or a sparse clone of the monorepo) and run the commands
from inside the folder.

## 1. Check the box

- It is a DGX Spark or other GB10 box with 128 GB unified memory, and no other model runs on it: `docker ps` and
  `nvidia-smi` show none.
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Local NVMe disk: at least 35 GB free for the full `kindlingai/inkling-2-mini-exlr8-k2-k3-k4` pack (`~31 GB` on disk).
- Hugging Face answers: `curl -sI https://huggingface.co`.
- Proactive memory compaction is off: `sysctl vm.compaction_proactiveness` prints 0. If not, as root:
  `sysctl -w vm.compaction_proactiveness=0`.

## 2. Download weights & write .env

Download the weights into `./models/inkling-2-mini-exlr8-k2-k3-k4` (or set `MODEL_DIR` in `.env`):

```bash
hf download kindlingai/inkling-2-mini-exlr8-k2-k3-k4 \
  --local-dir ./models/inkling-2-mini-exlr8-k2-k3-k4
```

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did). It is ready to boot `VARIANT=bit325` at
`TP=1` with `CAP=147456`, `SESSIONS=8` (`1.18M` total KV pool at max 8 concurrent streams, ~9.6 GiB free OS memory),
`MTP=7` (DFlash auto-discovered). Ask the person before changing `VARIANT` (`k4` for higher quality / graduate-level
science GPQA, `bit225` for fast 2.25-bit speed, `bit250`, or `k2`), `CAP`/`SESSIONS` (`163840x8`, `262144x5`,
`196608x8` with `PF_MX8_MOE=1`, `262144x8` with `PF_MX8_MOE=0`, or `1048576x1`), or `GR8_INK2_PF_MX8_MOE`.

## 3. Boot

Run `docker compose up -d`. Boot from local NVMe takes ~10 s. Follow with `docker compose logs -f`.

## 4. Check

- `curl -s http://127.0.0.1:8100/v1/models` returns `200` and lists `inkling-2-mini` with `max_model_len` `147456`.
- Run one short chat completion against `http://127.0.0.1:8100/v1/chat/completions` and verify a coherent reply.

## 5. Stop

Run `docker compose down`.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count and the
  engine build. Do not copy a number from another build without its date.
- `README.md`'s results and `kindling.json` say the same thing. A change to one changes the other, and the cards are
  drawn again from a `gr8` checkout:
  - `python3 bench/gif.py card kindling.json --out docs/card.png`
  - `python3 bench/gif.py card kindling.json --config tp1-bit225 --out docs/card-bit225.png`
- The engine pin is one exact `gr8` commit and one image digest (`@sha256:...`). Never a moving tag alone.
- From the monorepo root, run `python3 tools/check_pin.py --strict inkling-2-mini/dgx-spark/1x/exlr8-gr8` and
  `python3 tools/build_index.py --check` before you commit.

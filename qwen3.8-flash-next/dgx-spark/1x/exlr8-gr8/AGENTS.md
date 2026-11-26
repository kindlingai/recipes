# For agents: boot Qwen3.8-Flash-Next on one DGX Spark (K3 & K4)

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person. This recipe is the folder `qwen3.8-flash-next/dgx-spark/1x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe qwen3.8-flash-next-exlr8-1x-spark` (or a sparse clone of the monorepo) and run the commands
from inside the folder.

## 1. Check the box

- It is a DGX Spark or other GB10 box with 128 GB, and no other model runs on it: `docker ps` and `nvidia-smi` show
  none.
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Local NVMe disk: at least 200 GB free for `bit300` (K3) or 215 GB free for `bit400` (K4) — the release includes the
  102.4 GB Layer-1 PLE NVMe rowstore and uses a 32 GB `O_DIRECT` SSD KV prefix cache, both of which must live on fast
  local NVMe (not NFS/HDD):
  `df -h "$(docker info --format '{{.DockerRootDir}}')"`, or the `GR8_CACHE` directory if you set one.
- Hugging Face answers: `curl -sI https://huggingface.co`.
- Proactive memory compaction is off: `sysctl vm.compaction_proactiveness` prints 0. If not, as root:
  `sysctl -w vm.compaction_proactiveness=0`.

## 2. Write .env

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did). It is ready to boot `bit300` (K3) at
`TP=1` with `CAP=262208`, `MAX_MODEL_LEN=262144`, `SESS=6`, `MTP=3` (plus auto-loaded DFlash), `REUSE=1`, and the
32 GiB `O_DIRECT` SSD KV store as-is. Ask the person before changing `VARIANT=bit400` (K4, requires `SESS=4`, or
`SESS=5` with `MTP=0` and `GR8_QW38_NO_MTP=1`), `GR8_QW38_VISION=1` (reduce `SESS` by 1), or `GR8_QW38_DFL=0`.

## 3. Boot

Run `docker compose up -d`. The first boot downloads the model (~164 GB for `bit300` or ~179 GB for `bit400`). Later
boots from local NVMe take ~28 s. Follow it with `docker compose logs -f`.

## 4. Check

- `docker compose exec gr8 /opt/gr8/gr8 qw38 health` exits 0.
- `docker compose exec gr8 /opt/gr8/gr8 qw38 smoke` passes 8 of 8 (or 9 of 9 with `GR8_QW38_VISION=1` and
  `GR8_QW38_VISION_SMOKE=1`).
- `curl -s localhost:8100/v1/models` lists `qwen3.8-flash-next` with `max_model_len` 262144.

## 5. Stop

Run `docker compose exec gr8 /opt/gr8/gr8 qw38 down`, then `docker compose down`.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count and the
  engine build. Do not copy a number from another build without its date.
- `README.md`'s results and `kindling.json` say the same thing. A change to one changes the other, and the cards are
  drawn again from a `gr8` checkout:
  - `python3 bench/gif.py card kindling.json --out docs/card.png`
  - `python3 bench/gif.py card kindling.json --config tp1-k4 --out docs/card-k4.png`
- The engine pin is one exact `gr8` commit and one image digest (`@sha256:...`). Never a moving tag alone, never a
  patched engine. An engine change goes to [kindlingai/gr8](https://github.com/kindlingai/gr8) as a pull request; this
  recipe then moves its pin to the merged commit or next release.
- From the monorepo root, run `python3 tools/check_pin.py --strict qwen3.8-flash-next/dgx-spark/1x/exlr8-gr8` before
  you commit.

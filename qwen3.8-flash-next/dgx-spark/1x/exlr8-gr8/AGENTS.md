# For agents: boot Qwen3.8-Flash-Next on one DGX Spark (K3 & K4)

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person.

## 1. Check the box

- It is a DGX Spark or other GB10 box with 128 GB, and no other model runs on it: `docker ps` and `nvidia-smi` show
  none.
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Local NVMe disk: at least 165 GB free for `bit300` (K3) or 180 GB free for `bit400` (K4) — the release includes the
  102.4 GB Layer-1 PLE NVMe rowstore, which must live on fast local NVMe (not NFS/HDD):
  `df -h "$(docker info --format '{{.DockerRootDir}}')"`, or the `GR8_CACHE` directory if you set one.
- Hugging Face answers: `curl -sI https://huggingface.co`.
- Proactive memory compaction is off: `sysctl vm.compaction_proactiveness` prints 0. If not, as root:
  `sysctl -w vm.compaction_proactiveness=0`.

## 2. Write .env

Copy `.env.example` to `.env`. It is ready to boot `bit300` (K3) at `TP=1` with `CAP=139264`, `SESS=8`, `MTP=3` as-is.
Ask the person before changing `VARIANT=bit400` (K4), `MTP=4`, `GR8_QW38_VISION=1`, `REUSE=1`, or `KV_STORE`.

## 3. Boot

Run `docker compose up -d`. The first boot downloads the model (~163 GB for `bit300` or ~178 GB for `bit400`). Later
boots from local NVMe take ~16-18 s. Follow it with `docker compose logs -f`.

## 4. Check

- `docker compose exec gr8 /opt/gr8/gr8 qw38 health` exits 0.
- `docker compose exec gr8 /opt/gr8/gr8 qw38 smoke` passes 8 of 8 (or 9 of 9 with `GR8_QW38_VISION=1` and
  `GR8_QW38_VISION_SMOKE=1`).
- `curl -s localhost:8100/v1/models` lists `qwen3.8-flash-next` with `max_model_len` 139200.

## 5. Stop

Run `docker compose exec gr8 /opt/gr8/gr8 qw38 down`, then `docker compose down`.

## Rules for changes to this repo

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count and the
  engine build. Do not copy a number from another build without its date.
- `README.md`'s results and `kindling.json` say the same thing. A change to one changes the other, and the cards are
  drawn again from a `gr8` checkout:
  - `python3 bench/gif.py card kindling.json --out docs/card.png`
  - `python3 bench/gif.py card kindling.json --config tp1-k4 --out docs/card-k4.png`
- Once `gr8 v1.2.0` is published, the engine pin is one exact `gr8` commit and one image digest (`@sha256:...`). Never
  a moving tag alone, never a patched engine. An engine change goes to [kindlingai/gr8](https://github.com/kindlingai/gr8)
  as a pull request; this recipe then moves its pin to the merged commit or next release.
- Run `python3 check.py` (and `python3 check.py --strict` once `v1.2.0` is pinned) before you commit.

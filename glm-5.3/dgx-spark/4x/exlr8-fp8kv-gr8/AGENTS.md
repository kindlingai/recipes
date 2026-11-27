# For agents: boot GLM-5.3 Pure FP8 KV on 4× DGX Spark

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person. This recipe is the folder `glm-5.3/dgx-spark/4x/exlr8-fp8kv-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe glm-5.3-exlr8-fp8kv-4x-spark` (or a sparse clone of the monorepo) and run the commands from
inside the folder on all four boxes.

## 1. Check the boxes

Verify on all four boxes:

- Each box is a DGX Spark (or GB10 128 GB unified-memory host), and no other model runs on it: `docker ps` and
  `nvidia-smi` show none, and `/proc/meminfo` shows ~115+ GiB `MemAvailable`.
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Disk: at least 90 GB free where the model cache lives
  (`df -h "$(docker info --format '{{.DockerRootDir}}')"`, or `GR8_CACHE` if set). Add 200 GB if enabling the
  optional SSD `KV_STORE`.
- Hugging Face answers: `curl -sI https://huggingface.co`.
- Proactive memory compaction is off: `sysctl -n vm.compaction_proactiveness` prints `0`. If not, run as root:
  `sudo sysctl -w vm.compaction_proactiveness=0`.
- RoCE v2 fabric is up (`ls /dev/infiniband`, `rdma link show` active) and TCP ports `7340` and `7341` are open
  between all four boxes.

## 2. Write .env

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did) and place the **exact same `.env` file**
on all four boxes. Set `PEERS` to the four boxes' LAN addresses, head first. Ask the person before changing
`KV_FORMAT`, `KVB`, `MOE_UNION_CAP`, or `CAP` from the measured defaults.

## 3. Boot

Run `docker compose up -d` on all four boxes. The first boot pulls the pinned `gr8 v1.2.0` image, downloads this rank's
weight slices (~75 GB/box for `bit325`), and converts the local DFlash drafter pack. Subsequent warm boots reach
`/health` in ~66 s. Follow progress with `docker compose logs -f`.

## 4. Check

Run on the head box (first address in `PEERS`):

- `docker compose exec gr8 /opt/gr8/gr8 glm53 health` exits 0 (`docker compose ps` shows healthy).
- `curl -s localhost:8100/v1/models` lists `glm-5.3` with `max_model_len` `655346`.
- `docker compose exec gr8 /opt/gr8/gr8 glm53 smoke` passes 14 of 14 checks.
- Confirm pure FP8 KV runtime: `docker compose exec gr8 sh -c "ps -ef | grep g6m4 | grep -v grep"` shows `bin/g6m4`
  (not `g6m4-int4`).

## 5. Stop

Run on the head box first, then every box:

```bash
docker compose exec gr8 /opt/gr8/gr8 glm53 down
docker compose down
```

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count, and the
  engine build. Do not copy a number from another build without its date.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and `docs/card.png`
  is redrawn with `python3 tools/card.py glm-5.3/dgx-spark/4x/exlr8-fp8kv-gr8`.
- The engine pin is one exact commit and one image digest (`@sha256:...`). Never a moving tag alone, never a local
  build or Dockerfile.
- From the monorepo root, run `python3 tools/check_pin.py --strict glm-5.3/dgx-spark/4x/exlr8-fp8kv-gr8` and
  `python3 tools/lint_recipe.py --strict glm-5.3/dgx-spark/4x/exlr8-fp8kv-gr8` before committing.

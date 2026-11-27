# For agents: boot GLM-5.3 Full (743B) on two DGX Sparks (EXLR8 bit225 + 4-bit MLA latent KV + 48 GB NVMe SSD KV)

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person.

## 1. Check both boxes

- Each box is a DGX Spark (GB10, 128 GB unified memory) and **no other model or heavy workload runs on it**:
  `docker ps` and `nvidia-smi` show none. (TP=2 runs very close to the 256 GB unified-memory ceiling — ~64–88 MiB
  live `MemAvailable` floor with `GR8_MEM_MIN=1`.)
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Disk: at least **175 GB free on fast local NVMe** per box (~115 GB for this rank's weights/drafter plus 48 GB for the
  NVMe SSD `KV_STORE` under `GR8_HOME`): `df -h "$(docker info --format '{{.DockerRootDir}}')"`.
- Hugging Face answers: `curl -sI https://huggingface.co`.
- Proactive memory compaction is off: `sysctl vm.compaction_proactiveness` prints 0. If not, as root:
  `sysctl -w vm.compaction_proactiveness=0`.
- TCP ports 7340 and 7341 are open between the two boxes.
- ConnectX ports are up: `ls /dev/infiniband` lists devices.

## 2. Write .env

Copy `.env.example` to `.env`. Set `PEERS` to the two LAN addresses, head first. If the two Sparks are cabled directly
with no switch, set `SHAPE=direct` (otherwise leave `SHAPE=mesh`). Use the exact same `.env` on both boxes. Ask the
person before changing any other line.

## 3. Boot

On both boxes: `docker compose up -d`. The first boot downloads this rank's part of the weights and packs the native
INT4 DFlash drafter (`tp2-int4`). Subsequent warm boots from local NVMe take ~87–88 s. Follow progress with
`docker compose logs -f`.

## 4. Check

On the head:

- `docker compose exec gr8 /opt/gr8/gr8 glm53 health` exits 0.
- `curl -s localhost:8100/v1/models` returns `glm-5.3`.

## 5. Stop

On the head: `docker compose exec gr8 /opt/gr8/gr8 glm53 down`. Then `docker compose down` on both boxes.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, box count, and engine build.
- Keep `README.md`, `kindling.json`, and `docs/card.png` in sync (`python3 tools/card.py glm-5.3/dgx-spark/2x/exlr8-gr8`).
- Run `python3 tools/check_pin.py --strict glm-5.3/dgx-spark/2x/exlr8-gr8` and
  `python3 tools/lint_recipe.py glm-5.3/dgx-spark/2x/exlr8-gr8` before committing.

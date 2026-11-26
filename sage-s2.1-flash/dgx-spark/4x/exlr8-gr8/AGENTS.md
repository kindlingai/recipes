# For agents: boot Sage-S2.1-Flash on 4× DGX Spark

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and tell
the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and tell the
person. This recipe is the folder `sage-s2.1-flash/dgx-spark/4x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe sage-s2.1-flash-exlr8-4x-spark` (or a sparse clone of the monorepo) and run the commands from
inside the folder on all four boxes.

## 1. Check all four boxes

On all four boxes:

- All four boxes are DGX Sparks or other GB10 boxes (128 GB unified memory), on a 200G switch (`SHAPE=mesh`, default)
  or directly cabled in a ring (`SHAPE=ring`; `README.md`, Clustering), with `mtu: 9000` configured.
- No other model runs: `docker ps` shows no model container and `nvidia-smi` shows no GPU process.
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Disk: at least 47 GB free for this box's part of the `k4` release plus up to 64 GB for the prompt cache
  (`df -h "$(docker info --format '{{.DockerRootDir}}')"`, or `GR8_CACHE` if set).
- Hugging Face answers: `curl -sI https://huggingface.co`.
- TCP ports 7340 and 7341 are open between all four boxes.
- ConnectX devices exist: `ls /dev/infiniband` and `ip -br addr`.
- Proactive memory compaction is off: `sysctl vm.compaction_proactiveness` prints `0`. If not, as root:
  `sysctl -w vm.compaction_proactiveness=0` (`README.md`, What you need, has the permanent form).

## 2. Write .env

Copy `.env.example` to `.env` on all four boxes (the CLI already did). Use the exact same `.env` on all four boxes.

- **Switch without `mentat`:** set `PEERS` to the four 10G LAN addresses (head first), and uncomment `IPS` and `IPS2` if
  needed.
- **Direct ring without a switch:** uncomment `SHAPE=ring`, list `PEERS` in cable order, and leave `IPS` and `IPS2`
  commented out.
- **With `mentat`:** comment out `PEERS`, `IPS`, and `IPS2`, and uncomment `MENTAT=localhost` (never set both `PEERS`
  and `MENTAT`).
- Leave all other active lines as-is for the default measured `speed` config (`SESS=8`, `CAP=262208`,
  `MAX_MODEL_LEN=262144`, `MTP=2`, `S2_SHARED_WATERFILL=1`, `DFLASH=0`, `KV_FORMAT=int4`, `FLASH_CACHE=aligned`,
  `KV_STORE=@/etc/gr8/kv-store.yaml`). Ask the person before enabling experimental `context` (`CAP=2097152`,
  `MAX_MODEL_LEN=1048576`, `EXTRA_ENV=GR8_CP=1`), `quality` (`MTP=1`, `S2_SHARED_WATERFILL=0`), or untested vision
  (`GR8_GLM53F_VISION=1`).

## 3. Boot

1. Optionally verify resolved config on all four boxes:
   ```bash
   docker compose run --rm gr8 show-config --no-check
   ```
2. Start all four boxes within 600 s (`JOIN_TIMEOUT`) of each other:
   ```bash
   docker compose up -d
   ```
   `compose.yaml` pulls the pinned `gr8` image and bind-mounts `./kv-store.yaml` read-only at `/etc/gr8/kv-store.yaml`.
   First boot downloads ~47 GB per box. Follow logs on the head with `docker compose logs -f` until `serving: http://...`
   appears.

## 4. Check

On the head:

- `docker compose exec gr8 /opt/gr8/gr8 glm53f health` exits `0` (and `docker compose ps` shows healthy).
- `docker compose exec gr8 /opt/gr8/gr8 glm53f status` reports all four ranks serving.
- `docker compose exec gr8 /opt/gr8/gr8 glm53f smoke` passes 14 of 14 checks.
- `curl -s localhost:8100/v1/models` lists `glm-5.3-flash` with `max_model_len` `262144` (`1048576` with context
  preset).

## 5. Stop

On the head: `docker compose exec gr8 /opt/gr8/gr8 glm53f down`. Then `docker compose down` on all four boxes.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count and the
  engine build. Do not copy a number from another build without its date.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and `docs/card.png`
  is drawn again from `kindling.json`.
- The engine pin is one exact gr8 commit and one image digest (`@sha256:...`). Never a moving tag alone, never a
  patched engine or local `Dockerfile`. An engine change goes to [kindlingai/gr8](https://github.com/kindlingai/gr8) as
  a pull request; this recipe then moves its pin to the merged commit or next release.
- From the monorepo root, run `python3 tools/check_pin.py --strict sage-s2.1-flash/dgx-spark/4x/exlr8-gr8` and
  `python3 tools/lint_recipe.py --strict sage-s2.1-flash/dgx-spark/4x/exlr8-gr8` before you commit.

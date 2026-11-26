# For agents: boot GLM-5.3 K4 on 4× DGX Spark

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and tell
the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and tell the
person. This recipe is the folder `glm-5.3/dgx-spark/4x/exlr8-k4-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe glm-5.3-exlr8-k4-4x-spark` (or a sparse clone of the monorepo) and run the commands from inside
the folder on all four boxes.

## 1. Check each box

On all four boxes:

- It is a DGX Spark or other GB10 box (128 GB): `nvidia-smi` names a GB10.
- No other model runs: `docker ps` shows no model container, and `nvidia-smi` shows no GPU process.
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Disk: at least 110 GB free where Docker keeps volumes (`df -h "$(docker info --format '{{.DockerRootDir}}')"`, or
  `GR8_CACHE` if you set one).
- Hugging Face answers: `curl -sI https://huggingface.co`.
- The ConnectX ports are up: `ls /dev/infiniband` lists devices, and `ip -br addr` shows an address on each fabric port.
- TCP ports 7340 and 7341 are open between the boxes.
- Proactive compaction is off: `sysctl vm.compaction_proactiveness` prints `0`. If not, as root:
  `sysctl -w vm.compaction_proactiveness=0` (README.md, What you need, has the permanent form).

## 2. Write .env

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did). Keep its `GR8_MODEL`, `MODEL`, `DRAFTER`,
`VARIANT=/etc/gr8/exlr8-manifest-bit387.json`, `TP=4`, `KV_FORMAT=int4`, `DISPRAM=1`, `CAP=442368`,
`SHARE_LIMIT=16384`, `S2_ADAPT=0`, `DEC_BK=2048`, `DEC_BK_MAX=2048`, and `MOE_UNION_CAP=0` lines: the README's numbers
were measured with them (pure quality, uncapped routing, 4.3+ GiB free per box).

If the boxes run mentat (`docker ps` shows a `mentat` container), leave `PEERS` commented out. Otherwise uncomment and
fill in `PEERS` (the four LAN addresses, head first) and, if needed, `IPS` and `IPS2`. Use the same `.env` on every
box. Ask the person before changing any other line.

## 3. Boot

On all four boxes: `docker compose up -d`. `compose.yaml` pulls the pinned `gr8` image and bind-mounts
`./manifests` read-only at `/etc/gr8`. The first boot fetches this box's part of the model (~100 GB) and converts the
DFlash2 drafter, then the boxes handshake and load. Follow it on the head with `docker compose logs -f`; it is ready
when the log says the cluster serves.

## 4. Check

On the head:

- `docker compose exec gr8 /opt/gr8/gr8 glm53 health` exits `0` (and `docker compose ps` shows healthy).
- `docker compose exec gr8 /opt/gr8/gr8 glm53 smoke` passes 14 of 14 checks.
- `curl -s localhost:8100/v1/models` lists the model with `max_model_len` `442354`.

If a box's log says another engine is running, run `docker compose exec gr8 /opt/gr8/gr8 glm53 down` on the head, wait
until `pgrep -f 'bin/g6m4'` finds nothing on every box, and start again.

## 5. Stop

On the head: `docker compose exec gr8 /opt/gr8/gr8 glm53 down`. Then `docker compose down` on every box.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count and the
  engine build. Do not copy a number from another build without its date.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and `docs/card.png`
  is drawn again from the engine checkout.
- The engine pin is one exact gr8 commit and one image digest (`@sha256:...`). Never a moving tag alone, never a
  patched engine or local `Dockerfile`. An engine change goes to [kindlingai/gr8](https://github.com/kindlingai/gr8) as
  a pull request; this recipe then moves its pin to the merged commit or next release.
- This K4 recipe is quality-first: keep `MOE_UNION_CAP=0` (uncapped) in `.env.example`.
- From the monorepo root, run `bash glm-5.3/dgx-spark/4x/exlr8-k4-gr8/check.sh`,
  `python3 tools/check_pin.py --strict glm-5.3/dgx-spark/4x/exlr8-k4-gr8`, and
  `python3 tools/lint_recipe.py --strict glm-5.3/dgx-spark/4x/exlr8-k4-gr8` before you commit.

# For agents: boot GLM-5.3-Flash on 2× DGX Spark

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and tell
the person what failed. If this file and `knobs.sh`, `compose.yaml` or `.env.example` disagree, follow those files and
tell the person. If you cannot run a check yourself, ask the person to run it and paste the output. Do not skip it.

This recipe is the folder `glm-5.3-flash/dgx-spark/2x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe glm-5.3-flash-exlr8-2x-spark` (or a sparse clone of the monorepo) on both boxes and run the
commands from inside the folder. This recipe runs `gr8`'s published image
(`ghcr.io/kindlingai/gr8:v1.2.0@sha256:3de05aab...`) directly with read-only mounts for `entrypoint.sh`, `knobs.sh`,
`bin/gr8` and `kv-store.yaml`; nothing is built.

## 1. Check the two boxes

On both boxes:

- The box is a DGX Spark, or another GB10 box such as the ASUS GX10 (128 GB). The two boxes are joined by a 200G cable
  between their ConnectX ports (README.md, Clustering).
- Docker and the NVIDIA container toolkit are installed (both come with DGX OS): `docker info | grep -i nvidia` shows
  the `nvidia` runtime.
- Free disk where Docker keeps volumes: about 77 GB for this box's part of the model, vision tower, and drafter
  (~90 GB with `TUNE=quality`; ~130 GB if both are cached), plus up to 64 GB in the same cache volume for the prompt
  cache (`/var/lib/gr8/cache/prompts`), plus 73 GiB (a `VARIANT=k4` size) if enabling compact expert copies. Check with
  `df -h "$(docker info --format '{{.DockerRootDir}}')"`. Set `GR8_CACHE` in `.env` to a host directory owned by uid
  1000 to store outside Docker.
- The box can reach Hugging Face: `curl -sI https://huggingface.co` answers.
- No other model runs on the box: `docker ps` shows no other model container, and `nvidia-smi` shows no GPU process.
  Weights take ~76 GB per box (~86 GB with `TUNE=quality`).
- TCP ports 7340 and 7341 are open between the two boxes (check both directions with a python socket listener and
  `timeout 5 bash -c 'exec 3<>/dev/tcp/<peer>/7340'` on `PEERS`, `IPS`, and `IPS2`).
- Proactive memory compaction is off: `sysctl vm.compaction_proactiveness` prints `0`. If not, run as root once:

  ```bash
  echo 'vm.compaction_proactiveness = 0' > /etc/sysctl.d/90-gr8-no-proactive-compaction.conf
  sysctl -w vm.compaction_proactiveness=0
  ```

- ConnectX addressing, one of two ways:
  - With `mentat` running on both boxes (`docker ps` shows `mentat`): set `MENTAT=1` in `.env` and leave `PEERS`, `IPS`,
    `IPS2` commented out.
  - Without `mentat`: each box has one ConnectX address per PCIe root (`ip -br addr`, `ls /dev/infiniband`). Collect
    both boxes' 10G LAN addresses (`PEERS`, head first), root-1 ConnectX addresses (`IPS`), and root-2 addresses
    (`IPS2`), all in the same order.

## 2. Write .env and pick settings

Copy `.env.example` to `.env` on both boxes (the `npx @kindlingai/recipe` CLI already did) and keep both `.env` files
identical. Uncomment and fill in `PEERS`, `IPS` and `IPS2` (or set `MENTAT=1`).

`TUNE` picks what to prioritize. Keep `TUNE=speed` unless the person asks for another value:

| `TUNE` | what `knobs.sh` sets | what it gives |
|---|---|---|
| `speed` (default) | `VARIANT=bit349`, `SESS=4`, `CAP=2097152`, `MAX_MODEL_LEN=262144` | 4 concurrent requests up to 262,144 tokens each |
| `context` | `VARIANT=bit349`, `SESS=8`, `CAP=2097152`, `MAX_MODEL_LEN=1048576`, `GR8_CP=1` in `EXTRA_ENV` | 8 concurrent requests, up to 1,048,576 tokens with context-parallel KV |
| `quality` | `VARIANT=k4`, `SESS=4`, `CAP=262208`, `MAX_MODEL_LEN=262144` | widest weights (K4), 4 concurrent requests up to 262,144 tokens |

What else `knobs.sh` does:

- Any other `TUNE` value stops the boot (exit 2).
- Any explicit `VARIANT`, `SESS`, `CAP`, or `MAX_MODEL_LEN` in `.env` overrides `TUNE`.
- Image input is on by default (`GR8_GLM53F_VISION=1` is appended to `EXTRA_ENV` unless already named; set
  `EXTRA_ENV="GR8_GLM53F_VISION=0"` on both boxes to turn it off).
- With `MENTAT=0`, `PEERS` must name exactly two addresses, or the boot stops (exit 2).

Key knobs in `.env.example`:

| knob | values | default |
|---|---|---|
| `PEERS` | two 10G LAN addresses, comma-separated, head first, identical on both boxes | required unless `MENTAT=1` |
| `IPS`, `IPS2` | ConnectX root-1 and root-2 addresses in `PEERS` order | none |
| `TUNE` | `speed`, `context`, `quality` | `speed` |
| `VARIANT`, `SESS`, `CAP`, `MAX_MODEL_LEN` | override `TUNE`'s values | from `TUNE` |
| `DFLASH` | `1`: DFlash2 drafter (CC BY-NC-ND 4.0) for solo requests. `0`: MTP only | `1` |
| `MENTAT` | `0`: use `PEERS`. `1`: discover via host `mentat` daemon in `GROUP` | `0` |
| `GROUP` | `mentat` group when `MENTAT=1` | `gr8-glm53f-2x` |
| `GR8_GLM53F_VISION` (in `EXTRA_ENV`) | `1` (~1.6 GiB RAM, ~1.1 GB download per box) or `0` | `1` |
| `DEFAULT_MAX_TOKENS`, `DEFAULT_THINK_END_BOOST`, `DEFAULT_THINKING_BUDGET`, `DEFAULT_PRESENCE_PENALTY`, `UNDECLARED_TOOL_CALLS` | reply/thinking limits, loop guard, undeclared tool handling | active in `.env.example` |
| `GR8_CACHE`, `GR8_HOME` | compose only: host dirs (owned by uid 1000) in place of named volumes | named volumes |
| `GR8_STOP_GRACE` | compose only: `docker stop` grace period | `30s` |
| `GR8_IMAGE` | compose only: override the pinned `gr8` image | pinned `v1.2.0` digest |
| `MODEL`, `DRAFTER`, `HF_TOKEN` | pinned HF URLs (`@<commit>`) and optional token | measured commits |

## 3. Boot

1. Optional (no GPU needed): run `./check-config.sh` to verify `compose.yaml`, `.env.example`, and `knobs.sh` against
   the pinned gr8 image, or print resolved config on each box:

   ```bash
   docker compose run --rm --no-deps gr8 show-config --no-check
   ```

2. Optional, on both boxes: `check` runs pre-boot checks (cache, `/dev/infiniband`, free memory, no other engine):

   ```bash
   docker compose run --rm gr8 check
   ```

3. Optional (off by default): compact expert copies. Skip unless the person asks for them (note that switch-time
   numbers in README.md are `VARIANT=k4` on an older pin; `bit349` was not measured). To enable on both boxes, uncomment
   the `EXTRA_ENV="GR8_LOAD_COMPACT=..."` line in `.env` and run `docker compose run --rm gr8 prepare` (add `--rank 0` /
   `--rank 1` with `MENTAT=1`) before starting.

4. Start the container on both boxes within 10 minutes (`JOIN_TIMEOUT=600` s):

   ```bash
   docker compose up -d
   docker compose logs -f
   ```

5. To change `TUNE` or any knob later: `docker compose down` on both boxes, edit `.env` identically on both, and
   `docker compose up -d`.

## 4. Check that it serves

Wait for `serving:` in the head's log (`docker compose logs -f`), then verify:

- On both boxes: `docker compose exec gr8 /opt/glm53f-2x/bin/gr8 glm53f health` exits 0, and `docker compose ps` shows
  `healthy`.
- On the head: `curl -s -o /dev/null -w '%{http_code}\n' localhost:8100/health` returns `200`, and
  `curl -s localhost:8100/v1/models` lists `glm-5.3-flash` with the expected `max_model_len`.
- `docker compose exec gr8 /opt/glm53f-2x/bin/gr8 glm53f status` shows both boxes' state, engine, and free memory.
- On the head: `docker compose exec gr8 /opt/glm53f-2x/bin/gr8 glm53f smoke` runs 14 checks (`14/14 passed`).
- Send one text chat completion (and optionally an inline base64 `image_url` request) to `localhost:8100/v1/chat/completions`.

## 5. Stop

On both boxes:

```bash
docker compose down
```

## 6. When a step fails

| what you see | what to do |
|---|---|
| `TUNE=...: want speed (the default), context or quality ...` | use `speed`, `context`, or `quality` |
| `PEERS=...: want the two boxes' LAN addresses ...` | set two addresses in `PEERS` (same on both boxes) or `MENTAT=1` |
| `MENTAT=...: want 0 ... or 1 ...` | use `MENTAT=0` or `MENTAT=1` |
| `gr8: --max-model-len ...: more than CAP ...` | lower `MAX_MODEL_LEN` or raise `CAP` |
| `gr8: memlock is limited ...` | keep `ulimits.memlock: -1` in `compose.yaml` |
| `gr8: ... is not writable by uid 1000 ...` | run `chown 1000:1000` on host `GR8_HOME` / `GR8_CACHE` |
| `an engine is already running` or `a g6m4 --rank process is running` | ask the person, then stop the other model |
| `handshake refused: join: ... did not answer within 600s` | start both boxes within 600 s; verify identical `PEERS` and open ports 7340/7341 |
| `handshake refused: ...` | match `.env` and image digest on both boxes, fix reported `checks` failures, restart both |

Exit codes: 0 clean stop, 1 rank failed / join timeout, 2 bad options, 4 handshake refused. Read logs via
`docker compose logs` or `docker compose exec gr8 /opt/glm53f-2x/bin/gr8 glm53f logs supervisor` (`shim` / `front`).

## 7. Not measured yet: tell the person

- Re-measurement on published `gr8 v1.2.0` (`ab2eb95`): existing Results numbers are from prior `gr8` commit `4057009`.
- KL against BF16 at TP=2 has not been scored through gr8 for `bit349` or `k4`.
- `TUNE=context` with multiple simultaneous long prompts has not been measured.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count, and the engine
  build. Do not copy a number from another build without noting its source build.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and the card
  (`docs/card.png`) is redrawn from `kindling.json`.
- The engine pin is one exact commit and one image digest (`@sha256:...`). Never a moving tag alone, never a local
  Dockerfile build. An engine change goes to `kindlingai/gr8` first; this recipe then moves its pin to the published
  image.
- From the monorepo root, run `python3 tools/check_pin.py --strict glm-5.3-flash/dgx-spark/2x/exlr8-gr8`,
  `python3 tools/lint_recipe.py --strict glm-5.3-flash/dgx-spark/2x/exlr8-gr8`, and `./check-config.sh` inside this
  folder before you commit.

# For agents: boot GLM-5.3-Flash on 1× DGX Spark

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and tell
the person what failed. If this file and `knobs.sh`, `compose.yaml` or `.env.example` disagree, follow those files and
tell the person. If you cannot run a check yourself, ask the person to run it and paste the output. Do not skip it.

This recipe is the folder `glm-5.3-flash/dgx-spark/1x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe glm-5.3-flash-exlr8-1x-spark` (or a sparse clone of the monorepo) and run the commands from
inside the folder. This recipe runs `gr8`'s published image (`ghcr.io/kindlingai/gr8:v1.2.0@sha256:3de05aab...`)
directly with read-only mounts for `entrypoint.sh`, `knobs.sh`, `bin/gr8` and `kv-store.yaml`; nothing is built.

## 1. Check the box

- It is a DGX Spark, or another GB10 box such as the ASUS GX10 (128 GB).
- Docker and the NVIDIA container toolkit are installed (both come with DGX OS): `docker info | grep -i nvidia` shows
  the `nvidia` runtime.
- Free disk where Docker keeps volumes: at least 87 GB for the download (the model and the drafter), plus up to 64 GB
  for the prompt cache (`/var/lib/gr8/cache/prompts` inside the cache volume). Check with
  `df -h "$(docker info --format '{{.DockerRootDir}}')"`. You can set `GR8_CACHE` in `.env` to a host directory owned
  by uid 1000 instead.
- The box can reach Hugging Face for the download: `curl -sI https://huggingface.co` answers.
- No other model runs on the box: `docker ps` shows no other model container, and `nvidia-smi` shows no GPU process.
  The weights take about 93 GB of memory (measured with the K2 manifest; `bit201` takes about 0.4 GB more), and gr8 does
  not start while another gr8 engine runs on the box.
- Optional: gr8 logs a warning at boot when proactive memory compaction is on. `sysctl vm.compaction_proactiveness`
  prints 0 when it is off. To turn it off, as root, once:

  ```bash
  echo 'vm.compaction_proactiveness = 0' > /etc/sysctl.d/90-gr8-no-proactive-compaction.conf
  sysctl -w vm.compaction_proactiveness=0
  ```

## 2. Write .env and pick settings

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did). It is ready to boot `TUNE=speed` as-is.

`TUNE` picks what to prioritize. Ask the person whether they need one request longer than 262,144 tokens: then use
`TUNE=context`. Otherwise, or if you cannot ask, keep `TUNE=speed`.

| `TUNE` | what `knobs.sh` sets | what it gives |
|---|---|---|
| `speed` (default) | `MAX_MODEL_LEN=262144` | requests up to 262,144 tokens |
| `context` | `MAX_MODEL_LEN=700018` | one request up to 700,018 tokens (`CAP=700032` less DFlash2's 14 guard rows); other requests wait when the pool is full |
| `quality` | `MAX_MODEL_LEN=262144` | same as `speed`: K3 and K4 do not fit one box, and this recipe runs the int4 KV engine |

What else `knobs.sh` does:

- If you uncomment and set `MAX_MODEL_LEN` yourself in `.env`, `TUNE` leaves it alone.
- With `TUNE=context` and a `CAP` below 700,032, set `MAX_MODEL_LEN` too, to at most `CAP` less 14. When
  `MAX_MODEL_LEN` is more than `CAP`, the boot stops.
- Any other `TUNE` value stops the boot (exit 2).

Key knobs in `.env.example`:

| knob | values | default |
|---|---|---|
| `TUNE` | `speed`, `context`, `quality` | `speed` |
| `CAP` | KV pool in tokens, multiple of 64 (~5 KB/token). Tuned on DGX OS; Kindling Spark OS may allow `1000000` (not measured) | `700032` |
| `MAX_MODEL_LEN` | longest single request, prompt + output: at most `CAP` less guard rows (14 with DFlash2), max 1,048,576 | by `TUNE` |
| `VARIANT` | `bit201` (K2 with 124 routed experts at K3) or `k2` (~0.4 GB smaller). Non-`k2`/`k3`/`k4` names require `MODEL` pinned to a commit | `bit201` |
| `DFLASH` | `1`: DFlash2 drafter (CC BY-NC-ND 4.0) for solo requests. `0`: MTP only, drafter not downloaded | `1` |
| `MENTAT` | `0`: this box alone (`PEERS=127.0.0.1`). `1`: register with host `mentat` daemon in group `GROUP` | `0` |
| `GROUP` | `mentat` group when `MENTAT=1` | `gr8-glm53f-1x` |
| `DEFAULT_PRESENCE_PENALTY` | thinking 0.5 for all requests, reply 0.2 for greedy only; `0` disables | `greedy=0.2,greedy.thinking=0.5,nongreedy.thinking=0.5` |
| `UNDECLARED_TOOL_CALLS` | `emit` (return in `tool_calls`) or `text` (leave in `content`) | `emit` |
| `DEFAULT_MAX_TOKENS` | default `max_tokens` when omitted | `32768` |
| `DEFAULT_THINK_END_BOOST` | soft thinking budget boost (`</think>` logit) | `start=16384,per1k=4,max=10` |
| `DEFAULT_THINKING_BUDGET` | hard thinking token cap (`0` = no limit) | `28672` |
| `GR8_CACHE`, `GR8_HOME` | compose only: host dirs (owned by uid 1000) in place of named volumes | named volumes |
| `GR8_STOP_GRACE` | compose only: `docker stop` grace period | `30s` |
| `GR8_IMAGE` | compose only: override the pinned `gr8` image | pinned `v1.2.0` digest |
| `MODEL`, `DRAFTER` | Hugging Face repo URLs pinned with `@<commit>` | measured commits |
| `HF_TOKEN` | Hugging Face token for gated/private repos | none |

## 3. Boot

1. Optional (no GPU needed): run `./check-config.sh` to verify `compose.yaml`, `.env.example`, and `knobs.sh` against
   the pinned gr8 image, or print the resolved config with:

   ```bash
   docker compose run --rm --no-deps gr8 show-config --no-check
   ```

2. Optional: `check` runs the boot's own checks on the box without booting (model cache, no other engine running, free
   memory). Before the first boot it reports the model and drafter as not cached yet; any other `FAIL` line must be
   fixed before starting.

   ```bash
   docker compose run --rm gr8 check
   ```

3. Start the container:

   ```bash
   docker compose up -d
   docker compose logs -f
   ```

   The first boot pulls `ghcr.io/kindlingai/gr8:v1.2.0`, downloads 87 GB from Hugging Face into the cache volume, and
   converts the drafter (~10 minutes total; later boots ~45 s when measured on K2).

4. To change `TUNE` or any knob later: `docker compose down`, edit `.env`, `docker compose up -d`. Changing `TUNE` or
   `MAX_MODEL_LEN` alone downloads nothing.

## 4. Check that it serves

Wait for `serving:` in `docker compose logs -f`, then verify:

- `docker compose exec gr8 /opt/glm53f-1x/bin/gr8 glm53f health` exits 0, and `docker compose ps` shows `healthy`.
- `curl -s -o /dev/null -w '%{http_code}\n' localhost:8100/health` returns `200`, and `curl -s localhost:8100/v1/models`
  lists `glm-5.3-flash` with the expected `max_model_len`.
- `docker compose exec gr8 /opt/glm53f-1x/bin/gr8 glm53f status` shows box state, engine, and free memory.
- `docker compose exec gr8 /opt/glm53f-1x/bin/gr8 glm53f smoke` runs 14 checks against the API (`14/14 passed`).
- Send one chat completion:

  ```bash
  curl -s localhost:8100/v1/chat/completions -H 'Content-Type: application/json' -d '{
    "model": "glm-5.3-flash",
    "messages": [{"role": "user", "content": "Write a haiku about a small computer."}],
    "max_tokens": 4096
  }'
  ```

  Thinking comes back in `message.reasoning` and counts toward `max_tokens`.

## 5. Stop

```bash
docker compose down
```

## 6. When a step fails

| what you see | what to do |
|---|---|
| `TUNE=...: want speed (the default), context or quality ...` | use `speed`, `context`, or `quality` |
| `gr8: --max-model-len ...: more than CAP ...` | set `MAX_MODEL_LEN` to at most `CAP` less 14, or raise `CAP` |
| `MENTAT=...: want 0 (this box alone) or 1 ...` | use `MENTAT=0` or `MENTAT=1` |
| `gr8: memlock is limited ...` | keep `ulimits.memlock: -1` in `compose.yaml` (`--ulimit memlock=-1` with `docker run`) |
| `gr8: ... is not writable by uid 1000 ...` | run `chown 1000:1000` on your host `GR8_HOME` / `GR8_CACHE` directory |
| `an engine is already running` or `a g6m4 --rank process is running` | ask the person, then stop the other model |

Exit codes: 0 after clean stop, 1 engine failed, 2 bad options. Read logs via `docker compose logs` or
`docker compose exec gr8 /opt/glm53f-1x/bin/gr8 glm53f logs supervisor` (or `shim` / `front`).

## 7. Not measured yet: tell the person

- Re-measurement on published `gr8 v1.2.0` (`ab2eb95`): existing Results numbers are from prior `gr8` commit `d598965`.
- `TUNE=context` was measured once (one 672K-token prompt; lowest free memory 3.9 GiB on Kindling Spark OS, ~2 GiB less
  on DGX OS).
- The K2 width has not been scored against BF16 on this recipe.
- `CAP` above `700032` on Kindling Spark OS has no measurement yet.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count, and the engine
  build. Do not copy a number from another build without noting its source build.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and the card
  (`docs/card.png`) is redrawn from `kindling.json`.
- The engine pin is one exact commit and one image digest (`@sha256:...`). Never a moving tag alone, never a local
  Dockerfile build. An engine change goes to `kindlingai/gr8` first; this recipe then moves its pin to the published
  image.
- From the monorepo root, run `python3 tools/check_pin.py --strict glm-5.3-flash/dgx-spark/1x/exlr8-gr8`,
  `python3 tools/lint_recipe.py --strict glm-5.3-flash/dgx-spark/1x/exlr8-gr8`, and `./check-config.sh` inside this
  folder before you commit.

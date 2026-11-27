# For agents: boot DeepSeek-V4.1-Flash on 4× DGX Spark

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and tell
the person what failed. If this file and `knobs.sh`, `compose.yaml` or `.env.example` disagree, follow those files and
tell the person. If you cannot run a check yourself, ask the person to run it and paste the output.

This recipe is the folder `deepseek-v4.1-flash/dgx-spark/4x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe deepseek-v4.1-flash-exlr8-4x-spark` (or a sparse clone of the monorepo) on all four boxes and
run the commands from inside the folder. This recipe runs `gr8`'s published image (`ghcr.io/kindlingai/gr8:v1.3.1`,
pinned by digest in `compose.yaml`) directly with read-only mounts for `entrypoint.sh`, `knobs.sh`, and `fetch-release.sh`,
plus the shipped `seccomp-iouring.json` profile; nothing is compiled here.

## 1. Check the four boxes

On every box:

- It is a DGX Spark (GB10, 128 GB). All four are on one 200G switch, or cabled in a ring (README.md, Clustering).
- Docker and the NVIDIA container toolkit are installed (both come with DGX OS): `docker info | grep -i nvidia` shows
  the `nvidia` runtime.
- 510.6 GB of disk is free where Docker keeps volumes, for `ds41-release`:
  `df -h "$(docker info --format '{{.DockerRootDir}}')"`. Or set `RELEASE_DIR` in `.env` to a host directory on local
  NVMe owned by uid 1000. `.env.example` also turns on the gen cache (`GR8_GEN_CACHE=/var/lib/gr8/home/gen-cache`),
  which needs ~80 GB in `ds41-home` (`GR8_HOME_DIR`), up to ~160 GB once two cache keys exist.
- Hugging Face answers: `curl -sI https://huggingface.co`.
- TCP ports 7340 and 7341 are open between all four boxes (verify in both directions on `PEERS`, `IPS`, `IPS2` with a
  python socket listener and `timeout 5 bash -c 'exec 3<>/dev/tcp/<peer>/7340'`).
- No other model runs on the box: `docker ps` and `nvidia-smi` show none.
- Proactive memory compaction is off: `sysctl vm.compaction_proactiveness` prints `0`. If not, as root, once:

  ```bash
  echo 'vm.compaction_proactiveness = 0' > /etc/sysctl.d/90-gr8-no-proactive-compaction.conf
  sysctl -w vm.compaction_proactiveness=0
  ```

- Fabric configuration (one of):
  - With `mentat` on every box (`docker ps` shows `mentat`): set `MENTAT=1`, leave `PEERS`, `IPS`, `IPS2` commented out.
  - On a switch without `mentat`: collect all four boxes' 10G LAN addresses (`PEERS`, head first), root-1 ConnectX
    addresses (`IPS`), and root-2 addresses (`IPS2`), in identical order. Check `ip -br addr` and `ls /dev/infiniband`.
  - In a ring without a switch: set `SHAPE=ring` and `PEERS` in cable order (each box's f0 to next box's f1), no
    `IPS`/`IPS2`.

## 2. Write .env and pick settings

Copy `.env.example` to `.env` on all four boxes (the `npx @kindlingai/recipe` CLI already did) and keep all four `.env`
files identical. Uncomment and fill in `PEERS`, `IPS`, `IPS2` (or set `MENTAT=1`).

`TUNE` picks what to prioritize. Keep `TUNE=speed` unless the person asks for `context` or `quality`:

| `TUNE` | what `knobs.sh` sets | what it gives |
|---|---|---|
| `speed` (default) | fast-mode switches (`GR8_DS_RELAXED_ACCEPT`, `GR8_DS_MOE_TOPK_DECODE=4`, `GR8_DS41_HEAD_MX=1`, `GR8_DS_ATTN_TC_MF=2`, `GR8_DS_CACHE_MIB=1024`, `GR8_DS_ENGRAM_CACHE_MIB=2048`) + gr8 v2 12K prefill stack, `SESS=32`, `CAP=327680` | fast mode: 32 chats up to 327,670 tokens (not bit-identical to exact) |
| `context` | fast-mode switches + `GR8_DS_ATTN_TC_TILE=1`, `GR8_DS_MHC_ROW_SHARD=1`, `GR8_DS_CACHE_MIB=2048`, `SESS=16`, `CAP=1048576` | fast mode: 16 chats, one up to 1,048,566 tokens |
| `quality` | `EXACT=1`, `SESS=5`, `CAP=262144` (old prefill path, no fast-mode switches) | exact model output: 5 chats up to 262,134 tokens |

What else `knobs.sh` and `gr8` do:

- Engram is always on (`GR8_DS_ENGRAM=1`, `GR8_DS_ENGRAM_PREFIX=/var/lib/gr8/home/engram/ds41`). On first boot, `gr8`
  automatically generates and verifies `/var/lib/gr8/home/engram/ds41.engram.cmap` from `<release>/tokenizer.json`
  against `kCmapSha256` via `bin/g6front-rs engram-cmap` (no PyTorch or manual cmap step needed).
- `SESS` above 5 adds `GR8_DS_SESS_DRAFTS=1`.
- Any explicit `CAP`, `SESS`, or `EXTRA_ENV` key in `.env` wins over `knobs.sh`'s default.
- `.env.example` enables `EXTRA_ENV=GR8_GEN_CACHE=/var/lib/gr8/home/gen-cache` (~80 GB per cache key, keeps two keys).
  Warn the person before switching `TUNE` between `quality` and `speed`/`context`, as that writes a new ~80 GB cache key.
- `EXACT` set directly in `.env` is refused (exit 2) with a pointer to `TUNE=quality` / `TUNE=speed`.

## 3. Boot

1. On **every box**, fetch the 510.6 GB release (604 files) using the one-shot `fetch` service. Wait for all four boxes
   to finish before starting `gr8`:

   ```bash
   docker compose run --rm fetch
   ```

   Re-running resumes and verifies every file's hash. If migrating an old pre-hash record fails on any file, run
   `docker compose run --rm fetch --force` on that box.

2. Optional (no GPU needed): run `./check-config.sh` (or pass a `GR8_IMAGE` argument) to verify `compose.yaml`,
   `seccomp-iouring.json`, `.env.example`, and `knobs.sh`, or inspect the resolved config:

   ```bash
   docker compose run --rm --no-deps gr8 show-config --no-check
   ```

3. Start the container on all four boxes within 10 minutes (`JOIN_TIMEOUT=600` s):

   ```bash
   docker compose up -d
   docker compose logs -f
   ```

   `compose.yaml` applies `./seccomp-iouring.json` automatically for Engram `io_uring`. If Docker rejects the profile on
   an unusual host kernel, set `SECCOMP_PROFILE=builtin` in `.env` (Engram falls back to `pread` automatically).

4. To change `TUNE` or any knob later: `docker compose down` on all four boxes, edit `.env` identically on all four,
   and `docker compose up -d`.

## 4. Check that it serves

Wait for `serving:` in the head's log (`docker compose logs -f`), then verify:

- On every box: `docker compose exec gr8 /opt/ds41-4x/entrypoint.sh health` exits 0, and `docker compose ps` shows
  `healthy`.
- `docker compose exec gr8 /opt/ds41-4x/entrypoint.sh status` shows all four boxes' state, engine, and free memory.
- On the head: `docker compose exec gr8 /opt/ds41-4x/entrypoint.sh smoke` checks the API including tool calls (exits 0).
- On the head: `curl -s localhost:8100/v1/models` lists `deepseek-v4.1-flash`, and one chat completion succeeds:

  ```bash
  curl -s localhost:8100/v1/chat/completions -H 'Content-Type: application/json' -d '{
    "model": "deepseek-v4.1-flash",
    "messages": [{"role": "user", "content": "Write a haiku about a small computer."}],
    "max_tokens": 4096
  }'
  ```

## 5. Stop

On every box:

```bash
docker compose down
```

## 6. When a step fails

| what you see | what to do |
|---|---|
| `PEERS=...: want the four boxes' LAN addresses ...` | set four addresses in `PEERS` (identical on all boxes) or `MENTAT=1` |
| `ds41-4x: the release in ... is not whole: run the fetch first` | run `docker compose run --rm fetch` on that box |
| `ds41-4x: the fetch record ... was not migrated` | run `docker compose run --rm fetch --force` on that box |
| `MISMATCH <file>: ...` | run `docker compose run --rm fetch` to re-download the damaged file |
| `engram: .../ds41.engram.cmap: sha256 ... != expected ...` | delete the corrupt `.engram.cmap` in `ds41-home/engram/` and restart so `gr8` regenerates and verifies it |
| `TUNE=...: want speed ..., context ... or quality ...` | use `speed`, `context`, or `quality` |
| `EXACT=...: EXACT is now TUNE ...` | remove `EXACT`; set `TUNE=quality` or `TUNE=speed` |
| `SESS=...: want a number of chats, 1 or more` | set `SESS` to 1..32, no leading zero |
| `gr8: memlock is limited ...` | keep `ulimits.memlock: -1` in `compose.yaml` |
| `gr8: ... is not writable by uid 1000 ...` | `chown 1000:1000` on host `GR8_HOME_DIR` / `RELEASE_DIR` |
| a box never joins | start all four within 600 s; verify identical `.env` and open ports 7340/7341 |

Exit codes: 0 clean stop, 1 rank failed / join timeout, 2 bad options or missing release, 4 handshake refused. Logs:
`docker compose logs` or `docker compose exec gr8 /opt/ds41-4x/entrypoint.sh logs supervisor` (`shim` / `front`).

## 7. Not measured yet: tell the person

- Confirmation on published `gr8 v1.3.1` (`kindlingai/gr8#630`: `DS41_MX=48` + first-boot `g6front-rs engram-cmap`):
  `kindling.json` and `docs/card.png` are from 2026-11-11 on `gr8 c2220f2`, and the extended tables in `README.md` are
  from `gr8 43cad38` / `0015fd0`.
- `TUNE=context` 1M recall and multi-1M concurrency have not been re-measured on the current build.
- `TUNE=quality` has not been measured on the `DS41_MX=48` build.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count, and the engine
  build. Do not copy a number from another build without noting its source build.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and the card
  (`docs/card.png`) is redrawn from `kindling.json`.
- The engine pin is one exact commit and one image digest (`@sha256:...`). Never a moving tag alone once published,
  never a local Dockerfile build. Engine changes go to `kindlingai/gr8` first; this recipe then moves its pin to the
  published image.
- From the monorepo root, run `python3 tools/check_pin.py --strict deepseek-v4.1-flash/dgx-spark/4x/exlr8-gr8`,
  `python3 tools/lint_recipe.py deepseek-v4.1-flash/dgx-spark/4x/exlr8-gr8`, and `./check-config.sh` inside this folder
  before you commit.

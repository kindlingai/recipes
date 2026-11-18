# For agents: boot Sage-S2.1-Flash on four DGX Sparks

You are booting this recipe for someone. This file is the end-to-end quickstart from clone to a served, tested endpoint,
with every knob and how to check each step. It is derived from `README.md`, `knobs.sh`, `.env.example`, `compose.yaml`,
`Dockerfile`, and `gr8` (the `gr8/` submodule). If this file and `knobs.sh` or `compose.yaml` disagree, follow
`knobs.sh` and `compose.yaml` and tell the person. Do not skip checks.

## 1. Check the four boxes

On all four boxes:

- All four boxes are DGX Sparks or other GB10 boxes (128 GB unified memory), connected on a 200G switch (`SHAPE=mesh`,
  default) or directly cabled in a ring (`SHAPE=ring`; see `README.md`, Clustering).
- Docker and the NVIDIA container toolkit are installed: `docker info | grep -i nvidia` shows the `nvidia` runtime.
- Free disk where Docker keeps volumes: about 47 GB per box for this box's part of the `k4` release, plus up to 64 GB
  for the prompt cache. Check with `df -h "$(docker info --format '{{.DockerRootDir}}')"`. With compose, you can set
  `MODEL_CACHE_DIR` and `PROMPT_CACHE_DIR` to host directories owned by uid 1000 instead.
- Hugging Face is reachable: `curl -sI https://huggingface.co` answers.
- No other model is running: `docker ps` shows no other model container and `nvidia-smi` shows no GPU process. `gr8`
  refuses to start while another `gr8` engine runs on the box.
- TCP ports 7340 and 7341 are open between all four boxes (no firewall blocking them). Test while nothing listens:

  On any non-head box:
  ```bash
  python3 -c 'import socket; s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("", 7340)); s.listen(1); print("ACCEPTED from", s.accept()[1])'
  ```
  On the head:
  ```bash
  timeout 5 bash -c 'exec 3<>/dev/tcp/<box>/7340' && echo OPEN || echo BLOCKED
  ```
  Repeat for port 7341 across all pairs.
- Proactive memory compaction is off: `sysctl vm.compaction_proactiveness` prints `0`. If not, run once as root:
  ```bash
  echo 'vm.compaction_proactiveness = 0' > /etc/sysctl.d/90-gr8-no-proactive-compaction.conf
  sysctl -w vm.compaction_proactiveness=0
  ```
- Fabric addresses (choose one):
  - With `mentat`: `docker ps` shows `mentat` on all four boxes. Set `MENTAT=1` and omit `PEERS`, `IPS`, `IPS2`.
  - Switch (`SHAPE=mesh`, default): collect all four boxes' 10G LAN addresses (`PEERS`, head first), PCIe root-1
    ConnectX addresses (`IPS`), and PCIe root-2 ConnectX addresses (`IPS2`) in the same order. Check with `ip -br addr`
    and `ls /dev/infiniband`.
  - Direct ring (`SHAPE=ring`): list `PEERS` in cable order (each box's `f0` port cabled to the next box's `f1` port)
    and leave `IPS` and `IPS2` unset.

## 2. Clone and configure

Use the exact same `.env` on all four boxes.

```bash
git clone --recurse-submodules https://github.com/kindlingai/sage-s2.1-flash-exlr8-4x-spark
cd sage-s2.1-flash-exlr8-4x-spark
cp .env.example .env
```

Edit `.env` on all four boxes to uncomment and set `PEERS`, `IPS`, `IPS2` (or `PEERS` + `SHAPE=ring`, or `MENTAT=1`).
Pick `TUNE` only if the person asks for something other than the default (`speed`):

| `TUNE` | sets (`knobs.sh`) | use when |
|---|---|---|
| `speed` (default) | `VARIANT=k4`, `SESS=8`, `CAP=262208`, `MAX_MODEL_LEN=262144`, `MTP=2`, `S2_SHARED_WATERFILL=1` | default 4-Spark serving (8 concurrent sessions, 256K max context) |
| `context` | `VARIANT=k4`, `SESS=8`, `CAP=2097152`, `MAX_MODEL_LEN=1048576`, `MTP=2`, `S2_SHARED_WATERFILL=1`, `GR8_CP=1` | long context up to 1M tokens / 8 concurrent sessions (experimental) |
| `quality` | `VARIANT=k4`, `SESS=8`, `CAP=262208`, `MAX_MODEL_LEN=262144`, `MTP=1` | strict `MTP=1` baseline |

All knobs:

| knob | values | default |
|---|---|---|
| `PEERS` | four 10G LAN addresses, comma-separated, head first, identical on all four boxes | required unless `MENTAT=1` |
| `IPS`, `IPS2` | ConnectX addresses on PCIe root 1 and root 2, in `PEERS` order | none |
| `SHAPE` | `mesh` (switch) or `ring` (direct ring cable) | `mesh` |
| `TUNE` | `speed`, `context`, `quality` | `speed` |
| `VARIANT` | `k4` (or a custom manifest path) | `k4` |
| `SESS` | concurrent decoding sessions, 1 to 8 | `8` |
| `CAP` | KV pool in tokens, multiple of 64 | `262208` (`2097152` for `context`) |
| `MAX_MODEL_LEN` | max single request tokens (`<= CAP` less guard rows, `<= 1048576`) | `262144` (`1048576` for `context`) |
| `MTP` | MTP draft depth (`SESS * (MTP + 1) <= 32`) | `2` (`1` for `quality`) |
| `S2_SHARED_WATERFILL` | `1` or `0` | `1` (`speed`/`context`), unset (`quality`) |
| `DFLASH` | `0` (MTP only; no drafter configured by default) | `0` |
| `FLASH_CACHE` | `aligned` (disk + spare RAM prompt checkpoints via `kv-store.yaml`) | `aligned` |
| `MENTAT` | `0` (use `PEERS`) or `1` (discover peers via host `mentat`) | `0` |
| `GROUP` | `mentat` group name when `MENTAT=1` | `gr8-sage-4x` |
| `EXTRA_ENV` | space-separated engine `NAME=VALUE` pairs; text-only by default (`GR8_GLM53F_VISION=1` opts into untested vision weights) | unset (`GR8_CP=1` added for `TUNE=context`) |
| `DEFAULT_MAX_TOKENS` | default `max_tokens` when omitted by client | `32768` |
| `UNDECLARED_TOOL_CALLS` | `emit` or `text` | `emit` |
| `MODEL` | `https://huggingface.co/<org>/<repo>@<commit>` | pinned Sage `k4` commit |
| `HF_TOKEN` | token for gated/private HF repos | none |
| `IMAGE` | compose only: override image tag | `ghcr.io/kindlingai/sage-s2.1-flash-exlr8-4x-spark:latest` |
| `MODEL_CACHE_DIR`, `PROMPT_CACHE_DIR`, `GR8_HOME_DIR` | compose only: host paths owned by uid 1000 | compose named volumes |

## 3. Preflight and boot

1. Verify resolved options on all four boxes (rank 0 is head):
   ```bash
   docker compose run --rm gr8 show-config --no-check
   ```
   (Or with `docker run`: `docker run --rm --network host -e PEERS=<head>,<box2>,<box3>,<box4> ghcr.io/kindlingai/sage-s2.1-flash-exlr8-4x-spark:latest show-config --no-check`.)
2. Run preflight checks on all four boxes (on first boot, only missing model cache files should appear as `FAIL`):
   ```bash
   docker compose run --rm gr8 check
   ```
3. Start all four boxes within 600 s (`JOIN_TIMEOUT`) of each other:
   ```bash
   docker compose up -d
   ```
   (Use `docker compose up -d --build` to build locally from the `gr8/` submodule instead of pulling from GHCR.)
4. Follow logs on the head until `serving: http://...` appears:
   ```bash
   docker compose logs -f
   ```

## 4. Verify the served endpoint

Run all checks after `serving:` appears on the head:

1. Health on all four boxes:
   ```bash
   docker compose exec gr8 gr8 glm53f health
   curl -s -o /dev/null -w '%{http_code}\n' localhost:8100/health   # expect 200 on head
   ```
2. Cluster status:
   ```bash
   docker compose exec gr8 gr8 glm53f status
   ```
3. Built-in smoke test (head, expect `14/14 passed` and exit 0):
   ```bash
   docker compose exec gr8 gr8 glm53f smoke
   ```
4. Live OpenAI-compatible chat request (head, port 8100; served model name is `glm-5.3-flash`, `glm53f` also works):
   ```bash
   curl -s localhost:8100/v1/chat/completions -H 'Content-Type: application/json' -d '{
     "model": "glm-5.3-flash",
     "messages": [{"role": "user", "content": "Write a haiku about a small computer."}],
     "max_tokens": 4096
   }'
   ```
   Verify HTTP 200 and non-empty `choices[0].message.content` (thinking appears in `message.reasoning` and counts toward `max_tokens`).
5. Optional benchmark (head, pass `--hosts ''` because the container has no `ssh`):
   ```bash
   docker compose exec gr8 gr8 glm53f bench --quick --stages info,concurrency --streams 1,2,4,8 --hosts ''
   ```
6. To stop cleanly on all four boxes:
   ```bash
   docker compose down
   ```

## 5. Troubleshooting

| symptom | fix |
|---|---|
| `TUNE=...: want speed (the default), context or quality` | set `TUNE` to `speed`, `context`, or `quality` |
| `PEERS=...: want the four boxes' LAN addresses...` | set four comma-separated LAN IPs in `PEERS` (identical on all four boxes), or `MENTAT=1` |
| `MENTAT=...: want 0 ... or 1` | set `MENTAT=0` or `MENTAT=1` |
| `gr8: memlock is limited` | ensure `ulimits.memlock: -1` (compose) or `--ulimit memlock=-1` (`docker run`) |
| `gr8: ... is not writable by uid 1000` | `chown 1000:1000` on host volume directories |
| `an engine is already running` | stop the other model container first |
| `handshake refused: join: ... did not answer within 600s` | start all four boxes within 600 s; check `PEERS` matches and ports 7340/7341 are open |
| `handshake refused: ...` | ensure `.env` and image digest are identical on all four boxes |
| image fails to pull | run `docker compose build` on all four boxes from a clone with `--recurse-submodules` |

Logs while running: `docker compose exec gr8 gr8 glm53f logs supervisor` (or `shim`, `front`, or no arg for engine).

## 6. Pending measurements

- Clean-clone 4-Spark benchmark rows (single-stream, multi-stream, prefill, boot time) on this exact pin.
- Vision tower (`GR8_GLM53F_VISION=1`) is untested with this recipe; default is text-only.
- Fast switching (`GR8_LOAD_COMPACT` + `GR8_LOAD_MERGE_KB=1`) and remote KV tier are planned next steps.

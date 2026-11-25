# KindlingAI: Sage-S2.1-Flash EXLR8 on two DGX Sparks

If you are an agent booting this for someone, read [AGENTS.md](AGENTS.md) first, then the Quickstart.

_**Join our discord to learn more about KindlingAI and `gr8`: https://discord.gg/8EAvYPV2rE**_

Sage-S2.1-Flash on two DGX Sparks (GB10, 128 GB each) at TP=2, served by [gr8](https://github.com/kindlingai/gr8) from
the `k4` manifest of [kindlingai/sage-s2.1-flash-exlr8-k4](https://huggingface.co/kindlingai/sage-s2.1-flash-exlr8-k4).
For a four-box deployment, see [sage-s2.1-flash-exlr8-4x-spark](../../4x/exlr8-gr8).

![Sage-S2.1-Flash on two GB10s: decode, prefill and concurrency](docs/card.png)

![Four requests decoding at once on two GB10s, at 2x speed](docs/concurrency-4.gif)

## What you need

- Two Sparks joined by a 200G cable between their ConnectX ports (see Clustering).
- Docker and the NVIDIA container toolkit on each box (both come with DGX OS).
- Free disk where Docker keeps volumes: about 82 GiB (~88 GB) per box for this box's part of the `k4` release, plus up
  to 64 GB for the prompt cache (`kv-store.yaml`).
- No other model running on either box.
- A LAN between the two boxes, with TCP ports 7340 and 7341 open.
- Proactive memory compaction off on each box, once, as root (it holds across reboots):

  ```bash
  echo 'vm.compaction_proactiveness = 0' > /etc/sysctl.d/90-gr8-no-proactive-compaction.conf
  sysctl -w vm.compaction_proactiveness=0
  ```

## Clustering

Give each box one address per PCIe root. The Spark's ConnectX card shows each physical port twice, once on each PCIe
root, and the engines use both. Run `ip -br link` on each box to list your port names; the names in the example below
(`enp1s0f0np0` and `enP2p1s0f0np0`) are examples, so use yours. `mtu: 9000` (jumbo frames) must be set on both boxes,
and any switch between them must pass it. For a cable on the first port, with netplan:

```yaml
# /etc/netplan/60-connectx.yaml on the first box. On the second box: 10.0.0.2 and 10.0.1.2.
network:
  version: 2
  ethernets:
    enp1s0f0np0:        # the first port on PCIe root 1
      addresses: [10.0.0.1/24]
      mtu: 9000
    enP2p1s0f0np0:      # the same port on PCIe root 2
      addresses: [10.0.1.1/24]
      mtu: 9000
```

Then run `sudo netplan apply` on each box.

Two kinds of address are used below:

- The 10G LAN address is the box's address on your network (the Spark's 10G Ethernet port). `PEERS` holds the two
  boxes' 10G LAN addresses, head first, and the head serves the API on its LAN address.
- The ConnectX addresses are the ones you gave the ConnectX ports in the netplan file (`10.0.0.x` on PCIe root 1,
  `10.0.1.x` on PCIe root 2 in the example). `IPS` holds the two boxes' root-1 addresses and `IPS2` their root-2
  addresses.

With [`mentat`](https://github.com/kindlingai/mentat) running on each box, the recipe finds the other box and its
ConnectX addresses by itself. On each box:

```bash
docker run -d --name mentat --network host --restart unless-stopped ghcr.io/kindlingai/mentat:0.27.0
```

Then start the recipe with `MENTAT=1` in place of `PEERS`, `IPS` and `IPS2`.

Without `mentat`, set the two boxes' 10G LAN addresses in `PEERS` (head first), and the matching ConnectX addresses in
`IPS` (PCIe root 1) and `IPS2` (PCIe root 2), in the same order. In `.env.example` these three lines are commented
out, with placeholders: edit them and remove the `#` from each.

## Quickstart

Run the published image on both boxes with the same settings. Without `mentat`, replace `<head>` and `<box2>` with the
two boxes' 10G LAN addresses, the same list on both boxes. The head is the first box in `PEERS`: it serves the API on
port 8100. `IPS` and `IPS2` are the ConnectX addresses from the netplan example above: use yours.

```bash
docker run -d --name sage-2x-spark --gpus all --network host --pid host --device /dev/infiniband \
  --ulimit memlock=-1 --ulimit core=0 --cap-drop ALL --cap-add IPC_LOCK \
  --security-opt no-new-privileges --read-only --tmpfs /tmp:size=1g,mode=1777 --init --oom-score-adj 1000 \
  -e PEERS=<head>,<box2> -e IPS=10.0.0.1,10.0.0.2 -e IPS2=10.0.1.1,10.0.1.2 \
  -v sage-2x-cache:/var/lib/gr8/cache -v sage-2x-prompts:/var/lib/gr8/prompts -v sage-2x-home:/var/lib/gr8/home \
  ghcr.io/kindlingai/sage-s2.1-flash-exlr8-2x-spark:latest
docker logs -f sage-2x-spark     # on the head: ready at "serving: http://..."
```

With `mentat` running, replace the `PEERS`, `IPS` and `IPS2` settings with `-e MENTAT=1`. The head is then the box
with the lowest address.

The first boot downloads each box's part from Hugging Face into the `sage-2x-cache` volume (about 82 GiB per box). The
boxes wait up to 600 s (10 minutes) for each other, so start both within that time.

The API is OpenAI-compatible on the head's port 8100. Because `gr8 glm53f` serves the Flash engine architecture, the
served model name is `glm-5.3-flash` (`glm53f` also works):

```bash
curl -s localhost:8100/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "glm-5.3-flash",
  "messages": [{"role": "user", "content": "Write a haiku about a small computer."}],
  "max_tokens": 4096
}'
```

The model thinks before it answers. The thinking comes back in `message.reasoning` and counts toward `max_tokens`.

```bash
docker exec sage-2x-spark gr8 glm53f smoke   # on the head: 14 checks against the API
docker stop sage-2x-spark && docker rm sage-2x-spark   # on both boxes
```

`:latest` is `main`. Each commit is also published as `sha-<commit>`, and each git tag
`sage-s2.1-flash-exlr8-2x-spark/<name>` as `<name>`.

## Run it with compose

`compose.yaml` runs the same image with the same settings and reads `PEERS` and the knobs from `.env`. On both boxes:

```bash
npx @kindlingai/recipe sage-s2.1-flash-exlr8-2x-spark --engine && cd sage-s2.1-flash-exlr8-2x-spark
# the CLI already copied .env.example to .env; edit it: set PEERS, IPS and IPS2 and remove their #, the same file on both boxes
docker compose up -d
docker compose logs -f
```

`docker compose up -d --build` builds the image on the box instead, from the engine source that `--engine` put in
`gr8/`: gr8 at the commit `kindling.json` pins (`engine.commit`). In a clone of the monorepo,
`tools/engine.sh sage-s2.1-flash/dgx-spark/2x/exlr8-gr8` (from the root) puts it there.

This recipe lives in [kindlingai/recipes](https://github.com/kindlingai/recipes/tree/main/sage-s2.1-flash/dgx-spark/2x/exlr8-gr8)
at `sage-s2.1-flash/dgx-spark/2x/exlr8-gr8`; a [sparse clone](https://github.com/kindlingai/recipes#run-a-recipe) also
works.

## Knobs

Set these in `.env` next to `compose.yaml` (see `.env.example`), or with `docker run -e`, the same on both boxes:

| knob | default | |
|---|---|---|
| `TUNE` | `speed` | What to prioritize, see below. Sets defaults of `VARIANT`, `SESS`, `CAP`, `MAX_MODEL_LEN`, `MTP` and `S2_SHARED_WATERFILL`. Any other value stops the boot. |
| `PEERS` | none | The two boxes' 10G LAN addresses, head first. Required unless `MENTAT=1`. |
| `IPS`, `IPS2` | none | Each box's ConnectX address on PCIe root 1 and root 2, in `PEERS` order. |
| `VARIANT` | `k4` | The release's width manifest (`k4`). |
| `SESS` | `4` (`8` with `TUNE=context`) | The requests that decode at once, 1 to 8. |
| `CAP` | `262208` | The KV pool in tokens, shared by the sessions. Each request reserves its prompt + `max_tokens` from it. |
| `MAX_MODEL_LEN` | `262144` | The longest single request, prompt and output together. At most `CAP` less the guard rows. |
| `MTP` | `2` (`1` with `TUNE=quality`) | Speculative draft depth. `MTP=2` with `S2_SHARED_WATERFILL=1` is bit-exact to `MTP=1` on the pinned build. |
| `DFLASH` | `0` | `0` uses MTP only and downloads no drafter. |
| `FLASH_CACHE` | `aligned` | Prompt checkpoint cache on disk + spare RAM (`kv-store.yaml`, up to 64 GB per box). Checkpoints align to the 8,192-token prefill grid (`--prefill 4096 x 2 lanes`), so prompts of 8,192 tokens or fewer keep none (`gr8 bench`'s ~400-token short-prompt cache report returns 0/425 cached by design, while longer prompts > 8,192 tokens cache cleanly). |
| `MENTAT` | `0` | `1` finds the other box and ConnectX addresses through the host's `mentat` daemon, and registers the API in group `GROUP` (`gr8-sage-2x`). |
| `GR8_GLM53F_VISION` in `EXTRA_ENV` | unset (off) | Text-only by default. The HF release includes `dense/vision-bf16.safetensors` (1.13 GB), untested with this recipe; set `EXTRA_ENV="GR8_GLM53F_VISION=1"` on both boxes to opt in. |
| `DEFAULT_MAX_TOKENS` | `32768` | `max_tokens` for a request that sends none, or the room the context leaves if that is less. |
| `UNDECLARED_TOOL_CALLS` | `emit` | A call to a tool the request did not declare comes back as a tool call, so your agent can answer it with an unknown-tool error. `text` leaves it in the reply's text. |

The image pins the weights to a fixed Hugging Face commit. Set `MODEL` in `.env` to change it
(`https://huggingface.co/<org>/<repo>@<commit>`).

[gr8/KNOBS.md](https://github.com/kindlingai/gr8/blob/ca7e8745bfed31d4417d263ff1bc14dd59919f9c/KNOBS.md) lists the
advanced `gr8` options, which you can also set in `.env`.

## Pick what to prioritize

`TUNE` picks one of three settings. When you set `VARIANT`, `SESS`, `CAP`, `MAX_MODEL_LEN`, `MTP` or
`S2_SHARED_WATERFILL` yourself, your value wins.

| `TUNE` | sets |
|---|---|
| `speed` (default) | `VARIANT=k4`, `SESS=4`, `CAP=262208`, `MAX_MODEL_LEN=262144`, `MTP=2`, `S2_SHARED_WATERFILL=1` |
| `context` | `VARIANT=k4`, `SESS=8`, `CAP=262208`, `MAX_MODEL_LEN=262144`, `MTP=2`, `S2_SHARED_WATERFILL=1`, and context-parallel KV (`GR8_CP=1`, experimental) |
| `quality` | `VARIANT=k4`, `SESS=4`, `CAP=262208`, `MAX_MODEL_LEN=262144`, `MTP=1`, `S2_SHARED_WATERFILL=0` |

With bit-exact shared waterfill `MTP=2` drafting (`S2_SHARED_WATERFILL=1`, `MTP=2`, `DFLASH=0`), `TUNE=speed` boots warm
in 24 s and measures 55.1 / 41.8 / 56.0 tok/s single-stream decode (code / prose / structured), 1,832 / 1,775 / 1,627
tok/s cold prefill (8K / 32K / 128K), and 47.9 / 66.6 / 79.8 tok/s aggregate concurrency (1 / 2 / 4 streams; paired
quick ruler: 48.3 / 64.4 / 78.5 and 47.9 / 66.3 / 78.7 tok/s) against 44.5 / 60.8 / 74.2 tok/s at `MTP=1`. With
`SESS=8`, aggregate concurrency reaches 94.1 tok/s at 8 streams (48.6 / 66.5 / 77.4 / 94.1 tok/s at 1 / 2 / 4 / 8
streams).

## Compact expert copies

Optional, and off by default. `GR8_LOAD_COMPACT` and `GR8_LOAD_MERGE_KB=1` in `EXTRA_ENV` make the loader read dense
per-rank copies of its expert ranges in place of the release's sparse files. The bytes it loads are the same, and a
boot from a cold disk was faster in our runs.

To turn it on, on both boxes: remove the `#` from the compact-copies `EXTRA_ENV` line in `.env` (`.env.example` has it
commented out), write the copies once, then start or restart the recipe. Write the copies before the first boot or with
the recipe stopped (`prepare` writes files and starts no engine). With compose:

```bash
docker compose run --rm gr8 prepare               # on both boxes
docker compose run --rm gr8 prepare --rank 0      # with MENTAT=1 instead: the rank is only decided at boot, so name it
                                                  # (rank 0 on the head, rank 1 on the other box)
```

`prepare` first fetches and checks the model as a boot does. It then writes this box's expert ranges to
`/var/lib/gr8/cache/compact-tp2` (the cache volume), reads every copy back through the loader's map and checks it. A
directory that already exists is checked and reused, never overwritten. A boot never writes or refreshes copies.

- **Disk:** 72.8 GiB (78.2 GB) a box: 43 copy files and their 43 maps. `prepare` took 170 s a box. They sit beside the
  release, which stays. Run `prepare` on a disk with room: copies written onto a nearly full disk can fragment and read
  slower.
- **`EXTRA_ENV` holds one line.** If you also set another engine variable there (such as `GR8_GLM53F_VISION=1`), put
  both in the same line, on both boxes.
- **A different `VARIANT`, TP size or release** needs its own directory: set `GR8_LOAD_COMPACT` to a new path in
  `EXTRA_ENV` on both boxes and run `prepare` again.
- **Both boxes** need the same `EXTRA_ENV`. With `docker run`, add
  `-e EXTRA_ENV="GR8_LOAD_COMPACT=/var/lib/gr8/cache/compact-tp2 GR8_LOAD_MERGE_KB=1"` and the same volumes as the boot
  command to a `docker run --rm ... prepare --rank <0 or 1>` command, and add it to the boot command in the Quickstart,
  on both boxes: the copies are read only with it.
- **To turn it off again,** comment out the line in `.env` on both boxes and restart. The copies stay in the volume. To
  free the 72.8 GiB, delete the `compact-tp2` directory in the cache volume.

Measured on 2026-11-18 (Pacific time) on two DGX Sparks at TP=2, this recipe on gr8 `ca7e874`, `TUNE=speed`. Before
every boot the page cache was dropped on both boxes (`echo 3 > /proc/sys/vm/drop_caches`), so each boot read from disk.
The order was stock, knob, knob, stock. The total is from `docker run` until `/health` reports ready; the read time is
the loader's own for one rank:

| Boot from a cold disk | Total (n=2) | A rank's read |
|---|---|---|
| Stock | 29.4 / 29.0 s | 21.9-22.3 s (4.1 GB/s) |
| `GR8_LOAD_COMPACT` with `GR8_LOAD_MERGE_KB=1` | 18.6 / 18.5 s | 11.9-12.3 s (7.3-7.6 GB/s) |
| `GR8_LOAD_MERGE_KB=1` alone, no copies (n=1) | 28.6 s | 22.1-22.3 s |

The copies pay only together with `GR8_LOAD_MERGE_KB=1`. The same 10 fixed greedy prompts gave the same token ids as
the stock arm, 10 of 10. A warm boot (the release already in the page cache) was not measured with the copies.

## Remote KV store

Optional, and off by default. The prompt cache can keep its checkpoints on a KV node instead of the local disk: a box
that locks some of its memory and serves it as KV blocks over RDMA (`./gr8 kv`, gr8's
[engine/kvman-rs/REMOTE-TIER.md](https://github.com/kindlingai/gr8/blob/ca7e8745bfed31d4417d263ff1bc14dd59919f9c/engine/kvman-rs/REMOTE-TIER.md)).

1. Start the node on the box that gives the memory. `--gb` is what it locks; keep room for that box's own work
   (`--min-free-gb`):

   ```bash
   docker run -d --name sage-kv-node --network host --pid host --device /dev/infiniband \
     --ulimit memlock=-1 --ulimit core=0 --cap-drop ALL --cap-add IPC_LOCK \
     --security-opt no-new-privileges --read-only --tmpfs /tmp:size=256m,mode=1777 --init \
     -v sage-kv-home:/var/lib/gr8/home --entrypoint /opt/gr8/gr8 \
     ghcr.io/kindlingai/sage-s2.1-flash-exlr8-2x-spark:latest \
     kv up --gb 4 --port 7350 --bind 0.0.0.0 --min-free-gb 6 --mentat none \
       --work-dir /var/lib/gr8/home --bin /opt/gr8/bin/kvman-remote --foreground
   docker exec sage-kv-node /opt/gr8/gr8 kv status --work-dir /var/lib/gr8/home --mentat none
   ```

2. Write a `kv-store.yaml` that names the node by a ConnectX address of its box, and mount it over the shipped one
   (`-v $PWD/kv-store.yaml:/etc/gr8/kv-store.yaml:ro`) on both boxes of the recipe:

   ```yaml
   caches:
     spare: {kind: spare_ram, floor: 2G}   # optional: a copy in this box's spare RAM, read first
   tiers:
     - cache: spare
       store:
         remote: {address: 10.0.0.2:7350, size_per_rank: 1G}
   ```

   With `MENTAT=1`, `address: auto` finds the node the mentat group announces.

What to know:

- **One store.** The prompt cache keeps its checkpoints in one store: `kv-store.yaml` names either the shipped disk
  store or a remote one, not both. gr8 stops at boot with a file that names both.
- **Not kept across restarts.** The node gives each engine boot new, empty leases and frees them when the engine
  stops. The shipped disk store (`persist: true`) keeps the cache across restarts; a remote store does not.
- **Size:** `size_per_rank` is per rank, so the node needs `2 x size_per_rank` for this recipe. A 44,633-token prompt
  keeps a 40,960-row checkpoint of 282 MB a rank.

Measured on 2026-11-18 (Pacific time) on two DGX Sparks at TP=2, this recipe on gr8 `ca7e874`, `TUNE=speed`. The node
ran on the second box of the pair with `--gb 4`, and both ranks reached it over RDMA (no bytes over TCP). The same
44,633-token prompt, 64 output tokens:

| `kv-store.yaml` | first request | repeat | cached tokens on the repeat | checkpoint restore |
|---|---|---|---|---|
| remote only | 26.2 s | 3.7 s | 40,960 | 45 ms a rank |
| remote with the `spare` RAM cache | 26.7 s | 3.7 s | 40,960 | 18 ms a rank |

The repeat gave the same 64 tokens as the first request in both. After an engine restart with the node still up, the
first request found nothing (`cached_tokens` 0) and the repeat hit again. With the remote-only store, `gr8 bench
--quick` measured 48.8 / 67.8 / 79.5 tok/s at 1 / 2 / 4 streams, failed 0, the same as with the shipped store.

## Run another model

A box runs one model at a time. To switch, stop and remove this recipe's container on both boxes:

```bash
docker stop sage-2x-spark && docker rm sage-2x-spark   # compose: docker compose down
```

Each box's part stays in its `sage-2x-cache` volume, so a later start downloads nothing. To free the disk (about
82 GiB of model weights per box and up to 64 GB of prompt checkpoints), remove the volumes on both boxes:

```bash
docker volume rm sage-2x-cache sage-2x-prompts sage-2x-home   # compose: docker compose down -v
```

[gr8's Recipes](https://github.com/kindlingai/gr8#recipes) lists the other models and the number of boxes each one
needs.

## Help

Ask on Discord (https://discord.gg/8EAvYPV2rE) or open an issue in kindlingai/recipes
(https://github.com/kindlingai/recipes/issues) with `sage-s2.1-flash-exlr8-2x-spark` in the title. Include the command
you ran and the end of `docker logs sage-2x-spark`. Remove addresses and hostnames before you post.

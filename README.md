# KindlingAI: Sage-S2.1-Flash EXLR8 on two DGX Sparks

If you are an agent booting this for someone, read [AGENTS.md](AGENTS.md) first, then the Quickstart.

_**Join our discord to learn more about KindlingAI and `gr8`: https://discord.gg/8EAvYPV2rE**_

Sage-S2.1-Flash on two DGX Sparks (GB10, 128 GB each) at TP=2, served by [gr8](https://github.com/kindlingai/gr8) from
the `k4` manifest of [kindlingai/sage-s2.1-flash-exlr8-k4](https://huggingface.co/kindlingai/sage-s2.1-flash-exlr8-k4).
For a four-box deployment, see [sage-s2.1-flash-exlr8-4x-spark](https://github.com/kindlingai/sage-s2.1-flash-exlr8-4x-spark).

## Status and measured speeds

> **Pending clean-clone benchmark runs on this exact recipe pin.** Measured single-stream, multi-stream, prefill and
> boot-time rows will be added here once the clean-clone 2-Spark test matrix completes on the pinned image and release.
> No numbers are estimated or copied from other models or builds.

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

`:latest` is `main`. Each commit is also published as `sha-<commit>`, and each tag under its name.

## Run it with compose

`compose.yaml` runs the same image with the same settings and reads `PEERS` and the knobs from `.env`. On both boxes:

```bash
git clone --recurse-submodules https://github.com/kindlingai/sage-s2.1-flash-exlr8-2x-spark
cd sage-s2.1-flash-exlr8-2x-spark
cp .env.example .env          # edit PEERS, IPS and IPS2 and remove their #: the same file on both boxes
docker compose up -d
docker compose logs -f
```

`docker compose up -d --build` builds the image on the box instead.

## Knobs

Set these in `.env` next to `compose.yaml` (see `.env.example`), or with `docker run -e`, the same on both boxes:

| knob | default | |
|---|---|---|
| `TUNE` | `speed` | What to prioritize, see below. Sets defaults of `VARIANT`, `SESS`, `CAP`, `MAX_MODEL_LEN` (and `MTP=1` for `quality`). Any other value stops the boot. |
| `PEERS` | none | The two boxes' 10G LAN addresses, head first. Required unless `MENTAT=1`. |
| `IPS`, `IPS2` | none | Each box's ConnectX address on PCIe root 1 and root 2, in `PEERS` order. |
| `VARIANT` | `k4` | The release's width manifest (`k4`). |
| `SESS` | `4` (`8` with `TUNE=context`) | The requests that decode at once, 1 to 8. |
| `CAP` | `262208` (`1048640` with `TUNE=context`) | The KV pool in tokens, shared by the sessions. Each request reserves its prompt + `max_tokens` from it. |
| `MAX_MODEL_LEN` | `262144` (`1048576` with `TUNE=context`) | The longest single request, prompt and output together. At most `CAP` less the guard rows (and at most 1,048,576). |
| `DFLASH` | `0` | `0` uses MTP only and downloads no drafter. |
| `FLASH_CACHE` | `aligned` | Prompt checkpoint cache on disk + spare RAM (`kv-store.yaml`, up to 64 GB per box). |
| `MENTAT` | `0` | `1` finds the other box and ConnectX addresses through the host's `mentat` daemon, and registers the API in group `GROUP` (`gr8-sage-2x`). |
| `GR8_GLM53F_VISION` in `EXTRA_ENV` | unset (off) | Text-only by default. The HF release includes `dense/vision-bf16.safetensors` (1.13 GB), untested with this recipe; set `EXTRA_ENV="GR8_GLM53F_VISION=1"` on both boxes to opt in. |
| `DEFAULT_MAX_TOKENS` | `32768` | `max_tokens` for a request that sends none, or the room the context leaves if that is less. |
| `UNDECLARED_TOOL_CALLS` | `emit` | A call to a tool the request did not declare comes back as a tool call, so your agent can answer it with an unknown-tool error. `text` leaves it in the reply's text. |

The image pins the weights to a fixed Hugging Face commit. Set `MODEL` in `.env` to change it
(`https://huggingface.co/<org>/<repo>@<commit>`).

[gr8/KNOBS.md](https://github.com/kindlingai/gr8/blob/538f2d798b15f0117df484c91cd187d0ecc535fd/KNOBS.md) lists the
advanced `gr8` options, which you can also set in `.env`.

## Pick what to prioritize

`TUNE` picks one of three settings. When you set `VARIANT`, `SESS`, `CAP`, `MAX_MODEL_LEN` or `MTP` yourself, your
value wins.

| `TUNE` | sets |
|---|---|
| `speed` (default) | `VARIANT=k4`, `SESS=4`, `CAP=262208`, `MAX_MODEL_LEN=262144` |
| `context` | `VARIANT=k4`, `SESS=8`, `CAP=1048640`, `MAX_MODEL_LEN=1048576`, and context-parallel KV (`GR8_CP=1`, experimental) |
| `quality` | `VARIANT=k4`, `SESS=4`, `CAP=262208`, `MAX_MODEL_LEN=262144`, `MTP=1` |

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

## Next steps

Planned follow-ups once the baseline 2-Spark tuning and clean-clone matrix complete:

- **Fast model switching:** benchmark `GR8_LOAD_COMPACT` + `GR8_LOAD_MERGE_KB=1` (`prepare`) for faster warm switches
  between Sage and other models on the same two Sparks.
- **Remote KV tier:** test `gr8`'s remote KV tier (`KV_STORE` with `remote:auto`) for sharing cached prompt state across
  nodes.
- **Tokenizer update:** bump the `gr8` submodule once the literal control-token handling fix lands on `kindlingai/gr8`
  `main`.

## Help

Ask on Discord (https://discord.gg/8EAvYPV2rE) or open an issue in this repo
(https://github.com/kindlingai/sage-s2.1-flash-exlr8-2x-spark/issues). Include the command you ran and the end of
`docker logs sage-2x-spark`. Remove addresses and hostnames before you post.

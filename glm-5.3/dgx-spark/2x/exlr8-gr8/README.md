# GLM-5.3 EXLR8 on 2× DGX Spark

![GLM-5.3 EXLR8 on two DGX Sparks: prefill, concurrency and quality](docs/card.png)

If you are an agent booting this for someone, read [AGENTS.md](AGENTS.md) first, then the Quickstart. Join the
[KindlingAI Discord](https://discord.gg/8EAvYPV2rE) for help and updates.

Full **GLM-5.3 (743B)** on just **two DGX Sparks** (GB10, 128 GB unified memory each — 256 GB total) at `TP=2`, served
by upstream [gr8](https://github.com/kindlingai/gr8) (`main@fa5d82d3`) from the `bit225` mixed-precision profile of
[kindlingai/glm-5.3-exlr8-k2-k3-k4](https://huggingface.co/kindlingai/glm-5.3-exlr8-k2-k3-k4/tree/501d259894bf0de607ee4aa6f8a564a14d0c6b63)
with **4-bit MLA latent KV** (`416 B/layer/tok` excl. indexer vs `656 B` FP8), **native INT4 DFlash**
(`incoai/GLM-5.3-DFlash2`, auto-packed to `tp2-int4` on first boot) + `MTP=1`, and built-in **48 GB NVMe SSD KV
offloading** (`KV_STORE`). This recipe runs gr8's published image pinned by immutable digest with one `.env` file.
Nothing is compiled.

## Results

**`TP=2` (`bit225`, 4-bit MLA latent KV, INT4 DFlash + 48 GB SSD KV):** **RealMark RIPAL 800.4 Grade A** (`801.1 /
810.5 / 789.7` at `C=1 / 2 / 4`) · **24.1 / 50.3 / 98.4 tok/s** aggregate streaming decode at `1 / 2 / 4` streams
(`24.6 tok/s` per stream at `C=4`) · **99.2% prefix cache hit** across `293K` active `C=4` context · **323 / 378 /
344 tok/s** cold prefill (`32K / 64K / 128K`) · **140/200 (70.0%)** on 200 Thinking-ON coding/math/science tasks
(`86.25%` HumanEval+, tied with 4-Spark `gr8` `142/200`, `p = 0.7744`) · **21/24 (87.5%)** on `32K–128K` hard
long-context (`100%` needle & doc-QA recall to `128K`, `38.7 tok/s` decode at `128K`) · **87–88 s** warm boot · **0**
API errors.

Measured **2026-11-27** across two DGX Sparks on 200G RoCE v2 running upstream
`ghcr.io/kindlingai/gr8:main@sha256:494c44b2` (`fa5d82d3`) with this recipe's `.env` (`CAP=131072, SESS=4` for RealMark
and 200-task quality; `CAP=135168, SESS=2` for 32K–128K hard long-context).

RealMark multi-lane concurrency (`kindlingai/realmark@957f600d`, Thinking OFF, `--stage-prefill-rate 300`):

| concurrency | RIPAL score | aggregate decode | per-lane decode | effective out tok/s | active context | cache hit | done |
|---|---:|---:|---:|---:|---:|---:|---:|
| `C=1` | **801.1** | 24.1 tok/s | 24.1 tok/s | 20.2 tok/s | 96K | 99.29% | 16/16 |
| `C=2` | **810.5** | 50.3 tok/s | 25.1 tok/s | 20.3 tok/s | 156K | 99.20% | 10/16* |
| `C=4` | **789.7** | **98.4 tok/s** | 24.6 tok/s | 20.0 tok/s | 293K | 99.16% | 8/16* |

*`C=2` (`367.3 s` observed / `585.0 s` projected) and `C=4` (`302.8 s` observed / `601.9 s` projected) hit RealMark's
stage time cap under `--stage-prefill-rate 300`; `0/102` replies buffered; `5/34` word-overlap flags (`3` at `C=1`,
`2` at `C=4`).

Cold long-context prefill & recall (`CAP=135168, SESS=2`, Thinking ON, `max_tokens=6144`, `0` prefix reuse):

| context | cold prefill | decode after | task pass (`<=6144`) | stopped accuracy |
|---|---:|---:|---:|---:|
| 32K (`8` tasks) | **323 tok/s** | 12.1 tok/s | **8/8 (100%)** | 8/8 (100%) |
| 64K (`8` tasks) | **378 tok/s** | 38.4 tok/s | **7/8 (87.5%)** | 7/7 (100%) |
| 128K (`8` tasks) | **344 tok/s** | **38.7 tok/s** | **6/8 (75.0%)** | 6/6 (100%) |

Quality & verification checks:

| check | result |
|---|---|
| RealMark RIPAL (`C=1/2/4`, Thinking OFF) | **800.4 Grade A** (`0/102` buffered replies) |
| 200-Task Thinking-ON (`max_tokens=4096`) | **140/200 (70.0%)** base (`140/140 = 100%` stopped) — HumanEval+ **69/80 (86.25%)**, MATH-500 **53/60 (88.33%)**, GPQA **17/60 (28.33%)** |
| Hard Long-Context (`32K–128K`, 24 tasks) | **21/24 (87.5%)** (`101/109 = 92.7%` sub-items; `100%` multi-needle & doc-QA recall to 128K; all 3 misses hit `max_tokens=6144`) |
| Live memory floor (`MemAvailable`) | **0.064–0.088 GiB** across all runs (`0` OOMs, `0` API errors, max temp `85°C`) |

## Quickstart

Run on **both** DGX Sparks with the exact same `.env`:

```bash
cp .env.example .env
# Edit PEERS in .env to your two Spark LAN IPs (head first).
# If cabled directly without a switch, set SHAPE=direct.
docker compose up -d
docker compose logs -f
```

Verify from the head node once ready (~88 s warm boot):

```bash
docker compose exec gr8 /opt/gr8/gr8 glm53 health
curl -s http://localhost:8100/v1/models
```

Stop both ranks cleanly from the head:

```bash
docker compose exec gr8 /opt/gr8/gr8 glm53 down
docker compose down
```

## What you need

- **2× NVIDIA DGX Spark** (GB10, 128 GB unified memory each — 256 GB total) connected over 200G RoCE v2 (switch or
  direct cable).
- **No other GPU or heavy RAM workloads** running on either Spark — `TP=2` runs tight on unified RAM (`~64–88 MiB`
  live free RAM floor with `GR8_MEM_MIN=1`).
- **>= 175 GB free fast local NVMe** per Spark (~115 GB for weights/drafter + **48 GB** for the built-in NVMe SSD
  `KV_STORE`).
- Docker with the NVIDIA Container Toolkit, `/dev/infiniband` present, TCP ports `7340`/`7341` open between peers, and
  `sysctl -w vm.compaction_proactiveness=0` on both nodes.

## Settings

Key `.env` knobs:
- `VARIANT=bit225`: 2.25 bpw EXLR8 mixed-precision expert widths (required to fit 743B on 2 Sparks).
- `KV_FORMAT=int4`, `KVB=fp8`: **4-bit MLA latent KV** (`416 B/layer/tok` excl. indexer) for 36.6% lower KV footprint.
- `KV_STORE=ssd:/var/lib/gr8/home/kv-store,size=48G,persist=off,keep=all`: spills cold prefix pages to NVMe so 4
  concurrent sessions retain 99.2% prefix cache hit across ~293K active context.
- `DFLASH=1`, `MTP=1`, `SPEC_ADAPT=1`: native INT4 DFlash (`tp2-int4`) + MTP=1 speculative decoding.
- `CAP=131072`, `SESS=4` (multi-lane default) or `CAP=135168`, `SESS=2` (single-request 128K long context).

## Other sizes

- [3× DGX Spark (`bit273`, 384K context)](../../3x/exlr8-gr8/)
- [4× DGX Spark (`bit325`, 4-bit MLA latent KV, 655K–1.13M context)](../../4x/exlr8-gr8/)
- [4× DGX Spark (`bit325`, pure FP8 KV, 640K context)](../../4x/exlr8-fp8kv-gr8/)
- [5× DGX Spark](../../5x/exlr8-gr8/) and [6× DGX Spark](../../6x/exlr8-gr8/)

## Help

Join the [KindlingAI Discord](https://discord.gg/8EAvYPV2rE) or open an issue on
[kindlingai/recipes](https://github.com/kindlingai/recipes) or [kindlingai/gr8](https://github.com/kindlingai/gr8).

## Engine pin

- Engine: `kindlingai/gr8` `main` (`fa5d82d37751d8c71703e3d1e6f4c010427357d2`)
- Image: `ghcr.io/kindlingai/gr8:main@sha256:494c44b2315f607a3fabe1fb38cd1b1ddd7074bddfea81a7227451ad207f3c59`
- Weights: `kindlingai/glm-5.3-exlr8-k2-k3-k4@501d259894bf0de607ee4aa6f8a564a14d0c6b63` (`bit225`)
- Drafter: `incoai/GLM-5.3-DFlash2@425aa615ce320caac34400208b30808c8f14f76c` (`tp2-int4`)

## License

Recipe files are MIT. Model weights follow GLM-5.3's upstream license; `incoai/GLM-5.3-DFlash2` is CC BY-NC-ND.

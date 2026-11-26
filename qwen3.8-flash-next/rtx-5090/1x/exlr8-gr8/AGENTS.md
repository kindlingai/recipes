# For agents: boot Qwen3.8-Flash-Next EXLR8 on one RTX 5090

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person. This recipe is the folder `qwen3.8-flash-next/rtx-5090/1x/exlr8-gr8` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe qwen3.8-flash-next-exlr8-1x-gpu` (or a sparse clone of the monorepo) and run the commands from
inside the folder.

## 1. Check the box

- 1× NVIDIA Blackwell GPU (`sm_120a`, e.g. RTX 5090 32 GB) with enough free VRAM (~23 GiB minimum): check `nvidia-smi`
  and `docker ps`.
- Host RAM: at least 96–128 GB DDR5 (`free -h`) for the 46.7 GB pinned K3 routed experts and OS page cache.
- CPU: x86_64 with AVX-512 (`lscpu | grep -i avx512`).
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Local NVMe disk: at least 165 GB free where the model cache lives
  (`df -h "$(docker info --format '{{.DockerRootDir}}')"`, or `GR8_CACHE` / `MODEL_DIR` if set).
- Hugging Face answers (unless booting from a pre-downloaded `MODEL_DIR`): `curl -sI https://huggingface.co`.
- Proactive memory compaction is off: `sysctl vm.compaction_proactiveness` prints 0. If not, as root:
  `sysctl -w vm.compaction_proactiveness=0`.

## 2. Write .env

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did). It is ready to boot `bit300` (K3) in
single-GPU Strata mode (`GR8_QW38_STRATA=1`, `GR8_QW38_VRAM_RESERVE_MIB=1920`, `CAP=40960`, `MTP=4`,
`EXTRA_ARGS="--prefill 13312"`) as-is. If the person already downloaded the release locally, set `MODEL_DIR` to that
host directory and `MODEL=/var/lib/gr8/model` (mounted read-only). Ask the person before changing any other knob.

## 3. Boot

Run `docker compose up -d`. The first boot downloads `bit300` (~164 GB) into `GR8_CACHE` unless using a pre-downloaded
`MODEL_DIR`. Follow it with `docker compose logs -f`.

## 4. Check

- `docker compose exec gr8 /opt/gr8/gr8 qw38 health` exits 0.
- `docker compose exec gr8 /opt/gr8/gr8 qw38 smoke` passes.
- `curl -s http://127.0.0.1:8100/v1/models` lists `qwen3.8-flash-next` with `max_model_len` 40960.

## 5. Stop

Run `docker compose exec gr8 /opt/gr8/gr8 qw38 down`, then `docker compose down`.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the hardware and the
  engine build. Do not copy a number from another build without its date.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and
  `docs/card.png` is drawn again with `python3 tools/card.py`.
- Once `gr8 v1.3.0` publishes its `linux/amd64` `sm_120a` image, the engine pin is one exact `gr8` commit and one image
  digest (`@sha256:...`). Never a moving tag alone, never a patched engine or host build. An engine change goes to
  [kindlingai/gr8](https://github.com/kindlingai/gr8) as a pull request; this recipe then moves its pin to the merged
  commit or next release.
- From the monorepo root, run `python3 tools/check_pin.py qwen3.8-flash-next/rtx-5090/1x/exlr8-gr8` (add `--strict`
  once `v1.3.0` is pinned) and `python3 tools/lint_recipe.py qwen3.8-flash-next/rtx-5090/1x/exlr8-gr8` before you
  commit.

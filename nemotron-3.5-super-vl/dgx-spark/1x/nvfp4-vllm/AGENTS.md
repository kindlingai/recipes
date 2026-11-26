# For agents: boot Nemotron 3.5 Super VL 120B-A12B on 1× or 2× DGX Spark

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml`, `compose.tp2.yaml`, or `.env.example` disagree, follow
those files and tell the person. This recipe is the folder `nemotron-3.5-super-vl/dgx-spark/1x/nvfp4-vllm` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe nemotron-3.5-super-vl-dgx-spark` (or a sparse clone of the monorepo) and run the commands from
inside the folder.

## 1. Check the box (every box for TP=2)

- It is a DGX Spark (GB10, `linux/arm64`) with 128 GB unified memory, and no other model or large files in `/dev/shm`
  hold RAM: `docker ps`, `nvidia-smi`, and `df -h /dev/shm` show none.
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Disk: at least 100 GB free where the model and container cache live
  (`df -h "$(docker info --format '{{.DockerRootDir}}')"`, or `CACHE_DIR` if set).
- Hugging Face answers: `curl -sI https://huggingface.co`.
- For 2× DGX Spark (TP=2) only: the direct high-speed (RoCE) link is up (`ls /dev/infiniband` lists devices) and TCP
  port `29511` (or `MASTER_PORT`) is reachable between rank 0 and rank 1.

## 2. Write .env

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did).

- **1× DGX Spark (default):** ready to boot `PROFILE=1spark` as-is (DFlash LiLiCorr drafter, 7 tokens, 1 sequence, 1M
  context). Ask the person before switching to `PROFILE=1spark-nospec` (no drafter, 4 sequences) or changing
  `GPU_MEMORY_UTILIZATION` (kept at `0.75` to leave room for DGX OS and the vision encoder).
- **2× DGX Spark (TP=2):** uncomment and set `TP2_PROFILE` (`balanced`, `decode`, `prefill`, or `nospec`), `HEAD`
  (rank 0 IP on the fast link), `IFACE` (this box's fast-link NIC), and `NODE_RANK` (`0` on box A, `1` on box B). Use
  the same `TP2_PROFILE` and overrides on both boxes.

## 3. Boot

- **1× DGX Spark:** run `docker compose up -d` and follow with `docker compose logs -f`.
- **2× DGX Spark (TP=2):** start rank 0 first, then rank 1, with `docker compose -f compose.tp2.yaml up -d` and follow
  with `docker compose -f compose.tp2.yaml logs -f`.

The first boot pulls the digest-pinned `vllm/vllm-openai:v0.34.0` image, fetches the model + drafter into `CACHE_DIR`,
and runs kernel JIT/autotune (~8 minutes on first boot; 4–5 minutes on later boots). Nothing is `pip install`ed or
kernel-downloaded at container start.

## 4. Check

On the single box (or rank 0 for TP=2):

- `docker compose ps` (or `docker compose -f compose.tp2.yaml ps`) shows healthy.
- `curl -s localhost:8100/v1/models` lists `nemotron-3.5-super-vl` with 1M context (`max_model_len`).
- Run `python3 bench/bench.py smoke`: it prints `PASS` (answer contains `391`).

## 5. Stop

Run `docker compose down` (or `docker compose -f compose.tp2.yaml down` on both boxes for TP=2).

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count and the
  engine build. Do not copy a number from another build without noting which build measured it.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and the card
  (`docs/card.png`) is regenerated from `kindling.json`.
- The engine pin is one exact commit and one image digest (`@sha256:...`), shared identically by `compose.yaml`,
  `compose.tp2.yaml`, and `kindling.json`. Never a moving tag alone, never a locally built image, never an unpinned
  `pip install` at boot.
- From the monorepo root, run `python3 tools/check_pin.py --strict nemotron-3.5-super-vl/dgx-spark/1x/nvfp4-vllm` and
  `python3 tools/lint_recipe.py nemotron-3.5-super-vl/dgx-spark/1x/nvfp4-vllm` before you commit.

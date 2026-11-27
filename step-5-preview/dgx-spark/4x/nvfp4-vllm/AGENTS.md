# For agents: boot Step-5 Preview NVFP4 on 4× DGX Spark

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person. This recipe is the folder `step-5-preview/dgx-spark/4x/nvfp4-vllm` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe step5-tp4-gb10-recipe` (or a sparse clone of the monorepo) and run the commands from inside
the folder on each of the four boxes.

## 1. Check the four boxes

- Four NVIDIA DGX Spark (GB10, SM121) boxes with no other model running on them: `docker ps` and `nvidia-smi` show
  none.
- Docker with the NVIDIA Container Toolkit on all four boxes: `docker info | grep -i nvidia`.
- Working inter-node RDMA fabric (`/dev/infiniband` present on all four boxes; `ibv_devinfo` shows both active HCAs).
- Local NVMe capacity on holders 0–2 for the split weights (~94 GB on rank 0, ~78 GB on rank 1, ~224 GB on rank 2)
  plus space for the container image and `/var/cache/step5`.
- Kernel NFS server utilities on holders 0–2, NFSv4 client utilities on all four compute ranks, SSH, `rsync`, and
  Python 3.

## 2. Write `.env` on every node

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did). Set:

- `NODE_RANK` (`0` on the head box; `1`, `2`, `3` on the worker boxes)
- `NODE0`..`NODE3` (the four isolated fabric IPs)
- `NETWORK_IFACE` and `RDMA_HCA` (this box's socket interface and active dual-rail HCA pair)
- `NFS_CLIENT_CIDR`, `STEP5_ROOT`, `CACHE_DIR`, and `SSH_USER`

`PROFILE=b5-fp8` is the default (576K window, staged FP8 KV, MTP3). Ask the person before switching to `b4-fp8`
(442K safer FP8), `b4-bf16-192k` (192K BF16 safe option), or `b4-bf16-256k` (256K BF16).

## 3. Host storage and NFS prerequisites

1. Download `stepfun-ai/Step-5-Preview-NVFP4` at commit `bc246cc2848e17b37f377eda8fd825c5b3018d1f` to `SOURCE_DIR` on
   a staging machine, then copy the split subsets to holders 0–2: `scripts/copy-shards.sh`.
2. On holders 0, 1, and 2, verify checksums and export read-only NFS:
   `scripts/verify-shards.sh <rank>` then `sudo scripts/export-nfs.sh`.
3. On each compute node `0..3`, mount the remote holders and build the symlink view:
   `sudo scripts/mount-nfs.sh <rank>` then `scripts/mklinks.sh <rank>`.
   Confirm `${STEP5_ROOT}/model/config.json` and `${STEP5_ROOT}/model/model.safetensors.index.json` exist on every
   rank.

## 4. Boot

Start the worker ranks (`1`, `2`, `3`) first, then the head rank (`0`):

```bash
docker compose up -d
docker compose logs -f
```

If host NVRM allocation errors appear during boot, run `sudo scripts/drop-page-cache.sh` on each host while the cluster
loads (exits automatically after 15 minutes).

Note on the FP8 KV overlay: `fp8-kv/overlay/step5_fp8kv/hook.py` checks `SOURCE_SHA256` against
`vllm.models.step5.nvidia.model` inside the container at startup. If the pinned `vllm/vllm-openai:step-5-preview`
digest raises `ImportError: STEP5_FP8KV source hash mismatch`, stop and tell the person (either switch to
`PROFILE=b4-bf16-192k` or update the overlay/image pin).

## 5. Check

- `docker compose ps` shows healthy on all four ranks.
- On rank 0:
  ```bash
  curl -sf http://127.0.0.1:8100/v1/models
  curl -sf http://127.0.0.1:8100/v1/chat/completions -H 'Content-Type: application/json' -d '{
    "model": "step5",
    "messages": [{"role": "user", "content": "Reply with a short greeting."}],
    "max_tokens": 64,
    "temperature": 0
  }'
  ```

## 6. Stop

Run `docker compose down` on all four boxes.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count, the image
  digest, and the clock policy. Do not copy a number from another build without its date.
- `README.md`'s Results and `kindling.json` say the same thing. Re-measure with `kindlingai/gr8`'s `bench/bench.py`
  (`--stages info,decode,concurrency,prefill,correct`) when updating numbers.
- The image pin in `compose.yaml` is an immutable `@sha256:...` digest, never a moving tag alone.
- Run local CPU tests (`python3 -m unittest discover -s tests -v`, `python3 -m unittest discover -s fp8-kv/tests -v`),
  `scripts/privacy_scan.sh`, and from the monorepo root `python3 tools/lint_recipe.py step-5-preview/dgx-spark/4x/nvfp4-vllm`
  before committing.

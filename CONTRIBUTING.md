# Contributing

## Adding a recipe

1. Pick the folder: `<model>/<hardware>/<count>x/<variant>/` ([README](README.md#layout)). `count` is the box or GPU
   count of the default config; `variant` is `<quant>[-<tag>]-<engine>`. A new hardware slug goes in
   [`hardware.json`](hardware.json) in the same pull request.
2. Write its `kindling.json` ([schema](schema/kindling.v1.json)). Required: `version` (1), `id`, `status`, `title`,
   `configs`. `id` is permanent: it names the image, the site card, the CLI argument and the tags. For a new recipe use
   `<model>-<quant>[-<tag>]-<n>x-<hardware short name>`, like the existing ones. Only numbers you measured go in
   `configs` (see ["Benchmarking"](#benchmarking)); put the conditions (date, engine commit, settings, benchmark) in
   each config's `notes`.
3. Start from [`template/`](template/), which holds the standard files and README layout (["The recipe
   standard"](#the-recipe-standard)): copy it into the folder, fill it in, and keep the launch contract — one
   `compose.yaml` on the host network, the engine's published image pinned by digest, settings in `.env`, the OpenAI
   API on port 8100, no Dockerfile. `AGENTS.md` if agents should boot it.
4. Check it locally:

   ```bash
   pip install -r tools/requirements.txt
   python3 tools/build_index.py --check    # validates every recipe; "out of date" is expected, do not commit the result
   python3 tools/check_pin.py <path>
   python3 tools/lint_recipe.py <path>     # the recipe standard; warn-only until the #2 conversions land
   ```

5. Open a pull request. Do not commit `index.json` or the README tables: the Index workflow shows the tables your change
   produces in its job summary, and after the merge it commits them itself. The site picks the recipe up from
   `index.json` within about ten minutes.

`status`: `stable`; `experimental` or `wip` (the site tags the card Experimental); `external` (the recipe lives in its
own repo, `source.repo`; the folder holds a copy of that repo's `kindling.json`, refreshed daily by
`tools/sync_external.py`, and a pointer README); `retired` (kept, left off the site).

## The recipe standard

Every recipe looks and runs the same way. [`template/`](template/) is the skeleton: copy it to
`<model>/<hardware>/<count>x/<variant>/`, replace every `<placeholder>`, delete the comments. `tools/lint_recipe.py`
(CI: `recipes.yml`, on every changed recipe) checks the result:

- Files: `README.md`, `AGENTS.md`, `kindling.json`, `compose.yaml`, `.env.example`, `docs/card.png`, `.gitignore`.
- README section order: title line and card, Results, Quickstart, What you need, Settings, Other sizes, Help,
  Engine pin, License. Recipe-specific sections go between Settings and Other sizes.
- Launch contract: one `compose.yaml`, `network_mode: host`, the engine image pinned by digest, settings from
  `.env`, the OpenAI API on port 8100, no `build:` key and no `Dockerfile`. Files the engine needs at run time
  (presets, manifests, kv-store config) are bind-mounted read-only from the folder.
- Every `${VAR}` that compose.yaml references is documented in `.env.example`.

The lint runs warn-only while the conversions of #2 land; when they have, `recipes.yml` runs it with `--strict` and
it fails CI. Run it yourself before you commit:

```bash
python3 tools/lint_recipe.py glm-5.3/dgx-spark/4x/exlr8-gr8   # one recipe
python3 tools/lint_recipe.py                                  # every non-external recipe
```

## Benchmarking

Every non-external recipe's default config is measured the same way so the README tables, the generated cards and
[kindlingai.dev](https://www.kindlingai.dev) compare like with like.

### Standard harness

Use [`kindlingai/gr8`'s `bench/bench.py`](https://github.com/kindlingai/gr8/tree/main/bench). It uses only the Python 3
standard library and talks standard OpenAI/vLLM HTTP endpoints (`/v1/models`, `/v1/chat/completions` with
`stream_options.include_usage`, `/tokenize`, and `/metrics`), so the same harness runs against both **gr8** and
**vLLM** (or any OpenAI-compatible server exposing those endpoints).

- **Why `bench/bench.py` over [`kindlingai/realmark`](https://github.com/kindlingai/realmark):** `bench/bench.py`
  directly produces the fixed-prompt single-stream decode workloads (`code`, `prose`, `structured`), cold prefill at
  8K/32K/128K, concurrency 1/2/4/8, and 128K needle recall that the index and cards compare side by side, and its
  `bench.py kindling` subcommand writes directly to `kindling.json`. RealMark (RIPAL) measures word-based interactive
  agentic turnaround and letter-grade quality across C=1, 2, 4; run it as a complementary check and record its score
  under `quality`.

### Default level

Measure every non-external recipe's default config at the default level:

| Stage | What it measures | `kindling.json` field |
|---|---|---|
| Decode | Single-stream decode (`code`, `prose`, `structured`, 512 tokens, 1 warmup + 6 runs, T=0, salted per-run tags so runs never hit the prefix cache) | `decode`: `{"code", "prose", "structured"}` (optional `decode_ci95`, `decode_prompt_tokens`) |
| Cold prefill | Salted synthetic code documents sized via `/tokenize` at `8192` (8K), `32768` (32K), `131072` (128K) (`prompt_tokens / TTFT`); sizes with `context + 1000 > max_context` are skipped | `prefill`: `[{"context", "tps"}, ...]` |
| Concurrency | `1`, `2`, `4`, `8` concurrent 512-token streams (capped at `max_concurrent`), 2 batches each, rotating `code`/`prose`/`structured` prompts | `concurrency`: `[{"streams", "aggregate_tps", ...}]` (optional `per_stream_tps`, `ttft_p50_s`, `concurrency_prompt_tokens`) |
| Needle recall | Passphrase at 15% depth of a salted 128K document, greedy, 1,024 max tokens (skipped when `131072 + 1000 > max_context`) | `quality`: `{"name": "Needle recall", "value": "found at 128K"}` |

Extra single-stream workloads beyond `code`, `prose`, and `structured` — including `bench/bench.py`'s own `counting`
stage, `math`, long-prompt decode, or multi-turn tool decode — go under `decode_extra`, not `decode`, so headline
comparisons stay aligned across recipes. Always record the run conditions in `notes` (date, engine ref/commit, harness
and flags, GPU clock state, and active knobs).

### Running the benchmark

Fetch `bench/` from `kindlingai/gr8` (or run from an existing `gr8` checkout):

```bash
git clone --filter=blob:none --sparse https://github.com/kindlingai/gr8.git /tmp/gr8-bench
git -C /tmp/gr8-bench sparse-checkout set bench smoketest
```

Against a **gr8** server on port 8100:

```bash
# Single box or cluster with SSH + sudo thermal settling (stops sparkos-thermal, cools between timed stages):
python3 /tmp/gr8-bench/bench/bench.py \
  --url http://127.0.0.1:8100 \
  --hosts local \
  --json /tmp/bench-report.json

# Multi-node cluster: pass --hosts box1,box2,...
# Without thermal control (workstation / no passwordless sudo): omit --hosts
```

Against **vLLM or any non-gr8 OpenAI-compatible server**, skip gr8's local `smoke` shell scripts with `--stages` (and
pass `--effort nothink` when the model or chat template does not accept `chat_template_kwargs.reasoning_effort`, plus
`--streams` capped at `max_concurrent` when `max_concurrent < 8`):

```bash
python3 /tmp/gr8-bench/bench/bench.py \
  --url http://127.0.0.1:8100 \
  --stages info,decode,concurrency,prefill,correct \
  --json /tmp/bench-report.json
# Add --effort nothink for models without reasoning_effort
# Add --streams 1,2,4 (or --streams 1) if max_concurrent < 8
```

Write the measured metrics into the recipe's `kindling.json`:

```bash
python3 /tmp/gr8-bench/bench/bench.py kindling /tmp/bench-report.json \
  --out <recipe-path>/kindling.json \
  --config-id <config-id> --label "<label>" --nodes <n> --default
```

`bench.py kindling` fills `decode` (`code`, `prose`, `structured`), `prefill`, `concurrency` (`streams`,
`aggregate_tps`), `quality` (`Needle recall`), and `max_context` while preserving all other fields. Fill in
`decode_extra`, `decode_ci95`, `decode_prompt_tokens`, `concurrency_prompt_tokens`, `per_stream_tps`/`ttft_p50_s`,
`kv_pool_tokens`, `max_concurrent`, and `notes` from the JSON report and launch config.

### Metric enforcement & migration

`schema/kindling.v1.json` declares the standard `decode` keys (`code`, `prose`, `structured`) alongside `decode_extra`,
and `tools/lint_recipe.py` checks every non-external recipe's default config for the standard decode keys, extra keys
left in `decode`, cold prefill points (`8192`, `32768`, `131072` within `max_context`), concurrency points (`1`, `2`,
`4`, `8` within `max_concurrent`), and `Needle recall` (when `max_context >= 132072`). `schema/kindling.v1.json` keeps
`decode.additionalProperties` permissive while off-method recipes are re-measured (#9, #10, #11, #12, #13) and legacy
extra workloads move to `decode_extra`; once those land, `schema/kindling.v1.json` will enforce the fixed `decode`
keys strictly (`required: ["code", "prose", "structured"]`, `additionalProperties: false`).

## Engine pins

A gr8 recipe pins its engine in `kindling.json` `engine`, and `tools/check_pin.py` (CI: `recipes.yml`) keeps the
other files in agreement:

- `pin: "image"`: `compose.yaml` runs gr8's published image, `${GR8_IMAGE:-<engine.image>@<engine.image_digest>}`.
  While a gr8 release is unpublished, `commit` and `image_digest` may both be empty; fill them when it lands.
- `pin: "source"`: the recipe's `Dockerfile` builds gr8 from `engine.commit`. Before a local build, put the source in
  place with `tools/engine.sh <path>` (or `npx @kindlingai/recipe <id> --engine`); it lands in `<path>/gr8`, which is
  gitignored. To move the recipe to another gr8 commit, change `engine.commit` (and `engine.ref`). `compose.yaml` runs
  the recipe's own image, `${IMAGE:-<image>:latest}`.

## Images

A recipe whose `kindling.json` has a `build` object gets its image built by CI
([`recipe-image.yml`](.github/workflows/recipe-image.yml), called from `recipes.yml` when the folder changes): pull
requests build it and run the folder's `smoke.sh IMAGE` (no GPU), `main` pushes `latest`, `main` and `sha-<commit>`
to `image`. `build.nvcc_cache` names the gr8 compile cache kept between runs. To publish a named version, push a tag
`<id>/v<version>` (or `<id>/stable-<n>`); the image gets the part after the slash. Run any recipe's build by hand
with the Recipes workflow's dispatch (`recipe`: an id, or `all`).

Each image keeps the name it had when the recipe was its own repo, so the `ghcr.io/kindlingai/<id>` package must give
this repo write access (package settings → Manage Actions access).

## History

Recipes adopted from their own repo kept that history: `git log <path>` shows the commits since the move; the old
repo's commits are behind the commit "Move <id> into <path>/" (`git log <that commit>^`). Old branches and tags are
tags `<id>/<name>`. `git log --follow` on a common file name such as `README.md` also walks into other recipes' old
histories, so prefer `git log <path>` or `git blame`. `npx @kindlingai/recipe <id> --history` gives one recipe's
history as a repo of its own, the folder at its root.

## Adopting a repo

```bash
tools/adopt.sh <repo> <path> [id]     # merges kindlingai/<repo> into <path> with its history; tags become <id>/<name>
```

Then, in the same pull request: delete the folder's `.github/` (port anything it did to the root workflows; image
smoke tests go to `smoke.sh`), `.gitmodules` and its `gr8` submodule (`git rm --cached <path>/gr8`; the pin moves to
`engine.commit` with `pin: "source"`), `check.py`, and a `LICENSE` identical to the root one; add `id` and `status` to
its `kindling.json`; point its README at the monorepo (quickstart, issue links). After the merge: merge or close the
old repo's open pull requests, move its open issues (`gh issue transfer <n> kindlingai/recipes`), push a pointer README
to it, and archive it. Archive rather than delete, so its URL, stars and links keep working.

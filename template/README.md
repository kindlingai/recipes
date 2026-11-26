# <Model> <variant> on <count>× <hardware name>

<!-- This folder is the recipe standard. Copy it to <model>/<hardware>/<count>x/<variant>/ (template/ itself is
     outside the recipe glob, so the index and CI skip it), replace every <placeholder>, delete these comments, and
     keep the section order: tools/lint_recipe.py enforces it. Recipe-specific sections go between Settings and
     Other sizes. See CONTRIBUTING.md, "The recipe standard". -->

![<Model> <config>: decode, prefill and concurrency](docs/card.png)

One short paragraph: what the model, the hardware and the variant are, which engine serves it, and what makes this
recipe worth running. No number appears here that Results does not also have below.

## Results

One bold line per config with the headline numbers, then the measured tables. Everything here comes from one
measured run: say the date, the box count, the engine commit and the benchmark settings above the tables, and state
the unit (tok/s) once. Every number also lives in [kindling.json](kindling.json)'s `configs`; the cards are drawn
from it.

<!-- Typical tables, in this order: single-stream decode by workload (with 95% CI), requests at once (aggregate and
     per-request tok/s, first-token latency), prefill cold vs cached, quality checks (smoke, needle recall,
     perplexity). Shape examples: qwen3.8-flash-next/dgx-spark/1x/exlr8-gr8, glm-5.3/dgx-spark/4x/exlr8-gr8. -->

## Quickstart

First <any host prerequisite, e.g. a sysctl>, then:

```bash
npx @kindlingai/recipe <id> && cd <id>
# the CLI already copied .env.example to .env; edit it if you need to
docker compose up -d       # pulls the pinned engine image; the first boot fetches the model
docker compose logs -f     # ready when the OpenAI API answers on 127.0.0.1:8100
```

Once serving, send one smoke request:

```bash
curl -s localhost:8100/v1/models
curl -s localhost:8100/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "<model id>",
  "messages": [{"role": "user", "content": "Write a haiku about a small computer."}],
  "max_tokens": 256
}'
```

Stop the server cleanly with `docker compose down`.

## What you need

- One <hardware> box (<memory>), with no other model running on it.
- Docker with the NVIDIA container toolkit (<OS that has both>).
- <Disk space, and where the model cache must live (fast local NVMe when the engine streams over O_DIRECT).>
- <Any other host setting, with the permanent form linked.>

## Settings

`cp .env.example .env` (the CLI already did). Every knob is documented in [.env.example](.env.example); the active
lines are the exact settings the Results numbers were measured with.

| knob | default | what it does |
|---|---|---|
| `<KNOB>` | `<value>` | <effect> |

Where the engine has tuned presets, name them here:

| `TUNE` | tradeoff | what it changes |
|---|---|---|
| `<preset>` | <throughput vs quality> | <knobs it sets> |

## <Recipe-specific sections>

<!-- Anything this recipe needs beyond the standard: multimodal opt-ins, multi-config choices, per-size tables,
     benchmark method. Order is free, but every extra section stays between Settings and Other sizes. -->

## Other sizes

- **<count> boxes (<what changes>):** [<id>](<relative link to the sibling recipe folder>)

## Help

Ask on Discord (https://discord.gg/8EAvYPV2rE) or open an issue in the recipes repo
(https://github.com/kindlingai/recipes/issues) with `<id>` in the title. Say which step failed and include the end
of `docker compose logs` before you remove the container. Remove addresses and hostnames before you post.

## Engine pin

This recipe has no engine code. It runs one published engine image, named in [compose.yaml](compose.yaml) and in the
`engine` field of [kindling.json](kindling.json):

| | |
|---|---|
| engine | [<engine repo>](https://github.com/<engine repo>) [`<commit>`](https://github.com/<engine repo>/commit/<commit>) |
| image | `<image>:<tag>` |
| digest | `sha256:<digest>` |
| weights | [<model>](https://huggingface.co/<model>/commit/<weights_commit>) (`<short commit>`) |

`python3 tools/check_pin.py --strict <model>/<hardware>/<count>x/<variant>`, run from the monorepo root, verifies
that compose.yaml and kindling.json agree on the immutable image digest.

## License

MIT, see [LICENSE](../../../../LICENSE). <The model has its own licence: see the model page.>

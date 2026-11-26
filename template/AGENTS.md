# For agents: boot <Model> on <count>× <hardware>

You are booting this recipe for someone. Follow the steps in order and run each check. If a check fails, stop and
tell the person what failed. If this file and `compose.yaml` or `.env.example` disagree, follow those two files and
tell the person. This recipe is the folder `<model>/<hardware>/<count>x/<variant>` of
[kindlingai/recipes](https://github.com/kindlingai/recipes); paths below are relative to it. Get it with
`npx @kindlingai/recipe <id>` (or a sparse clone of the monorepo) and run the commands from inside the folder.

## 1. Check the box

- It is <hardware> with <memory>, and no other model runs on it: `docker ps` and `nvidia-smi` show none.
- Docker has the NVIDIA runtime: `docker info | grep -i nvidia`.
- Disk: at least <n> GB free where the model cache lives
  (`df -h "$(docker info --format '{{.DockerRootDir}}')"`, or `CACHE_DIR` if you set one).
- Hugging Face answers: `curl -sI https://huggingface.co`.
- <Any other host setting, with the command that checks it and the command that fixes it.>

## 2. Write .env

Copy `.env.example` to `.env` (the `npx @kindlingai/recipe` CLI already did). It is ready to boot <the default
config> as-is. Ask the person before changing <each knob that changes the tradeoff, and what it requires>.

## 3. Boot

Run `docker compose up -d`. The first boot downloads the model (<size>); later boots take <time>. Follow it with
`docker compose logs -f`.

## 4. Check

- The healthcheck goes green (`docker compose ps` shows healthy), or the engine's own health command exits 0.
- `curl -s localhost:8100/v1/models` lists <model id> with the expected `max_model_len`.
- The engine's smoke command passes (<n> of <n> checks).

## 5. Stop

Run the engine's clean shutdown command, then `docker compose down`.

## Rules for changes to this recipe

- Every number in `README.md` and `kindling.json` comes from a measured run. Say the date, the box count and the
  engine build. Do not copy a number from another build without its date.
- `README.md`'s Results and `kindling.json` say the same thing. A change to one changes the other, and the card
  (`docs/card.png`) is drawn again from the engine checkout.
- The engine pin is one exact commit and one image digest (`@sha256:...`). Never a moving tag alone, never a patched
  engine. An engine change goes to the engine repo as a pull request; this recipe then moves its pin to the merged
  commit or next release.
- From the monorepo root, run `python3 tools/check_pin.py --strict <model>/<hardware>/<count>x/<variant>` and
  `python3 tools/lint_recipe.py <model>/<hardware>/<count>x/<variant>` before you commit.

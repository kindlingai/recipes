# @kindlingai/recipe

One recipe from [kindlingai/recipes](https://github.com/kindlingai/recipes) in a folder of its own, ready to run.

```bash
npx @kindlingai/recipe glm-5.3-exlr8-3x-spark      # ./glm-5.3-exlr8-3x-spark, with .env copied from .env.example
npx @kindlingai/recipe --list                       # every recipe: id, hardware, status, path
```

Then follow the recipe's README: usually edit `.env`, then `docker compose up -d`.

| Option | |
|---|---|
| `<id\|path> [dir]` | the recipe, by id (`glm-5.3-exlr8-3x-spark`) or path (`glm-5.3/dgx-spark/3x/exlr8-gr8`); `dir` defaults to `./<id>` and must be empty or absent |
| `--engine` | also check out the engine source the recipe's Dockerfile builds (`kindling.json` `engine.commit`) into `<dir>/gr8`, for `docker compose build`. What `git clone --recurse-submodules` gave when each recipe was its own repo. |
| `--history` | make `<dir>` a git repo of the recipe's own history, the folder as its root: the old repo's commits (same ids and tags) followed by the recipe's commits in kindlingai/recipes |
| `--ref <ref>` | a branch, tag or commit of kindlingai/recipes |
| `--repo <url>` | a fork or local clone of kindlingai/recipes |

External recipes (those that live in their own repo, `status: external` in the index) are cloned from that repo.

## How it works

It needs git and Node 18 or newer, and has no dependencies. It reads `index.json` from a shallow, blobless clone of
kindlingai/recipes, finds the recipe, sparse-checks-out only its folder and moves it into place, so it downloads that
folder's files and nothing else. `--history` clones the whole repo instead and runs `git filter-branch
--subdirectory-filter` on the folder; for a recipe adopted from its own repo it grafts the result onto that repo's
history, rewriting only the commits made since the move.

## Development

```bash
node bin/recipe.js --repo .. --list     # against this checkout's committed index.json
sh smoke.sh                             # list, fetch, --history and an unknown id, against this checkout
```

Releases: bump `version` in `package.json`, merge, then push a tag `cli/v<version>`; `.github/workflows/cli.yml`
runs the smoke test and publishes to npm with provenance.

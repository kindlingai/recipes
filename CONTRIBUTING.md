# Contributing

## Adding a recipe

1. Pick the folder: `<model>/<hardware>/<count>x/<variant>/` ([README](README.md#layout)). `count` is the box or GPU
   count of the default config; `variant` is `<quant>[-<tag>]-<engine>`. A new hardware slug goes in
   [`hardware.json`](hardware.json) in the same pull request.
2. Write its `kindling.json` ([schema](schema/kindling.v1.json)). Required: `version` (1), `id`, `status`, `title`,
   `configs`. `id` is permanent: it names the image, the site card, the CLI argument and the tags. For a new recipe use
   `<model>-<quant>[-<tag>]-<n>x-<hardware short name>`, like the existing ones. Only numbers you measured go in
   `configs`; put the conditions (date, settings, benchmark) in each config's `notes`.
3. Put everything the recipe needs next to it: `README.md` with a quickstart that starts with
   `npx @kindlingai/recipe <id> && cd <id>`, `compose.yaml` and `.env.example` (or the scripts it runs), `AGENTS.md`
   if agents should boot it.
4. Check it locally:

   ```bash
   pip install -r tools/requirements.txt
   python3 tools/build_index.py --check    # validates every recipe; "out of date" is expected, do not commit the result
   python3 tools/check_pin.py <path>
   ```

5. Open a pull request. Do not commit `index.json` or the README tables: the Index workflow shows the tables your change
   produces in its job summary, and after the merge it commits them itself. The site picks the recipe up from
   `index.json` within about ten minutes.

`status`: `stable`; `experimental` or `wip` (the site tags the card Experimental); `external` (the recipe lives in its
own repo, `source.repo`; the folder holds a copy of that repo's `kindling.json`, refreshed daily by
`tools/sync_external.py`, and a pointer README); `retired` (kept, left off the site).

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

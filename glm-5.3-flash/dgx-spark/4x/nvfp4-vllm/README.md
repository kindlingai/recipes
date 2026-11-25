# glm-5.3-flash-gx10 (external)

GLM-5.3-Flash (NVFP4) at TP=4 across four GB10 boxes with vLLM and mentat instead of Ray. This recipe lives in its own repo, [kindlingai/glm-5.3-flash-gx10](https://github.com/kindlingai/glm-5.3-flash-gx10): the image, the
launchers, the gate and its issues are there.

This folder holds only its card data, so the recipe shows up in the [index](../../../../README.md#recipes) and on the
site. [kindling.json](kindling.json) is a copy of that repo's `kindling.json`; the Index workflow refreshes it daily
(`tools/sync_external.py`). Edit the numbers there, not here.

```bash
npx @kindlingai/recipe glm-5.3-flash-gx10    # clones kindlingai/glm-5.3-flash-gx10
```

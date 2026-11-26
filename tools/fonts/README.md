# Bundled fonts for `tools/card.py`

`tools/card.py` bundles two static TrueType fonts so recipe cards render identically across macOS, Linux, and CI with no external checkout or system font dependency:

- **`JetBrainsMono-Regular.ttf`** (body text, labels, values)
  - Upstream: https://github.com/JetBrains/JetBrainsMono (v2.304)
  - Copyright 2020 The JetBrains Mono Project Authors
  - License: SIL Open Font License, Version 1.1 ([`OFL-JetBrainsMono.txt`](OFL-JetBrainsMono.txt))

- **`SpaceGrotesk-Bold.ttf`** (card titles)
  - Upstream: https://github.com/floriankarsten/space-grotesk (v2.0.0)
  - Copyright 2020 The Space Grotesk Project Authors
  - License: SIL Open Font License, Version 1.1 ([`OFL-SpaceGrotesk.txt`](OFL-SpaceGrotesk.txt))

Both fonts are unmodified upstream binaries distributed under the SIL Open Font License 1.1. The OFL permits bundling and redistribution alongside this software, and imposes no license restriction on the PNG/GIF images rendered with them.

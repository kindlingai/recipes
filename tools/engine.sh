#!/usr/bin/env bash
# Usage: tools/engine.sh <recipe-dir>
#
# Checks out the engine a source-pinned recipe builds (kindling.json engine.repo at engine.commit) into
# <recipe-dir>/gr8, where its Dockerfile COPYs from. This replaces the gr8 submodule each recipe used to carry. The
# folder is gitignored; rerunning moves it to the pinned commit. CI (recipe-image.yml) does the same with
# actions/checkout.
set -euo pipefail

dir=${1:?usage: tools/engine.sh <recipe-dir>}
read -r pin repo commit < <(python3 -c '
import json, sys
e = json.load(open(sys.argv[1])).get("engine") or {}
print(e.get("pin", "-"), e.get("repo", "-"), e.get("commit") or "-")' "$dir/kindling.json")

if [ "$pin" != source ]; then
	echo "$dir: engine.pin is $pin, not source: the recipe runs a published image and builds nothing" >&2
	exit 1
fi
if [ "$commit" = - ]; then
	echo "$dir: engine.commit is missing" >&2
	exit 1
fi

dest=$dir/${repo##*/}
url=https://github.com/$repo.git
if [ ! -d "$dest/.git" ]; then
	rm -rf "$dest"
	git init -q "$dest"
	git -C "$dest" remote add origin "$url"
fi
if [ "$(git -C "$dest" rev-parse -q --verify HEAD 2> /dev/null)" != "$commit" ]; then
	git -C "$dest" fetch -q --depth 1 origin "$commit"
	git -C "$dest" checkout -q --detach FETCH_HEAD
fi
echo "$dest: $repo at $commit"

#!/bin/sh
# Usage: cli/smoke.sh [recipes-repo]   (default: this checkout; it needs full history for --history)
#
# Runs the CLI against a clone of kindlingai/recipes the way a user would: list, fetch one recipe, fetch one with its
# history, and refuse an unknown id. CI runs it before publishing (.github/workflows/cli.yml).
set -eu
cli=$(cd "$(dirname "$0")" && pwd)/bin/recipe.js
repo=${1:-$(cd "$(dirname "$0")/.." && pwd)}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"

node "$cli" --repo "$repo" --list > list.txt
id=$(awk 'NR == 1 { print $1 }' list.txt)
path=$(awk 'NR == 1 { print $NF }' list.txt)
echo "list: $(wc -l < list.txt | tr -d ' ') recipes, first $id ($path)"

node "$cli" --repo "$repo" "$id" > /dev/null
[ -f "$id/kindling.json" ] || { echo "fetch: $id/kindling.json missing"; exit 1; }
[ ! -e "$id/.git" ] || { echo "fetch: $id should not be a git repo"; exit 1; }
if [ -f "$id/.env.example" ]; then cmp -s "$id/.env.example" "$id/.env" || { echo "fetch: .env is not .env.example"; exit 1; }; fi
mkdir ref && git -C "$repo" archive HEAD "$path" | tar -x -C ref
diff -r -x .env "ref/$path" "$id" > /dev/null || { echo "fetch: $id differs from $path at HEAD"; exit 1; }
echo "fetch: $id matches $path"

node "$cli" --repo "$repo" --history "$path" hist > /dev/null
[ "$(git -C hist rev-parse --abbrev-ref HEAD)" = main ] || { echo "history: not on main"; exit 1; }
[ -z "$(git -C hist status --porcelain)" ] || { echo "history: work tree not clean"; exit 1; }
[ "$(git -C hist rev-parse HEAD:kindling.json)" = "$(git -C "$repo" rev-parse "HEAD:$path/kindling.json")" ] \
  || { echo "history: kindling.json is not the repo's"; exit 1; }
echo "history: $(git -C hist rev-list --count HEAD) commits"

if node "$cli" --repo "$repo" no-such-recipe 2> err.txt; then echo "unknown id: exit 0"; exit 1; fi
grep -q "no recipe no-such-recipe" err.txt || { echo "unknown id: $(cat err.txt)"; exit 1; }
echo "unknown id: refused"
echo smoke OK

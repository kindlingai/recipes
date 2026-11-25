#!/usr/bin/env bash
# Usage: tools/adopt.sh <repo> <path> [id]
#
# Merges kindlingai/<repo> into this repo under <path>/ (model/hardware/Nx/variant), keeping its history: one commit on
# top of the source's default branch moves every file into <path>/, then a merge brings that commit in. Source commits
# keep their IDs, and `git blame` follows the move. Derived from graveyard/bury.sh; the difference is that <path> may
# be nested, so the rename commit wraps the source tree in one tree per path level.
#
# Other branches and tags become tags named <id>/<name> (id defaults to <repo>). A pull request head that no branch,
# tag or main already holds becomes <id>/pull/<N>.
#
# Archiving the source repo is a separate manual step (see CONTRIBUTING.md, "Adopting a repo").
set -euo pipefail

repo=${1:?usage: tools/adopt.sh <repo> <path> [id]}
path=${2:?usage: tools/adopt.sh <repo> <path> [id]}
id=${3:-$repo}
path=${path%/}
cd "$(git rev-parse --show-toplevel)"

if [ -e "$path" ]; then
	echo "$path already exists" >&2
	exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
	echo "working tree is not clean" >&2
	exit 1
fi
if [ -n "$(git tag -l "$id/*" | head -1)" ]; then
	echo "tags $id/* already exist: $id was adopted before" >&2
	exit 1
fi

url=${ADOPT_URL:-https://github.com/kindlingai/$repo.git}
ns=refs/adopt/$id
# PR heads too: a squash-merged or closed PR whose branch was deleted keeps its commits only in refs/pull, which go
# away with the repo.
GIT_TERMINAL_PROMPT=0 git fetch -q --no-tags "$url" "+refs/heads/*:$ns/heads/*" "+refs/tags/*:$ns/tags/*" \
	"+refs/pull/*/head:$ns/pull/*"

default=$(git ls-remote --symref "$url" HEAD | awk '/^ref:/ { sub("refs/heads/", "", $2); print $2; exit }')
head=$(git rev-parse "$ns/heads/$default")

# The source tree wrapped in one tree per level of <path>, innermost first.
tree=$(git rev-parse "$head^{tree}")
IFS=/ read -r -a parts <<< "$path"
for ((i = ${#parts[@]} - 1; i >= 0; i--)); do
	tree=$(printf '040000 tree %s\t%s\n' "$tree" "${parts[i]}" | git mktree)
done

# A plain rename commit on top of the source head, so blame and log --follow see the move. A prefix merge alone hides
# it and blames the merge commit.
moved=$(git commit-tree -p "$head" -m "Move $repo into $path/" "$tree")
# The result is this repo's tree plus the source under <path>/, built directly rather than by a real merge, which
# could conflict when a source shares history with something adopted earlier.
git merge -q -s ours --no-commit --allow-unrelated-histories "$moved"
git read-tree --prefix="$path/" -u "$head"
git commit -q -m "Adopt $repo in $path/" -m "Source: kindlingai/$repo, $default at $head."

git for-each-ref --format='%(refname)' "$ns/heads" "$ns/tags" | while read -r ref; do
	[ "$ref" = "$ns/heads/$default" ] && continue
	name=${ref#"$ns/heads/"}
	name=${name#"$ns/tags/"}
	git tag -f "$id/$name" "$ref" > /dev/null
done
# Only PR heads whose commits are not already kept by main or a tag above.
git for-each-ref --format='%(refname) %(objectname)' "$ns/pull" | while read -r ref sha; do
	git merge-base --is-ancestor "$sha" HEAD && continue
	[ -n "$(git tag --contains "$sha" -l "$id/*" | head -1)" ] && continue
	git tag -f "$id/pull/${ref#"$ns/pull/"}" "$sha" > /dev/null
done
git for-each-ref --format='%(refname)' "$ns" | xargs -n1 git update-ref -d

echo "adopted $repo ($default $head) in $path/"

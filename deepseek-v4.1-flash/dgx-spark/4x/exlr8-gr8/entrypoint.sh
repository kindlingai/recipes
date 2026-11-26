#!/bin/bash
# The recipe's own commands, then gr8's entrypoint (gr8/docker/entrypoint.sh) with the recipe's knobs (knobs.sh):
#   fetch   fetch the whole release into the release volume (fetch-release.sh); run it once on every box
#   up      (the default) migrate a fetch record from an image older than sha-fe21314 (fetch-release.sh --migrate),
#           refuse to start until the release is whole, then boot (gr8 auto-generates and verifies
#           ENGRAM_PREFIX.engram.cmap on first boot from <release>/tokenizer.json against kCmapSha256)
set -euo pipefail
args=("$@")
while [ "${1:-}" = --no-check ]; do shift; done
cmd=${1:-up}
if [ "$cmd" = fetch ]; then
  shift
  exec /opt/ds41-4x/fetch-release.sh "$@"
fi
. /opt/ds41-4x/knobs.sh
if [ "$cmd" = up ]; then
  if ! /opt/ds41-4x/fetch-release.sh --migrate; then
    echo "ds41-4x: the fetch record beside $MODEL is from an older image and was not migrated (above)" >&2
    exit 2
  fi
  if ! /opt/ds41-4x/fetch-release.sh --check; then
    echo "ds41-4x: the release in $MODEL is not whole: run the fetch first, on every box (README.md, Quickstart)" >&2
    exit 2
  fi
  # Ensure the writable parent directory for gr8's auto-generated Engram token map and loader index exists.
  mkdir -p "$(dirname "$ENGRAM_PREFIX")"
fi
exec /opt/gr8/docker/entrypoint.sh ${args[@]+"${args[@]}"}

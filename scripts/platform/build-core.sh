#!/bin/sh
set -eu
repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repository_root"
cairn_cache="$repository_root/work/toolchain/cache/git-v0/db/a15250d2e29c4e16/.git"
cairn_pin=8e7e0ea67552383851dfcabfba0c4e9c8d007878
if ! test "$(git --git-dir="$cairn_cache" rev-parse "$cairn_pin^{commit}")" = "$cairn_pin"; then
  printf 'Pinned Cairn cache unavailable; synchronize the frozen cairn-bridge dependency group first.\n' >&2
  exit 1
fi
exec docker --context desktop-linux build --build-context "cairn-git=$cairn_cache" \
  -t wuji-core:core-loop -f services/execution-control/Dockerfile .

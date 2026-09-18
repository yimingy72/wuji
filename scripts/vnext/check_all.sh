#!/bin/sh
# Minimal P19/P20 gate.  It checks only the new archive/release path and the
# generated v2 contract; it does not stop services, switch traffic, or delete
# any legacy volume.
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
uv="$repository_root/scripts/vnext/uv.sh"
inventory_output=$(mktemp "${TMPDIR:-/tmp}/wuji-vnext-inventory.XXXXXX")
trap 'rm -f "$inventory_output"' EXIT HUP INT TERM

cd "$repository_root"
"$uv" run --frozen pytest \
  tests/vnext/test_archive_roundtrip.py \
  tests/vnext/test_release_inventory.py \
  -q
"$uv" run --frozen python scripts/vnext/assert_release_inventory.py \
  --root "$repository_root" \
  --output "$inventory_output"
"$uv" run --frozen python scripts/vnext/generate_contracts.py --check

printf '%s\n' 'P19/P20 minimal checks passed (archive, release inventory, v2 contracts).'

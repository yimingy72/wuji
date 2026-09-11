#!/bin/sh
set -eu
repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec "$repository_root/scripts/uv.sh" run --frozen --group task-runtime --group cairn-bridge python \
  "$repository_root/scripts/platform/core.py" "$@"

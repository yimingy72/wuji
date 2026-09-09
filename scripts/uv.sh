#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
toolchain_root="$repository_root/work/toolchain"
uv_path="$toolchain_root/bin/uv"
expected_uv_version=0.12.11

if ! test -x "$uv_path"; then
  printf 'Project uv is missing. Run ./scripts/bootstrap-toolchain.sh first.\n' >&2
  exit 1
fi

actual_uv_version=$("$uv_path" --version | awk '{print $2}')
if test "$actual_uv_version" != "$expected_uv_version"; then
  printf 'Expected project uv %s, got %s. Run ./scripts/bootstrap-toolchain.sh.\n' \
    "$expected_uv_version" "$actual_uv_version" >&2
  exit 1
fi

UV_CACHE_DIR="$toolchain_root/cache" \
UV_PYTHON_INSTALL_DIR="$toolchain_root/python" \
UV_PYTHON_BIN_DIR="$toolchain_root/bin" \
UV_MANAGED_PYTHON=true \
  exec "$uv_path" --directory "$repository_root" "$@"

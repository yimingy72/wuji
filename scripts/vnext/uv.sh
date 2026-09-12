#!/bin/sh
# Preserve caller cwd so repository-relative test/probe paths work.
set -eu
repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
toolchain_root="$repository_root/work/toolchain"
uv_path="$toolchain_root/bin/uv"
if ! test -x "$uv_path"; then
  printf 'Missing local uv; provision uv 0.12.11 under work/toolchain/bin.\n' >&2
  exit 2
fi
if test "$("$uv_path" --version | awk '{print $2}')" != 0.12.11; then
  printf 'vNext requires uv 0.12.11.\n' >&2
  exit 2
fi
export UV_CACHE_DIR="$toolchain_root/cache"
export UV_PYTHON_INSTALL_DIR="$toolchain_root/python"
export UV_PYTHON_BIN_DIR="$toolchain_root/bin"
export UV_PYTHON=3.13.15
export UV_MANAGED_PYTHON=true
export UV_PYTHON_DOWNLOADS=never
export UV_PROJECT_ENVIRONMENT="$repository_root/packages/maf-worker/.venv"
exec "$uv_path" --project "$repository_root/packages/maf-worker" "$@"

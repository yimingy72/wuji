#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
toolchain_root="$repository_root/work/toolchain"
uv_version=0.12.11
python_version=3.13.15

case "$(uname -s)-$(uname -m)" in
  Darwin-x86_64)
    uv_asset=uv-x86_64-apple-darwin.tar.gz
    uv_sha256=96d773bf5fda4f9b08c4444847f9183d1c14bc8a28ff9c0490e261a8fc6e5309
    python_install_name=cpython-3.13.15-macos-x86_64-none
    ;;
  Linux-x86_64)
    uv_asset=uv-x86_64-unknown-linux-gnu.tar.gz
    uv_sha256=4ae93e0f148a18434cc094072547cec88912fc4a72b984183c7d0d0e9586cb5e
    python_install_name=cpython-3.13.15-linux-x86_64-gnu
    ;;
  *)
    printf 'Unsupported bootstrap platform: %s-%s\n' "$(uname -s)" "$(uname -m)" >&2
    exit 2
    ;;
esac

downloads_dir="$toolchain_root/downloads"
bin_dir="$toolchain_root/bin"
archive_path="$downloads_dir/$uv_asset"
archive_url="https://github.com/astral-sh/uv/releases/download/$uv_version/$uv_asset"
mkdir -p "$downloads_dir" "$bin_dir"

verify_sha256() {
  expected=$1
  file=$2
  if command -v shasum >/dev/null 2>&1; then
    printf '%s  %s\n' "$expected" "$file" | shasum -a 256 -c - >/dev/null
  elif command -v sha256sum >/dev/null 2>&1; then
    printf '%s  %s\n' "$expected" "$file" | sha256sum -c - >/dev/null
  else
    printf 'Neither shasum nor sha256sum is available.\n' >&2
    return 1
  fi
}

if ! test -f "$archive_path" || ! verify_sha256 "$uv_sha256" "$archive_path"; then
  partial_path="$archive_path.partial"
  curl -fL --retry 3 --output "$partial_path" "$archive_url"
  verify_sha256 "$uv_sha256" "$partial_path"
  mv "$partial_path" "$archive_path"
fi

extract_dir=$(mktemp -d "$toolchain_root/.uv-extract.XXXXXX")
cleanup() {
  rm -rf -- "$extract_dir"
}
trap cleanup EXIT HUP INT TERM
tar -xzf "$archive_path" -C "$extract_dir"
install -m 0755 "$extract_dir/uv-x86_64-"*/uv "$bin_dir/uv"
install -m 0755 "$extract_dir/uv-x86_64-"*/uvx "$bin_dir/uvx"

actual_uv_version=$("$bin_dir/uv" --version | awk '{print $2}')
if test "$actual_uv_version" != "$uv_version"; then
  printf 'Expected uv %s, got %s.\n' "$uv_version" "$actual_uv_version" >&2
  exit 1
fi

UV_CACHE_DIR="$toolchain_root/cache" \
UV_PYTHON_INSTALL_DIR="$toolchain_root/python" \
UV_PYTHON_BIN_DIR="$toolchain_root/bin" \
  "$bin_dir/uv" python install --no-bin "$python_version"

python_path="$toolchain_root/python/$python_install_name/bin/python3"
if ! test -x "$python_path"; then
  printf 'Managed Python was not installed at the expected project path: %s\n' "$python_path" >&2
  exit 1
fi

"$python_path" -c 'import sys, sysconfig
assert sys.version_info[:3] == (3, 13, 15), sys.version
assert sysconfig.get_config_var("Py_GIL_DISABLED") in (0, None), "free-threaded Python is not allowed"
'

printf 'uv %s: %s\n' "$uv_version" "$bin_dir/uv"
printf 'Python %s (standard GIL): %s\n' "$python_version" "$python_path"

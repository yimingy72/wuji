"""Strict loading of secret local lifecycle run records."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any


def load_run_file(value: str | os.PathLike[str]) -> tuple[Path, dict[str, Any]]:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("run file path must be absolute")
    file_stat = path.stat()
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("run file must be a regular file")
    if stat.S_IMODE(file_stat.st_mode) & 0o077:
        raise PermissionError("run file must have mode 0600")
    if hasattr(os, "getuid") and file_stat.st_uid != os.getuid():
        raise PermissionError("run file must be owned by the current user")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported run file schema")
    if not isinstance(payload.get("run_id"), str) or not payload["run_id"]:
        raise ValueError("run file has no run_id")
    if Path(payload.get("control", {}).get("run_file", "")) != path:
        raise ValueError("run file ownership record does not match its path")
    return path, payload

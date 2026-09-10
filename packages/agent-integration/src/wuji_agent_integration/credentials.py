"""Credential loading that is imported and called only by the Provider child."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path


class CredentialFileError(RuntimeError):
    pass


def load_api_key(path: str) -> str:
    """Read one private JSON credential without following a final symlink."""

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(Path(path), flags)
    except OSError as exc:
        raise CredentialFileError("credential file could not be opened") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CredentialFileError("credential path is not a regular file")
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise CredentialFileError("credential file permissions must be 0600 or stricter")
        raw = os.read(descriptor, 16_385)
        if len(raw) > 16_384:
            raise CredentialFileError("credential file is too large")
    finally:
        os.close(descriptor)
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CredentialFileError("credential file is not valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"api_key"}:
        raise CredentialFileError("credential file must contain only api_key")
    api_key = payload["api_key"]
    if not isinstance(api_key, str) or not api_key.strip() or len(api_key) > 8_192:
        raise CredentialFileError("api_key is invalid")
    return api_key

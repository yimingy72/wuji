"""Write one private local-password credential without exposing the password."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys


SCHEMA_VERSION = "wuji.local-password.v1"
SCRYPT_N = 1 << 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,127}$")


def _encoded(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def credential_document(username: str, password: str, *, salt: bytes | None = None):
    if USERNAME.fullmatch(username) is None:
        raise ValueError("username must use 1..128 letters, digits, dot, underscore, @ or hyphen")
    password_bytes = password.encode("utf-8")
    if not 8 <= len(password_bytes) <= 4096:
        raise ValueError("password must be 8..4096 UTF-8 bytes")
    salt = salt or secrets.token_bytes(16)
    if len(salt) != 16:
        raise ValueError("salt must be 16 bytes")
    digest = hashlib.scrypt(
        password_bytes,
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "username": username,
        "salt": _encoded(salt),
        "digest": _encoded(digest),
    }


def write_credential(path: Path, document: dict[str, str]) -> None:
    if not path.parent.is_dir():
        raise ValueError("credential output directory does not exist")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(json.dumps(document, sort_keys=True, separators=(",", ":")).encode())
            stream.write(b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _password_from_stdin() -> str:
    raw = sys.stdin.buffer.read(4098)
    if len(raw) > 4097:
        raise ValueError("password input exceeds its bound")
    if raw.endswith(b"\r\n"):
        raw = raw[:-2]
    elif raw.endswith(b"\n"):
        raw = raw[:-1]
    if b"\n" in raw or b"\r" in raw:
        raise ValueError("password input must be one line")
    return raw.decode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="read one password line from stdin instead of a hidden terminal prompt",
    )
    arguments = parser.parse_args(argv)
    password = _password_from_stdin() if arguments.password_stdin else getpass.getpass("Password: ")
    write_credential(
        arguments.output,
        credential_document(arguments.username, password),
    )
    print(json.dumps({"output": str(arguments.output), "username": arguments.username}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

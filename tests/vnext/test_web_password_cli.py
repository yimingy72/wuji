from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import stat
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "vnext_set_web_password", ROOT / "scripts/vnext/set_web_password.py"
)
password_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(password_cli)


def test_password_cli_writes_only_a_private_scrypt_credential(
    tmp_path, monkeypatch, capsys
):
    output = tmp_path / "password.json"
    plaintext = "temporary test password"
    monkeypatch.setattr(
        password_cli.sys,
        "stdin",
        SimpleNamespace(buffer=io.BytesIO((plaintext + "\n").encode())),
    )

    assert password_cli.main([
        "--output", str(output), "--username", "developer", "--password-stdin",
    ]) == 0
    document = json.loads(output.read_text())
    printed = capsys.readouterr().out

    assert document == {
        "schema_version": "wuji.local-password.v1",
        "username": "developer",
        "salt": document["salt"],
        "digest": document["digest"],
    }
    assert plaintext not in output.read_text()
    assert plaintext not in printed
    assert stat.S_IMODE(output.stat().st_mode) == 0o600

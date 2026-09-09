from pathlib import Path

import pytest

from wuji_api.database_admin import build_seed_entities, safe_identifier
from wuji_api.run_file import load_run_file


@pytest.mark.unit
def test_seed_entities_are_stable_and_cover_real_pagination() -> None:
    first = build_seed_entities("run-1")
    second = build_seed_entities("run-1")
    assert first == second
    assert len(first["projects"]) == 57
    assert first != build_seed_entities("run-2")


@pytest.mark.unit
def test_postgresql_identifiers_are_restricted() -> None:
    assert safe_identifier("wuji_test_ab12", kind="database") == "wuji_test_ab12"
    for unsafe in ('wuji-test', 'wuji"admin', "postgres;drop", "UPPER"):
        with pytest.raises(ValueError):
            safe_identifier(unsafe, kind="role")


@pytest.mark.unit
def test_run_file_requires_absolute_owned_private_file(tmp_path: Path) -> None:
    run_file = tmp_path / "run.json"
    run_file.write_text(
        '{"schema_version":1,"run_id":"run-1","control":{"run_file":"'
        + str(run_file)
        + '"}}',
        encoding="utf-8",
    )
    run_file.chmod(0o600)
    path, run = load_run_file(run_file)
    assert path == run_file
    assert run["run_id"] == "run-1"

    run_file.chmod(0o644)
    with pytest.raises(PermissionError):
        load_run_file(run_file)

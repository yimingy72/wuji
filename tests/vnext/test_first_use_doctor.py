"""First-use doctor stays offline and never emits Secret contents."""

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "first_use_doctor", ROOT / "scripts" / "vnext" / "first_use_doctor.py"
)
doctor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = doctor
SPEC.loader.exec_module(doctor)


def test_offline_doctor_redacts_secret_and_preserves_unknowns(tmp_path):
    secret = tmp_path / "provider.key"
    secret.write_text("TOP-SECRET-MUST-NOT-APPEAR")
    source = tmp_path / "trial.json"
    source.write_text(json.dumps({
        "schema_version": "wuji.first-use-trial.config.v1",
        "identity": {"tenant_ref": "tenant", "project_ref": "project", "operator_ref": "operator"},
        "model": {
            "provider": "deepseek", "published_alias": "wuji-deepseek-observe-v1",
            "model_profile_ref": "profile-v1", "provider_secret_ref": "deepseek-key",
        },
        "secret_refs": {"deepseek-key": str(secret)},
        "budget": {"unlimited": True},
        "approval": {"approved": True},
        "target": {"approved_scope_ref": "scope-1", "entry_point": "http://fixture.invalid"},
        "data_policy": {"policy_ref": "fixture-policy", "allow_synthetic_material": True},
        "evidence": {"public_output_dir": str(tmp_path / "evidence")},
    }))
    report_dir = tmp_path / "report"
    assert doctor.main(["doctor", "--config", str(source), "--offline", "--output", str(report_dir)]) == 0
    report = json.loads((report_dir / "doctor.json").read_text())
    assert report["no_external_actions"] is True
    assert report["unknown"]
    assert "TOP-SECRET-MUST-NOT-APPEAR" not in json.dumps(report)
    assert report["secret_refs"] == [{"ref": "deepseek-key", "registered": True, "mounted": True}]


def test_doctor_rejects_non_offline_mode(tmp_path):
    source = tmp_path / "trial.json"
    source.write_text("{}")
    assert doctor.main(["doctor", "--config", str(source), "--output", str(tmp_path / "out")]) == 2

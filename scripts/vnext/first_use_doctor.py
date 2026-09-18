"""Read-only first-use readiness doctor.

This command inspects a脱敏 trial document or a trusted deployment document.  It
never reads Secret values, opens a database/network connection, resolves DNS,
calls a model/target, deploys resources, or changes platform state.  The output
directory is only a local report destination.

Usage::

    python scripts/vnext/first_use_doctor.py doctor \
        --config PATH --offline --output DIR
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


SCHEMA_VERSION = "wuji.first-use-doctor.v1"
MAX_CONFIG_BYTES = 1 << 20
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _read_json(path: Path) -> Mapping[str, Any]:
    if not path.is_absolute():
        raise ValueError("config path must be absolute")
    raw = path.read_bytes()
    if not 0 < len(raw) <= MAX_CONFIG_BYTES:
        raise ValueError("config exceeds the bounded doctor input")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("config root must be an object")
    return value


def _bounded_text(value: Any) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 4096 and "\x00" not in value


def _check(checks, *, check_id: str, layer: str, status: str, reason: str,
           owner: str, message: str, evidence_ref: str | None = None) -> None:
    # Messages are authored by this module and never include source exceptions,
    # URLs with credentials, config bodies, or response bodies.
    item = {
        "id": check_id,
        "layer": layer,
        "status": status,
        "reason_code": reason,
        "remediation_owner": owner,
        "message": message[:256],
    }
    if evidence_ref is not None and _bounded_text(evidence_ref):
        item["evidence_ref"] = evidence_ref
    checks.append(item)


def _secret_inventory(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs = config.get("secret_refs")
    if not isinstance(refs, dict):
        return []
    result = []
    for name, path in sorted(refs.items()):
        if not isinstance(name, str):
            continue
        # Expose only the ref name and file presence.  Never read the file.
        result.append({
            "ref": name[:128],
            "registered": isinstance(path, str),
            "mounted": bool(isinstance(path, str) and Path(path).is_file()),
        })
    return result


def _profile_state(config: Mapping[str, Any]) -> tuple[str, str, str]:
    model = config.get("model") if isinstance(config.get("model"), dict) else {}
    deployment = config.get("deployment") if isinstance(config.get("deployment"), dict) else {}
    if config.get("schema_version") == "wuji.deployment.v1":
        path = config.get("profiles_file")
        if isinstance(path, str) and Path(path).is_file():
            return "pass", "published_profile_available", "published profile file is present"
        return "fail", "profile_missing", "published profile file is unavailable"
    if all(model.get(key) for key in ("published_alias", "model_profile_ref")):
        return "pass", "profile_declared", "published model profile reference is present"
    if model.get("provider") == "deepseek":
        return "unknown", "profile_external_reference_missing", "DeepSeek is selected but published profile evidence is external"
    return "fail", "profile_missing", "model profile reference is missing"


def build_report(config: Mapping[str, Any], *, source: Path, offline: bool = True) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    schema = config.get("schema_version")
    is_trial = schema == "wuji.first-use-trial.config.v1"
    is_deployment = schema == "wuji.deployment.v1"
    _check(
        checks, check_id="identity", layer="identity",
        status="pass" if is_trial or is_deployment else "fail",
        reason="known_config_schema" if is_trial or is_deployment else "unknown_config_schema",
        owner="application", message="configuration schema is recognised" if is_trial or is_deployment else "configuration schema is not recognised",
    )

    if is_trial:
        identity = config.get("identity") if isinstance(config.get("identity"), dict) else {}
        identity_ok = all(identity.get(key) for key in ("tenant_ref", "project_ref", "operator_ref"))
        _check(checks, check_id="operator", layer="identity", status="pass" if identity_ok else "unknown",
               reason="operator_declared" if identity_ok else "operator_external_reference_missing",
               owner="user", message="operator/project references are declared" if identity_ok else "operator identity is held outside this document")
    else:
        owner = config.get("owner")
        _check(checks, check_id="operator", layer="identity", status="pass" if isinstance(owner, list) and len(owner) == 3 else "unknown",
               reason="owner_binding_declared" if isinstance(owner, list) and len(owner) == 3 else "owner_binding_external",
               owner="application", message="trusted owner binding is declared" if isinstance(owner, list) and len(owner) == 3 else "owner binding is not in the local doctor document")

    profile_status, profile_reason, profile_message = _profile_state(config)
    _check(checks, check_id="profile", layer="profile", status=profile_status,
           reason=profile_reason, owner="gateway", message=profile_message)

    model = config.get("model") if isinstance(config.get("model"), dict) else {}
    if is_trial:
        _check(checks, check_id="provider_secret_ref", layer="model",
               status="pass" if model.get("provider_secret_ref") else "unknown",
               reason="secret_ref_declared" if model.get("provider_secret_ref") else "secret_ref_external",
               owner="gateway", message="provider SecretRef name is present; value was not read" if model.get("provider_secret_ref") else "provider SecretRef is managed outside this document")
        _check(checks, check_id="model_execution", layer="model",
               status="unknown", reason="offline_not_executed", owner="gateway",
               message="offline doctor does not make a model request")
    else:
        _check(checks, check_id="model_execution", layer="model", status="unknown",
               reason="offline_not_executed", owner="gateway",
               message="offline doctor does not make a model request")

    budget = config.get("budget") if isinstance(config.get("budget"), dict) else {}
    unlimited = bool(budget.get("unlimited") or budget.get("amount_unlimited") or budget.get("policy") == "unlimited")
    budget_ref = budget.get("gateway_budget_ref") or budget.get("price_snapshot_ref")
    _check(checks, check_id="budget", layer="budget",
           status="pass" if unlimited or budget.get("approved_amount") is not None else "unknown",
           reason="unlimited_approved" if unlimited else "budget_external_reference_missing" if budget_ref is None else "budget_reference_declared",
           owner="gateway", message="budget is declared without reading a gateway key or making a request" if unlimited or budget.get("approved_amount") is not None else "effective budget/price approval is held in an external gateway record")

    approval = config.get("approval") if isinstance(config.get("approval"), dict) else {}
    approval_ref = approval.get("existing_approval_ref")
    _check(checks, check_id="approval", layer="identity",
           status="pass" if approval_ref else "unknown",
           reason="approval_reference_declared" if approval_ref else "approval_external_reference_missing",
           owner="user", message="approval reference is present" if approval_ref else "client approved flag is not treated as authority")

    target = config.get("target") if isinstance(config.get("target"), dict) else {}
    target_ok = bool(target.get("approved_scope_ref") and (target.get("entry_point") or target.get("approved_safe_entry_points")))
    _check(checks, check_id="target_scope", layer="target", status="pass" if target_ok else "unknown",
           reason="scope_and_entry_declared" if target_ok else "target_scope_external_reference_missing",
           owner="user", message="approved scope and safe entry reference are present" if target_ok else "target scope/entry approval is held outside this document")
    _check(checks, check_id="target_connectivity", layer="target", status="unknown",
           reason="offline_not_executed", owner="infrastructure",
           message="offline doctor does not resolve, connect, follow redirects, or request the target")

    if is_trial:
        deployment = config.get("deployment") if isinstance(config.get("deployment"), dict) else {}
        runtime_ok = bool(deployment.get("namespace_or_runtime_ref") and deployment.get("image_manifest_ref"))
    else:
        runtime_ok = bool(config.get("role") and config.get("profiles_file"))
    _check(checks, check_id="runtime", layer="runtime", status="pass" if runtime_ok else "unknown",
           reason="runtime_reference_declared" if runtime_ok else "runtime_external_reference_missing",
           owner="infrastructure", message="runtime reference and published material are declared" if runtime_ok else "runtime deployment details are held outside this document")

    data_policy = config.get("data_policy") if isinstance(config.get("data_policy"), dict) else {}
    data_ok = bool(data_policy.get("policy_ref") and data_policy.get("allow_synthetic_material"))
    _check(checks, check_id="data_policy", layer="material", status="pass" if data_ok else "unknown",
           reason="data_policy_declared" if data_ok else "data_policy_external_reference_missing",
           owner="user", message="synthetic material policy is declared" if data_ok else "data export policy is held outside this document")
    _check(checks, check_id="material_store", layer="material", status="pass" if (config.get("evidence") or {}).get("public_output_dir") else "unknown",
           reason="evidence_output_declared" if (config.get("evidence") or {}).get("public_output_dir") else "evidence_store_external_reference_missing",
           owner="application", message="doctor only records the output reference; it does not write platform state")

    blockers = [item["id"] for item in checks if item["status"] == "fail"]
    unknown = [item["id"] for item in checks if item["status"] == "unknown"]
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "doctor",
        "offline": bool(offline),
        "source_name": source.name,
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "can_request_start": not blockers,
        "checks": checks,
        "blockers": blockers,
        "unknown": unknown,
        "secret_refs": _secret_inventory(config),
        "no_external_actions": True,
    }


def _write_report(output: Path, report: Mapping[str, Any]) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "doctor.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="read-only first-use doctor")
    sub = parser.add_subparsers(dest="command")
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--config", required=True, type=Path)
    doctor.add_argument("--offline", action="store_true")
    doctor.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command != "doctor" or not args.offline:
        print("doctor requires the explicit --offline mode", file=sys.stderr)
        return 2
    try:
        config = _read_json(args.config)
        report = build_report(config, source=args.config, offline=True)
        path = _write_report(args.output, report)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return 2
    print(json.dumps({"command": "doctor", "output": path.name,
                      "can_request_start": report["can_request_start"],
                      "unknown_count": len(report["unknown"])}, sort_keys=True))
    return 2 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

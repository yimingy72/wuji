"""E06: closed trial cases with an independent grader and a replayable record.

Nothing in this script decides product truth: it prepares closed, non-sensitive
materials, proves the configuration before a run, launches the already-built
owner command, and reads back what the platform actually recorded. A case's
expected answer lives in ``grader/`` — outside the material root, never mounted
into the Task workspace and never part of a Task goal — so a Run cannot read it.

Subcommands (all bounded, no target contact in ``fixtures``/``preflight``)::

    exploration_trials.py fixtures --suite <dir>
    exploration_trials.py preflight --suite <dir> [--config <deployment.json>]
    exploration_trials.py case-config --suite <dir> --case <id> --config <deployment.json>
                                     --task <task-id> --out <run-config.json>
    exploration_trials.py run --run-config <file> --task <task-id> --phase prepare
    exploration_trials.py inspect --trial <dir>
    exploration_trials.py summarize --suite <dir>
    exploration_trials.py stop --config <deployment.json> --task <task-id> --reason <text>
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "wuji.exploration-trial.v1"

GOAL_REFERENCE = (
    "Report the inventory service version recorded in the registry file that the"
    " workspace entry document points to, and cite the file it came from."
)
GOAL_COMPARISON = (
    "Report whether the two inventory records in the workspace agree on the"
    " service version, and state the version."
)

# Materials are closed, non-sensitive fixtures. A variant's label and its
# expected answer exist only under grader/, never inside a material file, a Task
# goal or a tool name.
CASES = {
    "A-reference": {
        "family": "CASE-A",
        "goal": GOAL_REFERENCE,
        "materials": {
            "materials/entry.json": json.dumps(
                {"pointer": "materials/registry-oct.json"}, sort_keys=True
            ),
            "materials/registry-oct.json": json.dumps(
                {"service": "inventory", "version": "4.2.0", "changed": "2026-09-01"},
                sort_keys=True,
            ),
            "materials/registry-nov.json": json.dumps(
                {"service": "inventory", "version": "4.3.1", "changed": "2026-10-02"},
                sort_keys=True,
            ),
        },
        "expected": {
            "answer": "4.2.0",
            "answer_files": ["materials/registry-oct.json"],
            "reference_chain": [
                "materials/entry.json",
                "materials/registry-oct.json",
            ],
            "decoy_version": "4.3.1",
            "kind": "runtime_reference",
        },
    },
    "B-consistent": {
        "family": "CASE-B",
        "goal": GOAL_COMPARISON,
        "materials": {
            "materials/record-a.json": json.dumps(
                {"service": "inventory", "version": "4.2.0"}, sort_keys=True
            ),
            "materials/record-b.json": json.dumps(
                {"service": "inventory", "version": "4.2.0"}, sort_keys=True
            ),
        },
        "expected": {
            "answer": "agree",
            "version": "4.2.0",
            "answer_files": ["materials/record-a.json", "materials/record-b.json"],
            "kind": "consistent_pair",
        },
    },
    "B-conflict": {
        "family": "CASE-B",
        "goal": GOAL_COMPARISON,
        "materials": {
            "materials/record-a.json": json.dumps(
                {"service": "inventory", "version": "4.2.0"}, sort_keys=True
            ),
            "materials/record-b.json": json.dumps(
                {"service": "inventory", "version": "4.3.1"}, sort_keys=True
            ),
        },
        "expected": {
            "answer": "conflict",
            "versions": ["4.2.0", "4.3.1"],
            "answer_files": ["materials/record-a.json", "materials/record-b.json"],
            "kind": "conflicting_pair",
        },
    },
    "C-insufficient": {
        "family": "CASE-C",
        "goal": GOAL_COMPARISON,
        "materials": {
            "materials/record-a.json": json.dumps(
                {"service": "inventory", "version": "4.2.0"}, sort_keys=True
            ),
            "materials/record-b.json": json.dumps({"service": "inventory"}, sort_keys=True),
        },
        "expected": {
            "answer": "insufficient",
            "answer_files": ["materials/record-a.json"],
            "kind": "missing_field",
        },
    },
}

CASE_ORDER = ("A-reference", "B-consistent", "B-conflict", "C-insufficient")


def _write(path: Path, data: bytes, *, mode=0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


def _json(value) -> bytes:
    return json.dumps(value, sort_keys=True, indent=1).encode() + b"\n"


def build_fixtures(suite: Path) -> dict:
    """Write every case under ``suite``: materials and grader stay separate."""

    suite = Path(suite)
    written = {}
    for name in CASE_ORDER:
        case = CASES[name]
        material_root = suite / name / "materials"
        for relative, text in case["materials"].items():
            target = suite / name / relative
            _write(target, text.encode("utf-8") + b"\n")
        _write(
            suite / name / "goal.txt",
            (case["goal"] + "\n").encode("utf-8"),
        )
        _write(suite / "grader" / f"{name}.json", _json({
            "schema_version": SCHEMA_VERSION,
            "case": name,
            "family": case["family"],
            "expected": case["expected"],
            "material_sha256": {
                relative: sha256(text.encode("utf-8")).hexdigest()
                for relative, text in case["materials"].items()
            },
        }))
        written[name] = {
            "materials": sorted(case["materials"]),
            "material_root": str(material_root),
        }
    _write(suite / "manifest.json", _json({
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cases": written,
        "grader_root": str(suite / "grader"),
    }))
    return written


def case_materials(name: str, suite: Path) -> list[dict]:
    """The published material set for one case, read back from disk."""

    case = CASES[name]
    materials = []
    for relative in sorted(case["materials"]):
        text = (Path(suite) / name / relative).read_text()
        materials.append({"path": relative, "text": text})
    return materials


def preflight_case(name: str, suite: Path) -> dict:
    """Prove one case's separation and shape without touching any target."""

    case = CASES[name]
    suite = Path(suite)
    report = {"case": name, "family": case["family"], "checks": [], "blocked": []}

    def record(check, state, detail):
        report["checks"].append({"check": check, "state": state, "detail": detail})
        if state == "blocked":
            report["blocked"].append(check)

    grader_path = suite / "grader" / f"{name}.json"
    if not grader_path.is_file():
        record("grader", "blocked", "no independent expected-answer document")
        return report
    grader = json.loads(grader_path.read_text())
    record("grader", "ok", "independent document present")

    material_root = (suite / name / "materials").resolve()
    if grader_path.resolve().is_relative_to(material_root):
        record("separation", "blocked", "the expected answer is inside the material root")
    else:
        record("separation", "ok", "grader is outside the material root")

    expected = grader["expected"]
    answer_files = set(expected.get("answer_files") or ())
    answers = []
    for key in ("answer", "version"):
        value = expected.get(key)
        if isinstance(value, str) and value not in {"agree", "conflict", "insufficient"}:
            answers.append(value)
    answers.extend(expected.get("versions") or [])

    for relative in sorted(case["materials"]):
        path = suite / name / relative
        if not path.is_file():
            record("material:" + relative, "blocked", "published material is missing")
            continue
        text = path.read_text()
        digest = sha256(text.rstrip("\n").encode("utf-8")).hexdigest()
        if digest != grader["material_sha256"][relative]:
            record("material:" + relative, "blocked", "material bytes changed")
            continue
        leaked = [value for value in answers if value in text]
        # The file that legitimately holds the answer is the material under
        # study; every other file must not hand the answer over.
        if leaked and relative not in answer_files:
            record("material:" + relative, "blocked", "this file hands over the answer")
        else:
            record("material:" + relative, "ok", "material bytes unchanged")

    goal = (suite / name / "goal.txt").read_text().strip()
    if goal != case["goal"]:
        record("goal", "blocked", "the published goal text changed")
    elif any(value in goal for value in answers):
        record("goal", "blocked", "the goal states the expected answer")
    else:
        record("goal", "ok", "goal describes the question only")

    # A variant label must never reach the material or the goal.
    if name in goal or name in "".join(
        (suite / name / relative).read_text() for relative in case["materials"]
    ):
        record("variant_label", "blocked", "the variant label leaked into the run")
    else:
        record("variant_label", "ok", "no variant label in goal or materials")
    return report


def preflight_suite(suite: Path) -> dict:
    reports = [preflight_case(name, suite) for name in CASE_ORDER]
    goals = {}
    for name in CASE_ORDER:
        goals.setdefault(CASES[name]["family"], set()).add(CASES[name]["goal"])
    same_goal = {
        family: len(texts) == 1 for family, texts in goals.items() if family == "CASE-B"
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "suite": str(suite),
        "cases": reports,
        "blocked": [report["case"] for report in reports if report["blocked"]],
        "same_goal_for_variants": same_goal,
    }


def case_run_config(*, suite: Path, name: str, deployment: dict, task_id: str) -> dict:
    """The deployment document plus this case's closed materials."""

    if name not in CASES:
        raise SystemExit("unknown case: " + name)
    config = json.loads(json.dumps(deployment))
    config["materials"] = case_materials(name, suite)
    config["trial"] = {
        "schema_version": SCHEMA_VERSION,
        "case": name,
        "family": CASES[name]["family"],
        "task_id": task_id,
        "goal": CASES[name]["goal"],
    }
    return config


def _load_launcher():
    path = ROOT / "ops/vnext/task_launch.py"
    spec = importlib.util.spec_from_file_location("wuji_task_launch_trials", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["wuji_task_launch_trials"] = module
    spec.loader.exec_module(module)
    return module


def run_phase(config_path: Path, *, task_id: str, phase: str, options: dict) -> dict:
    """Delegate one owner phase to the real launcher; this script adds nothing."""

    launcher = _load_launcher()
    config = json.loads(Path(config_path).read_text())
    binding, result = launcher.run_phases(
        config, task_id=task_id, phases=[phase], options=options
    )
    return {"phase": phase, "task_id": task_id, "result": result}


def inspect_trial(directory: Path) -> dict:
    """Read one trial record back: what ran, what it produced, what is unknown."""

    directory = Path(directory)
    summary = {"trial": str(directory), "files": [], "missing": []}
    for name in ("trial.json", "manifest.json", "result.json", "grading.json"):
        path = directory / name
        if path.is_file():
            summary["files"].append(name)
            if name in {"trial.json", "grading.json"}:
                summary[name.split(".")[0]] = json.loads(path.read_text())
        else:
            summary["missing"].append(name)
    return summary


def summarize_suite(suite: Path) -> dict:
    """Aggregate trial records without inventing a success rate."""

    suite = Path(suite)
    trials = sorted(path for path in suite.glob("trials/*") if path.is_dir())
    rows = []
    for trial in trials:
        grading = trial / "grading.json"
        rows.append({
            "trial": trial.name,
            "graded": grading.is_file(),
            "case": json.loads((trial / "trial.json").read_text()).get("case")
            if (trial / "trial.json").is_file() else None,
        })
    return {
        "suite": str(suite),
        "trials": rows,
        "graded": sum(1 for row in rows if row["graded"]),
        "ungraded": sum(1 for row in rows if not row["graded"]),
    }


def stop_task(config_path: Path, *, task_id: str, reason: str, base_url: str | None) -> dict:
    """Send the real cancel command and read the Task back from storage."""

    launcher = _load_launcher()
    config = json.loads(Path(config_path).read_text())
    owner = (config["owner"][0], config["owner"][1], task_id)
    connection = launcher.owner_connection(config)
    try:
        row = connection.execute(
            "SELECT desired_state, observed_state, control_version FROM vnext.task"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            owner,
        ).fetchone()
        if row is None:
            raise SystemExit("unknown task")
        version = str(row[2])
    finally:
        connection.close()
    payload = {
        "schema_version": "wuji.api.v2",
        "command": "cancel",
        "expected_version": version,
        "reason": reason,
    }
    import httpx

    token = launcher.operator_token(config)
    with httpx.Client(verify=config["ca_file"], trust_env=False, timeout=15.0) as peer:
        response = peer.post(
            f"{base_url or 'https://runtime.wuji-vnext-test.svc:8443'}"
            f"/api/v2/tasks/{task_id}/commands",
            json=payload,
            headers={
                "Authorization": "Bearer " + token,
                "Idempotency-Key": f"trial-cancel-{task_id}",
            },
        )
    accepted = response.status_code == 202
    connection = launcher.owner_connection(config)
    try:
        after = connection.execute(
            "SELECT desired_state, observed_state, control_version FROM vnext.task"
            " WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
            owner,
        ).fetchone()
    finally:
        connection.close()
    return {
        "task_id": task_id,
        "accepted": accepted,
        "status_code": response.status_code,
        "before": {"desired_state": row[0], "observed_state": row[1]},
        "after": {"desired_state": after[0], "observed_state": after[1]},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="closed exploration trials (E06)")
    commands = parser.add_subparsers(dest="command", required=True)

    fixtures = commands.add_parser("fixtures")
    fixtures.add_argument("--suite", required=True)

    preflight = commands.add_parser("preflight")
    preflight.add_argument("--suite", required=True)

    case_config = commands.add_parser("case-config")
    case_config.add_argument("--suite", required=True)
    case_config.add_argument("--case", required=True, choices=list(CASE_ORDER))
    case_config.add_argument("--config", required=True)
    case_config.add_argument("--task", required=True)
    case_config.add_argument("--out", required=True)

    run = commands.add_parser("run")
    run.add_argument("--run-config", required=True)
    run.add_argument("--task", required=True)
    run.add_argument("--phase", default="prepare",
                     choices=["preflight", "prepare", "activate", "wire", "capability"])
    run.add_argument("--deployment-auth-dir", default="/run/wuji/deployment-signing")
    run.add_argument("--agent-image", default="")
    run.add_argument("--kali-image", default="")

    inspect = commands.add_parser("inspect")
    inspect.add_argument("--trial", required=True)

    summarize = commands.add_parser("summarize")
    summarize.add_argument("--suite", required=True)

    stop = commands.add_parser("stop")
    stop.add_argument("--config", required=True)
    stop.add_argument("--task", required=True)
    stop.add_argument("--reason", default="trial stop: operator ended the closed run")
    stop.add_argument("--base-url", default="")

    args = parser.parse_args(argv)
    if args.command == "fixtures":
        written = build_fixtures(Path(args.suite))
        print(json.dumps({"event": "trial_fixtures", "cases": written}, sort_keys=True))
        return 0
    if args.command == "preflight":
        report = preflight_suite(Path(args.suite))
        print(json.dumps({"event": "trial_preflight", **report}, sort_keys=True))
        return 1 if report["blocked"] else 0
    if args.command == "case-config":
        deployment = json.loads(Path(args.config).read_text())
        config = case_run_config(
            suite=Path(args.suite), name=args.case,
            deployment=deployment, task_id=args.task,
        )
        _write(Path(args.out), _json(config))
        print(json.dumps({
            "event": "trial_case_config", "case": args.case, "out": args.out,
            "materials": [item["path"] for item in config["materials"]],
        }, sort_keys=True))
        return 0
    if args.command == "run":
        result = run_phase(
            Path(args.run_config), task_id=args.task, phase=args.phase,
            options={
                "deployment_auth_dir": args.deployment_auth_dir,
                "agent_image": args.agent_image,
                "kali_image": args.kali_image,
            },
        )
        print(json.dumps({"event": "trial_run", **result}, sort_keys=True, default=str))
        return 0
    if args.command == "inspect":
        print(json.dumps({"event": "trial_inspect", **inspect_trial(Path(args.trial))},
                         sort_keys=True, default=str))
        return 0
    if args.command == "summarize":
        print(json.dumps({"event": "trial_summary", **summarize_suite(Path(args.suite))},
                         sort_keys=True))
        return 0
    if args.command == "stop":
        result = stop_task(
            Path(args.config), task_id=args.task, reason=args.reason,
            base_url=args.base_url or None,
        )
        print(json.dumps({"event": "trial_stop", **result}, sort_keys=True))
        return 0
    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main())

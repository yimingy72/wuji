"""Archive existing P09 records only. Never imports product code or runs tests/DB.

Input is this lane's original local JSONL transcript; it is not distributed.
Only allowlisted commands, relevant edits, and immutable Git files are exported.
"""

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DEST = Path(__file__).resolve().parent
BASE = "a3f7a95eacce20cbdeeaf654ea8f86064222ba0c"
RED_BASE = "57ec12ea2ada7acf7fe6a0ac7ac98b40e7c66012"
FIX = "e0a10b586905ed705b0d7f520bda6f6f96b26cac"
THREAD = "01a0991d-3297-7853-89df-ff3407025e11"
CUTOFF = "2026-09-13T06:45:00Z"
RUNS = [
    ("baseline-31", "exec-887d2c5f-1e6c-4a66-8872-65dafdc57ccc", 0, "31 passed in 16.57s", BASE, "committed_checkout"),
    ("consumers-4", "exec-ce8f2637-a518-4a79-a75a-6fd9768529be", 0, "4 passed in 3.53s", BASE, "committed_checkout"),
    ("capacity-race-1", "exec-5316558f-7a0e-4d09-b086-923ae1904d8f", 0, "1 passed in 0.74s", BASE, "committed_checkout"),
    ("review-abc-red", "exec-5116598f-4eb8-4693-879b-263ff4211cd1", 1, "3 failed in 5.04s", RED_BASE, "base_plus_uncommitted_tests"),
    ("review-abc-green", "exec-8ca1cc67-6b67-4009-9a50-d33539a37d0e", 0, "3 passed in 5.00s", FIX, "precommit_worktree_later_committed"),
    ("upgrade-0011", "exec-e0467c17-7016-41b1-a183-efb4c7e4e438", 0, "1 passed in 1.22s", FIX, "precommit_worktree_later_committed"),
    ("pod-uid-1", "exec-02e293b5-cccd-4e0d-85e2-0ae4925f3816", 0, "1 passed in 2.49s", FIX, "precommit_worktree_later_committed"),
]
CORE = "packages/wuji-core/src/wuji_core/"
OWNED = [CORE + p for p in (
    "scheduling/__init__.py", "scheduling/policy.py", "scheduling/claims.py",
    "scheduling/triggers.py", "scheduling/waiters.py", "scheduling/credentials.py",
    "persistence/schema.py", "persistence/scheduler_schema.py",
    "persistence/dispatch_fairness_schema.py", "persistence/snapshots.py",
)] + ["services/wuji-scheduler/main.py", "tests/vnext/test_scheduler_generations.py", "tests/vnext/support/p09.py"]
INPUTS = [CORE + p for p in (
    "persistence/uow.py", "persistence/control_schema.py", "persistence/knowledge_schema.py",
    "persistence/admission_schema.py", "persistence/admission_hardening_schema.py",
    "persistence/admission_request_guard_schema.py", "execution/control.py",
    "execution/capacity.py", "execution/dependencies.py", "execution/states.py",
    "blackboard/committer.py", "blackboard/claims.py", "blackboard/fact_view.py",
    "blackboard/relations.py", "blackboard/result_state.py", "blackboard/assessments.py",
    "evidence/artifacts.py", "evidence/observations.py", "admission/registry.py",
    "admission/common.py", "admission/ledger.py", "admission/tools.py", "admission/models.py",
    "http/auth.py", "http/json_boundary.py", "contracts/generated.py",
    "contracts/envelopes.py", "contracts/knowledge.py", "contracts/execution.py",
)] + ["tests/vnext/" + p for p in (
    "conftest.py", "support/p03.py", "support/p06.py", "support/postgres.py",
    "support/identity_provider.py", "support/http_capture.py", "test_capture_transactions.py",
    "test_knowledge_admission.py", "test_run_admission.py", "test_work_state_guards.py",
)] + ["scripts/vnext/uv.sh", "packages/maf-worker/src/wuji_maf_worker/factory.py",
      "packages/maf-worker/pyproject.toml", "packages/maf-worker/uv.lock"]


def digest(body):
    return hashlib.sha256(body).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def redact(value):
    if isinstance(value, str):
        value = value.replace(str(ROOT), "<WORKTREE>")
        value = re.sub(r"/private/var/folders/[^/]+/[^/]+/T", "<LOCAL_TMP>", value)
        value = re.sub(r"pytest-of-[A-Za-z0-9_-]+", "pytest-of-<USER>", value)
        value = value.replace(str(Path.home()), "<HOME>")
        value = re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "<REDACTED_JWT>", value)
        value = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----", "<REDACTED_PRIVATE_KEY>", value)
        return value
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, dict):
        return {redact(k): redact(v) for k, v in value.items()}
    return value


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_gzip(path, content):
    path.write_bytes(gzip.compress(content, mtime=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--pytest-root", type=Path, required=True)
    args = parser.parse_args()
    prefix = []
    events = []
    selected = {}
    edits = []
    raw_selected = []
    for line_no, line in enumerate(args.transcript.read_bytes().splitlines(keepends=True), 1):
        envelope = json.loads(line)
        if envelope["timestamp"] >= CUTOFF:
            continue
        prefix.append(line)
        payload = envelope.get("payload", {})
        if envelope["type"] != "event_msg" or payload.get("type") != "item_completed":
            continue
        item = payload["item"]
        provenance = {
            "transcript_line": line_no,
            "source_line_sha256": digest(line),
            "timestamp": envelope["timestamp"],
            "item_id": item["id"],
        }
        if item["type"] == "CommandExecution":
            command = item["command"][-1]
            is_test = command.startswith("./scripts/vnext/uv.sh run --frozen pytest") or command.startswith("./scripts/uv.sh run --frozen pytest")
            is_binding = command.startswith("git ") and any(word in command for word in ("rev-parse", "commit -m"))
            if not is_test and not is_binding:
                continue
            exported = dict(provenance, started_at_ms=payload["started_at_ms"],
                            completed_at_ms=payload["completed_at_ms"],
                            item=redact(item))
            events.append(exported)
            selected[item["id"]] = (exported, item)
            raw_selected.append(line)
        elif item["type"] == "FileChange" and envelope["timestamp"] >= "2026-09-13T06:23:00Z":
            changes = {k: v for k, v in item["changes"].items()
                       if k.removeprefix(str(ROOT) + "/") in OWNED}
            if changes:
                edits.append(dict(provenance, changes=redact(changes), status=item["status"]))

    private_dir = ROOT / "work/p09-evidence-private"
    private_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    private_dir.chmod(0o700)
    private_record = private_dir / "original-command-envelope-lines.jsonl"
    private_record.write_bytes(b"".join(raw_selected))
    private_record.chmod(0o600)

    write_gzip(DEST / "command-records.jsonl.gz", b"".join(
        (json.dumps(event, ensure_ascii=False) + "\n").encode() for event in events
    ))
    write_gzip(DEST / "review-edit-records.jsonl.gz", b"".join(
        (json.dumps(event, ensure_ascii=False) + "\n").encode() for event in edits
    ))

    runs = []
    for name, item_id, code, summary, revision, binding in RUNS:
        event, item = selected[item_id]
        assert item["exit_code"] == code and summary in item["aggregated_output"]
        path = DEST / "outputs" / (name + ".txt")
        path.parent.mkdir(exist_ok=True)
        body = redact(item["aggregated_output"]).encode()
        path.write_bytes(body)
        runs.append({
            "id": name, "command": item["command"][-1], "cwd": "<WORKTREE>",
            "exit_code": code, "summary": summary, "timestamp_utc": event["timestamp"],
            "record_id": item_id, "source_line": event["transcript_line"],
            "source_line_sha256": event["source_line_sha256"],
            "original_aggregated_output_sha256": digest(item["aggregated_output"].encode()),
            "output": str(path.relative_to(DEST)), "output_sha256": digest(body),
            "code_commit": revision, "code_binding": binding,
            "database": {
                "postgresql": "real_isolated_fixture",
                "application_role": ("not_used_by_migration_only_node" if name == "upgrade-0011" else "non_owner_no_bypassrls"),
                "migration_and_deployment_role": "separate_owner_role",
                "two_connections": ("two_tenants_shared_last_capacity" if name == "capacity-race-1" else "ownership_race_subtest_only" if name == "baseline-31" else "not_claimed"),
                "basis": "original completed command plus commit-pinned fixture/assertions; per-query runtime logs missing",
            },
            "sql_runtime_log": "missing_not_recreated",
            "notes": ("C failed on missing last_considered_work_id; final implementation/tests use consideration_round. "
                      "Uncommitted RED test bytes were not snapshotted; original edits and failure body are archived."
                      if name == "review-abc-red" else ""),
        })

    # Export Git bytes as data. Do not import/execute source or generate SQL.
    buffer = io.BytesIO()
    sources = []
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for revision in (BASE, RED_BASE, FIX):
            tree = {}
            for line in git("ls-tree", "-r", revision).decode().splitlines():
                meta, path = line.split("\t", 1)
                tree[path] = meta.split()[2]
            for path in sorted(set(OWNED + INPUTS)):
                if path not in tree:
                    continue
                body = git("cat-file", "blob", tree[path])
                member = revision[:7] + "/" + path
                info = tarfile.TarInfo(member)
                info.size = len(body)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(body))
                sources.append({"commit": revision, "path": path, "git_blob": tree[path],
                                "sha256": digest(body), "bytes": len(body), "member": member})
    write_gzip(DEST / "codefiles.tar.gz", buffer.getvalue())
    write_json(DEST / "codefile-index.json", {
        "type": "immutable_git_source_archive_not_runtime_fingerprint",
        "archive": "codefiles.tar.gz", "entries": sources,
        "limits": "Selected P09 implementation, SQL definitions, input factories and direct dependencies; not a complete runtime/environment archive. RED uncommitted tests are not falsely attributed to a commit.",
    })

    reviews = []
    for name in ("P09-review.md", "P09-rereview.md"):
        source = ROOT / ".superpowers/sdd/vnext-v2" / name
        target = DEST / "reviews" / name
        target.parent.mkdir(exist_ok=True)
        data = source.read_bytes()
        target.write_bytes(data)
        reviews.append({"path": str(target.relative_to(DEST)), "source": str(source.relative_to(ROOT)),
                        "sha256": digest(data), "copy": "byte_identical",
                        "note": "Historical missing-permanent-package statements describe review time; this archive was added later."})

    tmp_dirs = sorted(p.name for p in args.pytest_root.iterdir() if p.name != "pytest-current")
    # Do not inspect another lane's surviving SQL bodies. Name inventory is enough.
    candidate_logs = sorted(str(p.relative_to(args.pytest_root))
                            for p in args.pytest_root.rglob("postgres-events.jsonl")
                            if "scheduler" in str(p) or "shared_global_pool" in str(p)
                            or "reason_intents" in str(p) or "persisted_work_cursor" in str(p))
    assert not candidate_logs, "A P09 SQL log remains: inspect and redact before declaring it missing"
    write_json(DEST / "index.json", {
        "schema_version": 1, "stage": "P09", "status": "reviewed_partial_not_full_acceptance",
        "archived_at_utc": datetime.now(timezone.utc).isoformat(), "new_tests_run": False,
        "new_db_http_or_product_checks": False,
        "executing_lane": {"name": "Archimedes", "thread_id": THREAD, "assigned_model": "gpt-5.6-sol/xhigh"},
        "transcript": {"thread_id": THREAD, "file_name": args.transcript.name,
                       "cutoff_utc": CUTOFF, "prefix_sha256": digest(b"".join(prefix)),
            "raw_distribution": "local_only_not_archived", "selection": "CommandExecution and scoped FileChange only; no reasoning or unrelated conversations"},
        "runs": runs, "reviews": reviews,
        "run_binding_limits": {
            "baseline": "31+4+1 were executed after a3f7a95 commit. They are not e0a10b5 reruns.",
            "review_green": "3+upgrade1+UID1 were executed precommit; final seven-path bytes were committed to e0a10b5. No postcommit DB run or contemporaneous full file-hash manifest exists; binding relies on original edit/commit records and Dalton rereview.",
            "review_red": "57ec12e base plus uncommitted test changes. A/B P09 code unchanged from a3f7a95. C RED is missing-field failure, not a completed starvation trace.",
        },
        "evidence_gaps": {"pytest_root": "<LOCAL_TMP>/pytest-of-<USER>",
                          "surviving_directories_at_inventory": tmp_dirs,
                          "p09_sql_logs_recovered": 0,
                          "sql": "Original per-test postgres-events.jsonl/parameters/results could not be recovered; earlier pytest directories are absent. Code SQL is archived as source, not as replayed execution.",
                          "runtime_inputs": "Random run IDs, issued credentials, raw artifact bytes and per-test identity files absent with temporary directories. Literal input factories at Git commits are preserved, not regenerated.",
                          "junit": "Not requested by the original commands; no JUnit report created now.",
                          "http_screenshots": "No new HTTP or screenshot evidence. Consumers-4 includes actual in-process P04 HTTP calls; their original exchanges were not recovered. This archive does not manufacture HTTP records or claim a real network/Pod run."},
        "redaction": {"paths": ["<WORKTREE>", "<HOME>", "<LOCAL_TMP>"],
                      "values": ["JWT bearer strings", "PEM private keys"],
                      "policy": "Keep synthetic fixture IDs and SQL/schema; do not export local PG connection manifest or raw session. Output hashes before and after redaction retained.",
                      "restricted_local_copy": {"path": "<WORKTREE>/work/p09-evidence-private/original-command-envelope-lines.jsonl", "directory_mode": "0700", "file_mode": "0600", "sha256": digest(b"".join(raw_selected)), "git_included": False}},
        "partial_acceptance_ids": ["AC-007", "AC-015", "AC-018", "AC-024", "AC-025", "AC-026", "AC-027", "AC-028", "AC-029"],
        "deferred": ["Real P10/M2 Outbox/Supervisor/Worker/Pod chain", "P08 non-knowledge events at same board_revision",
                     "Reason failure/retry closure with authentic exit receipts", "Session restoration",
                     "Full accepted Reason/Wait/Completion consumer chain"],
    })
    files = sorted(p for p in DEST.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (DEST / "SHA256SUMS").write_text("".join(
        digest(p.read_bytes()) + "  " + p.relative_to(DEST).as_posix() + "\n"
        for p in files
    ))
    print(json.dumps({"archived_runs": len(runs), "archived_commands": len(events),
                      "scoped_edit_records": len(edits), "git_source_files": len(sources),
                      "sql_logs_recovered": 0, "new_execution": False}))


if __name__ == "__main__":
    main()

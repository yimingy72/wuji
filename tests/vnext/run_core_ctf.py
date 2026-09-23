"""Run the real local Core CTF mechanism chain through the password BFF.

The runner creates and starts one ordinary Task, verifies the deterministic
Reason/A/B mechanism from public records and sealed bytes, then cancels it and
waits for persisted external container termination. It never writes the database directly and
never submits a Goal-completion judgment.
"""

from __future__ import annotations

import argparse
import base64
import binascii
from datetime import datetime, timezone
from hashlib import sha256
import http.cookiejar
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops/vnext"))

from synthetic_model import (  # noqa: E402
    CORE_RESULT,
    CORE_SCRIPT,
    CORE_WORK_A,
    CORE_WORK_B,
    _core_script,
)
from wuji_core.contracts.generated import (  # noqa: E402
    TaskCommand,
    TaskCreate,
    WorkspaceBundleManifestV1,
)
from wuji_core.http import canonical_json_bytes, strict_json_loads  # noqa: E402


IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}$")
SOURCE_REVISION = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})\Z")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
IMAGE_ROLES = {"platform", "web", "agent", "kali", "capture", "postgres"}
BUSINESS_IMAGE_ROLES = {"platform", "web", "agent", "kali", "capture"}
RUN_KEYS = {
    "schema_version", "mode", "run_id", "configuration_directory",
    "evidence_directory", "expected_source_revision", "username", "password",
    "task", "timeout_seconds", "poll_seconds",
}
TASK_KEYS = {
    "name", "goal", "criteria", "authorization_expires_at", "budget_amount",
    "model_profile_ref", "runtime_profile_ref", "explore_concurrency",
}
SECRET_HEADERS = {"authorization", "cookie", "set-cookie", "x-wuji-local-access"}


class RunFailure(RuntimeError):
    pass


class OperationUnknown(RunFailure):
    pass


def _write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(value)


def _append(path: Path, value: dict) -> None:
    with path.open("ab") as stream:
        stream.write(canonical_json_bytes(value) + b"\n")


def _json(path: Path, value) -> None:
    _write(path, canonical_json_bytes(value) + b"\n")


def _private_file(path: Path) -> None:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise ValueError("run-file must be an absolute regular file")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("run-file must not be accessible to group or others")


def _absolute_private_work(path: str, *, must_exist: bool) -> Path:
    value = Path(path)
    if not value.is_absolute() or ROOT / "work" not in value.parents:
        raise ValueError("Core CTF paths must be absolute ignored work paths")
    if must_exist and not value.is_dir():
        raise ValueError("prepared configuration directory is unavailable")
    if not must_exist and value.exists():
        raise ValueError("evidence directory already exists")
    return value


def load_run(path: Path) -> dict:
    _private_file(path)
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict) or set(value) != RUN_KEYS:
        raise ValueError("fixed Core CTF run-file fields required")
    if value["schema_version"] != "wuji.core-ctf-run.v1" or value["mode"] != "mechanism":
        raise ValueError("only the Core CTF mechanism run is supported")
    if not isinstance(value["run_id"], str) or not IDENTIFIER.fullmatch(value["run_id"]):
        raise ValueError("bounded run_id required")
    if not isinstance(value["username"], str) or not value["username"]:
        raise ValueError("password login username required")
    if not isinstance(value["password"], str) or not value["password"]:
        raise ValueError("password login secret required")
    if not isinstance(value["expected_source_revision"], str) or not re.fullmatch(
        r"[a-f0-9]{7,64}", value["expected_source_revision"]
    ):
        raise ValueError("fixed source revision required")
    task = value["task"]
    if not isinstance(task, dict) or set(task) != TASK_KEYS:
        raise ValueError("fixed Task input required")
    if (
        not isinstance(task["criteria"], list)
        or not 1 <= len(task["criteria"]) <= 16
        or any(not isinstance(item, str) or not 1 <= len(item) <= 2048 for item in task["criteria"])
        or type(task["explore_concurrency"]) is not int
        or not 1 <= task["explore_concurrency"] <= 256
        or not isinstance(value["timeout_seconds"], int)
        or not 60 <= value["timeout_seconds"] <= 3600
        or isinstance(value["poll_seconds"], bool)
        or not isinstance(value["poll_seconds"], (int, float))
        or not 0.2 <= value["poll_seconds"] <= 10
    ):
        raise ValueError("bounded run limits and Task criteria required")
    for key in (
        "name", "goal", "authorization_expires_at", "budget_amount",
        "model_profile_ref", "runtime_profile_ref",
    ):
        if not isinstance(task[key], str) or not task[key]:
            raise ValueError("Task string fields must be nonempty")
    try:
        expiry = datetime.fromisoformat(
            task["authorization_expires_at"].replace("Z", "+00:00")
        )
    except ValueError as error:
        raise ValueError("Task authorization expiry must be ISO-8601") from error
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise ValueError("Task authorization must remain current")
    value["configuration_directory"] = _absolute_private_work(
        value["configuration_directory"], must_exist=True
    )
    value["evidence_directory"] = _absolute_private_work(
        value["evidence_directory"], must_exist=False
    )
    return value


def prepared_configuration(config: dict) -> tuple[dict, dict]:
    directory = config["configuration_directory"]
    public = strict_json_loads((directory / "public.json").read_bytes())
    images = strict_json_loads((directory / "images.json").read_bytes())
    if (
        not isinstance(public, dict)
        or public.get("mode") != "mechanism_synthetic"
        or public.get("task_count") != 0
        or not isinstance(public.get("project_id"), str)
        or not isinstance(public.get("start_url"), str)
        or not isinstance(public.get("web_url"), str)
        or not isinstance(images, dict)
        or set(images) not in (
            {"images", "source_revision"},
            {"images", "source_revision", "image_source_revisions"},
        )
        or not isinstance(images.get("source_revision"), str)
        or not SOURCE_REVISION.fullmatch(images["source_revision"])
        or images["source_revision"] != config["expected_source_revision"]
        or not isinstance(images.get("images"), dict)
        or set(images["images"]) != IMAGE_ROLES
        or any(
            not isinstance(value, str) or not IMAGE.fullmatch(value)
            for value in images["images"].values()
        )
    ):
        raise ValueError("prepared Core CTF public/image configuration is inconsistent")
    sources = images.get("image_source_revisions")
    if sources is None and "image_source_revisions" not in images:
        sources = {role: images["source_revision"] for role in BUSINESS_IMAGE_ROLES}
    if (
        not isinstance(sources, dict)
        or set(sources) != BUSINESS_IMAGE_ROLES
        or any(
            not isinstance(revision, str) or not SOURCE_REVISION.fullmatch(revision)
            for revision in sources.values()
        )
        or sources["platform"] != images["source_revision"]
    ):
        raise ValueError("prepared Core CTF image source revisions are inconsistent")
    images = {**images, "image_source_revisions": sources}
    web = urlsplit(public["web_url"])
    if web.scheme != "http" or web.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("password BFF must be an explicit loopback HTTP origin")
    target = urlsplit(public["start_url"])
    if target.scheme not in {"http", "https"} or not target.hostname:
        raise ValueError("prepared mechanism target URL is invalid")
    return public, images


def _redacted_headers(headers) -> dict:
    return {
        key: ("<redacted>" if key.lower() in SECRET_HEADERS else value)
        for key, value in headers
    }


class Browser:
    def __init__(self, origin: str, journal: Path):
        self.origin = origin.rstrip("/")
        self.journal = journal
        self.opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.sequence = 0

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        expected=(200,),
        idempotency_key: str | None = None,
        login=False,
        accept="application/json",
    ) -> tuple[bytes, dict]:
        self.sequence += 1
        raw = None if body is None else canonical_json_bytes(body)
        headers = {
            "Accept": accept,
            "User-Agent": "wuji-core-ctf-acceptance/1",
            "X-Request-ID": f"core-ctf-{self.sequence}",
        }
        if method != "GET":
            headers["Origin"] = self.origin
        if raw is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        request = Request(
            urljoin(self.origin + "/", path.lstrip("/")),
            data=raw,
            headers=headers,
            method=method,
        )
        error_name = None
        try:
            response = self.opener.open(request, timeout=30)
        except HTTPError as error:
            response = error
        except (URLError, OSError, TimeoutError) as error:
            response = None
            error_name = type(error).__name__
        if response is None:
            status, response_headers, response_body = None, {}, b""
        else:
            status = response.status
            response_headers = dict(response.headers.items())
            response_body = response.read(67_108_865)
            response.close()
            if len(response_body) > 67_108_864:
                raise RunFailure("HTTP response exceeds acceptance bound")
        logged_body = raw
        redactions = []
        if login and body is not None:
            logged_body = canonical_json_bytes({
                "username": body["username"], "password": "<redacted-from-private-run-file>"
            })
            redactions.append("request.body.password")
        sent_headers = _redacted_headers(request.header_items())
        if any(key.lower() in SECRET_HEADERS for key, _value in request.header_items()):
            redactions.append("request.headers.session")
        if any(key.lower() in SECRET_HEADERS for key in response_headers):
            redactions.append("response.headers.session")
        _append(self.journal, {
            "sequence": self.sequence,
            "request": {
                "method": method,
                "url": request.full_url,
                "headers": sent_headers,
                "body_base64": None if logged_body is None else base64.b64encode(logged_body).decode(),
            },
            "response": {
                "status": status,
                "headers": _redacted_headers(response_headers.items()),
                "body_base64": base64.b64encode(response_body).decode(),
                "error": error_name,
            },
            "redactions": redactions,
        })
        if status not in expected:
            message = f"{method} {path} returned {status or error_name}"
            if method != "GET" and (status is None or status in {502, 503, 504}):
                raise OperationUnknown(message)
            raise RunFailure(message)
        document = None
        if accept == "application/json" and status != 204:
            try:
                document = strict_json_loads(response_body)
            except (UnicodeDecodeError, ValueError) as error:
                raise RunFailure(f"{method} {path} returned invalid JSON") from error
            if not isinstance(document, dict):
                raise RunFailure(f"{method} {path} returned a non-object")
        return response_body, document

    def json(self, method, path, **kwargs) -> dict:
        return self.request(method, path, **kwargs)[1]

    def bytes(self, path: str) -> bytes:
        return self.request(
            "GET", path, expected=(200,), accept="application/octet-stream"
        )[0]


def _event(path: Path, phase: str, **fields) -> None:
    _append(path, {
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "phase": phase,
        **fields,
    })


def _task_document(config: dict, public: dict) -> dict:
    task, target = config["task"], urlsplit(public["start_url"])
    port = target.port or (443 if target.scheme == "https" else 80)
    value = {
        "schema_version": "wuji.api.v2",
        "project_id": public["project_id"],
        "name": task["name"],
        "scenario": "ctf",
        "goal": {
            "text": task["goal"],
            "criteria": [
                {
                    "criterion_id": f"criterion-{index}",
                    "object": "获准入口的非破坏性机制验证",
                    "condition": condition,
                    "evidence_requirements": [
                        "保存实际HTTP、工具、发布版本和采集证据；不自动宣称Goal满足"
                    ],
                    "allowed_methods": ["deterministic", "reproduced_check"],
                    "responsible_party": "operator",
                    "required": True,
                }
                for index, condition in enumerate(task["criteria"], 1)
            ],
        },
        "authorization_scope": [{
            "host": target.hostname,
            "protocol": target.scheme,
            "port": port,
        }],
        "authorization_expires_at": task["authorization_expires_at"],
        "entry_points": [public["start_url"]],
        "external_analysis_approved": True,
        "model_profile_ref": task["model_profile_ref"],
        "runtime_profile_ref": task["runtime_profile_ref"],
        "explore_concurrency": task["explore_concurrency"],
        "budget": {"amount": task["budget_amount"], "currency": "USD"},
    }
    return TaskCreate.model_validate(value).model_dump(mode="json")


def _q(value: str) -> str:
    return quote(value, safe="")


def _artifact(browser: Browser, task_id: str, ref: dict) -> bytes:
    record = browser.json(
        "GET",
        f"/api/v2/tasks/{_q(task_id)}/records/artifact/{_q(ref['id'])}?"
        + urlencode({"revision": str(ref["revision"])}),
    )
    blob = record["record"]["artifact_ref"]
    raw = browser.bytes(
        f"/api/v2/artifacts/{_q(blob['id'])}/content?"
        + urlencode({"version": str(blob["version"])})
    )
    if sha256(raw).hexdigest() != blob["sha256"]:
        raise RunFailure("downloaded Artifact digest differs from its authoritative ref")
    return raw


def _publication(
    browser: Browser, task_id: str, claim: dict, expected_path: str
) -> tuple[dict, bytes]:
    refs = claim.get("source_refs") or claim.get("basis_refs") or []
    manifests = [ref for ref in refs if ref.get("entity_type") == "artifact"]
    if len(manifests) != 1:
        raise RunFailure("mechanism Claim must cite exactly one publication manifest")
    raw = _artifact(browser, task_id, manifests[0])
    manifest = WorkspaceBundleManifestV1.model_validate(
        strict_json_loads(raw)
    ).model_dump(mode="json")
    if manifest["entrypoint"]["relative_path"] != expected_path:
        raise RunFailure("publication entrypoint does not match the mechanism phase")
    file = next(
        (item for item in manifest["files"] if item["relative_path"] == expected_path),
        None,
    )
    if file is None:
        raise RunFailure("publication omits its declared entrypoint")
    content = browser.bytes(
        f"/api/v2/artifacts/{_q(file['ref']['id'])}/content?"
        + urlencode({"version": str(file["ref"]["version"])})
    )
    if (
        sha256(content).hexdigest() != file["sha256"]
        or file["sha256"] != file["ref"]["sha256"]
    ):
        raise RunFailure("publication file digest is inconsistent")
    return manifest, content


def _capture_items(browser: Browser, task_id: str, session_id: str) -> list[dict]:
    items, after = [], 0
    while True:
        page = browser.json(
            "GET",
            f"/api/v2/tasks/{_q(task_id)}/capture-sessions/{_q(session_id)}/items?"
            + urlencode({"after": after, "limit": 100}),
        )
        items.extend(page["items"])
        next_item = page.get("next_item_seq")
        if next_item is None:
            return items
        after = int(next_item)


def _capture_match(
    browser: Browser, task_id: str, sessions: dict, result: dict
) -> tuple[dict, dict, str] | None:
    try:
        expected_body = base64.b64decode(result["body_base64"], validate=True)
    except (KeyError, TypeError, binascii.Error, ValueError) as error:
        raise RunFailure("sealed Work B result body is invalid") from error
    status = result.get("status")
    if type(status) is not int or result.get("length") != len(expected_body):
        raise RunFailure("sealed Work B result status/length is invalid")
    expected_digest = sha256(expected_body).hexdigest()
    saw_http = False
    for session in sessions.get("sessions") or []:
        if session.get("evidence_origin") != "live_capture":
            continue
        for item in _capture_items(
            browser, task_id, session["capture_session_id"]
        ):
            envelope = item["envelope"]
            if envelope.get("kind") != "http_exchange":
                continue
            saw_http = True
            parts = envelope.get("parts") or []
            refs = item.get("artifact_refs") or []
            if len(parts) != len(refs):
                raise RunFailure("capture part/ref cardinality differs")
            material = {}
            for part, ref in zip(parts, refs):
                if part.get("sha256") != ref.get("sha256"):
                    raise RunFailure("capture part digest differs from Artifact ref")
                material[part["part"]] = _artifact(browser, task_id, {
                    "entity_type": "artifact",
                    "id": ref["id"],
                    "revision": str(ref["version"]),
                })
            metadata_raw = material.get("response_metadata")
            body = material.get("response_body")
            if metadata_raw is None or body is None:
                continue
            metadata = strict_json_loads(metadata_raw)
            if (
                isinstance(metadata, dict)
                and (metadata.get("metadata") or {}).get("status_code") == status
                and sha256(body).hexdigest() == expected_digest
            ):
                return session, item, expected_digest
    if not saw_http:
        return None
    raise RunFailure("no sealed live HTTP capture matches Work B status/body digest")


def _read_chain(browser: Browser, task_id: str) -> dict | None:
    exploration = browser.json(
        "GET", f"/api/v2/tasks/{_q(task_id)}/exploration?mode=live&node_limit=300"
    )
    insights = exploration.get("insights") or []
    claim_a = next((item for item in insights if CORE_WORK_A in item.get("text", "")), None)
    claim_b = next((item for item in insights if CORE_WORK_B in item.get("text", "")), None)
    problems = exploration.get("problems") or []
    work_a = next((item for item in problems if CORE_WORK_A in item.get("question", "")), None)
    work_b = next((item for item in problems if CORE_WORK_B in item.get("question", "")), None)
    if any(item is None for item in (claim_a, claim_b, work_a, work_b)):
        return None
    if (
        work_a.get("execution_state") != "done"
        or work_b.get("execution_state") != "done"
        or not isinstance(work_a.get("work_result"), dict)
        or not isinstance(work_b.get("work_result"), dict)
        or any(ref.get("entity_type") != "claim" for ref in work_b.get("basis_refs") or [])
    ):
        return None
    script_manifest, script = _publication(browser, task_id, claim_a, CORE_SCRIPT)
    if script != _core_script().encode():
        raise RunFailure("published Work A script differs from the fixed mechanism script")
    result_manifest, result_raw = _publication(browser, task_id, claim_b, CORE_RESULT)
    try:
        result = strict_json_loads(result_raw)
    except (UnicodeDecodeError, ValueError) as error:
        raise RunFailure("Work B result is not strict JSON") from error
    if not isinstance(result, dict):
        raise RunFailure("Work B result is not an object")
    sessions = browser.json(
        "GET", f"/api/v2/tasks/{_q(task_id)}/capture-sessions"
    )
    matched = _capture_match(
        browser, task_id, sessions, result
    )
    if matched is None:
        return None
    session, capture_item, body_digest = matched
    return {
        "exploration": exploration,
        "claim_a_ref": claim_a["claim_ref"],
        "claim_b_ref": claim_b["claim_ref"],
        "work_a_ref": work_a["canonical_work_ref"],
        "work_b_ref": work_b["canonical_work_ref"],
        "script_manifest": script_manifest,
        "script": script,
        "result_manifest": result_manifest,
        "result": result,
        "body_sha256": body_digest,
        "capture_session": session,
        "capture_item": capture_item,
    }


def _wait_chain(
    browser: Browser, task_id: str, *, deadline: float, poll: float, events: Path
) -> dict:
    last = None
    while time.monotonic() < deadline:
        task = browser.json("GET", f"/api/v2/tasks/{_q(task_id)}")
        launch = browser.json("GET", f"/api/v2/tasks/{_q(task_id)}/launch")
        if launch.get("phase_status") == "failed":
            raise RunFailure("Task launch failed at " + str(launch.get("phase")))
        state = (task["desired_state"], task["observed_state"], task["version"])
        if state != last:
            _event(events, "task_progress", desired_state=state[0], observed_state=state[1], version=state[2])
            last = state
        if task["observed_state"] == "closed":
            raise RunFailure("Task closed before the mechanism chain was verified")
        chain = _read_chain(browser, task_id)
        if chain is not None:
            chain["task"] = task
            return chain
        if task["desired_state"] == "cancel":
            raise RunFailure("Task cancelled before the mechanism chain was verified")
        time.sleep(poll)
    raise RunFailure("mechanism chain did not complete before the deadline")


def _command(browser: Browser, task: dict, command: str, key: str) -> dict:
    body = TaskCommand.model_validate({
        "schema_version": "wuji.api.v2",
        "command": command,
        "expected_version": task["version"],
        "reason": "core-ctf-mechanism-acceptance:" + command,
    }).model_dump(mode="json")
    return browser.json(
        "POST",
        f"/api/v2/tasks/{_q(task['task_id'])}/commands",
        body=body,
        expected=(202,),
        idempotency_key=key,
    )


def _runtime_stopped(runtime: dict, task_id: str) -> bool:
    expected = {"task-network-init", "agent", "kali", "capture"}
    documents = runtime.get("terminal_observations") or []
    if runtime.get("state") != "stopped" or len(documents) != 4:
        return False
    names = {item.get("container_name") for item in documents}
    if names != expected or not runtime.get("pod_uid"):
        return False
    epochs = set()
    for item in documents:
        binding = item.get("binding") or {}
        if (
            binding.get("task_id") != task_id
            or binding.get("runtime_attempt") != runtime.get("runtime_attempt")
            or binding.get("pod_uid") != runtime["pod_uid"]
            or item.get("state") not in (
                {"terminated"} if item["container_name"] == "task-network-init"
                else {"terminated", "not_started"}
            )
        ):
            return False
        epochs.add(binding.get("execution_epoch"))
    return len(epochs) == 1 and None not in epochs


def _matching_capture_sessions(sessions: dict | None, runtime: dict, task_id: str) -> list[dict]:
    documents = runtime.get("terminal_observations") or []
    if sessions is None or not documents:
        return []
    binding = documents[0].get("binding") or {}
    return [
        item for item in sessions.get("sessions") or []
        if item.get("binding") == {
            "task_id": task_id,
            "runtime_attempt": runtime.get("runtime_attempt"),
            "execution_epoch": binding.get("execution_epoch"),
            "pod_uid": runtime.get("pod_uid"),
        }
    ]


def _cancel_and_stop(
    browser: Browser,
    task_id: str,
    key: str,
    *,
    deadline: float,
    poll: float,
    events: Path,
    require_capture_seal: bool = True,
) -> tuple[dict, dict | None, dict]:
    task = browser.json("GET", f"/api/v2/tasks/{_q(task_id)}")
    if task["observed_state"] == "closed" and task["desired_state"] != "cancel":
        raise RunFailure("Task closed before the required cancel command")
    if task["desired_state"] != "cancel":
        try:
            _command(browser, task, "cancel", key)
            _event(events, "cancel_accepted", task_id=task_id, version=task["version"])
        except OperationUnknown as error:
            _event(events, "cancel_response_unknown", task_id=task_id, error=type(error).__name__)
    while time.monotonic() < deadline:
        task = browser.json("GET", f"/api/v2/tasks/{_q(task_id)}")
        overview = browser.json("GET", f"/api/v2/tasks/{_q(task_id)}/overview")
        runtime = overview.get("runtime") or {}
        if task["desired_state"] == "cancel" and _runtime_stopped(runtime, task_id):
            try:
                sessions = browser.json(
                    "GET", f"/api/v2/tasks/{_q(task_id)}/capture-sessions"
                )
            except RunFailure as error:
                if require_capture_seal:
                    raise
                sessions = None
                _event(events, "capture_inventory_unavailable", task_id=task_id, error=type(error).__name__)
            current = _matching_capture_sessions(sessions, runtime, task_id)
            if require_capture_seal and (
                not current or any(item.get("state") != "sealed" for item in current)
            ):
                time.sleep(poll)
                continue
            _event(events, "external_runtime_stopped", task_id=task_id, pod_uid=runtime["pod_uid"])
            return task, sessions, overview
        time.sleep(poll)
    requirement = " and capture seal" if require_capture_seal else ""
    raise RunFailure("external container termination" + requirement + " was not observed before the deadline")


def _save_evidence(browser, task_id, chain, sessions, overview, evidence):
    _write(evidence / "workspace/fetch.py", chain["script"])
    _json(evidence / "workspace/script-manifest.json", chain["script_manifest"])
    _json(evidence / "workspace/result-manifest.json", chain["result_manifest"])
    _json(evidence / "workspace/result.json", chain["result"])
    _json(evidence / "runtime-terminal.json", overview["runtime"])
    _json(evidence / "exploration.json", chain["exploration"])
    kinds = set()
    for session in sessions["sessions"]:
        sid = session["capture_session_id"]
        items = _capture_items(browser, task_id, sid)
        _json(evidence / "capture" / sid / "index.json", items)
        for item in items:
            envelope = item["envelope"]
            kinds.add(envelope["kind"])
            if envelope["kind"] == "gap" or envelope["completeness"] != "complete":
                raise RunFailure("the mechanism capture contains an explicit evidence gap")
            for part in envelope["parts"]:
                raw = browser.bytes(
                    f"/api/v2/tasks/{_q(task_id)}/capture-sessions/{_q(sid)}/items/"
                    f"{envelope['item_seq']}/parts/{_q(part['part'])}"
                )
                if len(raw) != part["length"] or sha256(raw).hexdigest() != part["sha256"]:
                    raise RunFailure("capture download differs from its persisted descriptor")
                _write(evidence / "capture" / sid / f"{envelope['item_seq']}-{part['part']}", raw)
    if not {"http_exchange", "pcap_segment", "manifest"} <= kinds:
        raise RunFailure("the sealed capture is missing HTTP, PCAP or final manifest")
    command_work = set()
    expected_works = {chain["work_a_ref"], chain["work_b_ref"]}
    after = None
    while True:
        query = {"limit": 100}
        if after is not None:
            query["after"] = after
        page = browser.json("GET", f"/api/v2/tasks/{_q(task_id)}/command-inventory?" + urlencode(query))
        for item in page["items"]:
            if item["work_item_id"] not in expected_works:
                continue
            for ref in item["output_refs"]:
                raw = browser.bytes(f"/api/v2/artifacts/{_q(ref['id'])}/content?version={_q(ref['version'])}")
                if sha256(raw).hexdigest() != ref["sha256"]:
                    raise RunFailure("command log digest differs")
                document = strict_json_loads(raw)
                if document.get("schema_version") != "wuji.command-log.v1":
                    continue
                if document.get("exit_code") != 0 or document.get("truncated"):
                    raise RunFailure("a mechanism command did not finish with full output")
                command_work.add(item["work_item_id"])
                _write(evidence / "commands" / f"{ref['id']}.json", raw)
        after = page["next_after"]
        if after is None:
            break
    if not expected_works <= command_work:
        raise RunFailure("A/B sealed command logs are unavailable")


def run(config: dict, public: dict, images: dict) -> dict:
    evidence = config["evidence_directory"]
    evidence.mkdir(parents=True, mode=0o700)
    journal, events = evidence / "http-exchanges.jsonl", evidence / "events.jsonl"
    _write(journal, b"")
    _write(events, b"")
    fixed = {
        "schema_version": config["schema_version"],
        "mode": config["mode"],
        "run_id": config["run_id"],
        "configuration_directory": str(config["configuration_directory"]),
        "expected_source_revision": config["expected_source_revision"],
        "task": config["task"],
        "public": public,
        "images": images,
        "image_source_revisions": images["image_source_revisions"],
    }
    _json(evidence / "fixed-input.json", fixed)
    browser = Browser(public["web_url"], journal)
    task_id = None
    deadline = time.monotonic() + config["timeout_seconds"]
    login = browser.json(
        "POST", "/auth/login",
        body={"username": config["username"], "password": config["password"]},
        expected=(200,), login=True,
    )
    if login.get("mode") != "local_password" or login.get("project_id") != public["project_id"]:
        raise RunFailure("password BFF session is not bound to the prepared project")
    _event(events, "password_login", project_id=public["project_id"])
    try:
        options = browser.json(
            "GET", f"/api/v2/projects/{_q(public['project_id'])}/task-options"
        )
        if options.get("missing"):
            raise RunFailure("published Task options report missing dependencies")
        task_input = _task_document(config, public)
        for kind, key in (("model_profiles", "model_profile_ref"), ("runtime_profiles", "runtime_profile_ref")):
            if not any(item.get("ref") == task_input[key] for item in options.get(kind) or []):
                raise RunFailure("fixed Task profile is not published")
        created = browser.json(
            "POST", "/api/v2/tasks",
            body=task_input,
            expected=(201,),
            idempotency_key=config["run_id"] + ":create",
        )
        task_id = created["task_id"]
        activity = browser.json(
            "GET", f"/api/v2/tasks/{_q(task_id)}/activity?importance=all&limit=100"
        )
        launch = browser.json("GET", f"/api/v2/tasks/{_q(task_id)}/launch")
        if (
            created["desired_state"] != "pause"
            or created["observed_state"] != "ready"
            or created.get("activated_at") is not None
            or activity.get("items")
            or launch.get("phase") != "not_requested"
            or launch.get("operation_id") is not None
        ):
            raise RunFailure("new Task was not inert before explicit start")
        _event(events, "task_created_inert", task_id=task_id, version=created["version"])
        _command(browser, created, "start", config["run_id"] + ":start")
        _event(events, "start_accepted", task_id=task_id, version=created["version"])
        chain = _wait_chain(
            browser, task_id, deadline=deadline, poll=float(config["poll_seconds"]), events=events
        )
        _event(
            events,
            "mechanism_verified",
            task_id=task_id,
            status=chain["result"]["status"],
            body_sha256=chain["body_sha256"],
        )
        stopped, sealed, overview = _cancel_and_stop(
            browser,
            task_id,
            config["run_id"] + ":cancel",
            deadline=deadline,
            poll=float(config["poll_seconds"]),
            events=events,
        )
        _save_evidence(browser, task_id, chain, sealed, overview, evidence)
        result = {
            "schema_version": "wuji.core-ctf-acceptance.v1",
            "status": "passed",
            "mode": "mechanism",
            "task_id": task_id,
            "source_revision": config["expected_source_revision"],
            "image_source_revisions": images["image_source_revisions"],
            "images": images["images"],
            "reason_a_b": {
                key: chain[key] for key in (
                    "claim_a_ref", "claim_b_ref", "work_a_ref", "work_b_ref"
                )
            },
            "script_publication": {
                "asset_id": chain["script_manifest"]["asset_id"],
                "asset_revision": chain["script_manifest"]["asset_revision"],
                "entrypoint": chain["script_manifest"]["entrypoint"],
            },
            "result_publication": {
                "asset_id": chain["result_manifest"]["asset_id"],
                "asset_revision": chain["result_manifest"]["asset_revision"],
                "entrypoint": chain["result_manifest"]["entrypoint"],
                "http_status": chain["result"]["status"],
                "body_sha256": chain["body_sha256"],
            },
            "capture": {
                "capture_session_id": chain["capture_session"]["capture_session_id"],
                "http_item_seq": chain["capture_item"]["envelope"]["item_seq"],
                "final_sessions": sealed["sessions"],
            },
            "shutdown": {
                "desired_state": stopped["desired_state"],
                "observed_state": stopped["observed_state"],
                "close_trigger": stopped.get("close_trigger"),
                "pod_uid": chain["capture_session"]["binding"]["pod_uid"],
                "external_terminal_observation": overview["runtime"],
            },
            "goal_completion_asserted": False,
            "final_overview": overview,
        }
        _json(evidence / "result.json", result)
        return result
    except BaseException as error:
        cleanup = None
        if task_id is not None:
            try:
                stopped, cleanup_sessions, cleanup_overview = _cancel_and_stop(
                    browser,
                    task_id,
                    config["run_id"] + ":cancel",
                    deadline=time.monotonic() + 120,
                    poll=float(config["poll_seconds"]),
                    events=events,
                    require_capture_seal=False,
                )
                current = _matching_capture_sessions(
                    cleanup_sessions, cleanup_overview["runtime"], task_id
                )
                cleanup = {
                    "status": "external_stopped",
                    "desired_state": stopped["desired_state"],
                    "observed_state": stopped["observed_state"],
                    "runtime": cleanup_overview["runtime"],
                    "capture": {
                        "status": (
                            "unavailable" if cleanup_sessions is None else
                            "missing" if not current else
                            "sealed" if all(item.get("state") == "sealed" for item in current)
                            else "incomplete"
                        ),
                        "sessions": current,
                    },
                }
            except BaseException as cleanup_error:
                cleanup = {"status": "incomplete", "error": type(cleanup_error).__name__}
                _event(
                    events, "cleanup_incomplete", task_id=task_id,
                    error=type(cleanup_error).__name__,
                )
        _json(evidence / "failure.json", {
            "schema_version": "wuji.core-ctf-acceptance.v1",
            "status": "failed",
            "mode": "mechanism",
            "task_id": task_id,
            "error": type(error).__name__,
            "cleanup": cleanup,
            "image_source_revisions": images["image_source_revisions"],
            "goal_completion_asserted": False,
        })
        raise
    finally:
        try:
            browser.request("POST", "/auth/logout", expected=(204,))
        except BaseException:
            _event(events, "logout_incomplete", task_id=task_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mechanism",), required=True)
    parser.add_argument("--run-file", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    config = load_run(args.run_file.resolve())
    if args.mode != config["mode"]:
        raise SystemExit("CLI mode differs from the private run-file")
    public, images = prepared_configuration(config)
    _task_document(config, public)
    if args.validate_only:
        print(json.dumps({
            "event": "core_ctf_run_file_validated",
            "mode": config["mode"],
            "namespace": public["namespace"],
            "source_revision": images["source_revision"],
            "image_source_revisions": images["image_source_revisions"],
        }, sort_keys=True))
        return
    try:
        result = run(config, public, images)
    except BaseException as error:
        print(json.dumps({
            "event": "core_ctf_mechanism_failed",
            "error": type(error).__name__,
            "evidence_directory": str(config["evidence_directory"]),
        }, sort_keys=True))
        raise SystemExit(1) from None
    print(json.dumps({
        "event": "core_ctf_mechanism_passed",
        "task_id": result["task_id"],
        "evidence_directory": str(config["evidence_directory"]),
    }, sort_keys=True))


if __name__ == "__main__":
    main()

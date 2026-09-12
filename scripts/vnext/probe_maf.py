"""Released MAF public-API probe. Synthetic localhost only; no product runtime.

Run with scripts/vnext/uv.sh. The fixture is a real HTTP model peer; SDK,
serialization, approval handling and function invocation are never mocked.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata as metadata
import inspect
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tomllib
import traceback
import urllib.request
from urllib.parse import urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "packages/maf-worker/uv.lock"
BASELINE_SHA = "c9871a66dcebb0ac74205bbae8e94ed00cd1892e"
WHEELS = {
    "agent-framework-core": {
        "version": "1.18.0", "sha256": "75f2fac5eed229c62f0665630cf1478eb45204bde41200a4c94dab57d441cc84",
    },
    "agent-framework-openai": {
        "version": "1.14.3", "sha256": "b24b19b641531ef09e5cf52d5e5d20ba1be7299477d721e3516fc2da55e7f1ef",
    },
    "control": {
        "package": "agent-framework-core", "version": "1.17.0",
        "sha256": "75958ff692a38bf0c627aaa910bae6c4a89569dfec68e1e79eac8e206d88874d",
    },
}
PROFILE = {
    "disable_compaction": True, "disable_todo": True, "disable_mode": True,
    "disable_file_memory": True, "file_memory_store": None, "file_access_store": None,
    "skills_provider": None, "skills_paths": None, "background_agents": None,
    "shell_executor": None, "disable_web_search": True,
    "disable_tool_auto_approval": True, "auto_approval_rules": None,
    "loop_should_continue": None, "loop_next_message": None, "loop_max_iterations": 1,
}
INVOCATION_LIMITS = {
    "max_iterations": 3, "max_function_calls": 2, "max_duration_seconds": 15,
    "max_consecutive_errors_per_request": 1, "terminate_on_unknown_calls": True,
    "additional_tools": [],
}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_wheel(path, expected):
    actual = digest(Path(path).read_bytes())
    if actual != expected:
        raise ValueError(f"wheel SHA-256 mismatch: {Path(path).name}: expected {expected}, got {actual}")
    return actual


def prepare_wheels():
    """One finite package fetch per missing release, cached outside Git.

    No model request is made here. Every fetched wheel must match the fixed
    digest before use. Tests are offline once these three files are cached.
    """
    directory = ROOT / "work/p01/distributions"
    directory.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, pin in WHEELS.items():
        package = pin.get("package", name)
        filename = f"{package.replace('-', '_')}-{pin['version']}-py3-none-any.whl"
        path = directory / filename
        if not path.exists():
            url = f"https://pypi.org/pypi/{package}/{pin['version']}/json"
            with urllib.request.urlopen(url, timeout=20) as response:
                release = json.load(response)
            write_json(directory / f"{package}-{pin['version']}-pypi.json", release)
            asset = next(item for item in release["urls"] if item["filename"] == filename)
            if asset["digests"]["sha256"] != pin["sha256"]:
                raise ValueError(f"PyPI digest changed for {filename}")
            with urllib.request.urlopen(asset["url"], timeout=20) as response:
                raw = response.read()
            if digest(raw) != pin["sha256"]:
                raise ValueError(f"Downloaded wheel SHA-256 mismatch: {filename}")
            path.write_bytes(raw)
        verify_wheel(path, pin["sha256"])
        paths[name] = path
    return paths


def legacy_name(name):
    value = name.lower().replace("_", "-").split(".")[0]
    return value == "pi" or any(token in value for token in ("cairn", "pi-coding-agent", "claude-code", "claude-cli"))


def verify_runtime_inventory(names, commands):
    bad = [n for n in names if legacy_name(n)]
    bad += [word for cmd in commands for word in cmd if legacy_name(Path(word).name)]
    if bad:
        raise ValueError(f"legacy runtime detected: {bad}")


def distribution_record():
    from agent_framework import Agent, AgentSession, Content, create_harness_agent, tool
    from agent_framework.openai import OpenAIChatCompletionClient
    from openai import AsyncOpenAI

    lock = tomllib.loads(LOCK.read_text())
    paths = prepare_wheels()
    maf = {}
    for name in ("agent-framework-core", "agent-framework-openai"):
        dist = metadata.distribution(name)
        assert dist.version == WHEELS[name]["version"], f"Unexpected installed version: {name} {dist.version}"
        locked = next(p for p in lock["package"] if p["name"] == name)
        wheel = next(w for w in locked["wheels"] if w["url"].endswith(paths[name].name))
        assert wheel["hash"] == "sha256:" + WHEELS[name]["sha256"]
        manifest = {}
        with zipfile.ZipFile(paths[name]) as archive:
            for member in archive.namelist():
                if member.endswith("/") or member.endswith(".dist-info/RECORD"):
                    continue
                installed = Path(dist.locate_file(member))
                raw = installed.read_bytes()
                if raw != archive.read(member):
                    raise ValueError(f"Installed distribution differs from released wheel: {member}")
                manifest[member] = digest(raw)
        maf[name] = {
            "version": dist.version, "wheel_file": paths[name].name, "wheel_url": wheel["url"],
            "wheel_sha256": verify_wheel(paths[name], WHEELS[name]["sha256"]),
            "metadata_sha256": digest(dist.read_text("METADATA").encode()),
            "record_sha256": digest(dist.read_text("RECORD").encode()),
            "installed_manifest_sha256": digest(json.dumps(manifest, sort_keys=True).encode()),
            "verified_file_count": len(manifest), "installed_files": manifest,
            "requires_dist": dist.requires,
        }
    objects = [create_harness_agent, Agent.run, AgentSession.to_dict, AgentSession.from_dict,
               Content.from_dict, Content.to_function_approval_response, tool,
               OpenAIChatCompletionClient, AsyncOpenAI]
    signatures = {f"{o.__module__}.{o.__qualname__}": str(inspect.signature(o)) for o in objects}
    installed = sorted([{"name": d.metadata["Name"], "version": d.version} for d in metadata.distributions()], key=lambda d: d["name"])
    verify_runtime_inventory([d["name"] for d in installed], [[sys.executable, str(Path(__file__).resolve())]])
    return {
        "lock_path": "packages/maf-worker/uv.lock", "lock_sha256": digest(LOCK.read_bytes()),
        "locked_packages": lock["package"], "installed_distributions": installed,
        "maf": maf, "inspect_signatures": signatures,
        "toolchain": {"python": platform.python_version(), "platform": platform.platform(),
                      "uv": subprocess.check_output([ROOT / "work/toolchain/bin/uv", "--version"], text=True).strip(),
                      "node": subprocess.check_output([ROOT / "work/toolchain/bin/node", "--version"], text=True).strip()},
    }


async def worker(config):
    from agent_framework import AgentSession, Content, Message, create_harness_agent, tool
    from agent_framework.openai import OpenAIChatCompletionClient
    from openai import AsyncOpenAI, DefaultAsyncHttpxClient

    address = urlsplit(config["url"])
    if address.scheme != "http" or address.hostname != "127.0.0.1" or address.path != "/v1":
        raise ValueError("Only isolated 127.0.0.1 HTTP fixtures are permitted")
    directory = Path(config["directory"])
    output = {"pid": os.getpid(), "stage": config["stage"]}

    def read_record(record_id: str) -> str:
        """Read one synthetic offline record by its fixture ID."""
        if record_id != "synthetic-001":
            raise ValueError("Unknown synthetic record")
        raw = (directory / "record.json").read_text()
        frames = [{"module": f.frame.f_globals.get("__name__"), "function": f.function}
                  for f in inspect.stack() if str(f.frame.f_globals.get("__name__", "")).startswith("agent_framework")]
        event = {"pid": os.getpid(), "record_id": record_id, "record": json.loads(raw),
                 "fixture_sha256": digest(raw.encode()), "sdk_dispatch_stack": frames}
        with (directory / "reads.jsonl").open("a") as file:
            file.write(json.dumps(event) + "\n")
        return raw

    function = read_record
    if config["mode"] == "stub":
        # Explicit negative-control mutant, restricted to this probe. No read/count.
        def nonexecuting_stub(record_id: str) -> str:
            """Return without reading the synthetic record."""
            return "stub did not execute read_record"
        function = nonexecuting_stub
    registered = tool(name="read_record", approval_mode="always_require" if config["mode"] in ("approve", "reject") else "never_require")(function)
    async with AsyncOpenAI(
        api_key="synthetic-localhost-only", base_url=config["url"], max_retries=0,
        timeout=5, http_client=DefaultAsyncHttpxClient(trust_env=False),
    ) as transport:
        client = OpenAIChatCompletionClient(
            model="p01-synthetic", async_client=transport,
            function_invocation_configuration=INVOCATION_LIMITS,
        )
        agent = create_harness_agent(
            client=client, name="p01-read-only", harness_instructions="",
            agent_instructions="Read only the synthetic fixture using the explicit tool.",
            tools=[registered], **PROFILE,
        )
        checkpoint = directory / "checkpoint.json"
        if config["stage"] == "initial":
            session = agent.create_session()
            messages = "Read synthetic-001."
        else:
            saved = json.loads(checkpoint.read_text())
            session = AgentSession.from_dict(saved["session"])
            if config["stage"] == "restore":
                messages = "Continue with the restored history; do not read again."
            else:
                request = Content.from_dict(saved["approval_request"])
                response = request.to_function_approval_response(approved=config["stage"] == "approve")
                output["approval_response"] = response.to_dict()
                messages = Message(role="user", contents=[response])
        output["session_before"] = session.to_dict()
        try:
            response = await asyncio.wait_for(agent.run(messages, session=session), timeout=20)
            output["response"] = response.to_dict()
            requests = [c for m in response.messages for c in m.contents if c.type == "function_approval_request"]
            if requests:
                if len(requests) != 1:
                    raise ValueError("Expected one native approval request")
                output["approval_request"] = requests[0].to_dict()
            output["session_after"] = session.to_dict()
            if config["stage"] == "initial":
                write_json(checkpoint, {"session": output["session_after"], "approval_request": output.get("approval_request")})
        except Exception as exc:
            output["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
            output["session_after"] = session.to_dict()
    output["loaded_modules"] = sorted({name.split(".")[0] for name in sys.modules})
    write_json(directory / f"{config['stage']}-result.json", output)
    return output


def run_process(directory, url, mode, stage):
    config = {"directory": str(directory), "url": url, "mode": mode, "stage": stage}
    config_path = directory / f"{stage}-input.json"
    write_json(config_path, config)
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(config_path)]
    started = datetime.now(timezone.utc)
    timeout_seconds = 30
    record = {"command": command, "exit_code": None, "result": None}
    try:
        process = subprocess.run(
            command, cwd=directory,
            env={"PATH": str(Path(sys.executable).parent), "PYTHONNOUSERSITE": "1", "OTEL_SDK_DISABLED": "true"},
            text=True, capture_output=True, timeout=timeout_seconds,
        )
        record.update(outcome="exited", execution_outcome="returned", exit_code=process.returncode,
                      stdout=process.stdout, stderr=process.stderr)
    except subprocess.TimeoutExpired as exc:
        # subprocess.run kills and waits for the child, but does not expose its
        # return code on this path. A saved result also cannot prove full completion.
        timeout_seconds = exc.timeout
        record.update(
            command=exc.cmd, outcome="timed_out", execution_outcome="unknown",
            error={"type": "TimeoutExpired", "message": str(exc), "timeout_seconds": exc.timeout},
        )
        for stream, raw in (("stdout", exc.stdout), ("stderr", exc.stderr)):
            if isinstance(raw, str):
                raw = raw.encode()
            record[stream] = raw.decode(errors="replace") if raw is not None else None
            record[stream + "_base64"] = base64.b64encode(raw).decode() if raw is not None else None
    finally:
        record["deadline"] = {
            "started_at": started.isoformat(), "timeout_seconds": timeout_seconds,
            "expired_at_or_after": (started + timedelta(seconds=timeout_seconds)).isoformat(),
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        result_path = directory / f"{stage}-result.json"
        timed_out = record.get("outcome") == "timed_out"
        record["result_state"] = "missing_at_timeout" if timed_out else "missing"
        if result_path.exists():
            raw = result_path.read_bytes()
            record["result_raw_base64"] = base64.b64encode(raw).decode()
            try:
                record["result"] = json.loads(raw)
                record["result_state"] = "available_at_timeout" if timed_out else "complete"
            except (ValueError, UnicodeDecodeError) as exc:
                record["result_state"] = "unreadable_at_timeout" if timed_out else "unreadable"
                record["result_read_error"] = {"type": type(exc).__name__, "message": str(exc)}
        write_json(directory / f"{stage}-process.json", record)
    return record


def read_events(directory):
    path = directory / "reads.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def verify_roundtrip(case):
    assert len(case["events"]) == 1, "actual read_record execution count must equal one"
    assert case["events"][0]["sdk_dispatch_stack"], "missing native SDK dispatch stack"
    assert len(case["http"]) == 2, "expected model request and tool-result follow-up"
    followup = json.loads(case["http"][1]["request_body"])
    assert any(m.get("role") == "tool" and m.get("tool_call_id") == "call-p01-read" and
               m.get("content") == case["fixture_text"] for m in followup["messages"])


def capability_outcomes(record):
    """Derive local probe outcomes from raw observations, never SDK success flags.

    These are P01 feasibility checks, not G2/P08/P11 product acceptance.
    Exceptions preserve a concrete gated reason for missing public capability.
    """
    cases = record["cases"]
    incomplete = [name for name, case in cases.items() if case.get("observation_status") == "incomplete"]
    if incomplete:
        timeouts = [process["error"] for case in cases.values() for process in case["processes"]
                    if process.get("outcome") == "timed_out"]
        return {"watchdog" if timeouts else "reporting": {
            "status": "blocked", "execution_outcome": "unknown", "incomplete_cases": incomplete,
            "errors": timeouts or [cases[name].get("error") for name in incomplete],
            "scope": "Incomplete observations cannot establish SDK capability; no automatic retry",
        }}

    def successful_processes(case):
        for process in case["processes"]:
            assert process["exit_code"] == 0, process["result"].get("error", process["stderr"])
            assert "error" not in process["result"], process["result"].get("error")

    def tool_roundtrip():
        successful_processes(cases["roundtrip"])
        verify_roundtrip(cases["roundtrip"])
        try:
            verify_roundtrip(cases["stub"])
        except AssertionError:
            assert cases["stub"]["events"] == []
        else:
            raise AssertionError("nonexecuting stub passed the read-count gate")

    def settled_boundary():
        case = cases["roundtrip"]
        successful_processes(case)
        first, restored = [p["result"] for p in case["processes"]]
        assert first["pid"] != restored["pid"]
        assert restored["session_before"] == first["session_after"]
        assert restored["session_after"]["session_id"] == first["session_after"]["session_id"]
        assert len(case["restore_http"]) == 1
        messages = json.loads(case["restore_http"][0]["request_body"])["messages"]
        assert any(m.get("tool_call_id") == "call-p01-read" for m in messages)
        assert any(m.get("content") == "offline-p01-record received" for m in messages)
        assert len(case["events"]) == 1

    def approval_boundary():
        for decision, count in (("approve", 1), ("reject", 0)):
            case = cases[decision]
            successful_processes(case)
            first, restored = [p["result"] for p in case["processes"]]
            request, response = first["approval_request"], restored["approval_response"]
            assert case["events_before_resume"] == []
            assert first["pid"] != restored["pid"]
            assert restored["session_before"] == first["session_after"]
            assert request["id"] == response["id"] == request["function_call"]["id"]
            assert request["function_call"] == response["function_call"]
            assert response["function_call"]["call_id"] == "call-p01-read"
            assert response["approved"] is (decision == "approve")
            assert len(case["events"]) == count
            assert len(case["restore_http"]) == 1
            messages = json.loads(case["restore_http"][0]["request_body"])["messages"]
            returned = [m for m in messages if m.get("role") == "tool"]
            assert len(returned) == 1 and returned[0]["tool_call_id"] == "call-p01-read"
            if decision == "approve":
                assert returned[0]["content"] == case["fixture_text"]
            else:
                assert "reject" in returned[0]["content"].lower()

    def tool_profile():
        for case in cases.values():
            assert case["http"], "missing observed HTTP tool table"
            for exchange in case["http"] + case["restore_http"]:
                tools = json.loads(exchange["request_body"])["tools"]
                assert len(tools) == 1, "expected one explicit advertised tool"
                assert tools[0]["type"] == "function"
                assert tools[0]["function"]["name"] == "read_record"
            for process in case["processes"]:
                verify_runtime_inventory(process["result"]["loaded_modules"], [process["command"]])
        unknown = cases["unknown"]
        assert unknown["events"] == [] and len(unknown["http"]) == 1
        assert "unregistered_probe_tool" in unknown["processes"][0]["result"]["error"]["message"]

    def finite_http_failure():
        case = cases["http-error"]
        assert len(case["http"]) == 1 and case["http"][0]["response_status"] == 503
        assert case["events"] == []
        assert "503" in case["processes"][0]["result"]["error"]["message"]

    checks = {}
    for check in (tool_roundtrip, settled_boundary, approval_boundary, tool_profile, finite_http_failure):
        try:
            check()
            checks[check.__name__] = {"status": "passed", "scope": "P01 isolated SDK feasibility only"}
        except Exception as exc:
            checks[check.__name__] = {"status": "blocked", "error": {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}}
    return checks


def exchange_markdown(cases):
    # Scope comes only from probe observations, never HTTP/model-provided labels.
    count = sum(len(case["http"]) + len(case["restore_http"]) for case in cases.values())
    timed_out = any(process.get("outcome") == "timed_out"
                    for case in cases.values() for process in case.get("processes", []))
    statuses = [case.get("observation_status", "unknown") for case in cases.values()]
    complete = bool(cases) and count > 0 and not timed_out and all(status == "complete" for status in statuses)
    completeness = "complete as recorded by the probe" if complete else (
        "incomplete" if timed_out or "incomplete" in statuses else "unknown"
    )
    parts = [
        "# P01 HTTP observation record",
        "This package reproduces captured HTTP messages only. It does not establish SDK capability, "
        "approval outcomes, tool execution, or retry/failure validation.",
        f"Observation completeness: {completeness}.",
        f"Captured HTTP exchanges: {count}.",
    ]
    if not complete:
        parts += ["Execution outcome: unknown. Capability outcome: blocked.",
                  "Missing observations do not prove zero execution."]
    if timed_out:
        parts.append("A subprocess timeout was recorded. Only HTTP observations available at that boundary are reproduced.")
    if count == 0:
        parts.append("No captured HTTP exchanges.")
    for name, case in cases.items():
        for index, item in enumerate(case["http"] + case["restore_http"], 1):
            request = item["request_line"] + "\r\n" + "".join(f"{k}: {v}\r\n" for k, v in item["request_headers"]) + "\r\n" + item["request_body"]
            parts += [f"## {name} exchange {index}", f"URL: {item['url']}", "```http\n" + request + "\n```", "```http\n" + item["response_http"] + "\n```"]
    return "\n\n".join(parts) + "\n"


def run_probe(output_dir):
    sys.path.insert(0, str(ROOT / "tests/vnext"))
    from maf_fixture import SyntheticModel

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = {}
    record = {"baseline": {"source_commit": BASELINE_SHA, "document": "docs/vnext/implementation-baseline.md"},
              "profile": PROFILE, "explicit_tools": ["read_record"], "function_invocation_limits": INVOCATION_LIMITS,
              "transport": {"protocol": "OpenAI Chat Completions", "max_retries": 0, "timeout_seconds": 5, "trust_env": False},
              "cases": cases}
    modes = ("roundtrip", "approve", "reject", "unknown", "http-error", "stub")
    # Refuse reused destinations before finally can publish anything over them.
    for name in (*modes, "probe.json", "http-reproduction.md", "distributions.json"):
        if (output_dir / name).exists():
            raise FileExistsError(f"Evidence destination already exists: {output_dir / name}")
    try:
        for mode in modes:
            directory = output_dir / mode
            directory.mkdir(exist_ok=False)  # Never append to previous evidence.
            fixture_text = '{"id":"synthetic-001","value":"offline-p01-record"}'
            (directory / "record.json").write_text(fixture_text)
            case = {"fixture_text": fixture_text, "processes": [], "http": [], "restore_http": [],
                    "events": None, "events_before_resume": None, "observation_status": "incomplete"}
            cases[mode] = case
            server = None
            cut = None
            try:
                with SyntheticModel(mode) as server:
                    initial_process = run_process(directory, server.url, mode, "initial")
                    case["processes"].append(initial_process)
                    cut = len(server.exchanges)
                    if initial_process["outcome"] != "timed_out":
                        initial = initial_process["result"]
                        if initial is None:
                            raise ValueError("Worker exited without a readable result; observations incomplete")
                        case["events_before_resume"] = read_events(directory)
                        if mode in ("roundtrip", "approve", "reject") and "error" not in initial:
                            if mode == "roundtrip" or initial.get("approval_request"):
                                stage = "restore" if mode == "roundtrip" else mode
                                case["processes"].append(run_process(directory, server.url, mode, stage))
                        if not any(p["outcome"] == "timed_out" for p in case["processes"]):
                            case["events"] = read_events(directory)
                            case["observation_status"] = "complete"
            except Exception as exc:
                case["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
            finally:
                # Snapshot after fixture cleanup, including evidence captured before
                # a worker startup/run/shutdown timeout. Never infer zero execution.
                if server is not None:
                    case["http"] = list(server.exchanges if cut is None else server.exchanges[:cut])
                    case["restore_http"] = [] if cut is None else list(server.exchanges[cut:])
                if case["observation_status"] == "incomplete":
                    event_path = directory / "reads.jsonl"
                    raw = event_path.read_bytes() if event_path.exists() else None
                    case["event_log_base64"] = base64.b64encode(raw).decode() if raw is not None else None
                    available_events = []
                    for line in (raw or b"").splitlines():
                        try:
                            available_events.append(json.loads(line))
                        except (ValueError, UnicodeDecodeError) as exc:
                            case["event_read_error"] = {"type": type(exc).__name__, "message": str(exc)}
                            break
                    case["available_events"] = available_events
                    case["observed_event_count"] = len(available_events) if available_events else None
                    http_count = len(case["http"]) + len(case["restore_http"])
                    case["http_observation_count"] = http_count if http_count else None
                write_json(directory / "http.json", case["http"] + case["restore_http"])
                write_json(directory / "case.json", case)
            if case["observation_status"] == "incomplete":
                break  # Do not retry, resume, or run subsequent SDK cases after unknown execution.
    finally:
        record["not_run_cases"] = [mode for mode in modes if mode not in cases]
        record["capabilities"] = capability_outcomes(record)
        write_json(output_dir / "probe.json", record)
        (output_dir / "http-reproduction.md").write_text(exchange_markdown(cases))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--prepare-wheels", action="store_true")
    args = parser.parse_args()
    if args.worker:
        result = asyncio.run(worker(json.loads(args.worker.read_text())))
        return 2 if "error" in result else 0
    if args.prepare_wheels:
        print(json.dumps({k: str(v.relative_to(ROOT)) for k, v in prepare_wheels().items()}, indent=2))
        return 0
    if not args.output_dir:
        parser.error("--output-dir or --prepare-wheels is required")
    record = run_probe(args.output_dir)
    if not any(c["status"] == "blocked" for c in record["capabilities"].values()):
        try:
            write_json(args.output_dir / "distributions.json", distribution_record())
        except Exception as exc:
            record["capabilities"]["distribution"] = {"status": "blocked", "error": {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}}
            write_json(args.output_dir / "probe.json", record)
    for name, case in record["cases"].items():
        reads = "unknown" if case["events"] is None else len(case["events"])
        http_count = len(case["http"]) + len(case["restore_http"])
        if case["observation_status"] == "incomplete" and not http_count:
            http_count = "unknown"
        print(name, "reads=", reads, "HTTP observed=", http_count,
              "observation_status=", case["observation_status"],
              "errors=", [p.get("error") or (p["result"] or {}).get("error") for p in case["processes"]])
    print(json.dumps(record["capabilities"], indent=2))
    return 2 if any(c["status"] == "blocked" for c in record["capabilities"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Explicit loopback synthetic model peer for the isolated Gate Pod (D12).

Mechanism mode only. This peer is a deterministic stand-in for a model, and it
is deliberately not smarter than that: every path it reads, every value it
reports and every follow-up question it proposes is copied out of bytes the
platform actually delivered to it — the frozen context and the observed tool
result. Nothing here is a scripted answer to a fixture.

What it therefore demonstrates is the platform path, not model quality:
observation becomes a claim, the claim's own bytes name the next question, that
question is admitted and executed, and the next decision differs because the
new evidence is there. A real-model comparison needs a real gateway and stays
blocked until one exists.
"""

import argparse
import base64
from hashlib import sha256
import json
import re
import shlex
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import time
from urllib.parse import urljoin, urlsplit
from uuid import uuid4


CONTEXT_SCHEMA = "wuji.context.v2"
WORK_BRIEF_SCHEMA = "wuji.work-brief.v1"
CONTEXT_V4_SCHEMA = "wuji.worker-context.v4"
WORK_BRIEF_V2_SCHEMA = "wuji.work-brief.v2"
PAYLOAD_SCHEMA = "wuji.agent-payload.v2"
# A workspace reference the platform publishes; the peer never invents one.
PATH_REF = re.compile(r"workspace:([A-Za-z0-9][A-Za-z0-9._/-]{0,255})")
START_POINTS = re.compile(r"start points:([^\n]*)")
POINTER = re.compile(r'"pointer"\s*:\s*"([A-Za-z0-9][A-Za-z0-9._/-]{0,255})"')
READ_PREFIX = re.compile(r"^evidence read: ([^;]{1,256}); content: ", re.DOTALL)
HTTP_URL = re.compile(r"http://[^\s\"'<>]+")
CORE_HTTP_URL = re.compile(r"https?://[^\s\"'<>]+")
HTTP_BODY_PREFIX = "response.body:\n"
FIRST_USE_ALIAS = "synthetic-first-use"
CORE_CTF_ALIAS = "synthetic-core-ctf"
CORE_WORK_A = "synthetic-core-ctf work A"
CORE_WORK_B = "synthetic-core-ctf work B"
CORE_SCRIPT = "src/fetch.py"
CORE_RESULT = "output/result.json"
CORE_COMMAND_LOG = "application/vnd.wuji.command-log+json"
CORE_HTTP_EXCHANGE = "application/vnd.wuji.http-exchange+json"


def _text(message):
    """Every string a native message carries, in the order the model saw it."""

    parts = []
    for content in message.get("contents", ()):
        if not isinstance(content, dict):
            continue
        if content.get("type") == "text" and isinstance(content.get("text"), str):
            parts.append(content["text"])
        elif content.get("type") == "function_result" and isinstance(
            content.get("result"), str
        ):
            parts.append(content["result"])
    if not parts and isinstance(message.get("content"), str):
        parts.append(message["content"])
    return "\n".join(parts)


def _parsed(text):
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def messages_of(request):
    messages = request.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 256:
        raise ValueError("unbounded message list")
    return [message for message in messages if isinstance(message, dict)]


def role_of(messages):
    for message in messages:
        if message.get("role") != "system":
            continue
        text = _text(message)
        for kind in ("reason", "explore", "report"):
            if "your duty as " + kind + ":" in text:
                return kind
    raise ValueError("the frozen profile does not state this Run's duty")


def instructions_of(messages):
    return "\n".join(
        _text(message) for message in messages if message.get("role") == "system"
    )


def context_of(messages):
    for message in messages:
        if message.get("role") == "system":
            continue
        document = _parsed(_text(message))
        if document is not None and document.get("schema_version") in {
            CONTEXT_SCHEMA, WORK_BRIEF_SCHEMA, CONTEXT_V4_SCHEMA,
            WORK_BRIEF_V2_SCHEMA,
        }:
            return document
    raise ValueError("no frozen context document reached the model")


def tool_result_of(messages):
    """The material of the last completed tool call, exactly as delivered."""

    for message in reversed(messages):
        if message.get("role") != "tool":
            continue
        document = _parsed(_text(message))
        if document is None or "evidence_receipt" not in document:
            raise ValueError("an unreadable tool result reached the model")
        evidence = document.get("evidence_receipt") or {}
        if evidence.get("status") != "accepted":
            raise ValueError("the tool result carries no accepted observation")
        material = document.get("material")
        text = None
        if isinstance(material, dict) and isinstance(material.get("text"), str):
            text = material["text"]
        return {
            "observation_ref": evidence.get("observation_ref"),
            "material": text,
            "omitted": document.get("material_omitted"),
        }
    return None


def first_use_material(value):
    """Return verified v2 representation/body; never reinterpret raw evidence."""

    if (
        not isinstance(value, dict)
        or value.get("schema_version") != "wuji.model-material.v2"
        or value.get("status") != "delivered"
        or not isinstance(value.get("source"), dict)
        or not isinstance(value.get("representation"), dict)
    ):
        raise ValueError("first-use requires delivered HTTP material v2")
    source = value["source"]
    representation = value["representation"]
    text = representation.get("text")
    encoded = text.encode("utf-8") if isinstance(text, str) else b""
    if (
        not isinstance(text, str)
        or source.get("completeness") != "complete"
        or representation.get("encoding") != "utf-8"
        or representation.get("truncated") is not False
        or type(representation.get("byte_length")) is not int
        or representation["byte_length"] != len(encoded)
        or representation.get("representation_sha256") != sha256(encoded).hexdigest()
        or HTTP_BODY_PREFIX not in text
    ):
        raise ValueError("first-use HTTP material is incomplete or invalid")
    body_text = text.split(HTTP_BODY_PREFIX, 1)[1]
    try:
        body = json.loads(body_text)
    except (TypeError, ValueError) as error:
        raise ValueError("first-use HTTP body is not JSON") from error
    if not isinstance(body, dict):
        raise ValueError("first-use HTTP body is not an object")
    return text, body


def first_use_tool_result_of(messages):
    """The accepted ToolGate receipt and its exact v2 representation."""

    for message in reversed(messages):
        if message.get("role") != "tool":
            continue
        document = _parsed(_text(message))
        evidence = (document or {}).get("evidence_receipt") or {}
        if evidence.get("status") != "accepted" or not isinstance(
            evidence.get("observation_ref"), dict
        ):
            raise ValueError("the first-use tool result carries no observation")
        text, body = first_use_material((document or {}).get("material"))
        return {
            "observation_ref": evidence["observation_ref"],
            "representation": text,
            "body": body,
        }
    return None


def http_url(text):
    """One concrete HTTP URL copied from delivered text."""

    match = HTTP_URL.search(text or "")
    if match is None:
        raise ValueError("no HTTP URL was delivered")
    candidate = match.group(0).rstrip(".,);]")
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as error:
        raise ValueError("the delivered HTTP URL is invalid") from error
    if (
        parsed.scheme != "http"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port is None
        or parsed.fragment
    ):
        raise ValueError("the delivered HTTP URL is not a bounded fixture URL")
    return candidate


def latest_intent_url(context):
    candidates = [
        (str(body.get("created_at") or ""), http_url(body.get("question") or ""), ref)
        for ref, body in intents(context)
        if HTTP_URL.search(body.get("question") or "")
    ]
    return max(candidates) if candidates else None


def stored_first_use_material(context):
    """Every actual, digest-checked HTTP material packet in this ContextBundle."""

    result = []
    for record in records_of(context, "artifact"):
        material = record.get("material")
        if not isinstance(material, dict) or material.get("schema_version") != "wuji.model-material.v2":
            continue
        text, body = first_use_material(material)
        result.append((reference(record), text, body))
    return result


def read_path(question, instructions):
    for candidate in PATH_REF.findall(question or ""):
        return candidate
    match = START_POINTS.search(instructions)
    if match:
        for candidate in PATH_REF.findall(match.group(1)):
            return candidate
    raise ValueError("the admitted question names no workspace path")


def tool_names(tools):
    names = set()
    for definition in tools or ():
        function = definition.get("function") if isinstance(definition, dict) else None
        if isinstance(function, dict) and isinstance(function.get("name"), str):
            names.add(function["name"])
    return names


def tool_events(messages):
    """Completed calls with the names and ids the model itself emitted."""

    calls, events = {}, []
    for message in messages:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or ():
                function = call.get("function") if isinstance(call, dict) else None
                if isinstance(function, dict):
                    calls[call.get("id")] = function.get("name")
            for content in message.get("contents") or ():
                if not isinstance(content, dict) or content.get("type") != "function_call":
                    continue
                function = content.get("function")
                name = content.get("name")
                if isinstance(function, dict):
                    name = function.get("name")
                calls[content.get("call_id") or content.get("id")] = name
        if message.get("role") != "tool":
            continue
        contents = message.get("contents") or ()
        if not contents and isinstance(message.get("content"), str):
            contents = ({
                "type": "function_result",
                "call_id": message.get("tool_call_id"),
                "result": message["content"],
            },)
        for content in contents:
            if not isinstance(content, dict) or content.get("type") != "function_result":
                continue
            call_id = content.get("call_id")
            document = _parsed(content.get("result"))
            if isinstance(call_id, str) and isinstance(document, dict):
                events.append({"call_id": call_id, "name": calls.get(call_id), "document": document})
    return events


def tool_step(request, name, call_id, arguments):
    if name not in tool_names(request.get("tools")):
        raise ValueError("required core tool was not offered: " + name)
    return {
        "kind": "tool_call",
        "name": name,
        "call_id": call_id,
        "arguments": json.dumps(arguments, sort_keys=True),
    }


def core_url(text):
    match = CORE_HTTP_URL.search(text or "")
    if match is None:
        return None
    candidate = match.group(0).rstrip(".,);]")
    try:
        parsed = urlsplit(candidate)
        parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        return None
    return candidate


def core_start_url(context, instructions=""):
    brief = context.get("brief") if isinstance(context.get("brief"), dict) else {}
    values = [brief.get("question"), brief.get("task_goal")]
    values.extend(brief.get("authorization_summary") or ())
    values.append(instructions)
    for value in values:
        if isinstance(value, str):
            result = core_url(value)
            if result is not None:
                return result
    raise ValueError("the Core CTF brief carries no authorized start URL")


def core_ref(blob):
    return {
        "entity_type": "artifact",
        "id": blob["id"],
        "revision": str(blob["version"]),
    }


def core_v3(*, intents=(), decision=None, work_result=None):
    return {
        "schema_version": "wuji.agent-payload.v3",
        "claims": [],
        "intent_proposals": list(intents),
        "reason_decision": decision,
        "work_result": work_result,
        "input_acknowledgements": [],
    }


def _core_delivery_json(delivery):
    value = _parsed(delivery.get("text"))
    if value is None:
        raise ValueError("Core CTF knowledge delivery is not JSON")
    return value


def _core_result_check(delivered, result_asset):
    manifest_ref = core_ref(result_asset["manifest_ref"])
    manifest = _core_delivery_json(delivered[(
        "artifact", manifest_ref["id"], manifest_ref["revision"]
    )]).get("workspace_bundle_manifest")
    if not isinstance(manifest, dict):
        raise ValueError("Work B result manifest was not delivered")
    result_file = next((
        item for item in manifest.get("files") or ()
        if item.get("relative_path") == CORE_RESULT and isinstance(item.get("ref"), dict)
    ), None)
    if result_file is None:
        raise ValueError("Work B result manifest has no sealed result JSON")
    expected_digest = result_file["ref"].get("sha256")

    command_ref = result = None
    for key, delivery in delivered.items():
        if key[0] != "artifact":
            continue
        document = _parsed(delivery.get("text"))
        if (
            not isinstance(document, dict)
            or document.get("schema_version") != "wuji.command-log.v1"
            or CORE_RESULT not in str(document.get("command"))
            or document.get("truncated") is not False
        ):
            continue
        try:
            stdout = base64.b64decode(document["stdout_base64"], validate=True)
        except (KeyError, TypeError, ValueError):
            continue
        if (
            sha256(stdout).hexdigest() != expected_digest
            or document.get("stdout_sha256") != expected_digest
        ):
            continue
        try:
            result = json.loads(stdout)
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(result, dict):
            command_ref = delivery["ref"]
            break
    if command_ref is None:
        raise ValueError("Work B sealed result JSON does not match its manifest")
    try:
        body = base64.b64decode(result["body_base64"], validate=True)
        status = result["status"]
    except (KeyError, TypeError, ValueError):
        raise ValueError("Work B sealed result JSON is invalid") from None
    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError("Work B sealed result status is invalid")
    body_digest = sha256(body).hexdigest()

    for key, delivery in delivered.items():
        if key[0] != "artifact" or delivery["ref"] == command_ref:
            continue
        text = delivery.get("text")
        if not isinstance(text, str) or HTTP_BODY_PREFIX not in text:
            continue
        match = re.search(r"(?m)^response\.status: ([1-5][0-9]{2})$", text)
        if (
            match is not None
            and int(match.group(1)) == status
            and sha256(text.split(HTTP_BODY_PREFIX, 1)[1].encode()).hexdigest()
            == body_digest
        ):
            return command_ref, delivery["ref"], status, body_digest
    raise ValueError("Work B result does not match sealed capture evidence")


def core_reason_decision(request, messages, context):
    brief = context.get("brief") if isinstance(context.get("brief"), dict) else {}
    summaries = [str(item) for item in brief.get("related_work_summaries") or ()]
    results = [str(item) for item in brief.get("predecessor_result_summaries") or ()]
    events = tool_events(messages)
    deliveries = [
        event["document"] for event in events
        if event["name"] == "knowledge_read"
        and event["document"].get("schema_version") == "wuji.knowledge-delivery.v1"
    ]
    delivered = {
        (
            item["ref"]["entity_type"],
            item["ref"]["id"],
            str(item["ref"]["revision"]),
        ): item
        for item in deliveries
        if isinstance(item.get("ref"), dict)
    }
    indexes = [
        item for item in context.get("knowledge_index") or ()
        if isinstance(item, dict) and isinstance(item.get("ref"), dict)
    ]
    claim_indexes = [
        item for item in indexes if item["ref"].get("entity_type") == "claim"
    ]
    assets = [
        item for item in context.get("published_asset_index") or ()
        if isinstance(item, dict) and isinstance(item.get("manifest_ref"), dict)
    ]
    script_assets = [
        item for item in assets
        if (item.get("entrypoint") or {}).get("relative_path") == CORE_SCRIPT
    ]
    result_assets = [
        item for item in assets
        if (item.get("entrypoint") or {}).get("relative_path") == CORE_RESULT
    ]
    active_b = any(CORE_WORK_B in item for item in summaries)
    finished_b = any(CORE_WORK_B in item for item in results)
    active_a = any(CORE_WORK_A in item for item in summaries)
    finished_a = any(CORE_WORK_A in item for item in results) or bool(script_assets)

    claim_deliveries = [
        item for item in deliveries if item.get("ref", {}).get("entity_type") == "claim"
    ]
    b_claim = next((item for item in claim_deliveries if CORE_WORK_B in item.get("text", "")), None)
    a_claim = next((item for item in claim_deliveries if CORE_WORK_A in item.get("text", "")), None)

    if not finished_a and not active_a:
        url = core_start_url(context, instructions_of(messages))
        intent = {
            "client_ref": "core-work-a",
            "question": (
                CORE_WORK_A + ": fetch the authorized start URL " + url
                + " with a reusable urllib.request script, publish the script, and publish an evidence-based Claim."
            ),
            "basis_refs": [],
            "expected_output": "A fixed script publication, Claim, and WorkResult.",
            "planning": None,
        }
        return {
            "kind": "payload",
            "document": core_v3(
                intents=[intent],
                decision={
                    "decision": "propose_intents",
                    "wait_refs": [],
                    "public_rationale": "The frozen start URL has not been tested yet.",
                    "basis_refs": [],
                },
            ),
        }

    # A Reason Run must read the canonical Claim rather than infer its content
    # from an index row or an Artifact reference.
    wanted_claims = claim_indexes if finished_b else claim_indexes[:1]
    for item in wanted_claims:
        ref = item["ref"]
        key = (ref["entity_type"], ref["id"], str(ref["revision"]))
        if key not in delivered:
            return tool_step(request, "knowledge_read", "call-core-reason-claim-" + str(len(deliveries) + 1), {
                "snapshot_id": context["snapshot_id"],
                "ref": ref,
                "selector": {
                    "kind": "record_fields",
                    "fields": ["text", "basis_refs", "limitations", "kind", "assertion_role"],
                },
            })

    if finished_b:
        if b_claim is None:
            raise ValueError("Work B completed without a delivered result Claim")
        if not result_assets:
            raise ValueError("Work B completed without a sealed result publication")
        result_asset = result_assets[-1]
        manifest_ref = core_ref(result_asset["manifest_ref"])
        manifest_key = ("artifact", manifest_ref["id"], manifest_ref["revision"])
        if manifest_key not in delivered:
            return tool_step(request, "knowledge_read", "call-core-reason-result-manifest-" + str(len(deliveries) + 1), {
                "snapshot_id": context["snapshot_id"],
                "ref": manifest_ref,
                "selector": {"kind": "record_fields", "fields": ["workspace_bundle_manifest"]},
            })
        evidence_indexes = [
            item for item in indexes
            if item.get("material_type") in {CORE_COMMAND_LOG, CORE_HTTP_EXCHANGE}
            and "text_range" in (item.get("available_selectors") or ())
        ]
        for item in evidence_indexes:
            ref = item["ref"]
            key = (ref["entity_type"], ref["id"], str(ref["revision"]))
            if key not in delivered:
                return tool_step(request, "knowledge_read", "call-core-reason-evidence-" + str(len(deliveries) + 1), {
                    "snapshot_id": context["snapshot_id"],
                    "ref": ref,
                    "selector": {"kind": "text_range", "start": 0, "end": 16_384},
                })
        if not any(item.get("material_type") == CORE_COMMAND_LOG for item in evidence_indexes):
            raise ValueError("Work B has no sealed command result evidence")
        if not any(item.get("material_type") == CORE_HTTP_EXCHANGE for item in evidence_indexes):
            raise ValueError("Work B has no sealed capture evidence")
        command_ref, capture_ref, status, body_digest = _core_result_check(
            delivered, result_asset
        )
        return {
            "kind": "payload",
            "document": core_v3(decision={
                "decision": "propose_completion",
                "wait_refs": [],
                "public_rationale": (
                    "Work B's sealed result and capture agree on HTTP status "
                    + str(status) + " and body SHA-256 " + body_digest + "."
                ),
                "basis_refs": [b_claim["ref"], command_ref, capture_ref],
            }),
        }

    if active_b:
        return {
            "kind": "payload",
            "document": core_v3(decision={
                "decision": "wait", "wait_refs": [],
                "public_rationale": "Work B is already active.", "basis_refs": [],
            }),
        }

    if not finished_a:
        return {
            "kind": "payload",
            "document": core_v3(decision={
                "decision": "wait", "wait_refs": [],
                "public_rationale": "Work A is already active.", "basis_refs": [],
            }),
        }
    if a_claim is None or not script_assets:
        raise ValueError("Work A completed without its Claim and script publication")

    script = script_assets[-1]
    manifest_ref = core_ref(script["manifest_ref"])
    manifest_key = ("artifact", manifest_ref["id"], manifest_ref["revision"])
    if manifest_key not in delivered:
        return tool_step(request, "knowledge_read", "call-core-reason-manifest-" + str(len(deliveries) + 1), {
            "snapshot_id": context["snapshot_id"],
            "ref": manifest_ref,
            "selector": {"kind": "record_fields", "fields": ["workspace_bundle_manifest"]},
        })

    url = core_start_url(context, instructions_of(messages))
    intent = {
        "client_ref": "core-work-b",
        "question": (
            CORE_WORK_B + ": materialize publication " + script["publication_id"]
            + " with manifest " + manifest_ref["id"] + "@" + manifest_ref["revision"]
            + ", run its fixed script against " + url
            + ", and publish the sealed result and an evidence-based Claim."
        ),
        "basis_refs": [a_claim["ref"]],
        "expected_output": "A result from the exact materialized publication, with a Claim and WorkResult.",
        "planning": None,
    }
    return {
        "kind": "payload",
        "document": core_v3(
            intents=[intent],
            decision={
                "decision": "propose_intents", "wait_refs": [],
                "public_rationale": "The delivered Claim and manifest support fixed-version reuse in Work B.",
                "basis_refs": [a_claim["ref"]],
            },
        ),
    }


def _core_script():
    return (
        "import base64,json,sys,urllib.request\n"
        "request=urllib.request.Request(sys.argv[1],headers={'User-Agent':'wuji-core-mechanism/1'})\n"
        "with urllib.request.urlopen(request,timeout=15) as response:\n"
        " body=response.read()\n"
        " print(json.dumps({'body_base64':base64.b64encode(body).decode('ascii'),'length':len(body),'status':response.status,'url':response.geturl()},sort_keys=True))\n"
    )


def _core_process_step(request, events, prefix):
    process = [
        event for event in events
        if event["name"] in {"kali_exec", "kali_read"}
        and event["call_id"].startswith(prefix)
    ]
    if not process:
        return None, None
    latest = process[-1]["document"]
    if latest.get("schema_version") != "wuji.process-reply.v1":
        raise ValueError("core process returned an unknown document")
    if latest.get("state") == "running":
        return tool_step(
            request,
            "kali_read",
            prefix + "-read-" + str(sum(item["name"] == "kali_read" for item in process) + 1),
            {
                "handle": latest["handle"],
                "cursor": latest["next_cursor"],
                "max_bytes": 1_048_576,
                "wait_ms": 1000,
            },
        ), None
    if latest.get("state") != "exited" or latest.get("exit_code") != 0:
        return None, core_v3(work_result={
            "outcome": "inconclusive",
            "summary": "The bounded Core CTF process did not exit successfully.",
            "answer_basis_refs": [],
            "unresolved_items": ["process state: " + str(latest.get("state"))],
            "capability_gaps": [],
        })
    return None, latest


def _core_publish_arguments(*, result=False):
    path = CORE_RESULT if result else CORE_SCRIPT
    return {
        "purpose": CORE_WORK_B + " sealed execution result" if result else CORE_WORK_A + " reusable urllib script",
        "files": [{"relative_path": path}],
        "entrypoint": {
            "relative_path": path,
            "interpreter_argv": ["/bin/cat"] if result else ["/opt/wuji/ops/vnext/.venv/bin/python"],
        },
        "inputs_description": "The authorized start URL from the frozen Work brief.",
        "outputs_description": "A bounded JSON record of the HTTP response." if result else "A bounded JSON record on stdout.",
        "dependencies": [],
        "validation_statement": "Executed once through the bounded Kali process supervisor.",
        "limitations": ["Synthetic mechanism validation does not establish model quality."],
        "expected_base_publication_id": None,
    }


def _board_arguments(published, *, phase):
    manifest = core_ref(published["manifest_ref"])
    marker = CORE_WORK_A if phase == "A" else CORE_WORK_B
    return {
        "revises": None,
        "client_ref": "core-work-" + phase.lower() + "-claim",
        "kind": "observation-summary",
        "assertion_role": "candidate_fact",
        "text": (
            marker + " published " + published["publication_id"]
            + " with sealed manifest " + manifest["id"] + "@" + manifest["revision"] + "."
        ),
        "structured_assertion": {
            "phase": phase.lower(), "publication_id": published["publication_id"]
        },
        "basis_refs": [manifest],
        "limitations": ["The executor report is preserved separately from live capture evidence."],
    }


def _board_ref(document):
    receipt = document.get("receipt") or {}
    ref = receipt.get("canonical_ref")
    if isinstance(ref, dict):
        return ref
    claim = document.get("claim") or {}
    if claim.get("claim_id") is None:
        raise ValueError("board publication returned no canonical Claim")
    return {"entity_type": "claim", "id": claim["claim_id"], "revision": str(claim["revision"])}


def core_explore_decision(request, messages, context):
    question = explore_question(context)
    phase = "B" if CORE_WORK_B in question else "A" if CORE_WORK_A in question else None
    if phase is None:
        raise ValueError("the Core CTF Explore brief names no mechanism phase")
    events = tool_events(messages)
    url = core_start_url(context, instructions_of(messages))
    work_path = (context.get("workspace_binding") or {}).get("work_path")
    if not isinstance(work_path, str) or not work_path.startswith("/workspace/work/"):
        raise ValueError("the Core CTF brief carries no fixed Work path")

    if phase == "B":
        assets = [
            item for item in context.get("published_asset_index") or ()
            if isinstance(item, dict)
            and (item.get("entrypoint") or {}).get("relative_path") == CORE_SCRIPT
        ]
        if not assets:
            raise ValueError("Work B has no fixed script publication")
        asset = assets[-1]
        materialized = next((
            event["document"] for event in events
            if event["name"] == "workspace_materialize"
        ), None)
        if materialized is None:
            return tool_step(request, "workspace_materialize", "call-core-b-materialize", {
                "publication_id": asset["publication_id"],
                "manifest_ref": asset["manifest_ref"],
            })
        source = next((
            item.get("destination_path") for item in materialized.get("files") or ()
            if item.get("relative_path") == CORE_SCRIPT
        ), None)
        if not isinstance(source, str) or not source.startswith(work_path + "/imports/"):
            raise ValueError("the fixed script was not materialized into this Work")
        prefix = "call-core-b-exec"
        if not any(event["name"] == "kali_exec" for event in events):
            command = (
                "set -euo pipefail; mkdir -p output && "
                + shlex.quote("/opt/wuji/ops/vnext/.venv/bin/python") + " "
                + shlex.quote(source) + " " + shlex.quote(url)
                + " | tee " + shlex.quote(CORE_RESULT)
            )
            return tool_step(request, "kali_exec", prefix, {
                "command": command, "cwd": work_path, "timeout_seconds": 30,
            })
    else:
        prefix = "call-core-a-exec"
        if not any(event["name"] == "kali_exec" for event in events):
            encoded = base64.b64encode(_core_script().encode()).decode("ascii")
            command = (
                "set -euo pipefail; mkdir -p src output && printf %s " + shlex.quote(encoded)
                + " | base64 -d > " + shlex.quote(CORE_SCRIPT) + " && "
                + shlex.quote("/opt/wuji/ops/vnext/.venv/bin/python") + " "
                + shlex.quote(CORE_SCRIPT) + " " + shlex.quote(url)
                + " | tee output/initial.json"
            )
            return tool_step(request, "kali_exec", prefix, {
                "command": command, "cwd": work_path, "timeout_seconds": 30,
            })

    next_step, process = _core_process_step(request, events, prefix)
    if next_step is not None:
        return next_step
    if isinstance(process, dict) and process.get("schema_version") == "wuji.agent-payload.v3":
        return {"kind": "payload", "document": process}

    published = next((
        event["document"] for event in events
        if event["name"] == "workspace_publish"
    ), None)
    if published is None:
        return tool_step(
            request,
            "workspace_publish",
            "call-core-" + phase.lower() + "-publish",
            _core_publish_arguments(result=phase == "B"),
        )
    if published.get("status") != "published" or not isinstance(published.get("manifest_ref"), dict):
        raise ValueError("core workspace publication did not succeed")
    board = next((
        event["document"] for event in events if event["name"] == "board_publish"
    ), None)
    if board is None:
        return tool_step(
            request,
            "board_publish",
            "call-core-" + phase.lower() + "-board",
            _board_arguments(published, phase=phase),
        )
    claim_ref = _board_ref(board)
    return {
        "kind": "payload",
        "document": core_v3(work_result={
            "outcome": "answered",
            "summary": (
                (CORE_WORK_A + " published a reusable fixed script.")
                if phase == "A"
                else (CORE_WORK_B + " materialized that version and published its sealed result.")
            ),
            "answer_basis_refs": [claim_ref],
            "unresolved_items": [],
            "capability_gaps": [],
        }),
    }


def core_decision(request, messages, role, context):
    if context.get("schema_version") not in {CONTEXT_V4_SCHEMA, WORK_BRIEF_V2_SCHEMA}:
        raise ValueError("synthetic-core-ctf requires ContextV4/WorkBriefV2")
    if role == "reason":
        return core_reason_decision(request, messages, context)
    if role == "explore":
        return core_explore_decision(request, messages, context)
    raise ValueError("synthetic-core-ctf serves reason and explore only")


def records_of(context, kind):
    for record in context.get("records") or ():
        if isinstance(record, dict) and record.get("display_kind") == kind:
            yield record


def reference(record):
    """The canonical reference of a delivered record, taken from its own body."""

    body = record["record"]
    kind = record["display_kind"]
    if kind == "claim":
        return {"entity_type": "claim", "id": body["claim_id"], "revision": str(body["revision"])}
    if kind == "intent":
        return {"entity_type": "intent", "id": body["intent_id"], "revision": str(body["revision"])}
    if kind == "artifact":
        return {
            "entity_type": "artifact",
            "id": body["artifact_ref"]["id"],
            "revision": str(body["artifact_ref"]["version"]),
        }
    if kind == "observation":
        return {
            "entity_type": "observation",
            "id": body["observation_id"],
            "revision": str(body["revision"]),
        }
    raise ValueError("unsupported record kind: " + str(kind))


def observed_material(context):
    """Every sealed body this Run was actually handed, with its reference."""

    for record in records_of(context, "artifact"):
        body = record["record"]
        material = record.get("material")
        if isinstance(material, dict) and isinstance(material.get("text"), str):
            yield reference(record), body, material["text"]


def claims(context):
    for record in records_of(context, "claim"):
        yield reference(record), record["record"]


def observations(context):
    for record in records_of(context, "observation"):
        yield reference(record), record["record"]


def proposed_paths(context):
    """The workspace path each delivered question already asks for."""

    result = {}
    for ref, body in intents(context):
        for candidate in PATH_REF.findall(body.get("question") or ""):
            result.setdefault(candidate, ref)
    return result


def intents(context):
    for record in records_of(context, "intent"):
        yield reference(record), record["record"]


def claim_read_path(text):
    match = READ_PREFIX.match(text or "")
    return match.group(1) if match else None


def claim_bodies(context):
    """Each read claim as (ref, path, quoted body) — nothing interpreted yet."""

    for ref, claim in claims(context):
        path = claim_read_path(claim.get("text"))
        if path is None:
            continue
        quoted = (claim.get("text") or "")[len("evidence read: ") + len(path) + len("; content: "):]
        yield ref, path, quoted


SIBLING = {"a": "b", "b": "a"}
VERSION = re.compile(r'"version"\s*:\s*"([^"]{1,64})"')


def sibling_path(path):
    """The other record of a two-record fixture, or None.

    This is the closed CASE-B shape the trial suite publishes (record-a /
    record-b). The peer only renames the path it actually read; it never invents
    a file and never sees which variant is running.
    """

    stem, dot, suffix = path.rpartition(".")
    if not dot:
        return None
    head, dash, tail = stem.rpartition("-")
    if not dash or tail not in SIBLING:
        return None
    return head + "-" + SIBLING[tail] + "." + suffix


def reported_version(body):
    match = VERSION.search(body or "")
    return match.group(1) if match else None


def reason_payload(context):
    """One decision, derived only from what the frozen context contains."""

    review = (context.get("states") or {}).get("completion_review")
    if isinstance(review, dict):
        return payload(
            reason_decision={
                "decision": "blocked",
                "wait_refs": [],
                "reason": (
                    "The recorded completion review still reports open basis ("
                    + ", ".join(map(str, review.get("reasons") or ["unknown"]))
                    + "); this Run cannot satisfy it and an operator must decide."
                ),
            },
            limitations=["the review, not this peer, decides whether the Goal is met"],
        )
    read_paths = {
        claim_read_path(claim.get("text")) for _, claim in claims(context)
    }
    for ref, _body, text in observed_material(context):
        pointer = POINTER.search(text)
        if pointer is None:
            continue
        target = pointer.group(1)
        if target in read_paths:
            return payload(
                reason_decision={
                    "decision": "propose_completion",
                    "wait_refs": [],
                    "reason": (
                        "The pointed file " + target + " was read and its own bytes "
                        "carry the value the Goal asks for; nothing else is missing."
                    ),
                },
                limitations=["a completion request, not a judgment that the Goal is met"],
            )
        if target in proposed_paths(context):
            asked = proposed_paths(context)[target]
            return payload(
                reason_decision={
                    "decision": "wait",
                    "wait_refs": [
                        {
                            "ref": asked,
                            "predicate": "work_accepted_result",
                            "predicate_version": "1",
                        }
                    ],
                    "reason": (
                        "The question for " + target + " is already admitted; this "
                        "Run waits for that work's own accepted result instead of "
                        "asking the same thing twice."
                    ),
                },
                limitations=["no duplicate question was proposed"],
            )
        # An Intent is grounded in knowledge, never in a raw artifact reference,
        # so the basis is the newest claim or the observation it came from.
        basis = [claim_ref for claim_ref, _ in claims(context)]
        if not basis:
            basis = [observation_ref for observation_ref, _ in observations(context)]
        if not basis:
            raise ValueError("the pointer has no claim or observation to cite")
        return payload(
            intent_proposals=[
                {
                    "client_ref": client_ref(target),
                    "question": (
                        "Read workspace:" + target + " through the registered Kali "
                        "workspace tool and report the inventory service version it "
                        "records, citing the file it came from."
                    ),
                    "basis_refs": basis[-1:],
                    "expected_output": PAYLOAD_SCHEMA,
                }
            ],
            reason_decision={
                "decision": "propose_intents",
                "wait_refs": [],
                "reason": (
                    "The observed bytes point at " + target + "; the pointer is only "
                    "in that material, so the next question is bounded to it."
                ),
            },
            limitations=["the follow-up question came from the observed pointer"],
        )
    read = {path: (ref, body) for ref, path, body in claim_bodies(context)}
    for path, (ref, body) in read.items():
        sibling = sibling_path(path)
        if sibling is None or sibling in read:
            continue
        if sibling in proposed_paths(context):
            asked = proposed_paths(context)[sibling]
            return payload(
                reason_decision={
                    "decision": "wait",
                    "wait_refs": [
                        {
                            "ref": asked,
                            "predicate": "work_accepted_result",
                            "predicate_version": "1",
                        }
                    ],
                    "reason": (
                        "The question for " + sibling + " is already admitted; this "
                        "Run waits for its accepted result."
                    ),
                },
                limitations=["no duplicate question was proposed"],
            )
        return payload(
            intent_proposals=[
                {
                    "client_ref": client_ref(sibling),
                    "question": (
                        "Read workspace:" + sibling + " through the registered Kali "
                        "workspace tool and report the inventory service version it "
                        "records, citing the file it came from."
                    ),
                    "basis_refs": [ref],
                    "expected_output": PAYLOAD_SCHEMA,
                }
            ],
            reason_decision={
                "decision": "propose_intents",
                "wait_refs": [],
                "reason": (
                    "The Goal compares two records; " + path + " is read and its "
                    "sibling " + sibling + " is not, so the next question is to read it."
                ),
            },
            limitations=["the follow-up path is the sibling of the observed one"],
        )
    compared = {}
    for path, (ref, body) in read.items():
        version = reported_version(body)
        if version is not None:
            compared[path] = (ref, version)
    if len(read) >= 2 and len(compared) < 2:
        # One record carries no version at all. The peer never invents one: it
        # states what is missing and leaves the Goal unanswered.
        without = sorted(path for path in read if path not in compared)
        return payload(
            claims=[
                {
                    "client_ref": "comparison-inconclusive",
                    "kind": "derived-conclusion",
                    "assertion_role": "explanation",
                    "text": (
                        "the two records cannot be compared from the delivered bytes: "
                        + ", ".join(without) + " records no service version"
                    ),
                    "basis_refs": [read[p][0] for p in sorted(read)],
                    "limitations": ["no version was observed in every record that was read"],
                }
            ],
            reason_decision={
                "decision": "propose_completion",
                "wait_refs": [],
                "reason": (
                    "Every record the Goal needs was read; one of them records no "
                    "version, so the comparison stays inconclusive instead of guessed."
                ),
            },
            limitations=["an inconclusive conclusion, not a claim that the records agree"],
        )
    if len(compared) >= 2:
        paths = sorted(compared)
        versions = [compared[p][1] for p in paths]
        verdict = (
            "the two records agree on service version " + versions[0]
            if len(set(versions)) == 1
            else "the two records disagree: " + " vs ".join(
                p + " reports " + v for p, v in zip(paths, versions)
            )
        )
        return payload(
            claims=[
                {
                    "client_ref": "record-comparison",
                    "kind": "derived-conclusion",
                    "assertion_role": "explanation",
                    "text": verdict + " (quoted from " + ", ".join(paths) + ")",
                    "basis_refs": [compared[p][0] for p in paths],
                    "limitations": ["compared only the records that were actually read"],
                }
            ],
            reason_decision={
                "decision": "propose_completion",
                "wait_refs": [],
                "reason": (
                    "Both records were read and their own bytes decide the comparison; "
                    "the derived conclusion is recorded as a candidate, not a fact."
                ),
            },
            limitations=["the comparison is a candidate conclusion, not a judgment"],
        )
    for ref, _ in intents(context):
        return payload(
            reason_decision={
                "decision": "wait",
                "wait_refs": [
                    {
                        "ref": ref,
                        "predicate": "work_accepted_result",
                        "predicate_version": "1",
                    }
                ],
                "reason": (
                    "Nothing has been observed for the given start point yet; this "
                    "Run waits for the admitted question's own accepted result."
                ),
            },
            limitations=["no material is stored yet"],
        )
    raise ValueError("the frozen context carries neither material nor a question")


def client_ref(target):
    tail = target.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    cleaned = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in tail
    ).strip("-")
    return ("read-" + cleaned)[:64] or "read-follow-up"


def payload(*, claims=(), intent_proposals=(), limitations=(), reason_decision=None):
    document = {
        "schema_version": PAYLOAD_SCHEMA,
        "claims": list(claims),
        "intent_proposals": list(intent_proposals),
        "limitations": list(limitations),
    }
    if reason_decision is not None:
        document["reason_decision"] = reason_decision
    return document


def problem_payload(document, role):
    """Render the same fixture decision through the published v3 result shape."""

    claims = list(document.get("claims") or ())
    intents = [
        {**item, "planning": item.get("planning")}
        for item in document.get("intent_proposals") or ()
    ]
    if role == "reason":
        decision = document.get("reason_decision")
        if not isinstance(decision, dict):
            raise ValueError("problem Reason requires a decision")
        rendered_decision = {
            "decision": decision["decision"],
            "wait_refs": list(decision.get("wait_refs") or ()),
            "public_rationale": decision["reason"][:2048],
            "basis_refs": [
                ref for item in intents for ref in item.get("basis_refs") or ()
            ][:256],
        }
        work_result = None
    else:
        rendered_decision = None
        basis = [
            ref for claim in claims for ref in claim.get("basis_refs") or ()
        ][:256]
        work_result = {
            "outcome": "answered" if basis else "no_new_information",
            "summary": (
                "The authorized fixture result was returned with durable evidence."
                if basis else "No durable fixture result was available."
            ),
            "answer_basis_refs": basis,
            "unresolved_items": [],
            "capability_gaps": [],
        }
    return {
        "schema_version": "wuji.agent-payload.v3",
        "claims": claims,
        "intent_proposals": intents,
        "reason_decision": rendered_decision,
        "work_result": work_result,
        "input_acknowledgements": [],
    }


def explore_payload(path, observation_ref, material, omitted):
    if material is None:
        return payload(
            claims=[
                {
                    "client_ref": "read-without-body",
                    "kind": "observation-summary",
                    "assertion_role": "candidate_fact",
                    "text": (
                        "evidence read: " + path + "; content: the accepted "
                        "observation's body was not delivered in this Run ("
                        + str(omitted) + ")."
                    ),
                    "basis_refs": [observation_ref],
                    "limitations": ["no bytes reached the model in this Run"],
                }
            ],
            limitations=["the body was withheld (" + str(omitted) + ")"],
        )
    return payload(
        claims=[
            {
                "client_ref": "evidence-read",
                "kind": "observation-summary",
                "assertion_role": "candidate_fact",
                "text": "evidence read: " + path + "; content: " + material,
                "basis_refs": [observation_ref],
                "limitations": ["one bounded workspace read, quoted exactly as received"],
            }
        ],
        limitations=["the quoted content is the delivered body, not an interpretation"],
    )


def explore_question(context):
    """The newest admitted question is the one this Explore Run answers.

    A frozen context carries every question the Task has admitted so far, so the
    peer must not simply take the first one: it answers the most recently
    admitted question, which is the one the Scheduler dispatched this Run for.
    """

    if context.get("schema_version") in {WORK_BRIEF_SCHEMA, WORK_BRIEF_V2_SCHEMA}:
        question = (context.get("brief") or {}).get("question")
        if isinstance(question, str):
            return question
    candidates = [
        (str(body.get("created_at") or ""), body.get("question"))
        for _, body in intents(context)
        if isinstance(body.get("question"), str)
    ]
    if not candidates:
        raise ValueError("the delivered context carries no admitted question")
    return max(candidates)[1]


def first_use_intent(url, basis_refs):
    return {
        "client_ref": client_ref(urlsplit(url).path or "entry"),
        "question": (
            "Read the approved first-use HTTP fixture URL " + url
            + " once through http_target_get and cite the accepted observation."
        ),
        "basis_refs": list(basis_refs),
        "expected_output": PAYLOAD_SCHEMA,
    }


def first_use_reason_payload(context, instructions):
    """Reason only from frozen entry text and stored, verified HTTP material."""

    delivered = stored_first_use_material(context)
    known_urls = {
        http_url(body.get("question") or ""): ref
        for ref, body in intents(context)
        if HTTP_URL.search(body.get("question") or "")
    }

    # A terminal document wins over an older entry document.  Its exact body,
    # not a fixture answer table, supplies the candidate conclusion.
    terminals = [item for item in delivered if not any(
        isinstance(item[2].get(key), str) for key in ("source_path", "guide_path")
    )]
    if terminals:
        artifact_ref, _text_value, body = terminals[-1]
        exact = json.dumps(body, ensure_ascii=False, sort_keys=True)
        return payload(
            claims=[
                {
                    "client_ref": "first-use-http-result",
                    "kind": "derived-conclusion",
                    "assertion_role": "explanation",
                    "text": "the stored first-use HTTP body reports: " + exact,
                    "basis_refs": [artifact_ref],
                    "limitations": [
                        "synthetic mechanism conclusion copied from stored HTTP material v2"
                    ],
                }
            ],
            reason_decision={
                "decision": "propose_completion",
                "wait_refs": [],
                "reason": (
                    "The second approved HTTP read is stored with complete material; "
                    "the candidate conclusion quotes that body without a preset answer."
                ),
            },
            limitations=["synthetic-first-use demonstrates mechanism, not model quality"],
        )

    if delivered:
        _artifact_ref, _text_value, body = delivered[-1]
        relative = next(
            (
                body[key]
                for key in ("source_path", "guide_path")
                if isinstance(body.get(key), str)
            ),
            None,
        )
        if relative is None:
            raise ValueError("stored first-use entry names no next path")
        current = latest_intent_url(context)
        if current is None:
            raise ValueError("stored first-use entry has no admitted origin")
        base_url, _intent_ref = current[1], current[2]
        next_url = urljoin(base_url, relative)
        base, target = urlsplit(base_url), urlsplit(next_url)
        if (base.scheme, base.hostname, base.port) != (
            target.scheme,
            target.hostname,
            target.port,
        ):
            raise ValueError("stored first-use path leaves the admitted origin")
        if next_url in known_urls:
            return payload(
                reason_decision={
                    "decision": "wait",
                    "wait_refs": [
                        {
                            "ref": known_urls[next_url],
                            "predicate": "work_accepted_result",
                            "predicate_version": "1",
                        }
                    ],
                    "reason": "The material-derived HTTP read is already admitted.",
                },
                limitations=["no duplicate HTTP request was proposed"],
            )
        basis = [ref for ref, _claim in claims(context)]
        if not basis:
            basis = [ref for ref, _observation in observations(context)]
        if not basis:
            raise ValueError("stored first-use material has no board basis")
        return payload(
            intent_proposals=[first_use_intent(next_url, basis[-1:])],
            reason_decision={
                "decision": "propose_intents",
                "wait_refs": [],
                "reason": (
                    "The stored HTTP entry body names the next approved path; the URL "
                    "is derived from that path and the admitted entry origin."
                ),
            },
            limitations=["the marker/path came from stored HTTP material v2"],
        )

    current = latest_intent_url(context)
    if current is not None:
        return payload(
            reason_decision={
                "decision": "wait",
                "wait_refs": [
                    {
                        "ref": current[2],
                        "predicate": "work_accepted_result",
                        "predicate_version": "1",
                    }
                ],
                "reason": "The first approved HTTP read is admitted but has no stored result yet.",
            },
            limitations=["no synthetic result was invented"],
        )
    start_points = START_POINTS.search(instructions)
    if start_points is None:
        raise ValueError("the frozen Task start points were not delivered")
    entry = http_url(start_points.group(1))
    return payload(
        intent_proposals=[first_use_intent(entry, ())],
        reason_decision={
            "decision": "propose_intents",
            "wait_refs": [],
            "reason": "The initial URL is copied from the frozen Task start points.",
        },
        limitations=["synthetic-first-use demonstrates mechanism, not model quality"],
    )


def first_use_decision(request, messages, role, context):
    """Explicit synthetic-first-use behavior; other synthetic aliases are unchanged."""

    if role == "reason":
        if first_use_tool_result_of(messages) is not None:
            raise ValueError("a Reason Run must decide from stored context")
        return {
            "kind": "payload",
            "document": first_use_reason_payload(context, instructions_of(messages)),
        }
    if role != "explore":
        raise ValueError("synthetic-first-use serves reason and explore only")
    result = first_use_tool_result_of(messages)
    url = http_url(explore_question(context))
    if result is None:
        if "http_target_get" not in tool_names(request.get("tools")):
            raise ValueError("no registered first-use HTTP tool was offered")
        return {
            "kind": "tool_call",
            "arguments": json.dumps({"url": url, "method": "GET"}),
        }
    return {
        "kind": "payload",
        "document": payload(
            claims=[
                {
                    "client_ref": "first-use-http-read",
                    "kind": "observation-summary",
                    "assertion_role": "candidate_fact",
                    "text": (
                        "http evidence read: " + url + "; material: "
                        + result["representation"]
                    ),
                    "basis_refs": [result["observation_ref"]],
                    "limitations": ["quoted complete HTTP material v2 without interpretation"],
                }
            ],
            limitations=["synthetic-first-use demonstrates mechanism, not model quality"],
        ),
    }


def decision(request):
    """The bounded next step: a tool call, or one settled payload."""

    messages = messages_of(request)
    role = role_of(messages)
    context = context_of(messages)
    if request.get("model") == CORE_CTF_ALIAS:
        return core_decision(request, messages, role, context)
    if request.get("model") == FIRST_USE_ALIAS:
        step = first_use_decision(request, messages, role, context)
        if (
            step["kind"] == "payload"
            and context.get("schema_version") == WORK_BRIEF_SCHEMA
        ):
            step["document"] = problem_payload(step["document"], role)
        return step
    if role == "explore":
        result = tool_result_of(messages)
        if result is None:
            path = read_path(explore_question(context), instructions_of(messages))
            if "read_workspace" not in tool_names(request.get("tools")):
                raise ValueError("no registered workspace read tool was offered")
            return {
                "kind": "tool_call",
                "arguments": json.dumps({"path": path}),
            }
        path = read_path(explore_question(context), instructions_of(messages))
        return {"kind": "payload", "document": explore_payload(
            path, result["observation_ref"], result["material"], result["omitted"]
        )}
    if role == "reason":
        if tool_result_of(messages) is not None:
            raise ValueError("a Reason Run must decide from the frozen context")
        return {"kind": "payload", "document": reason_payload(context)}
    raise ValueError("this peer serves reason and explore only")


class Peer(BaseHTTPRequestHandler):
    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        if self.path != "/v1/chat/completions" or not 0 < size <= 1048576:
            self.send_error(400)
            return
        request = json.loads(self.rfile.read(size))
        if request.get("stream") is not True:
            self.send_error(400)
            return
        try:
            step = decision(request)
        except ValueError:
            self.send_error(422)
            return
        if step["kind"] == "tool_call":
            first_use = request.get("model") == FIRST_USE_ALIAS
            name = step.get(
                "name", "http_target_get" if first_use else "read_workspace"
            )
            call_id = step.get(
                "call_id", "call-first-use-http" if first_use else "call-c2-read"
            )
            delta = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "index": 0,
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": step["arguments"],
                        },
                    }
                ],
            }
            reason = "tool_calls"
        else:
            delta = {
                "role": "assistant",
                "content": json.dumps(step["document"], sort_keys=True),
            }
            reason = "stop"
        prefix = {
            "id": "synthetic-" + str(uuid4()),
            "object": "chat.completion.chunk",
            "created": int(time()),
            "model": request["model"],
        }
        chunks = [
            {**prefix, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {**prefix, "choices": [{"index": 0, "delta": {}, "finish_reason": reason}]},
        ]
        data = (
            b"".join(b"data: " + json.dumps(chunk).encode() + b"\n\n" for chunk in chunks)
            + b"data: [DONE]\n\n"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("D12 model peer must remain loopback-only")
    ThreadingHTTPServer((args.host, args.port), Peer).serve_forever()

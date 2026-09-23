"""The mechanism peer decides only from what the platform delivered to it.

These are the fixed rules of the loopback peer used in mechanism mode. They show
that the follow-up question and the final decision come from bytes the platform
handed over (the observed material and the frozen states), not from a script.
"""

import importlib.util
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "wuji_synthetic_peer", ROOT / "ops/vnext/synthetic_model.py"
)
peer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(peer)


ENTRY = '{"pointer": "materials/registry-a.json"}'
REGISTRY = '{"service": "inventory", "version": "4.2.0"}'


def reference(kind, identifier):
    return {"entity_type": kind, "id": identifier, "revision": "1"}


def artifact_record(text, identifier="artifact-entry"):
    return {
        "ref": reference("artifact", identifier),
        "display_kind": "artifact",
        "record": {
            "artifact_ref": {"id": identifier, "version": "1", "sha256": "a" * 64},
            "media_type": "text/plain; charset=utf-8",
            "size_bytes": len(text),
            "state": "sealed",
        },
        "material": {"encoding": "utf-8", "byte_length": len(text), "text": text},
    }


def claim_record(text, identifier="claim-1"):
    return {
        "ref": reference("claim", identifier),
        "display_kind": "claim",
        "record": {
            "claim_id": identifier,
            "revision": "1",
            "kind": "observation-summary",
            "assertion_role": "candidate_fact",
            "text": text,
            "basis_refs": [reference("observation", "observation-1")],
            "limitations": ["fixture"],
        },
        "assessment": None,
    }


def intent_record(question, identifier="intent-1"):
    return {
        "ref": reference("intent", identifier),
        "display_kind": "intent",
        "record": {
            "intent_id": identifier,
            "revision": "1",
            "question": question,
            "expected_output": "wuji.agent-payload.v2",
            "basis_refs": [],
            "acceptance_state": "admitted",
        },
    }


def request(
    *,
    role,
    records,
    question=None,
    tool_result=None,
    states=None,
    model="synthetic",
    start_point="workspace:materials/entry.json",
    tool_name="read_workspace",
):
    system = (
        "fixture role instructions\nstart points: " + start_point + "\n"
        "your duty as " + role + ": fixture duty"
    )
    context = {
        "schema_version": peer.CONTEXT_SCHEMA,
        "snapshot_id": "snapshot-fixture",
        "read_set": [record["ref"] for record in records],
        "records": records,
        "relations": [],
        "states": states or {"task": {"board_revision": "1"}},
    }
    messages = [
        {"role": "system", "contents": [{"type": "text", "text": system}]},
        {
            "role": "user",
            "contents": [{"type": "text", "text": json.dumps(context)}],
        },
    ]
    if tool_result is not None:
        messages.append(
            {
                "role": "tool",
                "contents": [
                    {
                        "type": "function_result",
                        "call_id": "call-c2-read",
                        "result": json.dumps(tool_result),
                    }
                ],
            }
        )
    return {
        "model": model,
        "stream": True,
        "messages": messages,
        "tools": [
            {"function": {"name": tool_name, "parameters": {"type": "object"}}}
        ],
    }


def http_material(body):
    body_text = json.dumps(body, ensure_ascii=False, sort_keys=True)
    text = (
        "schema_version: wuji.http-exchange.v1\n"
        "response.status: 200\n"
        "response.headers:\n"
        "content-type: application/json; charset=utf-8\n"
        "response.body:\n"
        + body_text
    )
    encoded = text.encode()
    return {
        "schema_version": "wuji.model-material.v2",
        "tool_call_id": "tool-call-first-use",
        "status": "delivered",
        "source": {
            "artifact_ref": {
                "id": "artifact-http",
                "version": "1",
                "sha256": "a" * 64,
            },
            "artifact_sha256": "a" * 64,
            "media_type": "application/vnd.wuji.http-exchange+json",
            "completeness": "complete",
        },
        "representation": {
            "renderer_version": "wuji-http-renderer.v2",
            "media_type": "text/plain; charset=utf-8",
            "encoding": "utf-8",
            "text": text,
            "byte_length": len(encoded),
            "representation_sha256": sha256(encoded).hexdigest(),
            "truncated": False,
            "redaction_applied": False,
        },
        "omission_reason": None,
    }


def http_artifact_record(body):
    packet = http_material(body)
    return {
        "ref": reference("artifact", "artifact-http"),
        "display_kind": "artifact",
        "record": {
            "artifact_ref": {
                "id": "artifact-http",
                "version": "1",
                "sha256": "a" * 64,
            },
            "media_type": "application/vnd.wuji.http-exchange+json",
            "size_bytes": 256,
            "state": "sealed",
        },
        "material": packet,
    }


def reason_document(context_records, states=None):
    step = peer.decision(
        request(role="reason", records=context_records, states=states)
    )
    assert step["kind"] == "payload"
    return step["document"]


def test_explore_reads_the_path_the_admitted_question_names():
    question = (
        "Read the fixture workspace file for Task start point"
        " workspace:materials/entry.json once through the registered Kali"
        " workspace tool and cite the returned evidence."
    )
    step = peer.decision(
        request(role="explore", records=[intent_record(question)])
    )
    assert step["kind"] == "tool_call"
    assert json.loads(step["arguments"]) == {"path": "materials/entry.json"}


def test_explore_quotes_the_delivered_body_instead_of_summarising_it():
    question = "Read workspace:materials/entry.json and cite it."
    receipt = {
        "evidence_receipt": {
            "status": "accepted",
            "observation_ref": reference("observation", "observation-1"),
        },
        "material": {"encoding": "utf-8", "byte_length": len(ENTRY), "text": ENTRY},
    }
    step = peer.decision(
        request(
            role="explore",
            records=[intent_record(question)],
            tool_result=receipt,
        )
    )
    claim = step["document"]["claims"][0]
    assert claim["text"].startswith("evidence read: materials/entry.json; content: ")
    assert ENTRY in claim["text"]
    assert claim["basis_refs"] == [reference("observation", "observation-1")]


def test_a_withheld_body_is_reported_as_withheld():
    question = "Read workspace:materials/entry.json and cite it."
    receipt = {
        "evidence_receipt": {
            "status": "accepted",
            "observation_ref": reference("observation", "observation-1"),
        },
        "material_omitted": "over_inline_limit",
    }
    step = peer.decision(
        request(role="explore", records=[intent_record(question)], tool_result=receipt)
    )
    text = step["document"]["claims"][0]["text"]
    assert "not delivered" in text and "over_inline_limit" in text
    assert ENTRY not in text


def test_reason_waits_for_the_first_accepted_result_when_nothing_is_observed():
    document = reason_document([intent_record("Read the entry document.")])
    decision = document["reason_decision"]
    assert decision["decision"] == "wait"
    assert decision["wait_refs"] == [
        {
            "ref": reference("intent", "intent-1"),
            "predicate": "work_accepted_result",
            "predicate_version": "1",
        }
    ]


def test_reason_proposes_the_pointer_it_actually_observed():
    document = reason_document(
        [artifact_record(ENTRY), claim_record("evidence read: materials/entry.json; content: " + ENTRY)]
    )
    decision = document["reason_decision"]
    assert decision["decision"] == "propose_intents"
    proposal = document["intent_proposals"][0]
    assert "workspace:materials/registry-a.json" in proposal["question"]
    assert proposal["basis_refs"] == [reference("claim", "claim-1")]


def test_reason_asks_for_completion_once_the_pointed_file_was_read():
    document = reason_document(
        [
            artifact_record(ENTRY),
            claim_record(
                "evidence read: materials/registry-a.json; content: " + REGISTRY,
                identifier="claim-2",
            ),
        ]
    )
    assert document["reason_decision"]["decision"] == "propose_completion"


def test_a_recorded_gap_review_stops_the_loop_for_the_operator():
    document = reason_document(
        [artifact_record(ENTRY)],
        states={
            "task": {"board_revision": "2"},
            "completion_review": {"decision": "wait", "reasons": ["criterion_open"]},
        },
    )
    assert document["reason_decision"]["decision"] == "blocked"


@pytest.mark.parametrize("role", ["report"])
def test_an_unsupported_duty_is_refused(role):
    with pytest.raises(ValueError):
        peer.decision(request(role=role, records=[intent_record("Read it.")]))


def test_a_pointer_without_a_claim_yet_is_cited_to_the_observation():
    """Before the claim is committed the only honest basis is the observation."""

    record = artifact_record(ENTRY)
    record["display_kind"] = "artifact"
    observation = {
        "ref": reference("observation", "observation-1"),
        "display_kind": "observation",
        "record": {
            "observation_id": "observation-1",
            "revision": "1",
            "artifact_refs": [{"id": "artifact-entry", "version": "1", "sha256": "a" * 64}],
        },
        "assessment": None,
    }
    document = reason_document([record, observation])
    assert document["reason_decision"]["decision"] == "propose_intents"
    assert document["intent_proposals"][0]["basis_refs"] == [
        reference("observation", "observation-1")
    ]


def test_an_already_admitted_question_is_waited_on_instead_of_repeated():
    entry = artifact_record(ENTRY)
    asked = intent_record(
        "Read workspace:materials/registry-a.json through the registered Kali"
        " workspace tool and report the inventory service version it records."
    )
    document = reason_document([entry, asked])
    decision = document["reason_decision"]
    assert decision["decision"] == "wait"
    assert decision["wait_refs"][0]["ref"] == asked["ref"]


RECORD_A = '{"service": "inventory", "version": "4.2.0"}'
RECORD_B_SAME = '{"service": "inventory", "version": "4.2.0"}'
RECORD_B_OTHER = '{"service": "inventory", "version": "4.3.1"}'
RECORD_B_EMPTY = '{"service": "inventory"}'


def compare_document(second_body, second_path="materials/record-b.json"):
    """The two-record case: one record read, then the sibling read."""

    first = claim_record(
        "evidence read: materials/record-a.json; content: " + RECORD_A,
        identifier="claim-a",
    )
    second = claim_record(
        "evidence read: " + second_path + "; content: " + second_body,
        identifier="claim-b",
    )
    return reason_document([first, second])


def test_one_record_read_asks_for_its_sibling():
    document = reason_document(
        [
            artifact_record(RECORD_A, identifier="artifact-a"),
            claim_record(
                "evidence read: materials/record-a.json; content: " + RECORD_A,
                identifier="claim-a",
            ),
        ]
    )
    assert document["reason_decision"]["decision"] == "propose_intents"
    proposal = document["intent_proposals"][0]
    assert "workspace:materials/record-b.json" in proposal["question"]
    assert proposal["basis_refs"] == [reference("claim", "claim-a")]


def test_the_comparison_claim_states_what_the_two_bodies_actually_say():
    agree = compare_document(RECORD_B_SAME)
    claim = agree["claims"][0]
    assert claim["kind"] == "derived-conclusion"
    assert "agree" in claim["text"] and "4.2.0" in claim["text"]
    assert claim["basis_refs"] == [
        reference("claim", "claim-a"),
        reference("claim", "claim-b"),
    ]
    assert agree["reason_decision"]["decision"] == "propose_completion"

    conflict = compare_document(RECORD_B_OTHER)
    text = conflict["claims"][0]["text"]
    assert "disagree" in text and "4.2.0" in text and "4.3.1" in text

    missing = compare_document(RECORD_B_EMPTY)
    # One record carries no version: the peer never invents one. It says so and
    # still asks the platform to look, instead of reporting a comparison.
    text = missing["claims"][0]["text"]
    assert "cannot be compared" in text and "record-b.json" in text
    assert "agree" not in text and "4.2.0" not in text
    assert missing["reason_decision"]["decision"] == "propose_completion"


def test_explore_answers_the_newest_admitted_question():
    older = intent_record("Read workspace:materials/record-a.json and cite it.", identifier="i-1")
    older["record"]["created_at"] = "2026-09-18T00:00:00.000001Z"
    newer = intent_record("Read workspace:materials/record-b.json and cite it.", identifier="i-2")
    newer["record"]["created_at"] = "2026-09-18T00:00:01.000001Z"
    step = peer.decision(request(role="explore", records=[older, newer]))
    assert step["kind"] == "tool_call"
    assert json.loads(step["arguments"]) == {"path": "materials/record-b.json"}


FIRST_USE_ORIGIN = "http://first-use-fixture.wuji-vnext-test.svc:8080"


def first_use_request(*, role, records, tool_result=None, start="/f1/entry"):
    return request(
        role=role,
        records=records,
        tool_result=tool_result,
        model="synthetic-first-use",
        start_point=FIRST_USE_ORIGIN + start,
        tool_name="http_target_get",
    )


def test_synthetic_first_use_is_reason_first_and_copies_the_frozen_entry_url():
    request_body = first_use_request(role="reason", records=[], start="/f1/entry?view=summary")
    # The real frozen instructions list scope before start points. Do not lose
    # path/query by copying the first HTTP-looking origin in the prompt.
    request_body["messages"][0]["contents"][0]["text"] = (
        "authorized scope: " + FIRST_USE_ORIGIN + "\n" + request_body["messages"][0]["contents"][0]["text"]
    )
    step = peer.decision(request_body)
    assert step["kind"] == "payload"
    proposal = step["document"]["intent_proposals"][0]
    assert FIRST_USE_ORIGIN + "/f1/entry?view=summary" in proposal["question"]
    assert proposal["basis_refs"] == []


def test_synthetic_first_use_renders_problem_v2_work_brief_as_payload_v3():
    request_body = first_use_request(role="reason", records=[])
    request_body["messages"][1]["contents"][0]["text"] = json.dumps({
        "schema_version": "wuji.work-brief.v1",
        "brief": {"question": "choose the next necessary work"},
        "knowledge_index": [],
        "initial_deliveries": [],
    })

    document = peer.decision(request_body)["document"]

    assert document["schema_version"] == "wuji.agent-payload.v3"
    assert document["reason_decision"]["decision"] == "propose_intents"
    assert document["intent_proposals"][0]["planning"] is None
    assert document["work_result"] is None


def test_synthetic_first_use_explore_calls_only_the_admitted_http_url():
    url = FIRST_USE_ORIGIN + "/f1/entry"
    step = peer.decision(
        first_use_request(
            role="explore",
            records=[intent_record("Read approved URL " + url)],
        )
    )
    assert step["kind"] == "tool_call"
    assert json.loads(step["arguments"]) == {"url": url, "method": "GET"}


def test_synthetic_first_use_derives_the_f1_marker_request_from_material_v2():
    marker = "f1-random-marker-from-response"
    body = {
        "fixture": "F1",
        "marker": marker,
        "source_path": "/f1/source?marker=" + marker,
    }
    url = FIRST_USE_ORIGIN + "/f1/entry"
    intent = intent_record("Read approved URL " + url)
    receipt = {
        "evidence_receipt": {
            "status": "accepted",
            "observation_ref": reference("observation", "observation-http"),
        },
        "material": http_material(body),
    }
    explored = peer.decision(
        first_use_request(
            role="explore", records=[intent], tool_result=receipt
        )
    )["document"]
    assert marker in explored["claims"][0]["text"]

    claim = claim_record(explored["claims"][0]["text"], identifier="claim-http")
    reasoned = peer.decision(
        first_use_request(
            role="reason",
            records=[intent, claim, http_artifact_record(body)],
        )
    )["document"]
    proposal = reasoned["intent_proposals"][0]
    assert FIRST_USE_ORIGIN + "/f1/source?marker=" + marker in proposal["question"]
    assert proposal["basis_refs"] == [reference("claim", "claim-http")]


@pytest.mark.parametrize(
    "variant,guide",
    [("a", "guide-a"), ("b", "guide-b")],
)
def test_synthetic_first_use_f2_follows_each_material_variant(variant, guide):
    url = FIRST_USE_ORIGIN + "/f2/" + variant + "/entry"
    body = {
        "fixture": "F2",
        "variant": variant,
        "guide_path": "/f2/" + variant + "/" + guide,
    }
    intent = intent_record("Read approved URL " + url)
    claim = claim_record("HTTP entry stored", identifier="claim-f2-" + variant)
    step = peer.decision(
        first_use_request(
            role="reason",
            records=[intent, claim, http_artifact_record(body)],
            start="/f2/" + variant + "/entry",
        )
    )
    question = step["document"]["intent_proposals"][0]["question"]
    assert FIRST_USE_ORIGIN + "/f2/" + variant + "/" + guide in question


CORE_URL = "https://challenge.core.invalid/start?case=mechanism"
CORE_TOOLS = [
    "knowledge_read", "kali_exec", "kali_read", "workspace_publish",
    "workspace_materialize", "board_publish",
]


def core_context(*, question, indexes=(), assets=(), related=(), results=()):
    return {
        "schema_version": peer.WORK_BRIEF_V2_SCHEMA,
        "snapshot_id": "snapshot-core",
        "brief": {
            "task_goal": "Recover the authorized answer from " + CORE_URL,
            "authorization_summary": ["https://challenge.core.invalid:443"],
            "question": question,
            "related_work_summaries": list(related),
            "predecessor_result_summaries": list(results),
        },
        "knowledge_index": list(indexes),
        "initial_deliveries": [],
        "workspace_binding": {"work_path": "/workspace/work/work-core"},
        "published_asset_index": list(assets),
    }


def core_request(*, role, context):
    return {
        "model": peer.CORE_CTF_ALIAS,
        "stream": True,
        "messages": [
            {
                "role": "system",
                "contents": [{
                    "type": "text",
                    "text": "your duty as " + role + ": fixed core mechanism",
                }],
            },
            {
                "role": "user",
                "contents": [{"type": "text", "text": json.dumps(context)}],
            },
        ],
        "tools": [
            {"function": {"name": name, "parameters": {"type": "object"}}}
            for name in CORE_TOOLS
        ],
    }


def complete_tool(request_body, step, result):
    request_body["messages"].extend([
        {
            "role": "assistant",
            "tool_calls": [{
                "id": step["call_id"], "type": "function",
                "function": {"name": step["name"], "arguments": step["arguments"]},
            }],
        },
        {
            "role": "tool",
            "contents": [{
                "type": "function_result", "call_id": step["call_id"],
                "result": json.dumps(result),
            }],
        },
    ])


def process_reply(*, state, handle="process-core", cursor=0, exit_code=None):
    return {
        "schema_version": "wuji.process-reply.v1",
        "handle": handle,
        "state": state,
        "exit_code": exit_code,
        "next_cursor": {"stdout_offset": cursor, "stderr_offset": 0},
    }


def core_asset():
    return {
        "publication_id": "publication-script-v1",
        "manifest_ref": {"id": "manifest-script", "version": "1", "sha256": "a" * 64},
        "entrypoint": {
            "relative_path": peer.CORE_SCRIPT,
            "interpreter_argv": ["/opt/wuji/ops/vnext/.venv/bin/python"],
        },
    }


def core_result_asset():
    return {
        "publication_id": "publication-result-v1",
        "manifest_ref": {
            "id": "manifest-result", "version": "1", "sha256": "b" * 64
        },
        "entrypoint": {
            "relative_path": peer.CORE_RESULT,
            "interpreter_argv": ["/bin/cat"],
        },
    }


def claim_index(identifier):
    return {
        "ref": reference("claim", identifier),
        "material_type": "claim",
        "available_selectors": ["record_fields"],
    }


def material_index(identifier, media_type):
    return {
        "ref": reference("artifact", identifier),
        "material_type": media_type,
        "available_selectors": ["record_fields", "text_range"],
    }


def knowledge_delivery(ref, text):
    return {
        "schema_version": "wuji.knowledge-delivery.v1",
        "ref": ref,
        "text": text,
    }


def test_core_reason_reads_claim_and_manifest_before_grounded_work_b():
    initial = core_request(
        role="reason",
        context=core_context(question="choose the next necessary work"),
    )
    first = peer.decision(initial)
    proposal = first["document"]["intent_proposals"][0]
    assert peer.CORE_WORK_A in proposal["question"]
    assert CORE_URL in proposal["question"]
    assert proposal["basis_refs"] == []

    context = core_context(
        question="choose the next necessary work",
        indexes=[claim_index("claim-work-a")],
        assets=[core_asset()],
        results=[peer.CORE_WORK_A + " published a reusable fixed script."],
    )
    request_body = core_request(role="reason", context=context)
    read_claim = peer.decision(request_body)
    assert read_claim["name"] == "knowledge_read"
    assert json.loads(read_claim["arguments"])["ref"] == reference("claim", "claim-work-a")
    complete_tool(
        request_body,
        read_claim,
        knowledge_delivery(
            reference("claim", "claim-work-a"),
            json.dumps({"text": peer.CORE_WORK_A + " published publication-script-v1."}),
        ),
    )

    read_manifest = peer.decision(request_body)
    manifest_ref = reference("artifact", "manifest-script")
    assert read_manifest["name"] == "knowledge_read"
    assert json.loads(read_manifest["arguments"])["ref"] == manifest_ref
    complete_tool(
        request_body,
        read_manifest,
        knowledge_delivery(
            manifest_ref,
            json.dumps({"workspace_bundle_manifest": {"schema_version": "wuji.workspace-bundle.v1"}}),
        ),
    )

    grounded = peer.decision(request_body)["document"]
    proposal = grounded["intent_proposals"][0]
    assert peer.CORE_WORK_B in proposal["question"]
    assert "publication-script-v1" in proposal["question"]
    assert proposal["basis_refs"] == [reference("claim", "claim-work-a")]
    assert all(ref["entity_type"] != "artifact" for ref in proposal["basis_refs"])


def test_core_explore_a_waits_for_running_process_then_publishes_board_before_result():
    context = core_context(
        question=peer.CORE_WORK_A + ": fetch " + CORE_URL,
    )
    request_body = core_request(role="explore", context=context)

    execute = peer.decision(request_body)
    assert execute["name"] == "kali_exec"
    command = json.loads(execute["arguments"])["command"]
    assert "base64 -d" in command and peer.CORE_SCRIPT in command
    complete_tool(request_body, execute, process_reply(state="running", cursor=0))

    read = peer.decision(request_body)
    assert read["name"] == "kali_read"
    assert json.loads(read["arguments"])["wait_ms"] == 1000
    complete_tool(request_body, read, process_reply(state="exited", cursor=128, exit_code=0))

    publish = peer.decision(request_body)
    assert publish["name"] == "workspace_publish"
    assert json.loads(publish["arguments"])["files"] == [{"relative_path": peer.CORE_SCRIPT}]
    publication = {
        "schema_version": "wuji.workspace-publish-result.v1",
        "status": "published",
        "publication_id": "publication-script-v1",
        "manifest_ref": {"id": "manifest-script", "version": "1", "sha256": "a" * 64},
    }
    complete_tool(request_body, publish, publication)

    board = peer.decision(request_body)
    assert board["name"] == "board_publish"
    board_arguments = json.loads(board["arguments"])
    assert board_arguments["basis_refs"] == [reference("artifact", "manifest-script")]
    complete_tool(request_body, board, {
        "schema_version": "wuji.board-publish-result.v1",
        "receipt": {"canonical_ref": reference("claim", "claim-work-a")},
    })

    final = peer.decision(request_body)
    assert final["kind"] == "payload"
    assert final["document"]["work_result"]["answer_basis_refs"] == [
        reference("claim", "claim-work-a")
    ]


def test_core_explore_b_materializes_fixed_script_and_publishes_result():
    context = core_context(
        question=(
            peer.CORE_WORK_B + ": materialize publication publication-script-v1 and run it against "
            + CORE_URL
        ),
        assets=[core_asset()],
    )
    request_body = core_request(role="explore", context=context)

    materialize = peer.decision(request_body)
    assert materialize["name"] == "workspace_materialize"
    assert json.loads(materialize["arguments"])["publication_id"] == "publication-script-v1"
    complete_tool(request_body, materialize, {
        "schema_version": "wuji.workspace-materialize-result.v1",
        "publication_id": "publication-script-v1",
        "files": [{
            "relative_path": peer.CORE_SCRIPT,
            "destination_path": "/workspace/work/work-core/imports/publication-script-v1/src/fetch.py",
        }],
    })

    execute = peer.decision(request_body)
    assert execute["name"] == "kali_exec"
    command = json.loads(execute["arguments"])["command"]
    assert "/imports/publication-script-v1/src/fetch.py" in command
    assert CORE_URL in command
    complete_tool(request_body, execute, process_reply(state="exited", cursor=256, exit_code=0))

    publish = peer.decision(request_body)
    assert publish["name"] == "workspace_publish"
    assert json.loads(publish["arguments"])["files"] == [{"relative_path": peer.CORE_RESULT}]
    complete_tool(request_body, publish, {
        "schema_version": "wuji.workspace-publish-result.v1",
        "status": "published",
        "publication_id": "publication-result-v1",
        "manifest_ref": {"id": "manifest-result", "version": "1", "sha256": "b" * 64},
    })

    board = peer.decision(request_body)
    assert board["name"] == "board_publish"
    assert peer.CORE_WORK_B in json.loads(board["arguments"])["text"]
    complete_tool(request_body, board, {
        "schema_version": "wuji.board-publish-result.v1",
        "receipt": {"canonical_ref": reference("claim", "claim-work-b")},
    })
    final = peer.decision(request_body)["document"]
    assert peer.CORE_WORK_B in final["work_result"]["summary"]
    assert final["work_result"]["answer_basis_refs"] == [reference("claim", "claim-work-b")]


def test_core_final_reason_reads_work_b_claim_before_completion():
    body = json.dumps({"answer": "core-mechanism-ok"}).encode()
    result = json.dumps({
        "body_base64": __import__("base64").b64encode(body).decode(),
        "length": len(body),
        "status": 200,
        "url": CORE_URL,
    }, sort_keys=True).encode() + b"\n"
    result_digest = sha256(result).hexdigest()
    context = core_context(
        question="choose the next necessary work",
        indexes=[
            claim_index("claim-work-a"), claim_index("claim-work-b"),
            material_index("command-work-b", peer.CORE_COMMAND_LOG),
            material_index("capture-work-b", peer.CORE_HTTP_EXCHANGE),
        ],
        assets=[core_asset(), core_result_asset()],
        results=[
            peer.CORE_WORK_A + " published a reusable fixed script.",
            peer.CORE_WORK_B + " materialized that version and published its sealed result.",
        ],
    )
    request_body = core_request(role="reason", context=context)
    first = peer.decision(request_body)
    complete_tool(
        request_body,
        first,
        knowledge_delivery(reference("claim", "claim-work-a"), peer.CORE_WORK_A + " result"),
    )
    second = peer.decision(request_body)
    complete_tool(
        request_body,
        second,
        knowledge_delivery(reference("claim", "claim-work-b"), peer.CORE_WORK_B + " result"),
    )
    manifest = peer.decision(request_body)
    complete_tool(request_body, manifest, knowledge_delivery(
        reference("artifact", "manifest-result"),
        json.dumps({"workspace_bundle_manifest": {
            "files": [{
                "relative_path": peer.CORE_RESULT,
                "ref": {"id": "result-json", "version": "1", "sha256": result_digest},
            }],
        }}),
    ))
    command = peer.decision(request_body)
    assert json.loads(command["arguments"])["ref"] == reference("artifact", "command-work-b")
    complete_tool(request_body, command, knowledge_delivery(
        reference("artifact", "command-work-b"),
        json.dumps({
            "schema_version": "wuji.command-log.v1",
            "command": "python imported/src/fetch.py | tee " + peer.CORE_RESULT,
            "stdout_base64": __import__("base64").b64encode(result).decode(),
            "stdout_sha256": result_digest,
            "truncated": False,
        }),
    ))
    capture = peer.decision(request_body)
    assert json.loads(capture["arguments"])["ref"] == reference("artifact", "capture-work-b")
    complete_tool(request_body, capture, knowledge_delivery(
        reference("artifact", "capture-work-b"),
        "schema_version: wuji.http-exchange.v1\nresponse.status: 200\n"
        "response.headers:\ncontent-type: application/json\nresponse.body:\n"
        + body.decode(),
    ))
    final = peer.decision(request_body)["document"]
    assert final["reason_decision"]["decision"] == "propose_completion"
    assert final["reason_decision"]["basis_refs"] == [
        reference("claim", "claim-work-b"),
        reference("artifact", "command-work-b"),
        reference("artifact", "capture-work-b"),
    ]
    assert "body SHA-256 " + sha256(body).hexdigest() in final["reason_decision"][
        "public_rationale"
    ]


def test_core_final_reason_rejects_a_capture_that_disagrees_with_the_result():
    body = b'{"answer":"expected"}'
    result = json.dumps({
        "body_base64": __import__("base64").b64encode(body).decode(),
        "length": len(body), "status": 200, "url": CORE_URL,
    }, sort_keys=True).encode() + b"\n"
    digest = sha256(result).hexdigest()
    context = core_context(
        question="choose the next necessary work",
        indexes=[
            claim_index("claim-work-a"), claim_index("claim-work-b"),
            material_index("command-work-b", peer.CORE_COMMAND_LOG),
            material_index("capture-work-b", peer.CORE_HTTP_EXCHANGE),
        ],
        assets=[core_asset(), core_result_asset()],
        results=[peer.CORE_WORK_A, peer.CORE_WORK_B],
    )
    request_body = core_request(role="reason", context=context)
    deliveries = [
        (reference("claim", "claim-work-a"), peer.CORE_WORK_A),
        (reference("claim", "claim-work-b"), peer.CORE_WORK_B),
        (reference("artifact", "manifest-result"), json.dumps({
            "workspace_bundle_manifest": {"files": [{
                "relative_path": peer.CORE_RESULT,
                "ref": {"id": "result-json", "version": "1", "sha256": digest},
            }]}
        })),
        (reference("artifact", "command-work-b"), json.dumps({
            "schema_version": "wuji.command-log.v1",
            "command": "tee " + peer.CORE_RESULT,
            "stdout_base64": __import__("base64").b64encode(result).decode(),
            "stdout_sha256": digest,
            "truncated": False,
        })),
        (reference("artifact", "capture-work-b"),
         "schema_version: wuji.http-exchange.v1\nresponse.status: 503\n"
         "response.headers:\nresponse.body:\nwrong"),
    ]
    for ref, text in deliveries:
        step = peer.decision(request_body)
        complete_tool(request_body, step, knowledge_delivery(ref, text))
    with pytest.raises(ValueError, match="does not match sealed capture"):
        peer.decision(request_body)

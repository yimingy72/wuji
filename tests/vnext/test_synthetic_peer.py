"""The mechanism peer decides only from what the platform delivered to it.

These are the fixed rules of the loopback peer used in mechanism mode. They show
that the follow-up question and the final decision come from bytes the platform
handed over (the observed material and the frozen states), not from a script.
"""

import importlib.util
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


def request(*, role, records, question=None, tool_result=None, states=None):
    system = (
        "fixture role instructions\nstart points: workspace:materials/entry.json\n"
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
        "model": "synthetic",
        "stream": True,
        "messages": messages,
        "tools": [
            {"function": {"name": "read_workspace", "parameters": {"type": "object"}}}
        ],
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

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
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import time
from uuid import uuid4


CONTEXT_SCHEMA = "wuji.context.v2"
PAYLOAD_SCHEMA = "wuji.agent-payload.v2"
# A workspace reference the platform publishes; the peer never invents one.
PATH_REF = re.compile(r"workspace:([A-Za-z0-9][A-Za-z0-9._/-]{0,255})")
START_POINTS = re.compile(r"start points:([^\n]*)")
POINTER = re.compile(r'"pointer"\s*:\s*"([A-Za-z0-9][A-Za-z0-9._/-]{0,255})"')
READ_PREFIX = re.compile(r"^evidence read: ([^;]{1,256}); content: ", re.DOTALL)


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
        if document is not None and document.get("schema_version") == CONTEXT_SCHEMA:
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
    for _, body in intents(context):
        question = body.get("question")
        if isinstance(question, str):
            return question
    raise ValueError("the delivered context carries no admitted question")


def decision(request):
    """The bounded next step: a tool call, or one settled payload."""

    messages = messages_of(request)
    role = role_of(messages)
    context = context_of(messages)
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
            delta = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call-c2-read",
                        "type": "function",
                        "function": {
                            "name": "read_workspace",
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

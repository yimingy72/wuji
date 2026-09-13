"""Canonical public MAF approval objects; business decisions remain at the Host."""

from agent_framework import Content, Message

from wuji_core.http import canonical_json_bytes, strict_json_loads


def _body(value):
    return value.model_dump(mode="python") if hasattr(value, "model_dump") else value


def validate_pending(content, binding):
    """Compare both native identities and the original uncoerced arguments."""
    if not isinstance(content, Content):
        raise TypeError("a public native approval Content is required")
    body = content.to_dict()
    record = _body(binding)
    call = body.get("function_call")
    if (
        body.get("type") != "function_approval_request"
        or not isinstance(call, dict)
        or not body.get("id")
        or body["id"] != call.get("id")
        or record["sdk_approval_id"] != body["id"]
        or record["sdk_content_id"] != call["id"]
        or record["provider_call_id"] != call.get("call_id")
    ):
        raise ValueError("native approval identity differs from its published binding")
    original = strict_json_loads(record["native_arguments"])
    arguments = call.get("arguments")
    if isinstance(arguments, str):
        arguments = strict_json_loads(arguments)
    if canonical_json_bytes(arguments) != canonical_json_bytes(original):
        raise ValueError("native approval changed the original arguments")
    return content


def extract_approval_requests(response, *, call_bindings):
    bindings = {_body(b)["sdk_approval_id"]: b for b in call_bindings
                if _body(b).get("sdk_approval_id") is not None}
    pending = []
    seen = set()
    for message in response.messages:
        for content in message.contents:
            if content.type != "function_approval_request":
                continue
            if content.id in seen or content.id not in bindings:
                raise ValueError("duplicate or unbound native approval")
            validate_pending(content, bindings[content.id])
            pending.append(content)
            seen.add(content.id)
    return tuple(pending)


def approval_response_message(*, pending_content, decision):
    """Convert a persisted decision, without granting execution permission.

    The caller must obtain the decision from Host.load_delivery. P06 still
    validates the approval reference in the real function callback transaction.
    """
    if not isinstance(pending_content, Content) or pending_content.type != "function_approval_request":
        raise TypeError("the restored native request is required")
    if decision not in ("approve", "reject") or type(decision) is not str:
        raise ValueError("a persisted approve/reject decision is required")
    return Message(role="user", contents=[
        pending_content.to_function_approval_response(approved=decision == "approve")
    ])

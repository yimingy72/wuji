"""Shared predicates for registered requests, independent of scheduling policy."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row
from wuji_core.execution.states import task_can_run


def digest(value):
    return sha256(canonical_json_bytes(value)).hexdigest()


def audit(tx, kind, details):
    tx.connection.execute("INSERT INTO vnext.admission_audit(tenant_id,project_id,task_id,audit_id,kind,subject,request_id,details_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (*tx.owner, str(uuid4()), kind, tx.access.principal.subject, tx.access.request_id, json_text(details)))


def current_run(tx, config, *, allow_leased_work=False):
    binding = tx.run_binding
    identity = binding.identity.model_dump(mode="json")
    run = row(tx.connection.execute("SELECT * FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s", (*tx.owner, identity["agent_run_id"])))
    work = row(tx.connection.execute("SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s FOR UPDATE", (*tx.owner, identity["work_item_id"])))
    if not run or not work or any(str(run[k]) != str(v) for k, v in identity.items()):
        raise DomainError("STALE_EXECUTION", 409)
    held = tx.connection.execute("SELECT 1 FROM vnext.work_suspension WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s LIMIT 1", (*tx.owner, work["work_item_id"])).fetchone()
    work_states = {"running", "leased"} if allow_leased_work else {"running"}
    if (not task_can_run(tx.task) or not run["execution_allowed"] or run["stop_kind"] is not None or run["process_state"] != "running" or not run["started_at"] or not run["pod_uid"] or not run["process_identity_json"] or work["state"] not in work_states or work["desired_state"] != "run" or held or work["current_run_id"] != run["agent_run_id"] or work["run_epoch"] != run["run_epoch"] or tx.task["execution_epoch"] != run["execution_epoch"] or tx.task["runtime_attempt"] != run["runtime_attempt"]):
        raise DomainError("STALE_EXECUTION", 409)
    from wuji_core.execution.dependencies import dependencies_satisfied, intent_current
    # The same dependency service reads canonical predecessors/criterion judgments.
    if not dependencies_satisfied(tx, work["work_item_id"]) or not intent_current(tx, work):
        raise DomainError("STALE_EXECUTION", 409)
    definition = strict_json_loads(tx.task["definition_json"])
    expiry = datetime.fromisoformat(definition["task"]["authorization_expires_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if expiry <= now or (now - tx.task["activated_at"]).total_seconds() >= config.runtime.limits.max_elapsed_seconds:
        raise DomainError("LIMIT_BLOCKED", 429)
    for pool in tx.capacity_pools:
        reservation = tx.connection.execute("SELECT state FROM vnext.capacity_reservation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND pool_key=%s", (*tx.owner, run["agent_run_id"], pool["pool_key"])).fetchone()
        if not reservation or reservation[0] == "released":
            raise DomainError("STALE_EXECUTION", 409)
    if not any(p["tier"] == "model" for p in tx.capacity_pools):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    return run, work


def model_function_capabilities(tx, registry, config, run, work):
    """Trusted final function set for this assigned Profile, including native tools."""

    definition = strict_json_loads(tx.task["definition_json"])
    profile = definition["worker_profiles"][work["kind"]]
    body = profile["body"]
    allowed = (
        set(config.allowed_tool_refs)
        & set(config.runtime.allowed_tool_refs)
        & set(tx.run_binding.allowed_tool_refs)
    )
    if body.get("schema_version") in {
        "wuji.harness.problem.v1", "wuji.harness.problem.v2"
    }:
        # current_run already binds this credential to the exact Task, Work,
        # Run epoch and immutable Task definition.  scheduler_assignment is
        # intentionally unreadable while request_purpose=model_request, so it
        # cannot be used as a second trust source here.
        capabilities = {
            item["name"]: item for item in body["capability_manifest"]
        }
        if len(capabilities) != len(body["capability_manifest"]):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        environment_refs = {
            item["source_ref"] for item in capabilities.values()
            if item["category"] == "environment_action"
        }
        if environment_refs != set(body["tool_definition_refs"]) or not environment_refs <= allowed:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        for item in capabilities.values():
            if item["category"] == "environment_action":
                tool = registry.tool(tx, item["source_ref"])
                if tool.name != item["name"] or digest(tool.input_schema) != item["input_schema_digest"]:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return capabilities, environment_refs
    definitions = {registry.tool(tx, ref).name: registry.tool(tx, ref) for ref in allowed}
    if len(definitions) != len(allowed):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    return ({
        name: {
            "name": name,
            "source_ref": value.ref,
            "input_schema_digest": digest(value.input_schema),
            "category": "environment_action",
        }
        for name, value in definitions.items()
    }, {value.ref for value in definitions.values()})


def counter(tx):
    tx.connection.execute("INSERT INTO vnext.admission_counter(tenant_id,project_id,task_id) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING", tx.owner)
    return row(tx.connection.execute("SELECT * FROM vnext.admission_counter WHERE tenant_id=%s AND project_id=%s AND task_id=%s FOR UPDATE", tx.owner))


def consume_attempt(tx, *, model, maximum):
    counts = counter(tx)
    name = "model_attempts" if model else "tool_attempts"
    if counts[name] >= maximum:
        raise DomainError("LIMIT_BLOCKED", 429)
    tx.connection.execute(f"UPDATE vnext.admission_counter SET {name}={name}+1 WHERE tenant_id=%s AND project_id=%s AND task_id=%s", tx.owner)


def allocate_output(tx, size, *, already, runtime, allow_partial=False):
    counts = counter(tx)
    remaining = max(
        0,
        min(
            runtime.limits.max_single_output_bytes - already,
            runtime.limits.max_total_output_bytes - counts["output_bytes"],
        ),
    )
    accepted_size = min(size, remaining)
    if not allow_partial and accepted_size != size:
        accepted_size = 0
    # received is the observed application chunk; rejected bytes aren't retained.
    tx.connection.execute("UPDATE vnext.admission_counter SET received_bytes=received_bytes+%s,output_bytes=output_bytes+%s,retained_bytes=retained_bytes+%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s", (size, accepted_size, accepted_size, *tx.owner))
    return accepted_size if allow_partial else accepted_size == size

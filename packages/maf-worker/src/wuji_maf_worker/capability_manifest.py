"""Schemas of the exact native and Host functions visible to a problem Profile."""

import asyncio
from functools import lru_cache
from hashlib import sha256

from agent_framework import AgentSession, SessionContext, TodoProvider

from wuji_core.contracts.sessions import SessionLimits
from wuji_core.http import canonical_json_bytes
from wuji_maf_worker.history import BoundedWorkMemoryProvider, VersionedMemoryStore


KNOWLEDGE_SCHEMAS = {
    "knowledge_list": {
        "type": "object", "additionalProperties": False,
        "required": ["snapshot_id"],
        "properties": {
            "snapshot_id": {"type": "string", "minLength": 1, "maxLength": 256},
            "material_types": {"type": "array", "maxItems": 4, "uniqueItems": True,
                               "items": {"type": "string", "enum": ["artifact", "observation", "claim", "intent"]},
                               "default": []},
            "cursor": {"anyOf": [{"type": "string", "minLength": 1, "maxLength": 4096}, {"type": "null"}], "default": None},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
        },
    },
    "knowledge_read": {
        "type": "object", "additionalProperties": False,
        "required": ["snapshot_id", "ref", "selector"],
        "properties": {
            "snapshot_id": {"type": "string", "minLength": 1, "maxLength": 256},
            "ref": {"type": "object", "additionalProperties": False,
                    "required": ["entity_type", "id", "revision"],
                    "properties": {
                        "entity_type": {"type": "string", "enum": ["artifact", "observation", "claim", "intent"]},
                        "id": {"type": "string", "minLength": 1, "maxLength": 256},
                        "revision": {"type": "string", "pattern": "^(0|[1-9][0-9]*)$"},
                    }},
            "selector": {"oneOf": [
                {"type": "object", "additionalProperties": False, "required": ["kind", "fields"],
                 "properties": {"kind": {"const": "record_fields"},
                                "fields": {"type": "array", "minItems": 1, "maxItems": 32,
                                           "uniqueItems": True, "items": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,63}$"}}}},
                {"type": "object", "additionalProperties": False, "required": ["kind", "start", "end"],
                 "properties": {"kind": {"const": "text_range"},
                                "start": {"type": "integer", "minimum": 0, "maximum": 1048576},
                                "end": {"type": "integer", "minimum": 1, "maximum": 1048576}}},
            ]},
        },
    },
    "knowledge_refresh": {
        "type": "object", "additionalProperties": False,
        "required": ["snapshot_id", "neighborhood"],
        "properties": {
            "snapshot_id": {"type": "string", "minLength": 1, "maxLength": 256},
            "neighborhood": {"type": "string", "const": "current_problem"},
        },
    },
}


def _digest(schema):
    return sha256(canonical_json_bytes(schema)).hexdigest()


async def _native_schemas():
    limits = SessionLimits(
        max_objects=32, max_reference_depth=8, max_object_bytes=8192,
        max_total_bytes=65536, max_messages=128, max_pending_approvals=4,
    )
    session = AgentSession(session_id="manifest")
    context = SessionContext(session_id="manifest", input_messages=[])
    providers = (
        TodoProvider(source_id="problem_todo"),
        BoundedWorkMemoryProvider(
            VersionedMemoryStore(limits=limits),
            source_id="problem_memory", scope="manifest",
        ),
    )
    for provider in providers:
        await provider.before_run(
            agent=None, session=session, context=context,
            state=session.state.setdefault(provider.source_id, {}),
        )
    return {tool.name: tool.parameters() for tool in context.tools}


@lru_cache(maxsize=1)
def native_schemas():
    return asyncio.run(_native_schemas())


def build_capability_manifest(*, environment_tools=(), include_todo, include_memory,
                              include_knowledge, session_limit, knowledge_limit,
                              environment_limit, knowledge_names=None):
    entries = []
    schemas = native_schemas() if include_todo or include_memory else {}
    for name, schema in sorted(schemas.items()):
        is_todo = name.startswith("todos_")
        if (is_todo and not include_todo) or (not is_todo and not include_memory):
            continue
        entries.append({
            "name": name,
            "source_ref": "maf.todo.v1" if is_todo else "maf.file-memory.v1",
            "input_schema_digest": _digest(schema),
            "category": "session_state",
            "implementation_version": "agent-framework-core-1.18.0",
            "per_work_limit": session_limit,
            "required_permissions": ["session_writer"],
        })
    if include_knowledge:
        selected = set(KNOWLEDGE_SCHEMAS if knowledge_names is None else knowledge_names)
        if not selected <= set(KNOWLEDGE_SCHEMAS):
            raise ValueError("unknown knowledge capability")
        for name, schema in KNOWLEDGE_SCHEMAS.items():
            if name not in selected:
                continue
            entries.append({
                "name": name, "source_ref": "wuji.knowledge.v1",
                "input_schema_digest": _digest(schema), "category": "knowledge_read",
                "implementation_version": "wuji.knowledge-delivery.v1",
                "per_work_limit": knowledge_limit,
                "required_permissions": ["task_read", "material_disclosure"],
            })
    for tool in environment_tools:
        entries.append({
            "name": tool["name"], "source_ref": tool["ref"],
            "input_schema_digest": _digest(tool["input_schema"]),
            "category": "environment_action",
            "implementation_version": tool["revision"],
            "per_work_limit": environment_limit,
            "required_permissions": ["tool_gate"],
        })
    if len({entry["name"] for entry in entries}) != len(entries):
        raise ValueError("capability function names must be unique")
    return entries

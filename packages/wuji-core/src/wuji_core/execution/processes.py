"""Typed process actions and executor-reported replies for the core Kali path."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

from wuji_core.contracts.generated import ProcessCursorV1, ProcessReplyV1
from wuji_core.http import canonical_json_bytes
from wuji_core.persistence.uow import DomainError, row


PROCESS_ACTION_BY_NAME = {
    "kali_exec": "exec",
    "kali_read": "read",
    "kali_input": "input",
    "kali_stop": "stop",
}


PROCESS_TOOL_SCHEMAS = {
    "kali_exec": {
        "type": "object",
        "additionalProperties": False,
        "required": ["command"],
        "properties": {
            "command": {"type": "string", "minLength": 1, "maxLength": 65536},
            "cwd": {
                "anyOf": [
                    {"type": "string", "minLength": 1, "maxLength": 4096},
                    {"type": "null"},
                ],
                "default": None,
            },
            "timeout_seconds": {
                "anyOf": [
                    {"type": "number", "exclusiveMinimum": 0},
                    {"type": "null"},
                ],
                "default": None,
            },
        },
    },
    "kali_read": {
        "type": "object",
        "additionalProperties": False,
        "required": ["handle", "cursor", "max_bytes"],
        "properties": {
            "handle": {"type": "string", "minLength": 1, "maxLength": 256},
            "cursor": {
                "type": "object",
                "additionalProperties": False,
                "required": ["stdout_offset", "stderr_offset"],
                "properties": {
                    "stdout_offset": {"type": "integer", "minimum": 0},
                    "stderr_offset": {"type": "integer", "minimum": 0},
                },
            },
            "max_bytes": {"type": "integer", "minimum": 1, "maximum": 1048576},
            "wait_ms": {
                "type": "integer",
                "minimum": 0,
                "maximum": 30000,
                "default": 0,
            },
        },
    },
    "kali_input": {
        "type": "object",
        "additionalProperties": False,
        "required": ["handle", "data"],
        "properties": {
            "handle": {"type": "string", "minLength": 1, "maxLength": 256},
            "data": {"type": "string", "maxLength": 1048576},
            "eof": {"type": "boolean", "default": False},
        },
    },
    "kali_stop": {
        "type": "object",
        "additionalProperties": False,
        "required": ["handle"],
        "properties": {
            "handle": {"type": "string", "minLength": 1, "maxLength": 256}
        },
    },
}


class ProcessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExecArguments(ProcessModel):
    command: StrictStr = Field(min_length=1, max_length=65536)
    cwd: StrictStr | None = Field(default=None, min_length=1, max_length=4096)
    timeout_seconds: float | None = Field(
        default=None, gt=0, allow_inf_nan=False
    )


class ReadArguments(ProcessModel):
    handle: StrictStr = Field(min_length=1, max_length=256)
    cursor: ProcessCursorV1
    max_bytes: StrictInt = Field(ge=1, le=1048576)
    wait_ms: StrictInt = Field(default=0, ge=0, le=30000)


class InputArguments(ProcessModel):
    handle: StrictStr = Field(min_length=1, max_length=256)
    data: StrictStr = Field(max_length=1048576)
    eof: StrictBool = False


class StopArguments(ProcessModel):
    handle: StrictStr = Field(min_length=1, max_length=256)


PROCESS_ARGUMENT_MODELS = {
    "exec": ExecArguments,
    "read": ReadArguments,
    "input": InputArguments,
    "stop": StopArguments,
}


class ExecutorActionPermitV1(ProcessModel):
    schema_version: Literal["wuji.executor-action-permit.v1"]
    issuer: StrictStr = Field(min_length=1, max_length=1024)
    audience: StrictStr = Field(min_length=1, max_length=1024)
    tenant_id: StrictStr = Field(min_length=1, max_length=256)
    project_id: StrictStr = Field(min_length=1, max_length=256)
    task_id: StrictStr = Field(min_length=1, max_length=256)
    work_item_id: StrictStr = Field(min_length=1, max_length=256)
    agent_run_id: StrictStr = Field(min_length=1, max_length=256)
    execution_epoch: StrictStr = Field(pattern=r"^[1-9][0-9]*$")
    run_epoch: StrictStr = Field(pattern=r"^[1-9][0-9]*$")
    runtime_attempt: StrictStr = Field(pattern=r"^[1-9][0-9]*$")
    receiver_id: StrictStr = Field(min_length=1, max_length=256)
    executor_ref: StrictStr = Field(min_length=1, max_length=256)
    action: Literal[
        "exec",
        "read",
        "input",
        "stop",
        "query",
        "workspace_export",
        "workspace_import",
    ]
    tool_call_id: StrictStr = Field(min_length=1, max_length=256)
    tool_attempt_id: StrictStr = Field(min_length=1, max_length=256)
    parent_handle: StrictStr | None = Field(default=None, min_length=1, max_length=256)
    arguments_digest: StrictStr = Field(pattern=r"^[a-f0-9]{64}$")
    issued_at: datetime
    expires_at: datetime
    jti: StrictStr = Field(min_length=1, max_length=256)


class ExecutorShutdownPermitV1(ProcessModel):
    schema_version: Literal["wuji.executor-shutdown-permit.v1"]
    issuer: StrictStr = Field(min_length=1, max_length=1024)
    audience: StrictStr = Field(min_length=1, max_length=1024)
    tenant_id: StrictStr = Field(min_length=1, max_length=256)
    project_id: StrictStr = Field(min_length=1, max_length=256)
    task_id: StrictStr = Field(min_length=1, max_length=256)
    execution_epoch: StrictStr = Field(pattern=r"^[1-9][0-9]*$")
    runtime_attempt: StrictStr = Field(pattern=r"^[1-9][0-9]*$")
    receiver_id: StrictStr = Field(min_length=1, max_length=256)
    executor_ref: StrictStr = Field(min_length=1, max_length=256)
    action: Literal["shutdown"]
    reason: StrictStr = Field(min_length=1, max_length=1024)
    issued_at: datetime
    expires_at: datetime
    jti: StrictStr = Field(min_length=1, max_length=256)


def process_action(definition) -> str | None:
    kinds = list(getattr(definition, "allowed_target_kinds", ()) or ())
    if kinds != ["process"]:
        return None
    action = PROCESS_ACTION_BY_NAME.get(definition.name)
    if action is None:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    return action


def validate_process_arguments(action, arguments, runtime):
    process_limits = runtime.process_limits
    if process_limits is None:
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    try:
        parsed = PROCESS_ARGUMENT_MODELS[action].model_validate(arguments)
    except (KeyError, TypeError, ValueError) as error:
        raise DomainError("INVALID_SCHEMA", 422) from error
    value = parsed.model_dump(mode="json")
    if action == "exec":
        timeout = value["timeout_seconds"]
        if timeout is not None and timeout > runtime.total_timeout_seconds:
            raise DomainError("INVALID_SCHEMA", 422)
        if timeout is None:
            value["timeout_seconds"] = runtime.total_timeout_seconds
    elif action == "read":
        if (
            value["max_bytes"] > runtime.chunk_bytes
            or value["wait_ms"] > process_limits.max_read_wait_milliseconds
        ):
            raise DomainError("INVALID_SCHEMA", 422)
    elif action == "input" and len(value["data"].encode("utf-8")) > process_limits.max_input_bytes:
        raise DomainError("INVALID_SCHEMA", 422)
    return value


def process_arguments_digest(arguments: dict[str, Any]) -> str:
    return sha256(canonical_json_bytes(arguments)).hexdigest()


def parent_process(tx, *, handle, work_item_id):
    value = row(
        tx.connection.execute(
            """SELECT p.*,a.work_item_id,a.execution_epoch,a.runtime_attempt,
            a.receiver_id,a.environment_ref,t.tool_call_id
            FROM vnext.process_execution p
            JOIN vnext.tool_attempt x ON
              (x.tenant_id,x.project_id,x.task_id,x.tool_attempt_id,x.agent_run_id)=
              (p.tenant_id,p.project_id,p.task_id,p.tool_attempt_id,p.agent_run_id)
            JOIN vnext.agent_run a ON
              (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)=
              (p.tenant_id,p.project_id,p.task_id,p.agent_run_id)
            JOIN vnext.tool_call t ON
              (t.tenant_id,t.project_id,t.task_id,t.tool_call_id)=
              (x.tenant_id,x.project_id,x.task_id,x.tool_call_id)
            WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s
            AND p.tool_attempt_id=%s""",
            (*tx.owner, handle),
        )
    )
    if (
        value is None
        or value["work_item_id"] != work_item_id
        or int(value["runtime_attempt"]) != int(tx.task["runtime_attempt"])
    ):
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    return value


def empty_cursor():
    return ProcessCursorV1(stdout_offset=0, stderr_offset=0)


def validate_process_reply(value, *, handle):
    reply = ProcessReplyV1.model_validate(value)
    if reply.handle != handle:
        raise DomainError("INVALID_REFERENCE", 422)
    for chunk, offset in (
        (reply.stdout, reply.cursor.stdout_offset),
        (reply.stderr, reply.cursor.stderr_offset),
    ):
        if chunk is not None and (
            chunk.offset != offset
            or chunk.next_offset < chunk.offset
            or chunk.byte_length != chunk.next_offset - chunk.offset
        ):
            raise DomainError("INVALID_REFERENCE", 422)
        if chunk is not None:
            try:
                data = base64.b64decode(chunk.data_base64, validate=True)
            except (ValueError, binascii.Error) as error:
                raise DomainError("INVALID_REFERENCE", 422) from error
            if (
                len(data) != chunk.byte_length
                or sha256(data).hexdigest() != chunk.sha256.root
                or base64.b64encode(data).decode("ascii") != chunk.data_base64
                or (
                    chunk.text is not None
                    and data.decode("utf-8") != chunk.text.root
                )
            ):
                raise DomainError("INVALID_REFERENCE", 422)
    if (
        reply.next_cursor.stdout_offset
        != (reply.stdout.next_offset if reply.stdout else reply.cursor.stdout_offset)
        or reply.next_cursor.stderr_offset
        != (reply.stderr.next_offset if reply.stderr else reply.cursor.stderr_offset)
    ):
        raise DomainError("INVALID_REFERENCE", 422)
    return reply

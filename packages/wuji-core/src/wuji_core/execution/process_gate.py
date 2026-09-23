"""Platform-owned process action gate over the canonical Tool ledger."""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
from hashlib import sha256

from starlette.concurrency import run_in_threadpool

from wuji_core.admission.common import allocate_output, audit, digest
from wuji_core.admission.tools import (
    ToolPermit,
    _attempt,
    _call,
    _settlement,
)
from wuji_core.contracts.admission import ToolCallRequest, ToolCallReceipt
from wuji_core.contracts.generated import ProcessReplyV1
from wuji_core.execution.processes import process_action, validate_process_reply
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row


COMMAND_LOG_MEDIA_TYPE = "application/vnd.wuji.command-log+json"


class ProcessToolGate:
    def __init__(self, gate, *, refresh=None):
        self.gate = gate
        self.admission = gate.admission
        self.registry = gate.registry
        self.refresh = refresh
        self._watchers = set()

    def _assembly(self, access, ref):
        binding = self.registry.binding(access)
        with self.admission.uow.transaction(
            access, binding.identity.task_id
        ) as tx:
            definition = self.registry.tool(tx, ref)
            action = process_action(definition)
            registration = self.registry.executor(tx, definition.executor_ref)
            executor = self.gate.executors.get((*tx.owner, registration.ref))
            collector = self.gate.collector_accesses.get((*tx.owner, registration.ref))
            if (
                action is None
                or registration.protocol != "process.v1"
                or executor is None
                or not callable(getattr(executor, "invoke", None))
                or not callable(getattr(executor, "query_process", None))
                or collector is None
                or collector.principal.subject != registration.collector_subject
            ):
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            return definition, registration, executor, action

    async def invoke(self, access, request, *, name=None):
        if self.refresh is not None:
            await run_in_threadpool(self.refresh)
        request = ToolCallRequest.model_validate(request)
        definition, registration, executor, action = await run_in_threadpool(
            self._assembly, access, request.tool_definition_ref
        )
        if name is not None and definition.name != name:
            raise DomainError("INVALID_REFERENCE", 422)
        permit = await run_in_threadpool(self.admission.authorize, access, request)
        parent_handle = None if action == "exec" else permit.arguments["handle"]
        if permit.replay:
            reply = await run_in_threadpool(
                self._saved_reply, permit, action, parent_handle
            )
            if reply.state.value == "exited":
                await self._finalize_parent(permit, executor, reply)
            action_receipt = await run_in_threadpool(
                self.gate.ledger.tool_call, access, permit.tool_call_id
            )
            parent_receipt = await run_in_threadpool(
                self._parent_receipt, access, permit, action, parent_handle
            )
            return reply, action_receipt, parent_receipt
        try:
            await run_in_threadpool(
                self.admission.check_execution,
                permit,
                receiver_id=registration.receiver_id,
            )
            reply = await asyncio.wait_for(
                executor.invoke(
                    permit, action=action, parent_handle=parent_handle
                ),
                timeout=permit.runtime.idle_timeout_seconds,
            )
            reply = validate_process_reply(
                reply,
                handle=permit.tool_attempt_id if action == "exec" else parent_handle,
            )
            terminal = await run_in_threadpool(
                self._store_reply, permit, action, parent_handle, reply
            )
            if terminal:
                await self._finalize_parent(permit, executor, reply)
            elif action == "exec" and reply.state.value in {"running", "stopping"}:
                self._watch(permit, executor)
        except (Exception, asyncio.CancelledError):
            await asyncio.shield(
                run_in_threadpool(self._unknown, permit, action, parent_handle)
            )
            reply = self._unknown_reply(
                permit.tool_attempt_id if action == "exec" else parent_handle
            )
        action_receipt = await run_in_threadpool(
            self.gate.ledger.tool_call, access, permit.tool_call_id
        )
        parent_receipt = await run_in_threadpool(
            self._parent_receipt, access, permit, action, parent_handle
        )
        return reply, action_receipt, parent_receipt

    def _parent_receipt(self, access, permit, action, parent_handle):
        if action == "exec":
            receipt = self.gate.ledger.tool_call(
                access, permit.tool_call_id
            )
        elif parent_handle is not None:
            binding = self.registry.binding(access)
            with self.admission.uow.transaction(
                access, binding.identity.task_id
            ) as tx:
                parent = row(
                    tx.connection.execute(
                        """SELECT t.tool_call_id FROM vnext.tool_attempt a
                        JOIN vnext.tool_call t USING(tenant_id,project_id,task_id,tool_call_id)
                        WHERE a.tenant_id=%s AND a.project_id=%s AND a.task_id=%s
                        AND a.tool_attempt_id=%s""",
                        (*tx.owner, parent_handle),
                    )
                )
            if parent is None:
                return None
            receipt = self.gate.ledger.tool_call(access, parent["tool_call_id"])
        else:
            return None
        if (
            receipt.status.value == "complete"
            and receipt.evidence_receipt is not None
            and receipt.evidence_receipt.status.value == "accepted"
            and receipt.result_ref is not None
        ):
            return receipt
        return None

    @staticmethod
    def _unknown_reply(handle):
        return ProcessReplyV1.model_validate(
            {
                "schema_version": "wuji.process-reply.v1",
                "handle": handle,
                "state": "unknown",
                "assurance": "executor_reported",
                "started_at": None,
                "finished_at": None,
                "exit_code": None,
                "signal": None,
                "stdout": None,
                "stderr": None,
                "cursor": {"stdout_offset": 0, "stderr_offset": 0},
                "next_cursor": {"stdout_offset": 0, "stderr_offset": 0},
                "has_more": False,
                "output_completeness": "unknown",
                "reason_code": "OPERATION_UNKNOWN",
            }
        )

    def _saved_reply(self, permit, action, parent_handle):
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id
        ) as tx:
            attempt = _attempt(tx, permit.tool_attempt_id)
            if action == "exec":
                process = row(
                    tx.connection.execute(
                        "SELECT last_receipt_json FROM vnext.process_execution "
                        "WHERE tenant_id=%s AND project_id=%s AND task_id=%s "
                        "AND tool_attempt_id=%s",
                        (*tx.owner, permit.tool_attempt_id),
                    )
                )
                raw = None if process is None else process["last_receipt_json"]
            else:
                raw = attempt["receipt_json"]
            if not raw or raw == "{}":
                return self._unknown_reply(
                    permit.tool_attempt_id if action == "exec" else parent_handle
                )
            return validate_process_reply(
                strict_json_loads(raw),
                handle=permit.tool_attempt_id if action == "exec" else parent_handle,
            )

    def _store_reply(self, permit, action, parent_handle, reply):
        saved = reply.model_dump(mode="json")
        receipt_digest = digest(saved)
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id, capability="tool_settle"
        ) as tx:
            attempt = _attempt(tx, permit.tool_attempt_id)
            if attempt["process_action"] != action:
                raise DomainError("INVALID_REFERENCE", 422)
            if action == "exec":
                process_id = permit.tool_attempt_id
            else:
                process_id = attempt["parent_process_attempt_id"]
                if process_id != parent_handle:
                    raise DomainError("INVALID_REFERENCE", 422)
            previous = row(
                tx.connection.execute(
                    "SELECT * FROM vnext.process_execution WHERE tenant_id=%s "
                    "AND project_id=%s AND task_id=%s AND tool_attempt_id=%s FOR UPDATE",
                    (*tx.owner, process_id),
                )
            )
            if previous is None:
                raise DomainError("INVALID_REFERENCE", 422)
            if previous["state"] == "exited" and reply.state.value != "exited":
                return True
            tx.connection.execute(
                """UPDATE vnext.process_execution SET state=%s,
                started_at=COALESCE(started_at,%s),finished_at=%s,exit_code=%s,
                signal=%s,output_completeness=%s,last_receipt_json=%s,
                last_receipt_digest=%s,updated_at=clock_timestamp()
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                AND tool_attempt_id=%s""",
                (
                    reply.state.value,
                    reply.started_at,
                    reply.finished_at,
                    None if reply.exit_code is None else reply.exit_code.root,
                    None if reply.signal is None else reply.signal.root,
                    reply.output_completeness.value,
                    json_text(saved),
                    receipt_digest,
                    *tx.owner,
                    process_id,
                ),
            )
            tx.connection.execute(
                "UPDATE vnext.tool_attempt SET receipt_json=%s,started_at=COALESCE(started_at,%s) "
                "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                (json_text(saved), reply.started_at, *tx.owner, permit.tool_attempt_id),
            )
            terminal = reply.state.value == "exited"
            if action == "exec":
                status = "unknown" if reply.state.value == "unknown" else "running"
                tx.connection.execute(
                    "UPDATE vnext.tool_attempt SET status=%s WHERE tenant_id=%s "
                    "AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                    (status, *tx.owner, permit.tool_attempt_id),
                )
                tx.connection.execute(
                    "UPDATE vnext.tool_call SET status=%s WHERE tenant_id=%s "
                    "AND project_id=%s AND task_id=%s AND tool_call_id=%s",
                    (status, *tx.owner, permit.tool_call_id),
                )
            else:
                if reply.state.value == "unknown":
                    tx.connection.execute(
                        "UPDATE vnext.tool_attempt SET status='unknown' WHERE tenant_id=%s "
                        "AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                        (*tx.owner, permit.tool_attempt_id),
                    )
                    tx.connection.execute(
                        "UPDATE vnext.tool_call SET status='unknown' WHERE tenant_id=%s "
                        "AND project_id=%s AND task_id=%s AND tool_call_id=%s",
                        (*tx.owner, permit.tool_call_id),
                    )
                    _settlement(tx, permit.identity.agent_run_id)
                    return terminal
                result = ToolCallReceipt.model_validate(
                    {
                        "tool_call_id": permit.tool_call_id,
                        "operation_id": permit.tool_call_id,
                        "tool_attempt_id": permit.tool_attempt_id,
                        "status": "complete",
                        "evidence_receipt": None,
                        "result_ref": None,
                        "reason_code": None,
                    }
                )
                tx.connection.execute(
                    "UPDATE vnext.tool_attempt SET status='complete',result_receipt_json=%s "
                    "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                    (
                        json_text(result.model_dump(mode="json")),
                        *tx.owner,
                        permit.tool_attempt_id,
                    ),
                )
                tx.connection.execute(
                    "UPDATE vnext.tool_call SET status='complete' WHERE tenant_id=%s "
                    "AND project_id=%s AND task_id=%s AND tool_call_id=%s",
                    (*tx.owner, permit.tool_call_id),
                )
                _settlement(tx, permit.identity.agent_run_id)
            audit(
                tx,
                "process.action_receipt",
                {
                    "tool_attempt_id": permit.tool_attempt_id,
                    "process_action": action,
                    "state": reply.state.value,
                },
            )
            return terminal

    def _watch(self, permit, executor):
        task = asyncio.create_task(self._watch_parent(permit, executor))
        self._watchers.add(task)
        task.add_done_callback(self._watchers.discard)

    async def _watch_parent(self, permit, executor):
        cursor = {"stdout_offset": 0, "stderr_offset": 0}
        try:
            while True:
                await asyncio.sleep(
                    min(1.0, max(0.05, permit.runtime.idle_timeout_seconds / 4))
                )
                reply = await asyncio.wait_for(
                    executor.query_process(permit, cursor=cursor, max_bytes=1),
                    timeout=permit.runtime.idle_timeout_seconds,
                )
                await run_in_threadpool(
                    self._store_process_observation, permit, reply
                )
                if reply.state.value == "exited":
                    await self._finalize_parent(permit, executor, reply)
                    return
                if reply.state.value == "unknown":
                    await run_in_threadpool(
                        self._unknown, permit, "exec", None
                    )
                    return
        except Exception:
            # The durable scanner resumes this parent after transport recovery or
            # process restart. A watcher never invents a terminal state.
            return

    def _store_process_observation(self, permit, reply):
        saved = reply.model_dump(mode="json")
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id, capability="tool_settle"
        ) as tx:
            tx.connection.execute(
                """UPDATE vnext.process_execution SET state=%s,
                started_at=COALESCE(started_at,%s),finished_at=%s,exit_code=%s,
                signal=%s,output_completeness=%s,last_receipt_json=%s,
                last_receipt_digest=%s,updated_at=clock_timestamp()
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                AND tool_attempt_id=%s AND finalization_state<>'sealed'
                AND (state<>'exited' OR %s='exited')""",
                (
                    reply.state.value,
                    reply.started_at,
                    reply.finished_at,
                    None if reply.exit_code is None else reply.exit_code.root,
                    None if reply.signal is None else reply.signal.root,
                    reply.output_completeness.value,
                    json_text(saved),
                    digest(saved),
                    *tx.owner,
                    permit.tool_attempt_id,
                    reply.state.value,
                ),
            )

    async def reconcile_registered(self, *, limit=32):
        """Recover open parents from durable rows after a Gate restart."""

        if type(limit) is not int or not 1 <= limit <= 256:
            raise ValueError("bounded process reconciliation limit required")
        if self.refresh is not None:
            await run_in_threadpool(self.refresh)
        candidates = []
        for key, collector in tuple(self.gate.collector_accesses.items()):
            task_id = key[2]
            with self.admission.uow.transaction(
                collector, task_id, capability="tool_settle"
            ) as tx:
                values = tx.connection.execute(
                    """SELECT a.permit_json,t.tool_definition_version
                    FROM vnext.process_execution p
                    JOIN vnext.tool_attempt a USING(tenant_id,project_id,task_id,tool_attempt_id)
                    JOIN vnext.tool_call t USING(tenant_id,project_id,task_id,tool_call_id)
                    WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s
                    AND p.finalization_state<>'sealed'
                    ORDER BY p.updated_at LIMIT %s""",
                    (*tx.owner, limit - len(candidates)),
                ).fetchall()
            for permit_json, definition_ref in values:
                permit = ToolPermit.restore(
                    strict_json_loads(permit_json), request_id="process-reconcile"
                )
                try:
                    _definition, _registration, executor, _action = self._assembly(
                        permit.access, definition_ref
                    )
                except DomainError:
                    continue
                candidates.append((permit, executor))
                if len(candidates) >= limit:
                    break
            if len(candidates) >= limit:
                break
        for permit, executor in candidates:
            try:
                reply = await asyncio.wait_for(
                    executor.query_process(
                        permit,
                        cursor={"stdout_offset": 0, "stderr_offset": 0},
                        max_bytes=1,
                    ),
                    timeout=permit.runtime.idle_timeout_seconds,
                )
                await run_in_threadpool(
                    self._store_process_observation, permit, reply
                )
                if reply.state.value == "exited":
                    await self._finalize_parent(permit, executor, reply)
            except Exception:
                continue
        return len(candidates)

    def _cleanup_context(
        self, access, task_id, execution_epoch, runtime_attempt
    ):
        with self.admission.uow.transaction(
            access, task_id, capability="control"
        ) as tx:
            task = tx.task
            receiver = row(tx.connection.execute(
                "SELECT * FROM vnext.scheduler_receiver WHERE tenant_id=%s "
                "AND project_id=%s AND task_id=%s AND runtime_attempt=%s",
                (*tx.owner, runtime_attempt),
            ))
            if (
                receiver is None
                or int(task["runtime_attempt"]) != int(runtime_attempt)
                or int(execution_epoch) > int(task["execution_epoch"])
            ):
                raise DomainError("STALE_EXECUTION", 409)
            registrations = []
            for key in self.gate.executors:
                if key[:3] != tx.owner:
                    continue
                registration = self.registry.executor(tx, key[3])
                if (
                    registration.protocol == "process.v1"
                    and receiver["receiver_id"] == registration.receiver_id
                    and receiver["environment_ref"] == registration.environment_ref
                ):
                    registrations.append(key)
            if len(registrations) != 1:
                raise DomainError("CAPABILITY_UNAVAILABLE", 503)
            key = registrations[0]
        executor = self.gate.executors.get(key)
        collector = self.gate.collector_accesses.get(key)
        if (
            executor is None
            or collector is None
            or not all(
                callable(getattr(executor, name, None))
                for name in ("drain", "query_process", "shutdown")
            )
        ):
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        return key, executor, collector

    def _cleanup_candidates(
        self, collector, task_id, execution_epoch, runtime_attempt, *, limit
    ):
        with self.admission.uow.transaction(
            collector, task_id, capability="tool_settle"
        ) as tx:
            values = tx.connection.execute(
                """SELECT a.permit_json FROM vnext.process_execution p
                JOIN vnext.tool_attempt a
                  USING(tenant_id,project_id,task_id,tool_attempt_id)
                JOIN vnext.agent_run r
                  ON (r.tenant_id,r.project_id,r.task_id,r.agent_run_id)=
                     (p.tenant_id,p.project_id,p.task_id,p.agent_run_id)
                WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s
                  AND r.execution_epoch=%s AND r.runtime_attempt=%s
                  AND p.finalization_state<>'sealed'
                ORDER BY p.updated_at LIMIT %s""",
                (*tx.owner, execution_epoch, runtime_attempt, limit),
            ).fetchall()
        result = []
        for (permit_json,) in values:
            permit = ToolPermit.restore(
                strict_json_loads(permit_json), request_id="process-cleanup"
            )
            if (
                permit.identity.execution_epoch.root == str(execution_epoch)
                and permit.identity.runtime_attempt.root == str(runtime_attempt)
            ):
                result.append(permit)
        return result

    def _cleanup_counts(
        self, collector, task_id, execution_epoch, runtime_attempt
    ):
        with self.admission.uow.transaction(
            collector, task_id, capability="tool_settle"
        ) as tx:
            return tx.connection.execute(
                """SELECT count(*),count(*) FILTER (
                    WHERE p.finalization_state='sealed')
                FROM vnext.process_execution p JOIN vnext.agent_run r
                  ON (r.tenant_id,r.project_id,r.task_id,r.agent_run_id)=
                     (p.tenant_id,p.project_id,p.task_id,p.agent_run_id)
                WHERE p.tenant_id=%s AND p.project_id=%s AND p.task_id=%s
                  AND r.execution_epoch=%s AND r.runtime_attempt=%s""",
                (*tx.owner, execution_epoch, runtime_attempt),
            ).fetchone()

    async def cleanup_task(
        self,
        access,
        *,
        task_id,
        execution_epoch,
        runtime_attempt,
        reason,
        limit=64,
        timeout_seconds=60.0,
    ):
        """Drain one revoked Task attempt, seal known logs, then stop Kali PID1."""

        if (
            not isinstance(task_id, str)
            or not task_id
            or not isinstance(reason, str)
            or not 1 <= len(reason) <= 1024
            or not str(execution_epoch).isdecimal()
            or int(execution_epoch) < 1
            or not str(runtime_attempt).isdecimal()
            or int(runtime_attempt) < 1
            or type(limit) is not int
            or not 1 <= limit <= 256
            or isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds <= 60
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        if self.refresh is not None:
            await run_in_threadpool(self.refresh)
        _key, executor, collector = await run_in_threadpool(
            self._cleanup_context,
            access,
            task_id,
            execution_epoch,
            runtime_attempt,
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + float(timeout_seconds)
        try:
            drain = await asyncio.wait_for(
                executor.drain(
                    execution_epoch=execution_epoch,
                    runtime_attempt=runtime_attempt,
                    reason=reason,
                ),
                timeout=max(0.001, deadline - loop.time()),
            )
        except Exception:
            drain = {"status": "unknown"}
        # Each pass removes successfully sealed parents from the next query.
        # Four bounded pages cover the published maximum active process count.
        for _ in range(4):
            if loop.time() >= deadline:
                break
            candidates = await run_in_threadpool(
                self._cleanup_candidates,
                collector,
                task_id,
                execution_epoch,
                runtime_attempt,
                limit=limit,
            )
            if not candidates:
                break
            progress = False
            for permit in candidates:
                if loop.time() >= deadline:
                    break
                try:
                    reply = await asyncio.wait_for(
                        executor.query_process(
                            permit,
                            cursor={"stdout_offset": 0, "stderr_offset": 0},
                            max_bytes=1,
                        ),
                        timeout=min(
                            permit.runtime.idle_timeout_seconds,
                            max(0.001, deadline - loop.time()),
                        ),
                    )
                    await run_in_threadpool(
                        self._store_process_observation, permit, reply
                    )
                    if reply.state.value != "exited":
                        continue
                    progress = await self._finalize_parent(
                        permit, executor, reply, deadline=deadline
                    ) or progress
                except Exception:
                    continue
            if not progress:
                break
        total, sealed = await run_in_threadpool(
            self._cleanup_counts,
            collector,
            task_id,
            execution_epoch,
            runtime_attempt,
        )
        shutdown = await executor.shutdown(
            execution_epoch=execution_epoch,
            runtime_attempt=runtime_attempt,
            reason=reason,
        )
        return {
            "schema_version": "wuji.process-cleanup.v1",
            "status": "accepted",
            "task_id": task_id,
            "execution_epoch": str(execution_epoch),
            "runtime_attempt": str(runtime_attempt),
            "drain_status": drain["status"],
            "archive_status": "complete" if total == sealed else "incomplete",
            "archived_processes": sealed,
            "unresolved_processes": total - sealed,
            "shutdown_status": shutdown["status"],
            "container_exit_confirmed": False,
        }

    def _unknown(self, permit, action, parent_handle):
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id, capability="tool_settle"
        ) as tx:
            attempt = _attempt(tx, permit.tool_attempt_id)
            if attempt["status"] in {"complete", "failed", "cancelled"}:
                return
            tx.connection.execute(
                "UPDATE vnext.tool_attempt SET status='unknown' WHERE tenant_id=%s "
                "AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                (*tx.owner, permit.tool_attempt_id),
            )
            tx.connection.execute(
                "UPDATE vnext.tool_call SET status='unknown' WHERE tenant_id=%s "
                "AND project_id=%s AND task_id=%s AND tool_call_id=%s",
                (*tx.owner, permit.tool_call_id),
            )
            if action == "exec":
                tx.connection.execute(
                    "UPDATE vnext.process_execution SET state='unknown',updated_at=clock_timestamp() "
                    "WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                    (*tx.owner, permit.tool_attempt_id),
                )
                for resource in permit.resource_keys:
                    tx.connection.execute(
                        "UPDATE vnext.resource_reservation SET state='unknown' "
                        "WHERE tenant_id=%s AND project_id=%s AND task_id=%s "
                        "AND agent_run_id=%s AND resource_key=%s",
                        (*tx.owner, permit.identity.agent_run_id, resource),
                    )
            _settlement(tx, permit.identity.agent_run_id)

    async def _finalize_parent(
        self, action_permit, executor, terminal_reply, *, deadline=None
    ):
        parent = await run_in_threadpool(
            self._parent_permit, action_permit, terminal_reply.handle
        )
        if terminal_reply.state.value != "exited":
            raise DomainError("INVALID_REFERENCE", 422)
        await run_in_threadpool(
            self._store_process_observation, parent, terminal_reply
        )
        claimed = await run_in_threadpool(self._claim_finalization, parent)
        if not claimed:
            return False
        stdout = bytearray()
        stderr = bytearray()
        cursor = {"stdout_offset": 0, "stderr_offset": 0}
        limit = executor.max_output_bytes
        try:
            while True:
                timeout = parent.runtime.idle_timeout_seconds
                if deadline is not None:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        raise TimeoutError("process cleanup deadline expired")
                    timeout = min(timeout, remaining)
                reply = await asyncio.wait_for(
                    executor.query_process(
                        parent, cursor=cursor, max_bytes=parent.runtime.chunk_bytes
                    ),
                    timeout=timeout,
                )
                for name, target in (("stdout", stdout), ("stderr", stderr)):
                    chunk = getattr(reply, name)
                    if chunk is not None:
                        target.extend(
                            base64.b64decode(chunk.data_base64, validate=True)
                        )
                cursor = reply.next_cursor.model_dump(mode="json")
                if len(stdout) + len(stderr) > limit:
                    raise DomainError("LIMIT_BLOCKED", 429)
                if not reply.has_more:
                    terminal_reply = reply
                    break
            document, completeness = self._command_log(
                parent, terminal_reply, bytes(stdout), bytes(stderr)
            )
            await run_in_threadpool(
                self._store_terminal, parent, terminal_reply, document, completeness
            )
            await run_in_threadpool(self.gate._capture, parent)
            receipt = await run_in_threadpool(
                self.gate.ledger.tool_call, parent.access, parent.tool_call_id
            )
            if (
                receipt.status.value != "complete"
                or receipt.evidence_receipt is None
                or receipt.evidence_receipt.status.value != "accepted"
                or receipt.result_ref is None
            ):
                raise DomainError("OPERATION_UNKNOWN", 409)
            await run_in_threadpool(self._finish_finalization, parent, "sealed")
            return True
        except Exception:
            await run_in_threadpool(self._finish_finalization, parent, "unknown")
            raise

    def _claim_finalization(self, permit):
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id, capability="tool_settle"
        ) as tx:
            changed = tx.connection.execute(
                """UPDATE vnext.process_execution SET finalization_state='draining',
                updated_at=clock_timestamp() WHERE tenant_id=%s AND project_id=%s
                AND task_id=%s AND tool_attempt_id=%s AND (
                  finalization_state IN ('pending','unknown') OR
                  (finalization_state='draining' AND updated_at<clock_timestamp()-%s*interval '1 second')
                ) RETURNING tool_attempt_id""",
                (
                    *tx.owner,
                    permit.tool_attempt_id,
                    permit.runtime.idle_timeout_seconds,
                ),
            ).fetchone()
            return changed is not None

    def _finish_finalization(self, permit, state):
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id, capability="tool_settle"
        ) as tx:
            tx.connection.execute(
                "UPDATE vnext.process_execution SET finalization_state=%s,"
                "updated_at=clock_timestamp() WHERE tenant_id=%s AND project_id=%s "
                "AND task_id=%s AND tool_attempt_id=%s",
                (state, *tx.owner, permit.tool_attempt_id),
            )

    def _parent_permit(self, action_permit, handle):
        with self.admission.uow.transaction(
            action_permit.access, action_permit.identity.task_id
        ) as tx:
            process = row(
                tx.connection.execute(
                    "SELECT agent_run_id FROM vnext.process_execution WHERE tenant_id=%s "
                    "AND project_id=%s AND task_id=%s AND tool_attempt_id=%s",
                    (*tx.owner, handle),
                )
            )
            attempt = _attempt(tx, handle)
            if (
                process is None
                or process["agent_run_id"] != action_permit.identity.agent_run_id
                or attempt["process_action"] != "exec"
            ):
                raise DomainError("INVALID_REFERENCE", 422)
            return ToolPermit.restore(
                strict_json_loads(attempt["permit_json"]),
                request_id=action_permit.access.request_id,
            )

    @staticmethod
    def _command_log(permit, reply, stdout, stderr):
        maximum = min(
            permit.runtime.buffer_bytes,
            permit.runtime.limits.max_single_output_bytes,
        )
        command = permit.arguments["command"]

        def encode(kept, include_command):
            out = stdout[:kept]
            err = stderr[: max(0, kept - len(out))]
            return canonical_json_bytes(
                {
                    "schema_version": "wuji.command-log.v1",
                    "handle": permit.tool_attempt_id,
                    "command": command if include_command else None,
                    "command_sha256": sha256(command.encode()).hexdigest(),
                    "cwd": permit.arguments.get("cwd"),
                    "started_at": None if reply.started_at is None else reply.started_at.isoformat(),
                    "finished_at": None if reply.finished_at is None else reply.finished_at.isoformat(),
                    "exit_code": None if reply.exit_code is None else reply.exit_code.root,
                    "signal": None if reply.signal is None else reply.signal.root,
                    "assurance": "executor_reported",
                    "stdout_bytes": len(stdout),
                    "stdout_sha256": sha256(stdout).hexdigest(),
                    "stdout_base64": base64.b64encode(out).decode("ascii"),
                    "stderr_bytes": len(stderr),
                    "stderr_sha256": sha256(stderr).hexdigest(),
                    "stderr_base64": base64.b64encode(err).decode("ascii"),
                    "truncated": len(out) != len(stdout) or len(err) != len(stderr),
                }
            )

        full = encode(len(stdout) + len(stderr), True)
        if len(full) <= maximum and reply.output_completeness.value == "complete":
            return full, "complete"
        low, high, fitted = 0, len(stdout) + len(stderr), encode(0, False)
        if len(fitted) > maximum:
            raise DomainError("LIMIT_BLOCKED", 429)
        while low <= high:
            middle = (low + high) // 2
            candidate = encode(middle, False)
            if len(candidate) <= maximum:
                fitted, low = candidate, middle + 1
            else:
                high = middle - 1
        return fitted, "partial"

    def _store_terminal(self, permit, reply, document, completeness):
        with self.admission.uow.transaction(
            permit.access, permit.identity.task_id, capability="tool_settle"
        ) as tx:
            attempt = _attempt(tx, permit.tool_attempt_id)
            if attempt["status"] == "complete":
                return
            if attempt["status"] == "evidence_pending":
                return
            if not allocate_output(
                tx,
                len(document),
                already=attempt["output_bytes"],
                runtime=permit.runtime,
            ):
                raise DomainError("LIMIT_BLOCKED", 429)
            saved = reply.model_dump(mode="json")
            tx.connection.execute(
                """UPDATE vnext.tool_attempt SET status='evidence_pending',
                started_at=COALESCE(started_at,%s),receipt_json=%s,output=%s,
                output_media_type=%s,output_completeness=%s,
                received_bytes=received_bytes+%s,retained_bytes=retained_bytes+%s,
                output_bytes=output_bytes+%s,received_digest=%s
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                AND tool_attempt_id=%s""",
                (
                    reply.started_at,
                    json_text(saved),
                    document,
                    COMMAND_LOG_MEDIA_TYPE,
                    completeness,
                    len(document),
                    len(document),
                    len(document),
                    sha256(document).hexdigest(),
                    *tx.owner,
                    permit.tool_attempt_id,
                ),
            )
            tx.connection.execute(
                "UPDATE vnext.tool_call SET status='evidence_pending' WHERE tenant_id=%s "
                "AND project_id=%s AND task_id=%s AND tool_call_id=%s",
                (*tx.owner, permit.tool_call_id),
            )
            tx.connection.execute(
                "UPDATE vnext.process_execution SET stdout_bytes=%s,stderr_bytes=%s,"
                "output_completeness=%s WHERE tenant_id=%s AND project_id=%s "
                "AND task_id=%s AND tool_attempt_id=%s",
                (
                    strict_json_loads(document)["stdout_bytes"],
                    strict_json_loads(document)["stderr_bytes"],
                    completeness,
                    *tx.owner,
                    permit.tool_attempt_id,
                ),
            )
            self.gate._release(tx, permit)

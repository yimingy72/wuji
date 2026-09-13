"""Private P09 -> durable receiver transport; never regenerate an operation.

The local journal records send uncertainty, not a second execution authority.
PostgreSQL transactions finish before network I/O. Credentials stay in a
restricted bootstrap store and never enter Outbox bodies or process receipts.
"""

from datetime import datetime, timedelta, timezone
import base64
from ipaddress import ip_address
from pathlib import Path
import os
import sqlite3
import ssl
from threading import Lock, get_ident
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

from wuji_core.contracts.envelopes import WorkerAssignment
from wuji_core.execution.dependencies import dependencies_satisfied, intent_current
from wuji_core.execution.reconcile import (
    ObservationUnavailable, ObservedExecution, read_registered_run, validate_receipt,
)
from wuji_core.execution.states import task_can_run
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, row


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ObservationUnavailable("RECEIVER_REDIRECT_REJECTED")


class SupervisorHttpTransport:
    """Fixed deployment URL and service credentials; no proxy/redirect/retry."""

    def __init__(self, base_url, *, authorization, timeout=10, max_response_bytes=65536,
                 audit=None, ssl_context=None):
        target = urlsplit(base_url)
        local = target.hostname == "localhost"
        try:
            local = local or ip_address(target.hostname).is_loopback
        except ValueError:
            pass
        if (target.scheme not in {"http", "https"} or not target.hostname
                or target.username or target.password or target.query or target.fragment
                or target.path not in {"", "/"} or (target.scheme == "http" and not local)):
            raise ValueError("authenticated HTTPS or loopback receiver origin required")
        if (not callable(authorization) or (audit is not None and not callable(audit))
                or not 0 < timeout <= 60 or not 0 < max_response_bytes <= 1048576):
            raise ValueError("bounded authenticated transport required")
        self.base_url = base_url.rstrip("/")
        self.authorization = authorization
        self.timeout, self.max_response_bytes = timeout, max_response_bytes
        if ssl_context is not None and (
            not isinstance(ssl_context, ssl.SSLContext)
            or ssl_context.verify_mode != ssl.CERT_REQUIRED
            or not ssl_context.check_hostname
        ):
            raise ValueError("verified TLS context required")
        self.opener = build_opener(ProxyHandler({}), _NoRedirect(), HTTPSHandler(context=ssl_context))
        self.audit = audit

    def _audit(self, *, method, url, encoded, status=None, headers=None, data=b"",
               error=None):
        if self.audit is None:
            return
        record = {
            "request": {
                "method": method,
                "url": url,
                "headers": {
                    "Authorization": "Bearer [REDACTED RECEIVER CREDENTIAL]",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                "body_base64": base64.b64encode(encoded or b"").decode("ascii"),
            },
            "response": {
                "status_code": status,
                "headers": dict(headers or {}),
                "body_base64": base64.b64encode(data).decode("ascii"),
                "error": error,
            },
        }
        try:
            self.audit(record)
        except Exception:
            # Observability cannot replace or alter the transport result.
            pass

    def _request(self, method, operation_id, body=None, *, control=False):
        token = self.authorization()
        if not isinstance(token, str) or not token or '\r' in token or '\n' in token:
            raise DomainError("UNAUTHENTICATED", 401)
        url = self.base_url + "/operations/" + quote(operation_id, safe="") + ("/control" if control else "")
        encoded = None if body is None else canonical_json_bytes(body)
        request = Request(url, data=encoded, method=method, headers={
            "Authorization": "Bearer " + token, "Content-Type": "application/json",
            "Accept": "application/json",
        })
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                data = response.read(self.max_response_bytes + 1)
                if len(data) > self.max_response_bytes:
                    raise ObservationUnavailable("RECEIVER_RESPONSE_TOO_LARGE")
                self._audit(
                    method=method, url=url, encoded=encoded,
                    status=response.status, headers=response.headers, data=data,
                )
                return strict_json_loads(data)
        except HTTPError as error:
            data = error.read(self.max_response_bytes + 1)
            self._audit(
                method=method, url=url, encoded=encoded,
                status=error.code, headers=error.headers, data=data,
            )
            try:
                code = strict_json_loads(data).get("code") if len(data) <= self.max_response_bytes else None
            except ValueError:
                code = None
            finally:
                error.close()
            if method == "GET" and error.code == 404 and code == "OPERATION_NOT_FOUND":
                return None
            if error.code in {401, 403, 409, 422}:
                # Whitelist codes; do not expose arbitrary upstream bodies.
                allowed = {"UNAUTHENTICATED", "STALE_EXECUTION", "INPUT_DIGEST_CONFLICT",
                           "UNREGISTERED_LAUNCH_PROFILE", "INVALID_REFERENCE"}
                raise DomainError(code if code in allowed else "STALE_EXECUTION", error.code) from None
            raise ObservationUnavailable() from None
        except (URLError, TimeoutError, OSError, ValueError) as error:
            self._audit(
                method=method, url=url, encoded=encoded,
                error=type(error).__name__,
            )
            raise ObservationUnavailable() from None

    def query(self, operation_id):
        return self._request("GET", operation_id)

    def start(self, assignment, *, profile_id):
        assignment = WorkerAssignment.model_validate(assignment)
        return self._request("PUT", assignment.operation_id, {
            "assignment": assignment.model_dump(mode="json"), "profile_id": profile_id,
        })

    def control(self, operation_id, *, control_operation_id, action, identity):
        return self._request("POST", operation_id, {
            "control_operation_id": control_operation_id, "action": action,
            "identity": identity.model_dump(mode="json"),
        }, control=True)


class DispatchJournal:
    """A durable sent marker survives sender crashes; no lease can erase it."""

    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink():
            raise ValueError("journal must not be a symlink")
        self.path = path
        self.connection = None
        self.owner_thread = None
        self.owner_lock = Lock()
        self.closed = False

    def _connection(self):
        current = get_ident()
        with self.owner_lock:
            if self.closed:
                raise RuntimeError("dispatch journal is closed")
            if self.owner_thread is None:
                self.owner_thread = current
            elif self.owner_thread != current:
                raise RuntimeError("dispatch journal belongs to another thread")
            if self.connection is None:
                if self.path.is_symlink():
                    self.owner_thread = None
                    raise ValueError("journal must not be a symlink")
                connection = None
                try:
                    connection = sqlite3.connect(
                        self.path, timeout=5, isolation_level=None
                    )
                    os.chmod(self.path, 0o600)
                    connection.execute("PRAGMA journal_mode=DELETE")
                    connection.execute("PRAGMA synchronous=FULL")
                    connection.execute("""CREATE TABLE IF NOT EXISTS delivery(
                        operation_key TEXT PRIMARY KEY, assignment_digest TEXT NOT NULL,
                        attempted INTEGER NOT NULL DEFAULT 0 CHECK(attempted IN(0,1)),
                        receipt_json TEXT)""")
                    self.connection = connection
                except BaseException:
                    if connection is not None:
                        connection.close()
                    self.owner_thread = None
                    raise
            return self.connection

    @staticmethod
    def key(run):
        return canonical_json_bytes({"identity": run.identity.model_dump(mode="json"),
                                     "operation_id": run.start_operation_id}).decode()

    def reserve_send(self, run):
        key = self.key(run)
        connection = self._connection()
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("INSERT OR IGNORE INTO delivery VALUES(?,?,0,NULL)", (key, run.assignment_digest))
            record = connection.execute("SELECT assignment_digest,attempted FROM delivery WHERE operation_key=?", (key,)).fetchone()
            if record[0] != run.assignment_digest:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            reserved = record[1] == 0
            if reserved:
                connection.execute("UPDATE delivery SET attempted=1 WHERE operation_key=?", (key,))
            connection.execute("COMMIT")
            return reserved
        except BaseException:
            connection.execute("ROLLBACK")
            raise

    def attempted(self, run):
        record = self._connection().execute("SELECT assignment_digest,attempted FROM delivery WHERE operation_key=?", (self.key(run),)).fetchone()
        if record and record[0] != run.assignment_digest:
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        return bool(record and record[1])

    def save(self, run, receipt):
        # Monotonic sent marker, including observations first found by query.
        self.reserve_send(run)
        self._connection().execute("UPDATE delivery SET receipt_json=? WHERE operation_key=?",
                                   (canonical_json_bytes(receipt).decode(), self.key(run)))

    def close(self):
        current = get_ident()
        with self.owner_lock:
            if self.closed:
                return
            if self.owner_thread is not None and self.owner_thread != current:
                raise RuntimeError("dispatch journal must close on its owner thread")
            if self.connection is not None:
                self.connection.close()
            self.connection = None
            self.closed = True


class DispatchOutbox:
    def __init__(self, uow, *, access, transport, journal_path):
        self.uow, self.access = uow, access
        self.transport = transport
        self.journal = DispatchJournal(journal_path)

    def _registered(self, task_id, operation_id):
        with self.uow.transaction(self.access, task_id, capability="observe") as tx:
            return read_registered_run(tx, operation_id)

    def inspect(self, task_id, operation_id):
        run, _assignment, _ref = self._registered(task_id, operation_id)
        try:
            receipt = self.transport.query(operation_id)
        except ObservationUnavailable:
            return ObservedExecution(run, "unknown", None, "receiver_response_unknown")
        if receipt is None:
            return ObservedExecution(run, "unknown", None, "receiver_record_absent")
        observed = validate_receipt(run, receipt)
        self.journal.save(run, receipt)
        return observed

    def deliver(self, task_id, operation_id):
        run, assignment, credential_ref = self._registered(task_id, operation_id)
        try:
            receipt = self.transport.query(operation_id)
        except ObservationUnavailable:
            return ObservedExecution(run, "unknown", None, "receiver_response_unknown")
        if receipt is not None:
            observed = validate_receipt(run, receipt)
            self.journal.save(run, receipt)
            return observed
        if self.journal.attempted(run):
            return ObservedExecution(run, "unknown", None, "previous_delivery_unresolved_no_replay")
        # read_registered_run derived this exact harness ref from the immutable
        # TaskDefinition and checked the complete Assignment profile tuple.
        profile = run.harness_profile_id
        # Re-read the same immutable operation before the attempted-send fence.
        # Node's bootstrap callback is the only Run credential consumer.
        with self.uow.transaction(self.access, task_id, capability="observe") as tx:
            fresh_run, fresh_assignment, fresh_ref = read_registered_run(tx, operation_id)
            if fresh_run != run or fresh_assignment != assignment or fresh_ref != credential_ref:
                raise DomainError("STALE_EXECUTION", 409)
        if not self.journal.reserve_send(run):
            return self.inspect(task_id, operation_id)
        try:
            receipt = self.transport.start(assignment, profile_id=profile)
        except ObservationUnavailable:
            # No new operation, no second PUT, even after a receiver 404.
            return self.inspect(task_id, operation_id)
        observed = validate_receipt(run, receipt)
        self.journal.save(run, receipt)
        return observed

    def close(self):
        self.journal.close()


class ReceiverAuthorizer:
    """Production grant producer from actual registered P09/P05 records.

    A private authenticated adapter supplies AccessContext; never obtain it
    from Worker JSON. This producer is intentionally not installed in a public
    HTTP router here. Main owns the actual host/control transport assembly.
    """

    def __init__(self, uow):
        self.uow = uow

    def authorize(self, *, access, action, assignment, assignment_digest, receiver, control_operation_id=None):
        if action not in {"query", "start", "stop", "stop_after_current"}:
            raise DomainError("INVALID_REFERENCE", 422)
        assignment = WorkerAssignment.model_validate(assignment)
        with self.uow.transaction(access, assignment.identity.task_id, capability="observe") as tx:
            run, stored, _ref = read_registered_run(tx, assignment.operation_id)
            if stored != assignment or run.assignment_digest != assignment_digest:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            expected = {"receiver_id": run.identity.receiver_id,
                        "runtime_attempt": run.identity.runtime_attempt.root,
                        "environment_ref": run.environment_ref, "pod_uid": run.pod_uid}
            if receiver != expected:
                raise DomainError("STALE_EXECUTION", 409)
            record = row(tx.connection.execute("""SELECT * FROM vnext.agent_run
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s""",
                (*tx.owner, run.identity.agent_run_id)))
            work = row(tx.connection.execute("""SELECT * FROM vnext.work_item
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s FOR UPDATE""",
                (*tx.owner, run.identity.work_item_id)))
            registered_receiver = row(tx.connection.execute("""SELECT * FROM vnext.scheduler_receiver
                WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND runtime_attempt=%s
                AND receiver_id=%s AND receiver_subject=%s""",
                (*tx.owner, run.identity.runtime_attempt.root, run.identity.receiver_id, access.principal.subject)))
            registration = {
                "receiver_id": registered_receiver["receiver_id"] if registered_receiver else None,
                "runtime_attempt": (
                    str(registered_receiver["runtime_attempt"])
                    if registered_receiver else None
                ),
                "receiver_subject": (
                    registered_receiver["receiver_subject"]
                    if registered_receiver else None
                ),
                "environment_ref": (
                    registered_receiver["environment_ref"]
                    if registered_receiver else None
                ),
                "pod_uid": registered_receiver["pod_uid"] if registered_receiver else None,
            }
            if (
                registration
                != {
                    **expected,
                    "receiver_subject": access.principal.subject,
                }
                or (action == "start" and not registered_receiver["enabled"])
            ):
                raise DomainError("STALE_EXECUTION", 409)
            allowed = False
            if action == "start":
                held = tx.connection.execute("""SELECT 1 FROM vnext.work_suspension
                    WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s LIMIT 1""",
                    (*tx.owner, run.identity.work_item_id)).fetchone()
                if (not task_can_run(tx.task) or not record["execution_allowed"] or record["stop_kind"] is not None
                        or record["process_state"] not in {"registered", "starting"}
                        or work["state"] != "leased" or work["desired_state"] != "run" or held
                        or work["current_run_id"] != record["agent_run_id"]
                        or work["run_epoch"] != record["run_epoch"]
                        or tx.task["execution_epoch"] != record["execution_epoch"]
                        or tx.task["runtime_attempt"] != record["runtime_attempt"]
                        or not intent_current(tx, work) or not dependencies_satisfied(tx, work["work_item_id"])):
                    raise DomainError("STALE_EXECUTION", 409)
                definition = strict_json_loads(tx.task["definition_json"])
                expiry = datetime.fromisoformat(definition["task"]["authorization_expires_at"].replace("Z", "+00:00"))
                if (expiry <= datetime.now(timezone.utc)
                        or (datetime.now(timezone.utc) - tx.task["activated_at"]).total_seconds() >= assignment.limits.max_elapsed_seconds):
                    raise DomainError("LIMIT_BLOCKED", 429)
                if not tx.capacity_pools:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 503)
                for pool in tx.capacity_pools:
                    reservation = tx.connection.execute("""SELECT state FROM vnext.capacity_reservation
                        WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND pool_key=%s""",
                        (*tx.owner, record["agent_run_id"], pool["pool_key"])).fetchone()
                    if not reservation or reservation[0] == "released":
                        raise DomainError("STALE_EXECUTION", 409)
                allowed = True
            elif action in {"stop", "stop_after_current"}:
                if not isinstance(control_operation_id, str) or not control_operation_id:
                    raise DomainError("INVALID_REFERENCE", 422)
                # Observe authority may settle old runs, but never silently
                # create a stop policy: P05 must have durably revoked first.
                if record["execution_allowed"] and record["stop_kind"] is None:
                    raise DomainError("STALE_EXECUTION", 409)
            return {"identity": run.identity.model_dump(mode="json"), "assignment_digest": assignment_digest,
                    "receiver": expected, "action": action, "subject": access.principal.subject,
                    "execution_allowed": allowed,
                    "valid_until": (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat().replace("+00:00", "Z")}

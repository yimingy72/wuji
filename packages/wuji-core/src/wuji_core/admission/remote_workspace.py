"""HTTPS transport for the existing P06 workspace executor and permit authority.

Only ExecutorPermitAuthority uses the platform UoW. Kali receives a frozen permit
document, but its synchronous admission adapter obtains every authority decision
from that platform service. Neither transport allocates attempts or retries reads.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
import math
import ssl
from urllib.parse import quote, urlsplit

import httpx

from wuji_core.admission.common import digest
from wuji_core.admission.tools import ToolExecutionReceipt, ToolPermit
from wuji_core.contracts import generated as wire
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError


@dataclass(frozen=True, kw_only=True)
class ExecutorDeploymentBinding:
    """Deployment-owned Task and service identities, never request configuration."""

    tenant_id: str
    project_id: str
    task_id: str
    executor_ref: str
    receiver_id: str
    environment_ref: str
    collector_subject: str
    gate_subject: str

    def __post_init__(self):
        if any(not isinstance(value, str) or not 1 <= len(value) <= 256
               for value in vars(self).values()):
            raise ValueError("a complete fixed executor deployment binding is required")
        if self.collector_subject == self.gate_subject:
            raise ValueError("Gate and collector must have distinct service subjects")

    @property
    def owner(self):
        return self.tenant_id, self.project_id, self.task_id

    def require_identity(self, identity):
        if ((identity.tenant_id, identity.project_id, identity.task_id) != self.owner
                or identity.receiver_id != self.receiver_id):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")

    def require_permit(self, permit):
        self.require_identity(permit.identity)
        if permit.executor_ref != self.executor_ref or permit.tool_attempt_id is None:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")

    def require_gate(self, principal):
        if (principal.tenant_id != self.tenant_id
                or principal.subject != self.gate_subject
                or "agent" in principal.roles):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")


class RemoteExecutorTransportError(OSError):
    """No authoritative response; must not become a not-started receipt."""


class _HttpsJsonEndpoint:
    def __init__(self, *, binding, base_url, ca_file, bearer_token,
                 timeout_seconds=15.0, max_request_bytes=1048576,
                 max_response_bytes=2097152):
        target = urlsplit(base_url)
        if (target.scheme != "https" or not target.hostname
                or target.username is not None or target.password is not None
                or target.query or target.fragment or target.path not in {"", "/"}
                or any(c.isspace() for c in base_url) or "\\" in base_url):
            raise ValueError("a fixed HTTPS origin without credentials or path is required")
        target.port  # Reject malformed configured ports before any request.
        if (not isinstance(binding, ExecutorDeploymentBinding) or not ca_file
                or not math.isfinite(timeout_seconds) or timeout_seconds <= 0
                or type(max_request_bytes) is not int or max_request_bytes < 1
                or type(max_response_bytes) is not int or max_response_bytes < 1):
            raise ValueError("trusted CA, deployment binding and positive limits are required")
        # Do not alter certifi or accept verify=False/a caller-supplied transport.
        self._tls = ssl.create_default_context(cafile=ca_file)
        self._tls.check_hostname = True
        self._tls.verify_mode = ssl.CERT_REQUIRED
        self._tls.minimum_version = ssl.TLSVersion.TLSv1_2
        self.binding = binding
        self._base_url = base_url.rstrip("/")
        self._bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds
        self.max_request_bytes = max_request_bytes
        self.max_response_bytes = max_response_bytes

    def _request(self, path, payload):
        body = canonical_json_bytes(payload)
        if len(body) > self.max_request_bytes:
            raise DomainError("LIMIT_BLOCKED", 429)
        token = self._bearer_token() if callable(self._bearer_token) else self._bearer_token
        if (not isinstance(token, str) or not token or not token.isascii()
                or any(c.isspace() or ord(c) < 33 or ord(c) == 127 for c in token)):
            raise RemoteExecutorTransportError("Executor transport credential is unavailable")
        return self._base_url + path, body, {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }

    def _response_headers(self, response):
        if (300 <= response.status_code < 400
                or response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                != "application/json"
                or response.headers.get("content-encoding", "identity").lower() != "identity"):
            raise RemoteExecutorTransportError("Executor response is not bounded JSON")
        length = response.headers.get("content-length")
        if length is not None and (not length.isascii() or not length.isdecimal()
                                   or len(length) > 20 or int(length) > self.max_response_bytes):
            raise RemoteExecutorTransportError("Executor response exceeds its wire limit")

    def _response(self, status, raw):
        try:
            value = strict_json_loads(raw)
        except ValueError as error:
            raise RemoteExecutorTransportError("Executor returned invalid JSON") from error
        if status == 200:
            return value
        # Only explicit authority rejections prove that check_execution was refused.
        # A timeout, malformed reply or 5xx can occur after its transaction committed.
        rejections = {
            401: {"UNAUTHENTICATED"},
            403: {"NOT_FOUND_OR_FORBIDDEN", "FORBIDDEN_COLLECTOR", "STALE_EXECUTION"},
            404: {"NOT_FOUND_OR_FORBIDDEN"},
            409: {"STALE_EXECUTION", "INPUT_DIGEST_CONFLICT"},
            422: {"INVALID_SCHEMA", "INVALID_REFERENCE"},
            429: {"LIMIT_BLOCKED"},
        }
        if isinstance(value, dict) and value.get("code") in rejections.get(status, set()):
            raise DomainError(value["code"], status)
        raise RemoteExecutorTransportError("Executor response does not establish authority")

    def post(self, path, payload):
        url, body, headers = self._request(path, payload)
        try:
            transport = httpx.HTTPTransport(verify=self._tls, retries=0, trust_env=False)
            with httpx.Client(transport=transport, trust_env=False, follow_redirects=False,
                              timeout=self.timeout_seconds) as client:
                with client.stream("POST", url, content=body, headers=headers) as response:
                    self._response_headers(response)
                    result = bytearray()
                    for chunk in response.iter_raw(chunk_size=65536):
                        if len(result) + len(chunk) > self.max_response_bytes:
                            raise RemoteExecutorTransportError("Executor response exceeds its wire limit")
                        result.extend(chunk)
                    return self._response(response.status_code, result)
        except httpx.HTTPError as error:
            raise RemoteExecutorTransportError("Executor HTTPS request was not confirmed") from error

    async def apost(self, path, payload):
        url, body, headers = self._request(path, payload)
        try:
            async with asyncio.timeout(self.timeout_seconds):
                transport = httpx.AsyncHTTPTransport(verify=self._tls, retries=0, trust_env=False)
                async with httpx.AsyncClient(transport=transport, trust_env=False,
                                             follow_redirects=False,
                                             timeout=self.timeout_seconds) as client:
                    async with client.stream("POST", url, content=body, headers=headers) as response:
                        self._response_headers(response)
                        result = bytearray()
                        async for chunk in response.aiter_raw(chunk_size=65536):
                            if len(result) + len(chunk) > self.max_response_bytes:
                                raise RemoteExecutorTransportError("Executor response exceeds its wire limit")
                            result.extend(chunk)
                        return self._response(response.status_code, result)
        except (httpx.HTTPError, TimeoutError) as error:
            raise RemoteExecutorTransportError("Executor HTTPS request was not confirmed") from error


def restore_transport_permit(document, *, permit_digest, request_id, binding):
    """Parse a frozen document, without conferring any authority on its issuer fields."""
    try:
        wire.ExecutorPermitDocument.model_validate(document)
        permit = ToolPermit.restore(document, request_id=request_id)
        normalized = permit.stored()
        if (not compare_digest(digest(document), digest(normalized))
                or not compare_digest(digest(normalized), permit_digest)):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
        binding.require_permit(permit)
        return permit
    except DomainError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise DomainError("INVALID_SCHEMA", 422) from error


def _output_limit(permit, maximum):
    if type(maximum) is not int or maximum < 1:
        raise ValueError("a positive executor output limit is required")
    return min(maximum, permit.runtime.buffer_bytes,
               permit.runtime.limits.max_single_output_bytes)


def _bound_receipt(permit, receipt, binding, maximum):
    binding.require_permit(permit)
    expected = {
        "tool_attempt_id": permit.tool_attempt_id,
        "receiver_id": binding.receiver_id,
        "environment_ref": binding.environment_ref,
        "arguments_digest": permit.arguments_digest,
        "receipt_id": receipt.receipt_id,
    }
    if (receipt.tool_attempt_id != permit.tool_attempt_id
            or receipt.receiver_id != binding.receiver_id
            or any(receipt.source_receipt.get(key) != value for key, value in expected.items())):
        raise DomainError("INVALID_REFERENCE", 422)
    if receipt.status == "exited":
        if (receipt.started_at is None or receipt.exited_at is None
                or receipt.exited_at < receipt.started_at):
            raise DomainError("INVALID_REFERENCE", 422)
    elif receipt.output is not None or receipt.exited_at is not None:
        raise DomainError("INVALID_REFERENCE", 422)
    if receipt.status == "not_started" and receipt.started_at is not None:
        raise DomainError("INVALID_REFERENCE", 422)
    if receipt.output is not None:
        size = len(receipt.output)
        if size > _output_limit(permit, maximum):
            raise DomainError("LIMIT_BLOCKED", 429)
        if (type(receipt.source_receipt.get("output_bytes")) is not int
                or receipt.source_receipt["output_bytes"] != size
                or receipt.source_receipt.get("output_sha256") != sha256(receipt.output).hexdigest()):
            raise DomainError("INPUT_DIGEST_CONFLICT", 409)


def receipt_to_wire(permit, receipt, *, binding, max_output_bytes):
    receipt = ToolExecutionReceipt.model_validate(receipt)
    _bound_receipt(permit, receipt, binding, max_output_bytes)
    value = receipt.model_dump(mode="json", exclude={"output"})
    body = receipt.output
    value.update(
        permit_digest=digest(permit.stored()),
        output_base64=base64.b64encode(body).decode("ascii") if body is not None else None,
        output_bytes=str(len(body)) if body is not None else None,
        output_sha256=sha256(body).hexdigest() if body is not None else None,
    )
    wire.ExecutorReceiptResponse.model_validate(value)
    return value


def receipt_from_wire(document, permit, *, binding, max_output_bytes):
    try:
        wire.ExecutorReceiptResponse.model_validate(document)
        value = dict(document)
        if not compare_digest(value.pop("permit_digest"), digest(permit.stored())):
            raise ValueError("receipt permit mismatch")
        encoded, length, checksum = (value.pop(key) for key in
                                     ("output_base64", "output_bytes", "output_sha256"))
        if encoded is None:
            if length is not None or checksum is not None:
                raise ValueError("incomplete null output envelope")
            body = None
        else:
            maximum = _output_limit(permit, max_output_bytes)
            if (not isinstance(length, str) or not length.isascii()
                    or not length.isdecimal() or len(length) > 20
                    or str(int(length)) != length or int(length) > maximum
                    or len(encoded) > 4 * ((maximum + 2) // 3)):
                raise ValueError("unbounded output envelope")
            body = base64.b64decode(encoded, validate=True)
            if (len(body) != int(length) or not isinstance(checksum, str)
                    or not compare_digest(sha256(body).hexdigest(), checksum)
                    or base64.b64encode(body).decode("ascii") != encoded):
                raise ValueError("invalid output envelope")
        value["output"] = body
        receipt = ToolExecutionReceipt.model_validate(value)
        _bound_receipt(permit, receipt, binding, max_output_bytes)
        return receipt
    except (KeyError, TypeError, ValueError, binascii.Error) as error:
        raise RemoteExecutorTransportError("Executor receipt failed its exact binding") from error


class RemoteWorkspaceExecutor(_HttpsJsonEndpoint):
    """ToolExecutorPort over HTTPS; an ambiguous dispatch only queries its attempt."""

    def __init__(self, *, max_output_bytes=1048576, **kwargs):
        super().__init__(**kwargs)
        if type(max_output_bytes) is not int or max_output_bytes < 1:
            raise ValueError("a positive executor output limit is required")
        self.max_output_bytes = max_output_bytes

    async def _invoke(self, action, permit, *, reason=None):
        self.binding.require_permit(permit)
        payload = {"permit": permit.stored(), "permit_digest": digest(permit.stored())}
        contract = {"dispatch": wire.ExecutorDispatchRequest,
                    "query": wire.ExecutorQueryRequest,
                    "cancel": wire.ExecutorCancelRequest}[action]
        if action == "cancel":
            payload["reason"] = reason
        contract.model_validate(payload)
        result = await self.apost("/internal/v2/executor/" + action, payload)
        receipt = receipt_from_wire(result, permit, binding=self.binding,
                                    max_output_bytes=self.max_output_bytes)
        if receipt.status == "not_started" and receipt.error_code == "not_registered":
            # An empty remote inbox cannot exclude a delayed dispatch or lost volume.
            raise RemoteExecutorTransportError("Executor has no durable attempt receipt")
        return receipt

    async def dispatch(self, permit):
        try:
            return await self._invoke("dispatch", permit)
        except RemoteExecutorTransportError:
            return await self.query(permit)

    async def query(self, permit):
        return await self._invoke("query", permit)

    async def cancel(self, permit, *, reason):
        try:
            return await self._invoke("cancel", permit, reason=reason)
        except RemoteExecutorTransportError:
            return await self.query(permit)


class RemoteToolAdmission(_HttpsJsonEndpoint):
    """Synchronous authority port consumed inside WorkspaceReadExecutor threads."""

    def _check(self, permit, *, receiver_id, purpose):
        self.binding.require_permit(permit)
        if receiver_id != self.binding.receiver_id:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        payload = {
            "identity": permit.identity.model_dump(mode="json"),
            "tool_attempt_id": permit.tool_attempt_id,
            "execution_token": permit.execution_token,
            "permit_digest": digest(permit.stored()),
            "purpose": purpose,
        }
        wire.ExecutorPermitCheckRequest.model_validate(payload)
        result = self.post("/internal/v2/executors/"
                           + quote(self.binding.executor_ref, safe="") + "/permits/check", payload)
        expected = {key: payload[key] for key in ("tool_attempt_id", "permit_digest", "purpose")}
        try:
            wire.ExecutorPermitCheckResponse.model_validate(result)
            if canonical_json_bytes(result) != canonical_json_bytes(expected):
                raise ValueError("authority did not acknowledge the exact attempt and purpose")
        except (TypeError, ValueError) as error:
            raise RemoteExecutorTransportError("Executor authority acknowledgement is invalid") from error

    def check_execution(self, permit, *, receiver_id):
        self._check(permit, receiver_id=receiver_id, purpose="check_execution")

    def validate_receipt_permit(self, permit, *, receiver_id):
        self._check(permit, receiver_id=receiver_id, purpose="validate_receipt")


class ExecutorPermitAuthority:
    """Platform-only adapter from a signed collector request to the real ToolPermit."""

    def __init__(self, admission, *, bindings):
        self.admission = admission
        self.bindings = {}
        for binding in bindings:
            if not isinstance(binding, ExecutorDeploymentBinding):
                raise ValueError("fixed executor deployment bindings are required")
            key = (*binding.owner, binding.executor_ref)
            if key in self.bindings:
                raise ValueError("duplicate executor deployment binding")
            self.bindings[key] = binding

    def check(self, access, executor_ref, payload):
        from wuji_core.evidence.artifacts import bound_attempt, require_collector

        request = wire.ExecutorPermitCheckRequest.model_validate(payload)
        # Generated UUID/digest scalars are RootModels; only the callback envelope
        # (which contains no permit timestamps) is safe to normalize this way.
        request_value = request.model_dump(mode="json")
        attempt_id = request_value["tool_attempt_id"]
        requested_digest = request_value["permit_digest"]
        purpose = request_value["purpose"]
        require_collector(access)
        identity = request.identity
        binding = self.bindings.get((identity.tenant_id, identity.project_id,
                                     identity.task_id, executor_ref))
        if (binding is None or access.principal.tenant_id != binding.tenant_id
                or access.principal.subject != binding.collector_subject):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        binding.require_identity(identity)
        # Read using the verified collector and current Task ACL. The client never
        # supplies the original Worker access/roles/runtime to this endpoint.
        with self.admission.uow.transaction(access, binding.task_id) as tx:
            if tx.owner != binding.owner or not tx.permissions["can_settle"]:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            actual = bound_attempt(tx, attempt_id)
            if not actual["binding_can_settle"]:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            visible = tx.connection.execute(
                "SELECT 1 FROM vnext.tool_call WHERE tenant_id=%s AND project_id=%s "
                "AND task_id=%s AND tool_call_id=%s AND access_level<=%s",
                (*tx.owner, actual["tool_call_id"], tx.permissions["clearance"]),
            ).fetchone()
            if visible is None:
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            registered = self.admission.registry.executor(tx, executor_ref)
            if (registered.ref != binding.executor_ref
                    or registered.receiver_id != binding.receiver_id
                    or registered.environment_ref != binding.environment_ref
                    or registered.collector_subject != binding.collector_subject
                    or actual["environment_ref"] != binding.environment_ref):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            stored = strict_json_loads(actual["permit_json"])
            # Only this database-origin document may recreate the original issuer.
            permit = ToolPermit.restore(stored, request_id=access.request_id)
            binding.require_permit(permit)
            original_digest = digest(stored)
            if (permit.tool_attempt_id != attempt_id
                    or permit.tool_call_id != actual["tool_call_id"]
                    or permit.identity != identity
                    or any(str(actual[key]) != str(value) for key, value in
                           identity.model_dump(mode="json").items())
                    or permit.tool_definition_ref not in registered.allowed_tool_refs
                    or not compare_digest(original_digest, digest(permit.stored()))
                    or not compare_digest(original_digest, requested_digest)
                    or not compare_digest(permit.execution_token, request.execution_token)):
                raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        # Keep native current-execution versus historical-settlement behavior and
        # lock order. No network request takes place in either UoW transaction.
        if purpose == "check_execution":
            self.admission.check_execution(permit, receiver_id=binding.receiver_id)
        else:
            self.admission.validate_receipt_permit(permit, receiver_id=binding.receiver_id)
        acknowledgement = {"tool_attempt_id": attempt_id,
                           "permit_digest": original_digest, "purpose": purpose}
        wire.ExecutorPermitCheckResponse.model_validate(acknowledgement)
        return acknowledgement

"""Run-only private HTTP proxy for PlatformWorkerHost; never executes an Agent."""

import asyncio
import base64
from datetime import datetime, timezone
from hashlib import sha256
from ipaddress import ip_address
import os
from pathlib import Path
import stat
import ssl
import tempfile
from urllib.parse import urlsplit

import httpx

from wuji_core.contracts import generated as wire
from wuji_core.contracts.envelopes import BlobRef, ResultReceipt, WorkerAssignment
from wuji_core.execution.session_bridge import SessionTransportCodec
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_maf_worker.context import ContextBundle


class HostTransportError(ValueError):
    """Sanitized failure; request bodies, credentials and remote text stay private."""


def scalar(value):
    return getattr(value, "root", value)


def document(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {k: document(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [document(v) for v in value]
    return value


def context_document(context):
    return {"snapshot_id": context.snapshot_id, "read_set": document(context.read_set),
            "record_refs": document(context.record_refs), "text": context.text,
            "input_digest": context.input_digest}


def private_read(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > maximum:
            raise HostTransportError("invalid private Worker file")
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise HostTransportError("private Worker file exceeds limit")
    return data


def private_save(path, body, maximum):
    if len(body) > maximum:
        raise HostTransportError("Worker archive exceeds transport limit")
    fd, temporary = tempfile.mkstemp(prefix=".worker-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if private_read(path, maximum) != body:
                raise HostTransportError("Worker retained request digest conflict") from None
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        os.unlink(temporary)


class RemoteWorkerHost:
    def __init__(self, origin, *, run_credential, token_verifier, receiver,
                 spool_directory, timeout=10, max_transport_bytes=67108864,
                 ssl_context=None):
        parsed = urlsplit(origin)
        local = parsed.hostname == "localhost"
        try:
            local = local or ip_address(parsed.hostname).is_loopback
        except ValueError:
            pass
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"} or parsed.scheme == "http" and not local):
            raise ValueError("fixed HTTPS or loopback Host origin required")
        if not isinstance(token_verifier, TokenVerifier):
            raise TypeError("the actual deployment TokenVerifier is required")
        if (not isinstance(run_credential, str) or not run_credential or len(run_credential) > 16384
                or any(c.isspace() for c in run_credential)):
            raise ValueError("a bounded Run bearer is required")
        if not 0 < timeout <= 60 or type(max_transport_bytes) is not int or not 1 <= max_transport_bytes <= 67108864:
            raise ValueError("bounded private transport required")
        self.origin, self._credential = origin.rstrip("/"), run_credential
        self.verifier = token_verifier
        self.receiver = wire.WorkerReceiver.model_validate(receiver)
        self.timeout, self.maximum = timeout, max_transport_bytes
        if ssl_context is not None and (
            not isinstance(ssl_context, ssl.SSLContext)
            or ssl_context.verify_mode != ssl.CERT_REQUIRED
            or not ssl_context.check_hostname
        ):
            raise ValueError("verified TLS context required")
        self.ssl_context = ssl_context
        self.session_codec = SessionTransportCodec(
            max_transport_bytes=max_transport_bytes
        )
        self.directory = Path(spool_directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.directory.is_symlink() or self.directory.stat().st_mode & 0o077:
            raise ValueError("private Worker directory required")
        self._assignment = None

    def _bind(self, assignment):
        assignment = WorkerAssignment.model_validate(assignment)
        if self._assignment is None:
            self._assignment = assignment.model_copy(deep=True)
        if (self._assignment != assignment
                or assignment.identity.receiver_id != self.receiver.receiver_id
                or assignment.identity.runtime_attempt.root != scalar(self.receiver.runtime_attempt)):
            raise HostTransportError("Worker assignment identity conflict")
        return assignment

    def _request(self, action, payload):
        # Existing WorkerHost methods are synchronous and MafRuntime calls them
        # in its worker thread. The inner async transport has a total deadline,
        # including a peer that keeps sending tiny chunks without going idle.
        return asyncio.run(self._request_async(action, payload))

    async def _request_async(self, action, payload):
        body = canonical_json_bytes(document(payload))
        if len(body) > self.maximum:
            raise HostTransportError("Host request exceeds transport limit")
        try:
            async with asyncio.timeout(self.timeout), httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=0, verify=self.ssl_context or True), trust_env=False,
                follow_redirects=False, timeout=httpx.Timeout(float(self.timeout)),
                headers={"Authorization": "Bearer " + self._credential,
                         "Content-Type": "application/json", "Accept": "application/json",
                         "Accept-Encoding": "identity"},
            ) as client, client.stream(
                "POST", self.origin + "/internal/v2/worker-host/" + action, content=body,
            ) as response:
                if response.status_code != 200:
                    # Bounded classification only: the HTTP status is stable,
                    # and reading the body inside this streaming context would
                    # disturb the success path the child depends on.  The body,
                    # headers, request and bearer stay private.
                    error = HostTransportError("Host request rejected or unresolved")
                    error.status_code = response.status_code
                    raise error
                if response.headers.get("content-encoding", "identity") != "identity":
                    raise HostTransportError("Host content encoding is unsupported")
                chunks, size = [], 0
                async for chunk in response.aiter_raw():
                    size += len(chunk)
                    if size > self.maximum:
                        raise HostTransportError("Host response exceeded byte limit")
                    chunks.append(chunk)
                return strict_json_loads(b"".join(chunks))
        except (httpx.HTTPError, OSError, TimeoutError):
            raise HostTransportError("Host transport outcome is unknown") from None

    async def await_start(self, assignment, *, timeout=120, poll_interval=0.1):
        assignment = self._bind(assignment)
        if not 0 < timeout <= 300 or not 0.01 <= poll_interval <= 5:
            raise ValueError("bounded start wait required")
        self.verifier.verify(self._credential)
        expected_digest = sha256(canonical_json_bytes(document(assignment))).hexdigest()
        async with asyncio.timeout(timeout):
            while True:
                response = wire.WorkerStartPermission.model_validate(await self._request_async(
                    "await-start", {"assignment": document(assignment)},
                ))
                if (response.identity != assignment.identity
                        or response.start_operation_id != assignment.operation_id
                        or scalar(response.assignment_digest) != expected_digest
                        or response.receiver != self.receiver
                        or response.valid_until <= datetime.now(timezone.utc)):
                    raise HostTransportError("start observation binding is stale")
                status = str(response.status)
                if status == "revoked":
                    raise HostTransportError("Worker start was revoked")
                if status == "ready":
                    if not response.birth_id or not response.observation_id or not response.source_digest:
                        raise HostTransportError("persisted birth observation is absent")
                    return response
                if status != "wait" or any((response.birth_id, response.observation_id, response.source_digest)):
                    raise HostTransportError("invalid start observation")
                await asyncio.sleep(poll_interval)

    def _resolved(self, assignment):
        assignment = self._bind(assignment)
        reply = wire.WorkerResolvedContext.model_validate(self._request(
            "resolve", {"assignment": document(assignment)},
        ))
        if scalar(reply.assignment_digest) != sha256(canonical_json_bytes(document(assignment))).hexdigest():
            raise HostTransportError("resolved assignment changed")
        context = reply.context
        if (context.snapshot_id != assignment.snapshot_id
                or scalar(context.input_digest) != sha256(context.text.encode()).hexdigest()):
            raise HostTransportError("resolved context identity/digest changed")
        return reply

    def load_context(self, assignment):
        value = self._resolved(assignment).context
        return ContextBundle(value.snapshot_id, tuple(value.read_set), tuple(value.record_refs),
                             value.text, scalar(value.input_digest))

    def resolve(self, assignment, context, *, verified_principal):
        if verified_principal != self.verifier.verify(self._credential):
            raise HostTransportError("verified Worker principal mismatch")
        reply = self._resolved(assignment)
        if canonical_json_bytes(document(reply.context)) != canonical_json_bytes(context_document(context)):
            raise HostTransportError("frozen context changed")
        resolved = reply.resolved
        if hasattr(resolved, "model_dump"):
            resolved = resolved.model_dump(mode="python", exclude_unset=True)
        return self.session_codec.decode_resolved(document(resolved))

    def _session_exchange(self, assignment, action, payload, decode):
        if payload.assignment != assignment:
            raise HostTransportError("Session request assignment changed")
        request_body = canonical_json_bytes(document(payload))
        request_digest = sha256(request_body).hexdigest()
        prefix = "p08-" + action + "-"
        private_save(
            self.directory / (prefix + "request-" + request_digest + ".json"),
            request_body,
            self.maximum,
        )
        response = self._request(action, payload)
        response_body = canonical_json_bytes(response)
        private_save(
            self.directory / (prefix + "response-" + request_digest + ".json"),
            response_body,
            self.maximum,
        )
        return decode(response)

    def stage_session(self, assignment, objects):
        assignment = self._bind(assignment)
        payload = wire.WorkerStageSessionRequest.model_validate(
            {
                "assignment": document(assignment),
                "boundary": document(self.session_codec.encode_boundary(objects)),
            }
        )
        return self._session_exchange(
            assignment, "stage-session", payload, self.session_codec.decode_staged
        )

    def publish_session(self, assignment, manifest, *, expected_revision):
        assignment = self._bind(assignment)
        payload = wire.WorkerPublishSessionRequest.model_validate(
            {
                "assignment": document(assignment),
                "manifest": document(manifest),
                "expected_revision": str(scalar(expected_revision)),
            }
        )
        return self._session_exchange(
            assignment, "publish-session", payload, self.session_codec.decode_receipt
        )

    def load_session(self, assignment, *, manifest_ref):
        assignment = self._bind(assignment)
        payload = wire.WorkerLoadSessionRequest.model_validate(
            {
                "assignment": document(assignment),
                "manifest_ref": scalar(manifest_ref),
            }
        )
        return self._session_exchange(
            assignment, "load-session", payload, self.session_codec.decode_published
        )

    def register_input(self, assignment, observation):
        assignment = self._bind(assignment)
        payload = wire.WorkerRegisterInputRequest.model_validate(
            {
                "assignment": document(assignment),
                "observation": document(
                    self.session_codec.encode_observation(observation)
                ),
            }
        )
        return self._session_exchange(
            assignment,
            "register-input",
            payload,
            self.session_codec.decode_input_receipt,
        )

    def load_delivery(self, assignment, *, delivery_id):
        assignment = self._bind(assignment)
        payload = wire.WorkerLoadDeliveryRequest.model_validate(
            {
                "assignment": document(assignment),
                "delivery_id": scalar(delivery_id),
            }
        )
        return self._session_exchange(
            assignment, "load-delivery", payload, self.session_codec.decode_human_input
        )

    def acknowledge_delivery(
        self, assignment, *, delivery_id, payload_digest
    ):
        assignment = self._bind(assignment)
        payload = wire.WorkerAcknowledgeDeliveryRequest.model_validate(
            {
                "assignment": document(assignment),
                "delivery_id": scalar(delivery_id),
                "payload_digest": scalar(payload_digest),
            }
        )
        return self._session_exchange(
            assignment,
            "acknowledge-delivery",
            payload,
            self.session_codec.decode_delivery_receipt,
        )

    def archive_sdk(self, assignment, body):
        assignment = self._bind(assignment)
        if not isinstance(body, bytes) or len(body) > min(assignment.limits.max_total_output_bytes, 16777216):
            raise HostTransportError("SDK output exceeds frozen limit")
        payload = wire.WorkerArchiveRequest.model_validate({
            "assignment": document(assignment), "sdk_output_base64": base64.b64encode(body).decode("ascii"),
            "sdk_digest": sha256(body).hexdigest(),
        })
        private_save(self.directory / "sdk-request.json", canonical_json_bytes(document(payload)), self.maximum)
        ref = BlobRef.model_validate(self._request("archive-sdk", payload))
        if ref.sha256.root != sha256(body).hexdigest():
            raise HostTransportError("SDK archive receipt digest changed")
        return ref

    def submit_result(self, assignment, *, raw_output, context, tool_receipts, sdk_output):
        assignment = self._bind(assignment)
        if (not isinstance(raw_output, bytes) or not isinstance(sdk_output, bytes)
                or len(raw_output) > min(assignment.limits.max_single_output_bytes, 16777216)
                or len(sdk_output) > min(assignment.limits.max_total_output_bytes, 16777216)):
            raise HostTransportError("result exceeds frozen output limit")
        payload = wire.WorkerSubmitRequest.model_validate({
            "assignment": document(assignment), "context": context_document(context),
            "raw_output_base64": base64.b64encode(raw_output).decode("ascii"),
            "sdk_output_base64": base64.b64encode(sdk_output).decode("ascii"),
            "raw_digest": sha256(raw_output).hexdigest(), "sdk_digest": sha256(sdk_output).hexdigest(),
            "tool_receipts": document(tool_receipts),
        })
        private_save(self.directory / "result-request.json", canonical_json_bytes(document(payload)), self.maximum)
        receipt = self._receipt(assignment, self._request("submit-result", payload))
        private_save(self.directory / "result-receipt.json", canonical_json_bytes(document(receipt)), self.maximum)
        return receipt

    def replay(self, assignment):
        assignment = self._bind(assignment)
        payload = wire.WorkerSubmitRequest.model_validate(strict_json_loads(
            private_read(self.directory / "result-request.json", self.maximum),
        ))
        if payload.assignment != assignment:
            raise HostTransportError("retained result assignment changed")
        return self._receipt(assignment, self._request("replay", payload))

    @staticmethod
    def _receipt(assignment, response):
        receipt = ResultReceipt.model_validate(response)
        expected = "maf-m1:" + sha256(canonical_json_bytes({
            "identity": document(assignment.identity), "operation_id": assignment.operation_id,
        })).hexdigest()
        if receipt.submission_id != expected:
            raise HostTransportError("result receipt belongs to another operation")
        return receipt

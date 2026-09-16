"""Registered inert Python child; one release barrier, one existing MAF run."""

import asyncio
from contextlib import contextmanager
from hashlib import sha256
import os
from pathlib import Path
import sys
import ssl

from wuji_core.contracts import generated as wire
from wuji_core.contracts.envelopes import ResultReceipt, WorkerAssignment
from wuji_core.contracts.sessions import InputReceipt
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_maf_worker.remote_host import (
    HostTransportError, RemoteWorkerHost, document, private_read, scalar,
)


@contextmanager
def _phase(step):
    """Attach one bounded step label to whatever fails inside it.

    Only the stage name reaches stderr; the exception text, bearer, HTTP request
    and deployment paths stay on the private diagnostic channel.
    """

    try:
        yield
    except Exception as error:
        if not hasattr(error, "wuji_step"):
            error.wuji_step = step
        raise


def validate_completion_receipt(value):
    """Keep saved Input and result receipts distinct from process observations."""
    if not isinstance(value, (ResultReceipt, InputReceipt)):
        raise TypeError("child completion requires a typed result or saved input receipt")
    return value


async def run_child(*, assignment_file, bootstrap_directory):
    directory = Path(bootstrap_directory)
    assignment_path = Path(assignment_file)
    if (not directory.is_absolute() or directory.is_symlink()
            or assignment_path != directory / "assignment.json"):
        raise HostTransportError("fixed private bootstrap layout required")
    with _phase("bootstrap"):
        assignment = WorkerAssignment.model_validate(strict_json_loads(private_read(assignment_path, 1048576)))
        bootstrap = wire.WorkerBootstrap.model_validate(strict_json_loads(private_read(directory / "bridge.json", 1048576)))
    if (bootstrap.assignment != assignment
            or scalar(bootstrap.assignment_digest) != sha256(canonical_json_bytes(document(assignment))).hexdigest()
            or bootstrap.receiver.receiver_id != assignment.identity.receiver_id
            or scalar(bootstrap.receiver.runtime_attempt) != assignment.identity.runtime_attempt.root
            or "PRIVATE KEY" in bootstrap.public_key_pem):
        raise HostTransportError("bootstrap binding or verification material is invalid")
    # Even a manually repeated module invocation cannot re-enter the SDK for
    # the same retained Worker directory. This marker is not process evidence.
    marker = os.open(directory / "child-entered", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fsync(marker)
    finally:
        os.close(marker)
    parent = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    verifier = TokenVerifier(public_key_pem=bootstrap.public_key_pem.encode(),
                             issuer=bootstrap.issuer, audience=bootstrap.audience)
    ca_file = os.environ.get("WUJI_TLS_CA_FILE")
    ssl_context = ssl.create_default_context(cafile=ca_file) if ca_file else None
    host = RemoteWorkerHost(
        bootstrap.host_origin, run_credential=bootstrap.run_credential,
        token_verifier=verifier, receiver=document(bootstrap.receiver),
        spool_directory=directory, timeout=bootstrap.transport_timeout_seconds,
        max_transport_bytes=bootstrap.max_transport_bytes,
        ssl_context=ssl_context,
    )
    with _phase("await_start"):
        await host.await_start(assignment, timeout=bootstrap.wait_timeout_seconds)
    with _phase("load_context"):
        context = await asyncio.to_thread(host.load_context, assignment)
    with _phase("run_assignment"):
        # Framework import and Agent construction happen only beyond the durable
        # platform barrier. Reuse its existing native stream/tool loop verbatim.
        from wuji_maf_worker.entrypoint import run_assignment

        receipt = await run_assignment(
            assignment,
            host=host,
            context=context,
            run_credential=bootstrap.run_credential,
            token_verifier=verifier,
            model_gate_url=bootstrap.model_gate_url,
            tool_gate_url=bootstrap.tool_gate_url,
            ssl_context=ssl_context,
        )
    with _phase("receipt"):
        return validate_completion_receipt(receipt)


def main():
    try:
        if len(sys.argv) != 1:
            raise HostTransportError("registered child accepts no command arguments")
        asyncio.run(run_child(
            assignment_file=os.environ["WUJI_WORKER_ASSIGNMENT_FILE"],
            bootstrap_directory=os.environ["WUJI_WORKER_BOOTSTRAP_DIRECTORY"],
        ))
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        # The exact raw/sdk/result files are the private diagnostic channel.
        # No exception string, bearer, HTTP request or deployment data is logged;
        # only the bounded phase label names the failing stage.
        step = getattr(error, "wuji_step", "unknown")
        if not isinstance(step, str) or not 1 <= len(step) <= 64:
            step = "unknown"
        sys.stderr.write(
            f"Wuji Worker stopped without a confirmed completion (step={step}).\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

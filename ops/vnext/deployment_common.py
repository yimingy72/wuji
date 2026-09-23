"""Explicit deployment configuration and constructors; no Task/Run producers."""

from contextlib import contextmanager
import os
from pathlib import Path
import re
import ssl

import psycopg
from pydantic import BaseModel, ConfigDict, Field

from wuji_core.admission.registry import AdmissionRegistry
from wuji_core.blackboard.assessments import AssessmentService
from wuji_core.blackboard.claims import ClaimService
from wuji_core.blackboard.committer import ResultCommitter
from wuji_core.blackboard.fact_view import FactLedger
from wuji_core.evidence.artifacts import ArtifactStore
from wuji_core.execution.approvals import ApprovalService
from wuji_core.execution.control import ControlService
from wuji_core.execution.inputs import InputService
from wuji_core.execution.sessions import SessionRepository
from wuji_core.http import strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_core.persistence.uow import AccessContext, UnitOfWork
from wuji_core.scheduling.credentials import RunCredentialIssuer


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "wuji.deployment.v1"
    role: str
    database_file: str
    public_key_file: str
    issuer: str
    audience: str
    service_token_file: str
    ca_file: str
    artifact_root: str = "/var/lib/wuji/platform/artifacts"
    artifact_max_bytes: int = Field(default=8 * 1024 * 1024, ge=1, le=67_108_864)
    journal_path: str = "/var/lib/wuji/platform/dispatch.sqlite3"
    spool_directory: str = "/var/lib/wuji/platform/intake"
    profiles_file: str
    worker_lock_digest: str | None = None
    secret_refs: dict[str, str] = Field(default_factory=dict)
    task_model_key_ref: str | None = None
    task_model_keys_directory: str | None = None
    task_model_keys_secret: str | None = None
    task_ids: list[str] = Field(default_factory=list, max_length=10000)
    work_kinds: list[str] = Field(default_factory=lambda: ["explore"])
    supervisor_url: str | None = None
    host_origin: str | None = None
    model_gate_url: str | None = None
    tool_gate_url: str | None = None
    receiver_token_file: str | None = None
    session_transport: bool = False
    public_commands: bool = False
    public_approvals: bool = False
    max_transport_bytes: int = Field(default=1048576, ge=1, le=67108864)
    executors: list[dict] = Field(default_factory=list, max_length=256)
    pod_runtime: dict | None = None


def read_file(path, maximum=1048576):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("deployment file paths must be absolute")
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("deployment file exceeds its bound")
    return data


def token(path):
    value = read_file(path, 16384).decode().strip()
    if not value or any(c.isspace() for c in value):
        raise ValueError("a bounded deployment bearer is required")
    return value


def load_settings(role):
    value = Settings.model_validate(strict_json_loads(read_file(
        os.environ.get("WUJI_DEPLOYMENT_CONFIG", "/config/deployment.json")
    )))
    if value.schema_version != "wuji.deployment.v1" or value.role != role:
        raise ValueError("wrong deployment configuration role/version")
    return value


class Deployment:
    def __init__(self, settings):
        self.settings = settings
        self.tls = ssl.create_default_context(cafile=settings.ca_file)
        self.verifier = TokenVerifier(
            public_key_pem=read_file(settings.public_key_file),
            issuer=settings.issuer, audience=settings.audience,
        )
        self.uow = UnitOfWork(self.connection)
        self.registry = AdmissionRegistry(self.uow)
        self.artifacts = ArtifactStore(
            self.uow, settings.artifact_root, max_bytes=settings.artifact_max_bytes
        )
        self.claims = ClaimService(self.uow)
        self.assessments = AssessmentService(self.uow, self.artifacts)
        self.ledger = FactLedger(self.uow)
        self.committer = ResultCommitter(self.uow, self.artifacts, self.claims)
        self.sessions = SessionRepository(self.uow, artifacts=self.artifacts, registry=self.registry)
        self.inputs = InputService(self.uow, sessions=self.sessions, registry=self.registry)
        self.approvals = ApprovalService(self.uow, sessions=self.sessions, registry=self.registry)
        self.control = ControlService(self.uow, artifacts=self.artifacts, sessions=self.sessions)
        from wuji_core.completion.precheck import CompletionService

        self.completion = CompletionService(self.uow, control=self.control)
        self.profiles = strict_json_loads(read_file(settings.profiles_file))
        if not isinstance(self.profiles, list):
            raise ValueError("published harness profiles must be a list")
        digests = {p["body"]["lock_digest"] for p in self.profiles}
        if len(digests) > 1:
            raise ValueError("one fixed Worker lock required")
        published = None if not digests else digests.pop()
        configured = settings.worker_lock_digest
        if configured is not None and not re.fullmatch(r"[a-f0-9]{64}", configured):
            raise ValueError("worker_lock_digest must be a SHA-256 digest")
        if published is not None and configured not in {None, published}:
            raise ValueError("published profiles differ from the configured Worker lock")
        self.lock_digest = published or configured
        if self.lock_digest is None:
            raise ValueError("an empty profile catalog requires worker_lock_digest")

    def access(self, path=None):
        return AccessContext(self.verifier.verify(token(path or self.settings.service_token_file)), "deployment")

    def connect(self):
        params = strict_json_loads(read_file(self.settings.database_file, 32768))
        allowed = {"host", "port", "dbname", "user", "password"}
        if not isinstance(params, dict) or set(params) != allowed:
            raise ValueError("explicit application database connection required")
        # No Unix-socket or environment fallback to a host fixture database.
        if not isinstance(params["host"], str) or not params["host"] or params["host"].startswith("/"):
            raise ValueError("deployment database must have an explicit network host")
        return psycopg.connect(**params, sslmode="verify-full",
            sslrootcert=self.settings.ca_file, connect_timeout=5, autocommit=True)

    @contextmanager
    def connection(self):
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    def secret(self, ref):
        path = self.settings.secret_refs.get(ref)
        if path is None:
            raise ValueError("unregistered deployment secret reference")
        return read_file(path, 65536)

    def issuer(self):
        def public(ref):
            if ref not in self.settings.secret_refs:
                raise ValueError("unregistered signing key reference")
            return read_file(self.settings.public_key_file)
        return RunCredentialIssuer(signing_key_resolver=self.secret,
            encryption_key_resolver=self.secret, public_key_resolver=public)

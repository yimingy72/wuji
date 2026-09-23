"""P09 real PostgreSQL and identity prerequisites; no scheduler policy or ledger fakes."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
import subprocess
from types import SimpleNamespace
from types import ModuleType
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from joserfc import jwt
from joserfc.jwk import RSAKey

from support.p03 import access
from support.p06 import (
    ENVIRONMENT,
    OWNER,
    RECEIVER,
    TASK,
    register_workspace_components,
    task_admission_config,
)
from test_work_state_guards import command, control_case
from wuji_core.admission.registry import AdmissionRegistry
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.persistence.uow import AccessContext
from wuji_core.scheduling.claims import (
    DispatchRepository,
    Scheduler,
    SchedulerOwnership,
)
from wuji_core.scheduling.credentials import RunCredentialIssuer
from wuji_maf_worker.factory import HarnessProfile

SCHEDULER = access("scheduler-fixture", role="scheduler")
RECEIVER_ACCESS = access("observer-fixture", role="controller")
TOOL_REF = "fixture-reader-v1"
TEMPLATE_REF = "scheduler-worker-template-v1"
SIGNING_KEY_REF = "scheduler-signing-key-v1"
ENCRYPTION_KEY_REF = "scheduler-encryption-key-v1"
ISSUER = "https://scheduler.identity.fixture.invalid"
AUDIENCE = "wuji-vnext-scheduler-tests"
POD_UID = "synthetic-p09-pod-uid"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
P09_SCHEMA_REVISION = "a3f7a95eacce20cbdeeaf654ea8f86064222ba0c"


@dataclass(frozen=True)
class SchedulerKeys:
    private_pem: bytes
    public_pem: bytes
    encryption_key: bytes

    @classmethod
    def generate(cls) -> "SchedulerKeys":
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return cls(
            private_pem=private.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ),
            public_pem=private.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            ),
            encryption_key=bytes(range(32)),
        )

    def signing(self, ref: str) -> bytes:
        if ref != SIGNING_KEY_REF:
            raise KeyError(ref)
        return self.private_pem

    def public(self, ref: str) -> bytes:
        if ref != SIGNING_KEY_REF:
            raise KeyError(ref)
        return self.public_pem

    def encryption(self, ref: str) -> bytes:
        if ref != ENCRYPTION_KEY_REF:
            raise KeyError(ref)
        return self.encryption_key


def _lock_digest() -> str:
    return sha256(
        (REPOSITORY_ROOT / "packages/maf-worker/uv.lock").read_bytes()
    ).hexdigest()


def migrate_p09_head_then_current(environment) -> None:
    source = subprocess.check_output(
        [
            "git",
            "show",
            P09_SCHEMA_REVISION
            + ":packages/wuji-core/src/wuji_core/persistence/schema.py",
        ],
        cwd=REPOSITORY_ROOT,
        text=True,
    )
    historical = ModuleType("p09_0010_schema")
    historical.__file__ = "git:" + P09_SCHEMA_REVISION + "/schema.py"
    exec(compile(source, historical.__file__, "exec"), historical.__dict__)

    with environment.migration_connection() as connection:
        historical.migrate(connection, application_role=environment.application_role)
        heads = {
            row[0]
            for row in connection.execute(
                "SELECT head FROM vnext.schema_migration"
            ).fetchall()
        }
        if "vnext_0010_p09_scheduler" not in heads:
            raise AssertionError("historical P09 migration head was not established")
        if "vnext_0011_p09_dispatch_fairness" in heads:
            raise AssertionError("historical P09 setup unexpectedly contains fairness")

    from wuji_core.persistence.schema import migrate

    with environment.migration_connection() as connection:
        migrate(connection, application_role=environment.application_role)
        migrate(connection, application_role=environment.application_role)
        assert connection.execute(
            "SELECT count(*) FROM vnext.schema_migration WHERE head='vnext_0011_p09_dispatch_fairness'"
        ).fetchone() == (1,)
        assert connection.execute("""SELECT count(*) FROM information_schema.columns
            WHERE table_schema='vnext' AND table_name='scheduler_work'
            AND column_name='consideration_round'""").fetchone() == (1,)
        assert connection.execute("""SELECT count(*) FROM information_schema.columns
            WHERE table_schema='vnext' AND table_name='scheduler_receiver'
            AND column_name='pod_uid'""").fetchone() == (1,)


def _profiles(lock_digest: str) -> dict[str, dict[str, object]]:
    profiles = {}
    for kind in ("explore", "reason", "report"):
        profile = HarnessProfile(
            ref=f"harness.{kind}.p09.v1",
            revision="1",
            work_kind=kind,
            instructions=f"Use the fixed P09 {kind} fixture inputs and registered tool.",
            tool_definition_refs=(TOOL_REF,),
            lock_digest=lock_digest,
            max_context_records=128,
            max_context_bytes=65_536,
            max_output_tokens=2_048,
        )
        profiles[kind] = profile.snapshot()
    return profiles


def _configure_scheduler(
    case,
    *,
    profiles: dict[str, dict[str, object]],
    template_clearance: int,
    max_work_items: int,
    capacity: int,
    gateway_url: str = "https://model.fixture.invalid/v1",
    approval_required: bool = False,
    max_single_output_bytes: int = 4096,
    max_total_output_bytes: int = 65_536,
    evaluation_mode: str | None = None,
    reason_retry_attempts: int = 0,
    repair_attempts: int = 1,
    max_no_progress_rounds: int | None = None,
    max_reason_runs: int = 2,
    task_run_limits: dict[str, int] | None = None,
    definition_task_run_limits: dict[str, int] | None = None,
    explore_concurrency: int | None = None,
    component_registrar=None,
    admission_config=None,
) -> None:
    registry = __import__(
        "wuji_core.admission.registry", fromlist=["TaskAdmissionConfig"]
    )
    lock_digest = _lock_digest()
    tool_refs = sorted(
        {
            ref
            for profile in profiles.values()
            for ref in profile["body"]["tool_definition_refs"]
        }
    )
    if admission_config is None:
        config = task_admission_config(
            registry,
            gateway_url=gateway_url,
            max_model_requests=8,
            max_tool_calls=8,
            max_total_output_bytes=max_total_output_bytes,
            allowed_tool_refs=tool_refs,
        )
        config = config.model_copy(
            update={
                "runtime": config.runtime.model_copy(
                    update={
                        "lock_digest": lock_digest,
                        "task_run_limits": (
                            None
                            if task_run_limits is None
                            else registry.TaskRunLimits.model_validate(task_run_limits)
                        ),
                        "limits": config.runtime.limits.model_copy(
                            update={
                                "max_work_items": max_work_items,
                                "max_reason_runs": max_reason_runs,
                                "max_single_output_bytes": max_single_output_bytes,
                                "reason_retry_attempts": reason_retry_attempts,
                                "repair_attempts": repair_attempts,
                                "max_no_progress_rounds": max_no_progress_rounds,
                            }
                        ),
                    }
                )
            }
        )
    else:
        config = registry.TaskAdmissionConfig.model_validate(admission_config)
        if (
            config.runtime.lock_digest != lock_digest
            or set(config.allowed_tool_refs) != set(tool_refs)
            or set(config.runtime.allowed_tool_refs) != set(tool_refs)
        ):
            raise AssertionError("the supplied admission config differs from its profiles")
    with case.env.migration_connection() as connection:
        definition = strict_json_loads(
            connection.execute(
                "SELECT definition_json FROM vnext.task WHERE task_id=%s", (TASK,)
            ).fetchone()[0]
        )
        definition["lock_digest"] = lock_digest
        definition["worker_profiles"] = profiles
        if admission_config is not None:
            definition["model_profile"] = config.model.model_dump(mode="json")
            definition["runtime_profile"] = config.runtime.model_dump(mode="json")
            definition["task"]["model_profile_ref"] = config.model.ref
            definition["task"]["runtime_profile_ref"] = config.runtime.ref
        frozen_run_limits = definition_task_run_limits or task_run_limits
        if frozen_run_limits is not None:
            definition["runtime_profile"]["task_run_limits"] = frozen_run_limits
        if explore_concurrency is not None:
            definition["task"]["explore_concurrency"] = explore_concurrency
        if evaluation_mode is not None:
            definition["evaluation_mode"] = evaluation_mode
        body = canonical_json_bytes(definition).decode("utf-8")
        connection.execute(
            "UPDATE vnext.task SET definition_json=%s,definition_digest=%s WHERE task_id=%s",
            (body, sha256(body.encode("utf-8")).hexdigest(), TASK),
        )
        connection.execute(
            "UPDATE vnext.capacity_pool SET capacity=%s WHERE pool_key IN ('platform','tenant-fixture')",
            (capacity,),
        )
        model_pool = "model:" + config.model.ref
        connection.execute(
            "INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,published_ref) VALUES(%s,'model',NULL,%s,'fixture-capacity-v1')",
            (model_pool, capacity),
        )
        connection.execute(
            "INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key) VALUES(%s,%s,%s,%s)",
            (*OWNER, model_pool),
        )
        if TOOL_REF in tool_refs:
            register_workspace_components(
                registry,
                connection,
                approval_required=approval_required,
            )
        if component_registrar is not None:
            component_registrar(registry, connection)
        registry.register_task_config(connection, owner=OWNER, config=config)
        connection.execute(
            """INSERT INTO vnext.scheduler_identity_template(
            tenant_id,project_id,task_id,template_ref,issuer,audience,
            signing_key_ref,signing_kid,encryption_key_ref,clearance,enabled)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)""",
            (
                *OWNER,
                TEMPLATE_REF,
                ISSUER,
                AUDIENCE,
                SIGNING_KEY_REF,
                "p09-test-key",
                ENCRYPTION_KEY_REF,
                template_clearance,
            ),
        )
        connection.execute(
            """INSERT INTO vnext.scheduler_receiver(
            tenant_id,project_id,task_id,runtime_attempt,receiver_id,environment_ref,
            model_mode,receiver_subject,credential_template_ref,harness_profiles_json,pod_uid,enabled)
            VALUES(%s,%s,%s,1,%s,%s,'synthetic','observer-fixture',%s,%s,%s,true)""",
            (
                *OWNER,
                RECEIVER,
                ENVIRONMENT,
                TEMPLATE_REF,
                canonical_json_bytes(profiles).decode(),
                POD_UID,
            ),
        )
        connection.execute(
            """UPDATE vnext.task_access SET
              can_settle=true,can_write=false,can_model_output=false
              WHERE tenant_id=%s AND project_id=%s AND task_id=%s
                AND subject='observer-fixture'""",
            OWNER,
        )
    case.scheduler_config = config


def _publish_intent(case, *, access_level: int, start=True):
    if start:
        command(case, "start")
    artifact = case.store.stage(
        access("collector-fixture", role="collector"),
        TASK,
        "attempt-fixture",
        b"P09 authorized fixed input\n",
        "text/plain",
        conditions=("isolated P09 input",),
        provenance="capture",
        access_level=access_level,
    )
    case.store.seal(access("collector-fixture", role="collector"), TASK, artifact)
    human = access("reader-fixture", role="human")
    claim = case.claims.propose(
        human,
        TASK,
        {
            "client_ref": "p09-input-claim",
            "kind": "observation-summary",
            "assertion_role": "candidate_fact",
            "text": "The isolated P09 input is available.",
            "structured_assertion": {"fixture": "p09"},
            "basis_refs": [
                {
                    "entity_type": "artifact",
                    "id": artifact.id,
                    "revision": artifact.version.root,
                }
            ],
            "limitations": ["isolated fixture"],
        },
        idempotency_key="p09-input-claim",
    )
    intent = case.claims.propose_intent(
        human,
        TASK,
        {
            "client_ref": "p09-intent",
            "question": "Read the isolated P09 input.",
            "basis_refs": [claim.canonical_ref.model_dump(mode="json")],
            "expected_output": "wuji.agent-payload.v2",
        },
        idempotency_key="p09-intent",
    )
    return artifact, claim.canonical_ref, intent.canonical_ref


@contextmanager
def scheduler_case(
    environment,
    tmp_path: Path,
    audit_directory: Path,
    *,
    template_clearance: int = 1,
    input_access_level: int = 1,
    max_work_items: int = 4,
    capacity: int = 2,
    profiles: dict[str, dict[str, object]] | None = None,
    gateway_url: str = "https://model.fixture.invalid/v1",
    approval_required: bool = False,
    max_single_output_bytes: int = 4096,
    max_total_output_bytes: int = 65_536,
    evaluation_mode: str | None = None,
    reason_retry_attempts: int = 0,
    repair_attempts: int = 1,
    max_no_progress_rounds: int | None = None,
    max_reason_runs: int = 2,
    task_run_limits: dict[str, int] | None = None,
    definition_task_run_limits: dict[str, int] | None = None,
    explore_concurrency: int | None = None,
    completion=None,
    component_registrar=None,
    admission_config=None,
    seed_intent=True,
):
    keys = SchedulerKeys.generate()
    with control_case(environment, tmp_path, audit_directory) as control:
        profiles = (
            profiles(control)
            if callable(profiles)
            else profiles or _profiles(_lock_digest())
        )
        _configure_scheduler(
            control,
            profiles=profiles,
            template_clearance=template_clearance,
            max_work_items=max_work_items,
            capacity=capacity,
            gateway_url=gateway_url,
            approval_required=approval_required,
            max_single_output_bytes=max_single_output_bytes,
            max_total_output_bytes=max_total_output_bytes,
            evaluation_mode=evaluation_mode,
            reason_retry_attempts=reason_retry_attempts,
            repair_attempts=repair_attempts,
            max_no_progress_rounds=max_no_progress_rounds,
            max_reason_runs=max_reason_runs,
            task_run_limits=task_run_limits,
            definition_task_run_limits=definition_task_run_limits,
            explore_concurrency=explore_concurrency,
            component_registrar=component_registrar,
            admission_config=admission_config,
        )
        if seed_intent:
            artifact_ref, claim_ref, intent_ref = _publish_intent(
                control, access_level=input_access_level
            )
        else:
            command(control, "start")
            artifact_ref = claim_ref = intent_ref = None
        issuer = RunCredentialIssuer(
            signing_key_resolver=keys.signing,
            encryption_key_resolver=keys.encryption,
            public_key_resolver=keys.public,
        )
        registry = AdmissionRegistry(control.uow)
        snapshots = SnapshotRepository(control.uow)
        with environment.additional_app_connection() as scheduler_connection:
            ownership = SchedulerOwnership(scheduler_connection)
            if not ownership.acquire():
                raise AssertionError(
                    "isolated P09 scheduler could not acquire ownership"
                )
            scheduler = Scheduler(
                control.uow,
                ownership=ownership,
                accesses=(SCHEDULER,),
                snapshots=snapshots,
                registry=registry,
                control=control.control,
                credential_issuer=issuer,
                completion=completion(control) if callable(completion) else completion,
            )
            try:
                yield SimpleNamespace(
                    control=control,
                    scheduler=scheduler,
                    ownership=ownership,
                    issuer=issuer,
                    registry=registry,
                    snapshots=snapshots,
                    keys=keys,
                    profiles=profiles,
                    artifact_ref=artifact_ref,
                    claim_ref=claim_ref,
                    intent_ref=intent_ref,
                    scheduler_access=SCHEDULER,
                    receiver_access=RECEIVER_ACCESS,
                )
            finally:
                ownership.close()


def publish_additional_intent(case, suffix: str, *, include_basis: bool = True):
    receipt = case.control.claims.propose_intent(
        access("reader-fixture", role="human"),
        TASK,
        {
            "client_ref": "p09-intent-" + suffix,
            "question": "Read another isolated P09 input: " + suffix,
            "basis_refs": (
                [case.claim_ref.model_dump(mode="json")] if include_basis else []
            ),
            "expected_output": "wuji.agent-payload.v2",
        },
        idempotency_key="p09-intent-" + suffix,
    )
    if receipt.canonical_ref is None:
        raise AssertionError("production intent proposal was not accepted")
    return receipt.canonical_ref


def explore_assignment(receipt):
    return next(
        item for item in receipt.assignments if item.work_kind.value == "explore"
    )


def worker_credential(case, assignment):
    with case.control.uow.transaction(
        case.receiver_access, TASK, capability="observe"
    ) as tx:
        persisted, credential_ref = DispatchRepository().read(
            tx, operation_id=assignment.operation_id
        )
        if persisted != assignment:
            raise AssertionError("dispatch lookup changed the immutable assignment")
        token = case.issuer.retrieve(
            tx, credential_ref=credential_ref, identity=assignment.identity
        )
    verifier = TokenVerifier(
        public_key_pem=case.keys.public_pem, issuer=ISSUER, audience=AUDIENCE
    )
    principal = verifier.verify(token)
    return SimpleNamespace(
        token=token,
        principal=principal,
        access=AccessContext(principal, "p09-worker"),
        credential_ref=credential_ref,
        binding=case.registry.binding(AccessContext(principal, "p09-binding")),
    )


def signed_sibling_worker(case, *, subject: str) -> AccessContext:
    now = int(datetime.now(UTC).timestamp())
    token = jwt.encode(
        {"alg": "RS256", "kid": "p09-test-key"},
        {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": subject,
            "tenant_id": OWNER[0],
            "roles": ["worker"],
            "iat": now,
            "nbf": now,
            "exp": now + int(timedelta(minutes=5).total_seconds()),
            "jti": str(uuid4()),
        },
        RSAKey.import_key(case.keys.private_pem),
        algorithms=["RS256"],
    )
    principal = TokenVerifier(
        public_key_pem=case.keys.public_pem, issuer=ISSUER, audience=AUDIENCE
    ).verify(token)
    return AccessContext(principal, "p09-unregistered-sibling-token")

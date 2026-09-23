"""Real Core CTF catalog material adapted only to the isolated test owner."""

from copy import deepcopy
from pathlib import Path
import sys

from support.p06 import ENVIRONMENT, OWNER, RECEIVER
from wuji_core.http import strict_json_loads


ROOT = Path(__file__).resolve().parents[3]
OPS = ROOT / "ops" / "vnext"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

import core_ctf_catalog  # noqa: E402
import task_launch  # noqa: E402


PROCESS_REFS = core_ctf_catalog.PROCESS_REFS
WORKSPACE_REFS = core_ctf_catalog.WORKSPACE_REFS


def catalog(*, explore_limit=3, pool_capacity=6):
    return core_ctf_catalog.owner_template(
        {
            "database": {
                "host": "postgres.fixture.invalid",
                "port": 5432,
                "dbname": "wuji",
                "password": "must-not-copy",
            },
            "roles": {},
            "owner": list(OWNER),
            "identity": {
                "issuer": "https://identity.fixture.invalid",
                "audience": "wuji-vnext-tests",
            },
            "ca_file": "/config/ca.crt",
            "public_key_file": "/config/identity.pub",
            "operator_token_file": "/run/wuji/operator.token",
            "operator_subject": "operator-fixture",
            "pod_controller_subject": "observer-fixture",
        },
        mode="mechanism_synthetic",
        published_at=core_ctf_catalog.PUBLISHED_AT,
        lock_digest=task_launch.shipped_worker_lock_digest(),
        namespace="wuji-core-fixture",
        model_gateway_url="http://127.0.0.1:8081/v1/chat/completions",
        client_model="core-fixture-model",
        upstream_model="fixture/core-model",
        task_key_ref="core-fixture-model-key",
        model_capability_ref="core-fixture-model-capability-v1",
        kali_image_digest="d" * 64,
        architecture="amd64",
        action_signing_key_ref="core-fixture-action-key",
        action_signing_kid="core-fixture-action-kid",
        explore_limit=explore_limit,
        pool_capacity=pool_capacity,
    )


def profile_factory(value):
    """Render the same profiles Task launch publishes for the real catalog."""

    def profiles(case):
        with case.env.migration_connection() as connection:
            definition = strict_json_loads(
                connection.execute(
                    "SELECT definition_json FROM vnext.task WHERE tenant_id=%s "
                    "AND project_id=%s AND task_id=%s",
                    OWNER,
                ).fetchone()[0]
            )
        definition.update(
            evaluation_mode=value["evaluation_mode"],
            model_profile=deepcopy(value["definition"]["model_profile"]),
            runtime_profile=deepcopy(value["definition"]["runtime_profile"]),
            lock_digest=value["definition"]["lock_digest"],
        )
        definition["task"]["model_profile_ref"] = value["definition"][
            "model_profile"
        ]["ref"]
        definition["task"]["runtime_profile_ref"] = value["definition"][
            "runtime_profile"
        ]["ref"]
        definition["task"]["explore_concurrency"] = value["definition"][
            "runtime_profile"
        ]["task_run_limits"]["explore"]
        return task_launch.published_session_profiles(value, definition)

    return profiles


def component_registrar(value):
    """Register the catalog's tools and its Task-specific executor binding."""

    def register(registry, connection):
        for tool in value["tools"]:
            registry.register_tool_definition(
                connection,
                tenant_id=OWNER[0],
                definition=deepcopy(tool),
            )
        executor = {
            **deepcopy(value["executor"]),
            "receiver_id": RECEIVER,
            "environment_ref": ENVIRONMENT,
            "collector_subject": "collector-fixture",
        }
        registry.register_executor(
            connection,
            owner=OWNER,
            executor=executor,
        )

    return register

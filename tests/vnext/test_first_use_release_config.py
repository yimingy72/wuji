"""First-use release configuration tests, no cluster or supplier access."""
import base64
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops/vnext"))
import first_use_catalog as catalog
import task_launch
from wuji_core.admission.registry import ModelProfile, RuntimeProfile, ToolDefinition
from wuji_core.admission.tools import HttpTargetExecutor, validate_input_schema
from wuji_core.http import strict_json_loads
from wuji_core.persistence.uow import DomainError
from wuji_maf_worker.factory import ProblemHarnessProfile, parse_profile

spec = importlib.util.spec_from_file_location("first_use_manifests", ROOT / "ops/vnext/kubernetes/first_use.py")
manifests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifests)


def source():
    result = {key: {} for key in ("database", "roles", "identity")}
    result["database"] = {"host": "postgres.invalid", "port": 5432, "dbname": "isolated", "password": "bootstrap-test-password"}
    result.update(owner=["tenant", "project", "old-anchor"], ca_file="/config/ca.crt",
                  public_key_file="/config/identity.pub", operator_token_file="/run/wuji/bootstrap/operator.token",
                  operator_subject="operator", pod_controller_subject="pod-controller",
                  materials=[{"path": "answer.txt", "text": "old scripted answer"}],
                  seed_intent={"question": "old seed"}, trial={"expected": "old answer"})
    return result


@pytest.mark.parametrize("mode", ["mechanism_synthetic", "real_model"])
def test_catalog_keeps_immutable_limits_without_old_fixture_answers(mode):
    config = catalog.owner_template(source(), mode=mode, lock_digest="a" * 64)
    assert config == catalog.owner_template(source(), mode=mode, lock_digest="a" * 64)
    assert not {"materials", "seed_intent", "trial"} & config.keys()
    assert "old scripted" not in json.dumps(config)
    assert "bootstrap-test-password" not in json.dumps(config)
    assert ModelProfile.model_validate(config["definition"]["model_profile"]).model_dump(mode="json") == config["definition"]["model_profile"]
    runtime = RuntimeProfile.model_validate(config["definition"]["runtime_profile"])
    assert runtime.model_dump(mode="json") == config["definition"]["runtime_profile"]
    assert runtime.limits.max_tool_calls == 4
    assert runtime.limits.max_model_requests == 12
    assert runtime.limits.max_elapsed_seconds == 600
    assert runtime.revision == "2"
    assert runtime.buffer_bytes == runtime.limits.max_single_output_bytes == 1048576
    for tool in config["tools"]:
        ToolDefinition.model_validate(tool)
        validate_input_schema(tool["input_schema"])
    assert config["tools"][1]["input_schema"]["properties"]["method"]["enum"] == ["GET", "HEAD"]
    for kind in ("reason", "report"):
        assert config["definition"]["worker_profiles"][kind]["body"]["tool_definition_refs"] == []
    instructions = config["definition"]["worker_profiles"]["reason"]["body"]["instructions"]
    assert "When read_set is empty" in instructions
    assert "initial Intent must use an empty basis_refs list" in instructions
    assert "Do not create work merely because the queue is empty" in instructions
    assert "propose one bounded initial problem" in task_launch.ROLE_DUTIES["reason"]
    assert "do not use ProposalLocalRef" in instructions
    assert "at most three independent problems" in instructions
    assert "AgentPayloadV3" in instructions
    assert "no work_result" in instructions
    explore = config["definition"]["worker_profiles"]["explore"]["body"]
    assert explore["ref"] == "first-use-explore-instructions-v6"
    assert explore["revision"] == "6"
    assert "inside this WorkItem and Session" in explore["instructions"]
    assert "read exact fixed material on demand" in explore["instructions"]
    assert "finish without tools" in explore["instructions"]
    assert "AgentPayloadV3" in explore["instructions"]
    assert config["problem_core_enabled"] is True
    assert ("mechanism_http_origins" in config) == (mode == "mechanism_synthetic")


def test_first_use_http_envelope_keeps_an_approved_large_response(tmp_path):
    runtime = RuntimeProfile.model_validate(
        catalog.owner_template(source(), mode="real_model", lock_digest="a" * 64)[
            "definition"
        ]["runtime_profile"]
    )
    executor = HttpTargetExecutor(
        receipt_root=tmp_path,
        admission=object(),
        receiver_id="receiver",
        environment_ref="environment",
    )
    body = b"x" * 250042
    raw, truncated = executor._exchange(
        SimpleNamespace(
            runtime=runtime,
            resource_keys=("target:http://39.97.227.109:80:read:run",),
            tool_attempt_id="attempt",
        ),
        "http://39.97.227.109/static/js/app.js",
        "GET",
        body=body,
        headers={"accept": "*/*"},
        status=200,
        response_headers={"content-length": str(len(body))},
        truncated=False,
    )
    document = strict_json_loads(raw)
    assert truncated is False
    assert len(raw) <= runtime.limits.max_single_output_bytes
    assert document["response"]["truncated"] is False
    assert base64.b64decode(document["response"]["body_base64"]) == body


def test_problem_catalog_publishes_exact_native_and_host_capabilities():
    lock = task_launch.shipped_worker_lock_digest()
    config = catalog.owner_template(source(), mode="real_model", lock_digest=lock)
    definition = {
        **config["definition"],
        "evaluation_mode": "real_model",
        "task": {
            "schema_version": "wuji.api.v2", "project_id": "project", "name": "problem",
            "scenario": "web_single",
            "goal": {"text": "Determine the fixed material version.", "criteria": [{
                "criterion_id": "version", "object": "material", "condition": "version identified",
                "evidence_requirements": ["fixed source"], "allowed_methods": ["deterministic"],
                "responsible_party": "platform", "required": True,
            }]},
            "authorization_scope": [{"host": "fixture.invalid", "protocol": "https", "port": 443}],
            "authorization_expires_at": "2026-09-22T17:00:00+08:00",
            "entry_points": ["https://fixture.invalid/"], "external_analysis_approved": True,
            "model_profile_ref": config["definition"]["model_profile"]["ref"],
            "runtime_profile_ref": config["definition"]["runtime_profile"]["ref"],
            "budget": {"amount": "1", "currency": "USD"},
        },
        "start_points": ["https://fixture.invalid/"],
    }
    profiles = task_launch.published_session_profiles(config, definition)
    reason, explore = profiles["reason"], profiles["explore"]
    assert isinstance(parse_profile(reason), ProblemHarnessProfile)
    assert isinstance(parse_profile(explore), ProblemHarnessProfile)
    assert profiles["report"]["body"]["schema_version"] == "wuji.harness.session.v1"
    assert reason["body"]["memory_mode"] == "disabled"
    assert explore["body"]["memory_mode"] == "work_memory"
    assert explore["body"]["tool_choice_policy"] == "auto"
    assert '"const":"wuji.agent-payload.v3"' in reason["body"]["instructions"]
    reason_names = {item["name"] for item in reason["body"]["capability_manifest"]}
    assert {"knowledge_list", "knowledge_read"} <= reason_names
    assert "knowledge_refresh" not in reason_names
    categories = {item["name"]: item["category"] for item in explore["body"]["capability_manifest"]}
    assert categories["todos_add"] == "session_state"
    assert categories["file_memory_write"] == "session_state"
    assert categories["knowledge_read"] == "knowledge_read"
    assert categories["knowledge_refresh"] == "knowledge_read"
    assert categories["http_target_get"] == "environment_action"


@pytest.mark.parametrize("methods", [[], ["POST"], ["GET", "POST"]])
def test_catalog_http_method_schema_cannot_expand_read_only_methods(methods):
    config = catalog.owner_template(source(), mode="mechanism_synthetic", lock_digest="a" * 64)
    schema = config["tools"][1]["input_schema"]
    schema["properties"]["method"]["enum"] = methods
    with pytest.raises(DomainError):
        validate_input_schema(schema)


def test_launcher_separates_owner_management_and_provider_secrets():
    images = {role: "local/" + role + "@sha256:" + "b" * 64 for role in ("agent", "kali", "platform")}
    config, deployment = manifests.launch_manifests(images=images, mode="real_model", source_revision="c" * 40,
        evidence_ref="tests/protocol-actual", public_data={"ca.crt": "test-ca", "identity.pub": "test-public"})
    settings = json.loads(config["data"]["launch.json"])
    assert settings["gateway_url"] == "https://first-use-litellm.wuji-first-use-model.svc:4000"
    assert catalog.GATEWAY_ORIGIN == settings["gateway_url"]
    pod = deployment["spec"]["template"]["spec"]
    owner = next(volume["secret"] for volume in pod["volumes"] if volume["name"] == "input")
    assert owner["secretName"] == "first-use-deepseek-owner-v11"
    assert pod["serviceAccountName"] == "first-use-launch"
    management = next(volume["secret"] for volume in pod["volumes"] if volume["name"] == "gateway")
    assert management["items"] == [{"key": "master.key", "path": "master.key"}]
    assert "deepseek-provider" not in json.dumps([config, deployment])
    grants = [item for item in manifests.rbac_manifests() if item["kind"] == "Role"]
    launch = next(item for item in grants if item["metadata"]["name"] == "first-use-launch")
    assert all("deployments" not in item["resources"] for item in launch["rules"])
    assert all("list" not in item["verbs"] and "update" not in item["verbs"]
               for item in launch["rules"] if "secrets" in item["resources"])
    gate = next(item for item in grants if item["metadata"]["name"] == "first-use-gates")
    assert gate["rules"] == [{"apiGroups": [""], "resources": ["secrets"], "resourceNames": ["task-model-keys"], "verbs": ["get"]}]


def test_explicit_capacity_set_requires_published_matching_tenant():
    records = {"global-new": ("global", None), "tenant-a": ("tenant", "tenant"), "model-new": ("model", None)}
    connection = SimpleNamespace(execute=lambda query, args: SimpleNamespace(fetchone=lambda: records.get(args[0])))
    config = {"owner": ["tenant", "project", "old-anchor"], "capacity_pool_keys": list(records)}
    assert task_launch.deployment_pool_keys(connection, config) == tuple(sorted(records))
    records["tenant-a"] = ("tenant", "another-tenant")
    with pytest.raises(ValueError, match="unavailable"):
        task_launch.deployment_pool_keys(connection, config)
    records.pop("model-new")
    with pytest.raises(ValueError, match="unavailable"):
        task_launch.deployment_pool_keys(connection, config)

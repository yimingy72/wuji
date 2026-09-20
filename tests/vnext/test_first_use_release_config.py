"""First-use release configuration tests, no cluster or supplier access."""
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
from wuji_core.admission.tools import validate_input_schema
from wuji_core.persistence.uow import DomainError

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
    for tool in config["tools"]:
        ToolDefinition.model_validate(tool)
        validate_input_schema(tool["input_schema"])
    assert config["tools"][1]["input_schema"]["properties"]["method"]["enum"] == ["GET", "HEAD"]
    for kind in ("reason", "report"):
        assert config["definition"]["worker_profiles"][kind]["body"]["tool_definition_refs"] == []
    instructions = config["definition"]["worker_profiles"]["reason"]["body"]["instructions"]
    assert "When read_set is empty" in instructions
    assert "initial Intent must use an empty basis_refs list" in instructions
    assert "propose exactly one Intent" in instructions
    assert "do not use ProposalLocalRef" in instructions
    assert "return claims=[]" in instructions
    assert "Never wait on the current Reason WorkItem" in instructions
    assert "propose that Intent" in instructions
    explore = config["definition"]["worker_profiles"]["explore"]["body"]
    assert explore["ref"] == "first-use-explore-instructions-v4"
    assert explore["revision"] == "4"
    assert "no more than two target HTTP reads" in explore["instructions"]
    assert "never wait on that same Intent" in explore["instructions"]
    assert "call http_target_get before the final response" in explore["instructions"]
    assert "'/' is never such a path" in explore["instructions"]
    assert "observation-summary claim" in explore["instructions"]
    assert "final response is the DeepSeek analysis" in explore["instructions"]
    assert "at most one later HTTP read" in explore["instructions"]
    assert ("mechanism_http_origins" in config) == (mode == "mechanism_synthetic")


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
    assert owner["secretName"] == "first-use-deepseek-owner-v6"
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

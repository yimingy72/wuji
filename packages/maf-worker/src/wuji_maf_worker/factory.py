"""Fixed M1 profiles and the released MAF harness factory; no application loop."""

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import re
import sys

from agent_framework import ContextWindowCompactionStrategy, create_harness_agent
from agent_framework.openai import OpenAIChatCompletionClient
from openai import AsyncOpenAI

from wuji_core.http import canonical_json_bytes
from wuji_core.contracts.sessions import SessionLimits
from wuji_core.contracts.knowledge import KnowledgeRef


@dataclass(frozen=True)
class HarnessProfile:
    ref: str
    revision: str
    work_kind: str
    instructions: str
    tool_definition_refs: tuple[str, ...]
    lock_digest: str
    max_context_records: int
    max_context_bytes: int
    max_output_tokens: int
    material_representation: str | None = field(default=None, kw_only=True)

    def __post_init__(self):
        if (
            not 1 <= len(self.ref) <= 256
            or not re.fullmatch(r"[1-9][0-9]*", self.revision)
            or self.work_kind not in {"reason", "explore", "report"}
            or self.material_representation not in {None, "wuji.model-material.v2"}
            or not 1 <= len(self.instructions) <= 32768
            or not self.tool_definition_refs
            or len(set(self.tool_definition_refs)) != len(self.tool_definition_refs)
            or any(not 1 <= len(ref) <= 256 for ref in self.tool_definition_refs)
            or not re.fullmatch(r"[a-f0-9]{64}", self.lock_digest)
            or any(type(n) is not int or n <= 0 for n in (
                self.max_context_records, self.max_context_bytes, self.max_output_tokens
            ))
        ):
            raise ValueError("invalid published M1 harness profile")

    def snapshot(self):
        body = asdict(self)
        if self.material_representation is None:
            body.pop("material_representation")
        body["tool_definition_refs"] = list(self.tool_definition_refs)
        body["capabilities"] = {
            key: False for key in (
                "todo", "mode", "file_memory", "file_access", "skills", "shell",
                "web_search", "background_agents", "outer_loop", "auto_approval",
                "compaction", "restoration", "mcp",
            )
        }
        return {
            "ref": self.ref, "revision": self.revision,
            "digest": sha256(canonical_json_bytes(body)).hexdigest(), "body": body,
        }

    @classmethod
    def from_snapshot(cls, snapshot):
        body = dict(snapshot["body"])
        body.pop("capabilities", None)
        body["tool_definition_refs"] = tuple(body["tool_definition_refs"])
        profile = cls(**body)
        if canonical_json_bytes(profile.snapshot()) != canonical_json_bytes(snapshot):
            raise ValueError("harness profile snapshot mismatch")
        return profile


@dataclass(frozen=True)
class SessionHarnessProfile(HarnessProfile):
    """An explicit candidate combination; only the platform can publish it."""

    history_source_id: str
    memory_mode: str
    memory_source_id: str
    session_limits: SessionLimits
    max_context_window_tokens: int
    compaction_enabled: bool
    memory_inputs: tuple[dict, ...] = ()
    schema_version: str = "wuji.harness.session.v1"

    def __post_init__(self):
        super().__post_init__()
        if (
            self.schema_version != "wuji.harness.session.v1"
            or self.memory_mode not in {"disabled", "pinned_context"}
            or not isinstance(self.session_limits, SessionLimits)
            or type(self.compaction_enabled) is not bool
            or type(self.max_context_window_tokens) is not int
            or self.max_context_window_tokens <= self.max_output_tokens
            or any(not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", source) for source in (
                self.history_source_id, self.memory_source_id,
            ))
            or self.history_source_id == self.memory_source_id
            or {self.history_source_id, self.memory_source_id} & {"compaction"}
        ):
            raise ValueError("invalid versioned Session Profile")
        paths, refs = set(), set()
        for item in self.memory_inputs:
            if not isinstance(item, dict) or set(item) != {"path", "ref"}:
                raise ValueError("memory input requires one fixed path and reference")
            path = item["path"]
            reference = KnowledgeRef.model_validate(item["ref"])
            if (
                self.memory_mode != "pinned_context"
                or reference.entity_type.value != "artifact"
                or not isinstance(path, str)
                or not 1 <= len(path.encode("utf-8")) <= 1024
                or path.startswith("/")
                or "\\" in path
                or any(ord(char) < 32 or ord(char) == 127 for char in path)
                or any(part in {"", ".", ".."} for part in path.split("/"))
                or path in paths
                or (reference.id, reference.revision.root) in refs
            ):
                raise ValueError("memory input must be a unique pinned artifact")
            paths.add(path)
            refs.add((reference.id, reference.revision.root))
        if len(self.memory_inputs) > self.session_limits.max_objects:
            raise ValueError("memory inputs exceed the fixed Session object limit")

    def snapshot(self):
        body = {name: getattr(self, name) for name in HarnessProfile.__dataclass_fields__}
        if self.material_representation is None:
            body.pop("material_representation")
        body["tool_definition_refs"] = list(self.tool_definition_refs)
        body.update({
            "schema_version": self.schema_version,
            "history_source_id": self.history_source_id,
            "memory_mode": self.memory_mode, "memory_source_id": self.memory_source_id,
            "session_limits": self.session_limits.model_dump(mode="python"),
            "max_context_window_tokens": self.max_context_window_tokens,
            "compaction_enabled": self.compaction_enabled,
            "capabilities": {key: False for key in (
                "todo", "mode", "file_memory", "file_access", "skills", "shell",
                "web_search", "background_agents", "outer_loop", "auto_approval", "mcp",
            )},
        })
        if self.memory_inputs:
            body["memory_inputs"] = [
                {
                    "path": item["path"],
                    "ref": KnowledgeRef.model_validate(item["ref"]).model_dump(
                        mode="json"
                    ),
                }
                for item in self.memory_inputs
            ]
        body["capabilities"].update({
            "compaction": self.compaction_enabled, "restoration": True,
            "native_approval": True, "versioned_memory": self.memory_mode != "disabled",
        })
        return {
            "ref": self.ref, "revision": self.revision,
            "digest": sha256(canonical_json_bytes(body)).hexdigest(), "body": body,
        }

    @classmethod
    def from_snapshot(cls, snapshot):
        body = dict(snapshot["body"])
        body.pop("capabilities", None)
        body["tool_definition_refs"] = tuple(body["tool_definition_refs"])
        body["session_limits"] = SessionLimits.model_validate(body["session_limits"])
        body["memory_inputs"] = tuple(body.get("memory_inputs", ()))
        profile = cls(**body)
        if canonical_json_bytes(profile.snapshot()) != canonical_json_bytes(snapshot):
            raise ValueError("Session Profile snapshot mismatch")
        return profile


def parse_profile(snapshot):
    if snapshot["body"].get("schema_version") == "wuji.harness.session.v1":
        return SessionHarnessProfile.from_snapshot(snapshot)
    return HarnessProfile.from_snapshot(snapshot)


def build_agent(*, resolved, profile, model_http, model_gate_url, run_credential,
                tools, middleware, response_parser, history=None, memory_provider=None):
    """Build the same released public Harness for a fixed fresh/restored profile."""
    if (
        sys.version_info[:3] != (3, 13, 15)
        or version("agent-framework-core") != "1.18.0"
        or version("agent-framework-openai") != "1.14.3"
        or sha256((Path(__file__).resolve().parents[2] / "uv.lock").read_bytes()).hexdigest()
        != profile.lock_digest
    ):
        raise ValueError("installed MAF release/lock does not match published profile")
    limits = resolved["limits"]
    if not tools or limits["max_model_requests"] < 1 or limits["max_tool_calls"] < 1:
        raise ValueError("M1 needs a nonempty bounded tool profile")
    session_options = {}
    if isinstance(profile, SessionHarnessProfile):
        if (
            history is None or history.source_id != profile.history_source_id
            or history.compatibility.profile_snapshot != profile.snapshot()
            or history.limits != profile.session_limits
            or (memory_provider is not None) != (profile.memory_mode == "pinned_context")
            or profile.session_limits.max_object_bytes > limits["max_single_output_bytes"]
            or profile.session_limits.max_total_bytes > limits["max_total_output_bytes"]
        ):
            raise ValueError("providers do not match the fixed Session combination")
        if profile.memory_mode == "pinned_context":
            store = getattr(memory_provider, "store", None)
            snapshot_files = getattr(store, "snapshot_files", None)
            if not callable(snapshot_files):
                raise ValueError("fixed memory provider lacks an immutable file snapshot")
            expected_paths = {item["path"] for item in profile.memory_inputs}
            actual_paths = set(snapshot_files())
            if actual_paths != expected_paths:
                raise ValueError("fixed memory files do not match the published Session Profile")
        session_options = {"history_provider": history, "context_providers": []}
        if memory_provider is not None:
            if memory_provider.source_id != profile.memory_source_id:
                raise ValueError("memory source differs from the fixed profile")
            session_options["context_providers"].append(memory_provider)
        if profile.compaction_enabled:
            # These public strategies use native token/annotation processing,
            # never a hidden summarization client or another Agent loop.
            strategy_options = {
                "max_context_window_tokens": profile.max_context_window_tokens,
                "max_output_tokens": profile.max_output_tokens,
                "keep_last_tool_call_groups": 4,
                "preserve_first_user_group": True,
                "tool_eviction_threshold": 0.5, "truncation_threshold": 0.8,
            }
            session_options.update({
                "before_compaction_strategy": ContextWindowCompactionStrategy(**strategy_options),
                "after_compaction_strategy": ContextWindowCompactionStrategy(**strategy_options),
            })
    elif history is not None or memory_provider is not None:
        raise ValueError("M1 does not accept Session providers")
    native = AsyncOpenAI(
        api_key=run_credential, base_url=model_gate_url.rstrip("/") + "/",
        http_client=model_http, max_retries=0, organization="", project="",
    )
    client = OpenAIChatCompletionClient(
        model=resolved["client_model"], async_client=native,
        response_parser=response_parser,
        function_invocation_configuration={
            "enabled": True,
            "max_iterations": limits["max_model_requests"],
            "max_function_calls": limits["max_tool_calls"],
            "max_duration_seconds": float(limits["max_elapsed_seconds"]),
            "terminate_on_unknown_calls": True,
            "additional_tools": [], "include_detailed_errors": False,
        },
    )
    agent = create_harness_agent(
        client, name="wuji-" + profile.work_kind,
        harness_instructions="", agent_instructions=profile.instructions,
        tools=tools, middleware=[middleware],
        max_output_tokens=profile.max_output_tokens,
        disable_compaction=not (isinstance(profile, SessionHarnessProfile) and profile.compaction_enabled),
        disable_todo=True, disable_mode=True,
        disable_file_memory=True, file_access_store=None,
        skills_provider=None, skills_paths=None, shell_executor=None,
        background_agents=None, disable_web_search=True,
        disable_tool_auto_approval=True, loop_should_continue=None,
        default_options={"allow_multiple_tool_calls": False},
        **session_options,
    )
    return agent, native

"""Fixed M1 profiles and the released MAF harness factory; no application loop."""

from dataclasses import asdict, dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import re
import sys

from agent_framework import create_harness_agent
from agent_framework.openai import OpenAIChatCompletionClient
from openai import AsyncOpenAI

from wuji_core.http import canonical_json_bytes


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

    def __post_init__(self):
        if (
            not 1 <= len(self.ref) <= 256
            or not re.fullmatch(r"[1-9][0-9]*", self.revision)
            or self.work_kind not in {"reason", "explore", "report"}
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


def build_agent(*, resolved, profile, model_http, model_gate_url, run_credential,
                tools, middleware, response_parser):
    """Return the real Agent and its owned OpenAI transport for one fresh Run."""
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
        disable_compaction=True, disable_todo=True, disable_mode=True,
        disable_file_memory=True, file_access_store=None,
        skills_provider=None, skills_paths=None, shell_executor=None,
        background_agents=None, disable_web_search=True,
        disable_tool_auto_approval=True, loop_should_continue=None,
        default_options={"allow_multiple_tool_calls": False},
    )
    return agent, native

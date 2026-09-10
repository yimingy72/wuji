"""Restricted Deep Agents assembly and actual-tool-surface inspection."""

from __future__ import annotations

from typing import Any

from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, create_deep_agent, register_harness_profile
from deepagents.middleware.filesystem import FilesystemMiddleware

from .ipc_model import IpcChatModel
from .tools import EXPECTED_TOOL_NAMES, PROBE_TOOLS


_BUILT_IN_TOOL_NAMES = frozenset(
    {"ls", "read_file", "write_file", "edit_file", "delete", "glob", "grep", "execute", "task"}
)
_PROFILE_REGISTERED = False


def _register_restricted_profile() -> None:
    global _PROFILE_REGISTERED
    if _PROFILE_REGISTERED:
        return
    register_harness_profile(
        "wuji-ipc",
        HarnessProfile(
            excluded_tools=_BUILT_IN_TOOL_NAMES,
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )
    _PROFILE_REGISTERED = True


def build_restricted_harness(model: IpcChatModel) -> Any:
    """Build Deep Agents while leaving only the deterministic local tool visible."""

    _register_restricted_profile()
    # 0.7.13 requires read_file when a filesystem allowlist is constructed.
    # Clearing the resulting public tool list preserves the required middleware
    # scaffold while removing every filesystem dispatcher from the graph.
    filesystem = FilesystemMiddleware(tools=["read_file"])
    filesystem.tools = []
    return create_deep_agent(
        model=model,
        tools=list(PROBE_TOOLS),
        system_prompt=(
            "This is a deterministic connection check. Call wuji_synthetic_check exactly once. "
            "After its result, answer with WUJI_GATEWAY_OK and do not call another tool."
        ),
        middleware=(filesystem,),
        subagents=(),
        skills=None,
        memory=None,
        checkpointer=None,
        store=None,
    )


def compiled_tool_names(agent: Any) -> tuple[str, ...]:
    """Read tool names from the compiled graph instead of trusting input config."""

    node = agent.get_graph().nodes.get("tools")
    candidates = [getattr(node, "data", None), getattr(agent.nodes.get("tools"), "bound", None)]
    for candidate in candidates:
        tools_by_name = getattr(candidate, "tools_by_name", None)
        if isinstance(tools_by_name, dict):
            return tuple(sorted(tools_by_name))
    raise RuntimeError("compiled Deep Agents tool surface could not be inspected")


def assert_restricted_tool_surface(agent: Any) -> tuple[str, ...]:
    names = compiled_tool_names(agent)
    if names != EXPECTED_TOOL_NAMES:
        raise RuntimeError(f"unexpected compiled tool surface: {names!r}")
    return names

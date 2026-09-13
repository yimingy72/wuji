"""Execution wire types and the published WorkItem transition graph."""

from pydantic import model_validator

from wuji_core.contracts.generated import (
    AgentRunRecord,
    ApprovalDecision,
    ApprovalDecisionValue,
    AuthorizationScopeEntry,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ChatToolCall,
    ClaimWork,
    CloseTrigger,
    CommandDisposition,
    CommandReceipt,
    CommandResourceRef,
    CommandResourceType,
    ControlReceipt,
    ControlAction,
    ControlStatus,
    DependencyCondition,
    DispatchReceipt,
    DispatchStatus,
    ExecutionLimits,
    GoalCriterionRef,
    ModelMode,
    MoneyBudget,
    RecoveryClass,
    ResultOutcome,
    RunProcessState,
    RunResultState,
    SessionManifest,
    StartReceipt,
    StartStatus,
    SuspensionCause,
    TaskCommand,
    TaskCommandName,
    TaskCreate,
    TaskDesired,
    TaskObserved,
    TaskView,
    TestResult,
    TokenUsage,
    WorkCommand,
    WorkCommandName,
    WorkDependency as GeneratedWorkDependency,
    WorkDesired,
    WorkItemView,
    WorkKind,
    WorkState,
    WorkerAssignment,
    WorkerControl,
)


class WorkDependency(GeneratedWorkDependency):
    """Apply OpenAPI's conditional criterion requirement at the public boundary."""

    @model_validator(mode="after")
    def validate_condition_reference(self):
        if (self.condition == DependencyCondition.criterion_satisfied) != (
            self.criterion_ref is not None
        ):
            raise ValueError(
                "criterion_satisfied requires exactly one GoalCriterionRef"
            )
        return self


_ALLOWED_WORK_TRANSITIONS: frozenset[tuple[WorkState, WorkState]] = frozenset(
    {
        (WorkState.ready, WorkState.leased),
        (WorkState.leased, WorkState.running),
        (WorkState.leased, WorkState.reconciling),
        (WorkState.leased, WorkState.stopping),
        (WorkState.running, WorkState.waiting_input),
        (WorkState.running, WorkState.done),
        (WorkState.running, WorkState.failed),
        (WorkState.running, WorkState.stopping),
        (WorkState.running, WorkState.reconciling),
        (WorkState.ready, WorkState.blocked),
        (WorkState.blocked, WorkState.ready),
        (WorkState.ready, WorkState.cancelled),
        (WorkState.blocked, WorkState.cancelled),
        (WorkState.waiting_input, WorkState.cancelled),
        (WorkState.suspended, WorkState.cancelled),
        (WorkState.waiting_input, WorkState.ready),
        (WorkState.suspended, WorkState.ready),
        (WorkState.stopping, WorkState.suspended),
        (WorkState.stopping, WorkState.cancelled),
        (WorkState.stopping, WorkState.reconciling),
        (WorkState.reconciling, WorkState.done),
        (WorkState.reconciling, WorkState.failed),
        (WorkState.reconciling, WorkState.suspended),
        (WorkState.reconciling, WorkState.cancelled),
        (WorkState.ready, WorkState.suspended),
        (WorkState.blocked, WorkState.suspended),
        (WorkState.waiting_input, WorkState.suspended),
        (WorkState.suspended, WorkState.waiting_input),
        (WorkState.suspended, WorkState.blocked),
    }
)


def can_transition_work(current: WorkState, target: WorkState) -> bool:
    """Return whether the versioned contract publishes this direct transition."""

    return (current, target) in _ALLOWED_WORK_TRANSITIONS


__all__ = [
    "AgentRunRecord",
    "ApprovalDecision",
    "ApprovalDecisionValue",
    "AuthorizationScopeEntry",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
    "ChatToolCall",
    "ClaimWork",
    "CloseTrigger",
    "CommandDisposition",
    "CommandReceipt",
    "CommandResourceRef",
    "CommandResourceType",
    "ControlReceipt",
    "ControlAction",
    "ControlStatus",
    "DependencyCondition",
    "DispatchReceipt",
    "DispatchStatus",
    "ExecutionLimits",
    "GoalCriterionRef",
    "ModelMode",
    "MoneyBudget",
    "RecoveryClass",
    "ResultOutcome",
    "RunProcessState",
    "RunResultState",
    "SessionManifest",
    "StartReceipt",
    "StartStatus",
    "SuspensionCause",
    "TaskCommand",
    "TaskCommandName",
    "TaskCreate",
    "TaskDesired",
    "TaskObserved",
    "TaskView",
    "TestResult",
    "TokenUsage",
    "WorkCommand",
    "WorkCommandName",
    "WorkDependency",
    "WorkDesired",
    "WorkItemView",
    "WorkKind",
    "WorkState",
    "WorkerAssignment",
    "WorkerControl",
    "can_transition_work",
]

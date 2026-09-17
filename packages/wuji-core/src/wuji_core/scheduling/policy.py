"""Deterministic bounded selection over a frozen, non-authoritative read model."""

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256

from wuji_core.http.json_boundary import canonical_json_bytes


@dataclass(frozen=True)
class WorkKey:
    problem_id: str
    intent_id: str | None
    intent_revision: str | None
    method_ref: str
    profile_digest: str
    basis: tuple[tuple[str, str, str], ...]
    environment_ref: str
    output_contract: str

    def __post_init__(self):
        if any(
            not isinstance(x, str) or not x
            for x in (
                self.problem_id,
                self.method_ref,
                self.profile_digest,
                self.environment_ref,
                self.output_contract,
            )
        ) or (self.intent_id is None) != (self.intent_revision is None):
            raise ValueError("incomplete exact work identity")
        if self.intent_revision is not None and (
            not self.intent_id
            or not self.intent_revision.isdecimal()
            or str(int(self.intent_revision)) != self.intent_revision
        ):
            raise ValueError("invalid fixed intent revision")
        if not isinstance(self.basis, tuple) or any(
            not isinstance(ref, tuple)
            or len(ref) != 3
            or ref[0] not in {"artifact", "observation", "claim", "intent"}
            or not all(isinstance(x, str) and x for x in ref)
            or not ref[2].isdecimal()
            or str(int(ref[2])) != ref[2]
            for ref in self.basis
        ):
            raise ValueError("invalid exact basis")

    def digest(self):
        # Arrays retain their specified order, as required by canonical JSON.
        return sha256(canonical_json_bytes(asdict(self))).hexdigest()


def problem_digest(
    *,
    question,
    basis,
    method_ref,
    profile_digest,
    environment_ref,
    output_contract,
):
    """The exact same question, basis, method, environment and output contract.

    A new Intent ID, a renamed client reference, a re-ordered basis list or a
    later timestamp never changes this digest: those are the same question asked
    twice. A new basis reference or a different environment does change it,
    because continuing one question under new evidence is legitimate work.
    Wording is compared as published — only surrounding whitespace is collapsed —
    so a reworded question is *not* claimed to be the same question.
    """

    return sha256(
        canonical_json_bytes(
            {
                "question": " ".join(str(question).split()),
                "basis": [list(item) for item in sorted(basis)],
                "method_ref": method_ref,
                "profile_digest": profile_digest,
                "environment_ref": environment_ref,
                "output_contract": output_contract,
            }
        )
    ).hexdigest()


@dataclass(frozen=True)
class Candidate:
    tenant_id: str
    task_id: str
    work_item_id: str
    kind: str
    priority: int
    ready_since: datetime
    eligible: bool = True
    consideration_round: int = 0

    def __post_init__(self):
        if not all(
            isinstance(v, str) and v
            for v in (
                self.tenant_id,
                self.task_id,
                self.work_item_id,
            )
        ) or self.kind not in {"reason", "explore", "report"}:
            raise ValueError("invalid candidate identity")
        if type(self.priority) is not int or not -10 <= self.priority <= 10:
            raise ValueError("priority must be bounded to -10..10")
        if (
            self.ready_since.tzinfo is None
            or type(self.eligible) is not bool
            or type(self.consideration_round) is not int
            or self.consideration_round < 0
        ):
            raise ValueError("candidate requires an aware timestamp")


@dataclass(frozen=True)
class SchedulingSnapshot:
    candidates: tuple[Candidate, ...]
    now: datetime
    tenant_cursor: str | None = None
    task_cursors: tuple[tuple[str, str], ...] = ()
    limit: int = 16
    aging_seconds: int = 60

    def __post_init__(self):
        if (
            not isinstance(self.candidates, tuple)
            or self.now.tzinfo is None
            or type(self.limit) is not int
            or not 1 <= self.limit <= 256
            or type(self.aging_seconds) is not int
            or self.aging_seconds < 1
            or not isinstance(self.task_cursors, tuple)
        ):
            raise ValueError("invalid frozen scheduling snapshot")
        keys = [(c.tenant_id, c.task_id, c.work_item_id) for c in self.candidates]
        if len(set(keys)) != len(keys) or len(dict(self.task_cursors)) != len(
            self.task_cursors
        ):
            raise ValueError("duplicate candidate or cursor")


@dataclass(frozen=True)
class SelectionProposal:
    tenant_id: str
    task_id: str
    work_item_id: str


def _after(values, cursor):
    values = sorted(values)
    return [v for v in values if cursor is None or v > cursor] + [
        v for v in values if cursor is not None and v <= cursor
    ]


class SchedulerPolicy:
    @staticmethod
    def select(snapshot):
        if not isinstance(snapshot, SchedulingSnapshot):
            raise ValueError("a frozen SchedulingSnapshot is required")
        groups = {}
        for candidate in snapshot.candidates:
            if candidate.eligible:
                groups.setdefault(candidate.tenant_id, {}).setdefault(
                    candidate.task_id, []
                ).append(candidate)

        def rank(candidate):
            age = max(0, int((snapshot.now - candidate.ready_since).total_seconds()))
            # A finite control bonus cannot defeat unbounded waiting age.
            score = (
                age // snapshot.aging_seconds
                + candidate.priority
                + (3 if candidate.kind in {"reason", "report"} else 0)
            )
            # Every Work participates once per persisted consideration round.
            # Priority and aging rank candidates only within that round, so a
            # repeatedly rejected high-rank Work cannot reclaim the next batch.
            return (
                candidate.consideration_round,
                -score,
                candidate.ready_since,
                candidate.work_item_id,
            )

        for tasks in groups.values():
            for candidates in tasks.values():
                candidates.sort(key=rank)
        cursors = dict(snapshot.task_cursors)
        tenant_cursor = snapshot.tenant_cursor
        selected = []
        while groups and len(selected) < snapshot.limit:
            tenant = _after(groups, tenant_cursor)[0]
            tasks = groups[tenant]
            task = _after(tasks, cursors.get(tenant))[0]
            candidate = tasks[task].pop(0)
            selected.append(SelectionProposal(tenant, task, candidate.work_item_id))
            tenant_cursor, cursors[tenant] = tenant, task
            if not tasks[task]:
                del tasks[task]
            if not tasks:
                del groups[tenant]
        return tuple(selected)


@dataclass(frozen=True)
class ProgressSummary:
    new_material: int = 0
    resolved_blockers: int = 0
    new_problem_classes: int = 0
    classification: str = "unknown"

    def __post_init__(self):
        if any(
            type(n) is not int or n < 0
            for n in (
                self.new_material,
                self.resolved_blockers,
                self.new_problem_classes,
            )
        ) or self.classification not in {"known", "unknown"}:
            raise ValueError("invalid observable progress")

    @property
    def made_progress(self):
        return bool(
            self.new_material
            or self.resolved_blockers
            or (self.classification == "known" and self.new_problem_classes)
        )

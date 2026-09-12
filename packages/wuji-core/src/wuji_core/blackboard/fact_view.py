"""Published-policy aggregation over one immutable ClaimRevision body."""

from wuji_core.contracts.knowledge import ClaimRecord, KnowledgeRef
from wuji_core.contracts.generated import ClaimAssessmentView, RecordView, IntentRecord
from wuji_core.persistence.uow import DomainError, row
from wuji_core.http.json_boundary import strict_json_loads
from wuji_core.blackboard.relations import resolve, policy


def fact_view_eligible(claim_kind, grounding, evidence, applicability, method):
    return (
        claim_kind in {"observation-summary", "derived-conclusion"}
        and grounding == "content_checked"
        and evidence == "supported"
        and applicability == "current"
        and method in {"deterministic", "reproduced_check", "human_attestation"}
    )


def claim_record(tx, claim):
    prior = tx.connection.execute(
        "SELECT target_type,target_id,target_revision FROM vnext.entity_relation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND source_type='claim' AND source_id=%s AND source_revision=%s AND relation='supersedes'",
        (*tx.owner, claim["entity_id"], claim["revision"]),
    ).fetchone()
    return ClaimRecord.model_validate(
        dict(
            claim_id=claim["entity_id"],
            revision=str(claim["revision"]),
            task_id=tx.owner[2],
            kind=claim["kind"],
            assertion_role=claim["assertion_role"],
            text=claim["text"],
            structured_assertion=(
                strict_json_loads(claim["structured_json"])
                if claim["structured_json"]
                else None
            ),
            basis_refs=strict_json_loads(claim["basis_json"]),
            limitations=strict_json_loads(claim["limitations_json"]),
            producer_kind=claim["producer_kind"],
            producer_ref=claim["producer_ref"],
            created_at=claim["created_at"],
            supersedes=(
                dict(entity_type=prior[0], id=prior[1], revision=str(prior[2]))
                if prior
                else None
            ),
        )
    )


def inputs_current(tx, refs):
    for ref in refs:
        target = resolve(tx, ref)
        if ref.entity_type.value == "claim":
            latest = tx.connection.execute(
                "SELECT max(revision) FROM vnext.claim_revision WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s",
                (*tx.owner, ref.id),
            ).fetchone()[0]
            if str(latest) != ref.revision.root:
                return False
        if ref.entity_type.value in {"artifact", "observation"}:
            env = target["environment_ref"]
            current = tx.connection.execute(
                "SELECT 1 FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND environment_ref=%s AND execution_epoch=%s AND runtime_attempt=%s LIMIT 1",
                (
                    *tx.owner,
                    env,
                    tx.task["execution_epoch"],
                    tx.task["runtime_attempt"],
                ),
            ).fetchone()
            if not current:
                return False
    return True


def aggregate(tx, claim):
    selected = policy(tx)
    rows = tx.connection.execute(
        """SELECT assessment_id,revision,grounding_state,evidence_state,applicability_state,
        method_kind,conditions_json FROM vnext.assessment WHERE tenant_id=%s AND project_id=%s AND task_id=%s
        AND claim_id=%s AND claim_revision=%s AND policy_version=%s ORDER BY assessment_id LIMIT 1025""",
        (*tx.owner, claim["entity_id"], claim["revision"], selected["policy_version"]),
    ).fetchall()
    if len(rows) > 1024:
        raise DomainError("LIMIT_BLOCKED", 422)
    valid = []
    stale = False
    conditions = []
    disputed = False
    for aid, rev, g, e, a, m, c in rows:
        actions = tx.connection.execute(
            "SELECT kind FROM vnext.assessment_action WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND target_id=%s AND target_revision=%s",
            (*tx.owner, aid, rev),
        ).fetchall()
        kinds = {r[0] for r in actions}
        if kinds.intersection({"superseded", "retracted"}):
            continue
        refs = [
            KnowledgeRef.model_validate(dict(entity_type=t, id=i, revision=str(v)))
            for t, i, v in tx.connection.execute(
                "SELECT entity_type,entity_id,revision FROM vnext.assessment_input WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND assessment_id=%s AND assessment_revision=%s",
                (*tx.owner, aid, rev),
            ).fetchall()
        ]
        if a == "stale" or "stale" in kinds or not inputs_current(tx, refs):
            stale = True
            continue
        if a == "retracted":
            continue
        if a == "disputed" or "disputed" in kinds:
            disputed = True
        conditions.extend(strict_json_loads(c))
        valid.append((aid, g, e, a, m))
    # Model opinions do not vote on truth, positively or negatively.
    qualified = [r for r in valid if r[4] != "model_review"]
    supports = [
        r
        for r in qualified
        if r[1] == "content_checked" and r[2] == "supported" and r[3] == "current"
    ]
    contradicts = [
        r for r in qualified if r[1] == "content_checked" and r[2] == "contradicted"
    ]
    grounding = (
        "content_checked"
        if any(r[1] == "content_checked" for r in qualified)
        else "linked" if strict_json_loads(claim["basis_json"]) else "unchecked"
    )
    evidence = (
        "supported"
        if supports
        else (
            "contradicted"
            if contradicts
            else (
                "inconclusive"
                if any(r[2] == "inconclusive" for r in qualified)
                else "unassessed"
            )
        )
    )
    applicability = "current"
    if (supports and contradicts) or disputed:
        evidence = "inconclusive"
        applicability = "disputed"
    elif not valid and stale:
        applicability = "stale"
    eligible = fact_view_eligible(
        claim["kind"],
        grounding,
        evidence,
        applicability,
        supports[0][4] if supports else None,
    )
    conditions = list(dict.fromkeys(conditions))
    if len(conditions) > 1024:
        raise DomainError("LIMIT_BLOCKED", 422)
    return ClaimAssessmentView.model_validate(
        dict(
            policy_version=selected["policy_version"],
            grounding_state=grounding,
            evidence_state=evidence,
            applicability_state=applicability,
            eligible=eligible,
            assessment_ids=[r[0] for r in valid],
            conditions=conditions,
            limitations=strict_json_loads(claim["limitations_json"]),
        )
    )


class FactLedger:
    def __init__(self, uow):
        self.uow = uow

    def read(self, access, task_id, ref, *, snapshot_id=None):
        ref = KnowledgeRef.model_validate(ref)
        with self.uow.transaction(access, task_id) as tx:
            record = resolve(tx, ref)
            manifest = None
            if snapshot_id:
                from wuji_core.persistence.snapshots import SnapshotRepository

                manifest = SnapshotRepository(self.uow)._get(tx, snapshot_id)
                if ref not in manifest.refs:
                    raise DomainError("INVALID_REFERENCE", 422)
                for basis in manifest.refs:
                    resolve(tx, basis)
            if ref.entity_type.value == "intent":
                value = IntentRecord.model_validate(
                    dict(
                        intent_id=ref.id,
                        revision=ref.revision.root,
                        task_id=task_id,
                        question=record["question"],
                        basis_refs=strict_json_loads(record["basis_json"]),
                        expected_output=record["expected_output"],
                        acceptance_state=record["acceptance_state"],
                        created_at=record["created_at"],
                    )
                )
                return RecordView.model_validate(
                    dict(ref=ref, display_kind="intent", record=value)
                )
            if ref.entity_type.value != "claim":
                raise DomainError("INVALID_REFERENCE", 422)
            if snapshot_id:
                key = ref.id + "@" + ref.revision.root
                frozen = manifest.states.get("claim_assessments", {}).get(key)
                if frozen is None:
                    raise DomainError("HISTORY_UNAVAILABLE", 410)
                assessment = ClaimAssessmentView.model_validate(frozen)
            else:
                assessment = aggregate(tx, record)
            return RecordView.model_validate(
                dict(
                    ref=ref,
                    display_kind="fact" if assessment.eligible else "claim",
                    record=claim_record(tx, record),
                    assessment=assessment,
                )
            )

"""Append-only shared candidate knowledge, without epistemic self-certification."""

from uuid import uuid4
from wuji_core.contracts.knowledge import (
    ClaimProposal,
    IntentProposal,
    ComponentReceipt,
    KnowledgeRef,
)
from wuji_core.http import strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text
from wuji_core.blackboard.relations import (
    actor,
    refs_for,
    resolve,
    add_relation,
    operation,
    save_operation,
)


def receipt(local_ref, request_id, canonical=None, code=None):
    return ComponentReceipt.model_validate(
        dict(
            status="accepted_shared" if canonical else "rejected",
            local_ref=local_ref,
            request_id=request_id,
            canonical_ref=canonical,
            code=code,
        )
    )


class ClaimService:
    def __init__(self, uow):
        self.uow = uow

    def propose(self, access, task_id, proposal, *, idempotency_key):
        return self._propose(access, task_id, proposal, idempotency_key, "claim")

    def propose_intent(self, access, task_id, proposal, *, idempotency_key):
        return self._propose(access, task_id, proposal, idempotency_key, "intent")

    def _propose(self, access, task_id, proposal, key, kind):
        proposal = (
            ClaimProposal if kind == "claim" else IntentProposal
        ).model_validate(proposal)
        with self.uow.transaction(access, task_id, capability="write") as tx:
            who = actor(tx)
            if who["producer_kind"] == "agent" and not tx.task["execution_allowed"]:
                raise DomainError("STALE_EXECUTION", 403)
            digest, saved = operation(
                tx, kind + "_propose", key, proposal.model_dump(mode="python")
            )
            if saved:
                return ComponentReceipt.model_validate(saved)
            try:
                result, level = self.append(tx, proposal, kind=kind, who=who)
            except DomainError as error:
                if error.code != "INVALID_REFERENCE":
                    raise
                result = receipt(
                    proposal.client_ref, access.request_id, code=error.code
                )
                level = tx.permissions["clearance"]
            save_operation(
                tx,
                kind + "_propose",
                key,
                digest,
                result.model_dump(mode="python"),
                level,
            )
            if result.canonical_ref:
                tx.semantic_event(
                    kind + "_shared",
                    result.model_dump(mode="python"),
                    access_level=level,
                )
            return result

    def append(
        self,
        tx,
        proposal,
        *,
        kind="claim",
        who=None,
        local=None,
        run_id=None,
        stale=False,
    ):
        who = who or actor(tx)
        allowed = (
            ("claim", "observation", "artifact")
            if kind == "claim"
            else ("claim", "observation")
        )
        basis, level = refs_for(tx, proposal.basis_refs, local, allowed=allowed)
        entity_id = str(uuid4())
        revision = 1
        old = None
        if kind == "claim" and proposal.revises:
            old = proposal.revises
            if old.entity_type.value != "claim":
                raise DomainError("INVALID_REFERENCE", 422)
            previous = resolve(tx, old)
            latest = tx.connection.execute(
                "SELECT max(revision) FROM vnext.claim_revision WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s",
                (*tx.owner, old.id),
            ).fetchone()[0]
            if str(latest) != old.revision.root:
                raise DomainError("STALE_VERSION", 409)
            if (
                who["producer_kind"] == "agent"
                and previous["actor_subject"] != who["subject"]
            ):
                grant = tx.connection.execute(
                    "SELECT 1 FROM vnext.claim_editor WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s AND subject=%s",
                    (*tx.owner, old.id, old.revision.root, who["subject"]),
                ).fetchone()
                if not grant:
                    raise DomainError("NOT_FOUND_OR_FORBIDDEN")
            entity_id = old.id
            revision = int(old.revision.root) + 1
            level = max(level, previous["access_level"])
        ref = KnowledgeRef.model_validate(
            dict(entity_type=kind, id=entity_id, revision=str(revision))
        )
        refs_json = json_text([r.model_dump(mode="json") for r in basis])
        limits = (
            proposal.model_dump(mode="python")["limitations"] if kind == "claim" else []
        )
        if stale:
            limits.append(
                "stale_input: basis no longer current; cannot drive control decisions"
            )
        if kind == "claim":
            tx.connection.execute(
                """INSERT INTO vnext.claim_revision(tenant_id,project_id,task_id,entity_id,revision,
                kind,assertion_role,text,structured_json,producer_kind,producer_ref,actor_subject,agent_run_id,
                limitations_json,basis_json,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    entity_id,
                    revision,
                    proposal.kind.value,
                    proposal.assertion_role.value,
                    proposal.text,
                    (
                        json_text(proposal.structured_assertion)
                        if proposal.structured_assertion is not None
                        else None
                    ),
                    who["producer_kind"],
                    run_id or who["subject"],
                    who["subject"],
                    run_id,
                    json_text(limits),
                    refs_json,
                    level,
                ),
            )
            for target in basis:
                add_relation(tx, ref, "cites", target, level)
            if old:
                add_relation(tx, ref, "supersedes", old, level)
        else:
            planning = getattr(proposal, "planning", None)
            if planning is not None:
                for criterion in planning.goal_criterion_refs:
                    if tx.connection.execute(
                        "SELECT 1 FROM vnext.goal_criterion WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND criterion_id=%s AND revision=%s",
                        (*tx.owner, criterion.criterion_id, criterion.revision.root),
                    ).fetchone() is None:
                        raise DomainError("INVALID_REFERENCE", 422)
                definition = strict_json_loads(tx.task["definition_json"])
                published = {
                    item["source_ref"]
                    for profile in definition.get("worker_profiles", {}).values()
                    for item in profile.get("body", {}).get("capability_manifest", ())
                }
                if not {
                    item.root for item in planning.required_capability_refs
                } <= published:
                    raise DomainError("CAPABILITY_UNAVAILABLE", 422)
            tx.connection.execute(
                """INSERT INTO vnext.intent_revision(tenant_id,project_id,task_id,entity_id,revision,
                question,expected_output,producer_subject,agent_run_id,basis_json,limitations_json,planning_json,access_level)
                VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    entity_id,
                    proposal.question,
                    proposal.expected_output,
                    who["subject"],
                    run_id,
                    refs_json,
                    json_text(limits),
                    None if planning is None else json_text(planning.model_dump(mode="json")),
                    level,
                ),
            )
            for source in basis:
                add_relation(tx, source, "input_to", ref, level)
        return (
            receipt(
                proposal.client_ref,
                tx.access.request_id,
                ref,
                code="STALE_INPUT" if stale else None,
            ),
            level,
        )

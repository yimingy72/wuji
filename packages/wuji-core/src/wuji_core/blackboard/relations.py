"""Typed reference resolution and commit-local dependency ordering."""

from hashlib import sha256
from psycopg import sql
from wuji_core.contracts.knowledge import KnowledgeRef
from wuji_core.persistence.uow import DomainError, json_text, row
from wuji_core.http.json_boundary import strict_json_loads


def ref_value(ref):
    return ref.model_dump(mode="json")


def resolve(tx, ref):
    if not isinstance(ref, KnowledgeRef):
        ref = KnowledgeRef.model_validate(ref)
    tables = {
        "claim": "claim_revision",
        "artifact": "artifact",
        "observation": "observation",
        "intent": "intent_revision",
    }
    kind = ref.entity_type.value
    if kind not in tables:
        raise DomainError("INVALID_REFERENCE", 422)
    found = row(
        tx.connection.execute(
            sql.SQL(
                "SELECT * FROM {} WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND entity_id=%s AND revision=%s"
            ).format(sql.Identifier("vnext", tables[kind])),
            (*tx.owner, ref.id, ref.revision.root),
        )
    )
    if not found or (kind == "artifact" and found["state"] != "sealed"):
        raise DomainError("INVALID_REFERENCE", 422)
    return found


def refs_for(tx, refs, local=None, *, allowed=("claim", "observation", "artifact")):
    result = []
    level = 0
    for item in refs:
        value = item.root if hasattr(item, "root") else item
        if not isinstance(value, KnowledgeRef):
            if local is None or value.client_ref not in local:
                raise DomainError("INVALID_REFERENCE", 422)
            value = local[value.client_ref]
        if value.entity_type.value not in allowed:
            raise DomainError("INVALID_REFERENCE", 422)
        found = resolve(tx, value)
        level = max(level, found["access_level"])
        if value not in result:
            result.append(value)
    return result, level


def add_relation(tx, source, relation, target, level):
    # SQL additionally enforces composite ownership, endpoint kinds and clearance.
    resolve(tx, source)
    resolve(tx, target)
    tx.connection.execute(
        """INSERT INTO vnext.entity_relation(tenant_id,project_id,task_id,source_type,source_id,
        source_revision,relation,target_type,target_id,target_revision,access_level)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            *tx.owner,
            source.entity_type.value,
            source.id,
            source.revision.root,
            relation,
            target.entity_type.value,
            target.id,
            target.revision.root,
            level,
        ),
    )


def actor(tx, subject=None):
    who = subject or tx.access.principal.subject
    found = row(
        tx.connection.execute(
            "SELECT * FROM vnext.knowledge_actor WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND subject=%s",
            (*tx.owner, who),
        )
    )
    if not found:
        raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    if subject is None:
        roles = tx.access.principal.roles
        if (found["producer_kind"] == "agent") != ("agent" in roles):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
    return found


def policy(tx):
    found = row(
        tx.connection.execute(
            """SELECT p.* FROM vnext.task_assessment_policy t JOIN vnext.assessment_policy p USING(policy_version)
        WHERE t.tenant_id=%s AND t.project_id=%s AND t.task_id=%s""",
            tx.owner,
        )
    )
    if (
        not found
        or sha256(found["document"].encode()).hexdigest() != found["document_sha256"]
    ):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    return found


def operation(tx, kind, key, value):
    if not isinstance(key, str) or not 1 <= len(key) <= 256:
        raise DomainError("INVALID_SCHEMA", 422)
    digest = sha256(json_text(value).encode()).hexdigest()
    saved = row(
        tx.connection.execute(
            "SELECT * FROM vnext.knowledge_operation WHERE tenant_id=%s AND task_id=%s AND operation_kind=%s AND operation_id=%s",
            (tx.owner[0], tx.owner[2], kind, key),
        )
    )
    if saved and saved["input_digest"] != digest:
        raise DomainError("INPUT_DIGEST_CONFLICT", 409)
    return digest, strict_json_loads(saved["receipt_json"]) if saved else None


def save_operation(tx, kind, key, digest, receipt, level=0):
    tx.connection.execute(
        """INSERT INTO vnext.knowledge_operation(tenant_id,project_id,task_id,operation_kind,
        operation_id,input_digest,receipt_json,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
        (*tx.owner, kind, key, digest, json_text(receipt), level),
    )


def batch_order(components):
    """Topological proposal ordering, separate from the sole WorkDependency DAG."""
    counts = {}
    for _, p in components:
        counts[p.client_ref] = counts.get(p.client_ref, 0) + 1
    invalid = {k for k, n in counts.items() if n != 1}
    by_id = {
        p.client_ref: (kind, p) for kind, p in components if p.client_ref not in invalid
    }
    # Two competing revisions are rejected before either can publish.
    revisions = {}
    for kind, p in components:
        if kind == "claim" and p.revises:
            revisions.setdefault(p.revises.id, []).append(p.client_ref)
    invalid.update(k for group in revisions.values() if len(group) > 1 for k in group)
    ordered = []
    active = set()
    done = set()

    def visit(key):
        if key in invalid or key not in by_id:
            return False
        if key in done:
            return True
        if key in active:
            invalid.add(key)
            return False
        active.add(key)
        _, p = by_id[key]
        for item in p.basis_refs:
            value = item.root
            if not isinstance(value, KnowledgeRef) and not visit(value.client_ref):
                invalid.add(key)
        active.remove(key)
        if key in invalid:
            return False
        done.add(key)
        ordered.append(by_id[key])
        return True

    for key in by_id:
        visit(key)
    return ordered, invalid

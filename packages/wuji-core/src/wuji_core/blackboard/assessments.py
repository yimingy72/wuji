"""Qualified immutable assessment events and generic, exactly scoped checkers."""

from decimal import Decimal
from hashlib import sha256
import re
from uuid import uuid4

from wuji_core.contracts.knowledge import (
    AssessmentCommand,
    AssessmentReceipt,
    KnowledgeRef,
)
from wuji_core.contracts.envelopes import BlobRef
from wuji_core.http.json_boundary import (
    strict_json_loads,
    canonical_json_bytes,
    InvalidJsonDocument,
)
from wuji_core.persistence.uow import DomainError, json_text, row
from wuji_core.blackboard.relations import (
    actor,
    resolve,
    policy,
    operation,
    save_operation,
)


def _pointer(document, pointer):
    if (
        not isinstance(pointer, str)
        or (pointer and not pointer.startswith("/"))
        or re.search(r"~(?![01])", pointer)
    ):
        raise ValueError("invalid RFC6901 pointer")
    current = document
    for token in pointer.split("/")[1:] if pointer else []:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif (
            isinstance(current, list)
            and re.fullmatch(r"0|[1-9][0-9]*", token)
            and int(token) < len(current)
        ):
            current = current[int(token)]
        else:
            return False, None
    return True, current


def _scalar_equal(actual, expected):
    if expected is None or isinstance(expected, (str, bool)):
        return type(actual) is type(expected) and actual == expected
    return (
        type(actual) in (int, Decimal)
        and type(expected) in (int, Decimal)
        and actual == expected
    )


class AssessmentService:
    def __init__(self, uow, artifacts):
        self.uow, self.artifacts = uow, artifacts

    def _authorize(self, tx):
        if (
            "assessor" not in tx.access.principal.roles
            or "agent" in tx.access.principal.roles
            or not tx.permissions["can_assess"]
        ):
            raise DomainError("FORBIDDEN_ASSESSOR", 403)
        return actor(tx)

    def _prepare(self, access, task_id, command):
        a = command.assessment
        with self.uow.transaction(access, task_id, capability="assess") as tx:
            who = self._authorize(tx)
            if a.reviewer_ref != who["subject"]:
                raise DomainError("FORBIDDEN_ASSESSOR", 403)
            if a.claim_ref.entity_type.value != "claim":
                raise DomainError("INVALID_REFERENCE", 422)
            if command.expected_version.root != a.claim_ref.revision.root:
                raise DomainError("STALE_VERSION", 409)
            claim = resolve(tx, a.claim_ref)
            selected = policy(tx)
            methods = strict_json_loads(selected["methods_json"])
            if a.method_version not in methods:
                raise DomainError("INVALID_SCHEMA", 422)
            inputs = [resolve(tx, ref) for ref in a.input_refs]
            level = max([claim["access_level"], *(r["access_level"] for r in inputs)])
            if a.method_kind.value == "human_attestation":
                if (
                    a.method_version != "human-attestation-v1"
                    or not who["qualified_human"]
                    or "human" not in access.principal.roles
                    or not a.reason.strip()
                ):
                    raise DomainError("FORBIDDEN_ASSESSOR", 403)
            elif a.method_kind.value == "model_review":
                if a.method_version != "model-review-v1":
                    raise DomainError("INVALID_SCHEMA", 422)
            elif a.method_kind.value != "deterministic" or a.method_version not in {
                "json-pointer-equals-v1",
                "json-pointer-absent-v1",
            }:
                raise DomainError("INVALID_SCHEMA", 422)
            structured = (
                strict_json_loads(claim["structured_json"])
                if claim["structured_json"]
                else None
            )
            artifact = None
            if a.method_kind.value == "deterministic" and isinstance(structured, dict):
                try:
                    ref = BlobRef.model_validate(structured.get("artifact_ref"))

                    # An artifact must be in both the candidate basis and this check's inputs (directly or through one Observation).
                    def covers(refs):
                        for source in refs:
                            target = resolve(tx, source)
                            if (
                                source.entity_type.value == "artifact"
                                and source.id == ref.id
                                and source.revision.root == ref.version.root
                            ):
                                return True
                            if (
                                source.entity_type.value == "observation"
                                and tx.connection.execute(
                                    """SELECT 1 FROM vnext.observation_artifact WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND observation_id=%s AND observation_revision=%s AND artifact_id=%s AND artifact_revision=%s""",
                                    (
                                        *tx.owner,
                                        source.id,
                                        source.revision.root,
                                        ref.id,
                                        ref.version.root,
                                    ),
                                ).fetchone()
                            ):
                                return True
                        return False

                    bases = [
                        KnowledgeRef.model_validate(r)
                        for r in strict_json_loads(claim["basis_json"])
                    ]
                    if covers(bases) and covers(a.input_refs):
                        artifact = self.artifacts.record(tx, ref)
                        if (
                            artifact["state"] != "sealed"
                            or artifact["provenance"] == "model_output"
                        ):
                            artifact = None
                except (ValueError, DomainError):
                    artifact = None
        return claim, inputs, artifact, structured, level, selected

    def record(self, access, task_id, command, *, idempotency_key):
        command = AssessmentCommand.model_validate(command)
        command_data = command.model_dump(mode="python")
        supersedes = command_data["supersedes_assessment_ids"] or []
        supersedes_reason = command_data["supersedes_reason"]
        claim, inputs, artifact, structured, level, selected = self._prepare(
            access, task_id, command
        )
        a = command.assessment
        method = a.method_kind.value
        grounding = "linked"
        evidence = "unassessed"
        applicability = a.applicability_state.value
        reason = a.reason
        scope = {
            "claim_sha256": sha256(claim["text"].encode()).hexdigest(),
            "input_refs": [r.model_dump(mode="json") for r in a.input_refs],
        }
        if method in {"human_attestation", "model_review"}:
            grounding = a.grounding_state.value
            evidence = a.evidence_state.value
        else:
            grounding, evidence, reason = self._check(
                claim, structured, artifact, a.method_version
            )
            applicability = "current"
        with self.uow.transaction(access, task_id, capability="assess") as tx:
            self._authorize(tx)
            resolve(tx, a.claim_ref)
            for ref in a.input_refs:
                resolve(tx, ref)
            if policy(tx)["policy_version"] != selected["policy_version"]:
                raise DomainError("STALE_VERSION", 409)
            digest, saved = operation(
                tx, "assess", idempotency_key, command.model_dump(mode="python")
            )
            if saved:
                return AssessmentReceipt.model_validate(saved)
            previous = tx.connection.execute(
                "SELECT 1 FROM vnext.assessment WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND assessment_id=%s",
                (*tx.owner, a.assessment_id),
            ).fetchone()
            if previous:
                raise DomainError("INPUT_DIGEST_CONFLICT", 409)
            if supersedes and (not supersedes_reason or not supersedes_reason.strip()):
                raise DomainError("INVALID_SCHEMA", 422)
            for target in supersedes:
                old = self._target(tx, target)
                if (
                    old["claim_id"] != a.claim_ref.id
                    or str(old["claim_revision"]) != a.claim_ref.revision.root
                ):
                    raise DomainError("INVALID_REFERENCE", 422)
                level = max(level, old["access_level"])
            env = (
                artifact["environment_ref"]
                if artifact
                else next(
                    (i["environment_ref"] for i in inputs if "environment_ref" in i),
                    None,
                )
            )
            tx.connection.execute(
                """INSERT INTO vnext.assessment(tenant_id,project_id,task_id,assessment_id,revision,claim_id,claim_revision,
                grounding_state,evidence_state,applicability_state,method_kind,method_version,reviewer_ref,reason,conditions_json,
                access_level,policy_version,environment_ref,scope_json,actor_subject) VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *tx.owner,
                    a.assessment_id,
                    a.claim_ref.id,
                    a.claim_ref.revision.root,
                    grounding,
                    evidence,
                    applicability,
                    method,
                    a.method_version,
                    access.principal.subject,
                    reason,
                    json_text(a.model_dump(mode="python")["conditions"]),
                    level,
                    selected["policy_version"],
                    env,
                    json_text(scope),
                    access.principal.subject,
                ),
            )
            for ref in a.input_refs:
                tx.connection.execute(
                    """INSERT INTO vnext.assessment_input(tenant_id,project_id,task_id,assessment_id,assessment_revision,
                    entity_type,entity_id,revision,access_level) VALUES(%s,%s,%s,%s,1,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (
                        *tx.owner,
                        a.assessment_id,
                        ref.entity_type.value,
                        ref.id,
                        ref.revision.root,
                        level,
                    ),
                )
            for target in supersedes:
                self._action(
                    tx,
                    target,
                    "superseded",
                    supersedes_reason,
                    level,
                    replacement=a.assessment_id,
                )
            result = AssessmentReceipt.model_validate(
                dict(
                    assessment_id=a.assessment_id,
                    revision="1",
                    status="accepted_for_check",
                    claim_ref=a.claim_ref,
                    request_id=access.request_id,
                    code=None,
                )
            )
            save_operation(
                tx,
                "assess",
                idempotency_key,
                digest,
                result.model_dump(mode="python"),
                level,
            )
            tx.semantic_event(
                "assessment_recorded",
                result.model_dump(mode="python"),
                access_level=level,
            )
            return result

    def _check(self, claim, structured, artifact, method):
        unverified = (
            "linked",
            "unassessed",
            "Method does not cover the complete assertion",
        )
        if (
            not artifact
            or not isinstance(structured, dict)
            or structured.get("predicate") != method
        ):
            return unverified
        keys = {"predicate", "artifact_ref", "pointer"} | (
            {"expected"} if method == "json-pointer-equals-v1" else set()
        )
        if set(structured) != keys:
            return unverified
        pointer = structured["pointer"]
        try:
            _pointer({}, pointer)
            if method == "json-pointer-equals-v1":
                expected = structured["expected"]
                if not (
                    expected is None or type(expected) in (str, bool, int, Decimal)
                ):
                    return unverified
                template = f"已捕获内容 {artifact['entity_id']}@{artifact['revision']} 的 {pointer} 字段等于 {canonical_json_bytes([expected])[1:-1].decode()}。"
            else:
                template = f"完整捕获内容 {artifact['entity_id']}@{artifact['revision']} 中不存在 {pointer}。"
            if claim["text"] != template:
                return unverified
            if (
                method == "json-pointer-absent-v1"
                and artifact["completeness"] != "complete"
            ):
                return (
                    "linked",
                    "inconclusive",
                    "Incomplete capture cannot establish document-wide absence",
                )
            document = strict_json_loads(self.artifacts.checked_bytes(artifact))
            found, value = _pointer(document, pointer)
            if method == "json-pointer-absent-v1":
                supported = not found
            elif not found:
                return "linked", "inconclusive", "Required field is not captured"
            else:
                supported = _scalar_equal(value, expected)
            return (
                "content_checked",
                "supported" if supported else "contradicted",
                "Independent sealed-byte check of the complete assertion",
            )
        except (ValueError, DomainError, InvalidJsonDocument, UnicodeError):
            return (
                "linked",
                "inconclusive",
                "Required immutable bytes or JSON scope unavailable",
            )

    def _target(self, tx, target):
        old = row(
            tx.connection.execute(
                "SELECT * FROM vnext.assessment WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND assessment_id=%s AND revision=1",
                (*tx.owner, target),
            )
        )
        if not old:
            raise DomainError("INVALID_REFERENCE", 422)
        return old

    def _action(self, tx, target, kind, reason, level, *, replacement=None):
        tx.connection.execute(
            """INSERT INTO vnext.assessment_action(tenant_id,project_id,task_id,action_id,target_id,kind,
            replacement_id,replacement_revision,reason,actor_subject,access_level) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                *tx.owner,
                str(uuid4()),
                target,
                kind,
                replacement,
                1 if replacement else None,
                reason,
                tx.access.principal.subject,
                level,
            ),
        )

    def invalidate(
        self, access, task_id, assessment_id, *, kind, reason, idempotency_key
    ):
        if (
            kind not in {"stale", "retracted", "disputed"}
            or not isinstance(reason, str)
            or not 1 <= len(reason) <= 8192
        ):
            raise DomainError("INVALID_SCHEMA", 422)
        with self.uow.transaction(access, task_id, capability="assess") as tx:
            self._authorize(tx)
            old = self._target(tx, assessment_id)
            digest, saved = operation(
                tx,
                "assessment_action",
                idempotency_key,
                dict(id=assessment_id, kind=kind, reason=reason),
            )
            if saved:
                return saved
            self._action(tx, assessment_id, kind, reason, old["access_level"])
            result = dict(assessment_id=assessment_id, kind=kind)
            save_operation(
                tx,
                "assessment_action",
                idempotency_key,
                digest,
                result,
                old["access_level"],
            )
            tx.semantic_event(
                "assessment_invalidated", result, access_level=old["access_level"]
            )
            return result

"""Real per-Run JWT issuance and encrypted transactional credential storage.

Deployment supplies versioned signing/encryption keys; no generated/default
master key, fixture signer, or hand-written identity protocol exists here.
"""

from datetime import datetime, timezone
import os
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import RSAKey

from wuji_core.admission.registry import RunCredentialBinding
from wuji_core.contracts.envelopes import RunIdentity
from wuji_core.http.auth import AuthenticationError, TokenVerifier
from wuji_core.http.json_boundary import canonical_json_bytes, strict_json_loads
from wuji_core.persistence.uow import DomainError, json_text, row
from wuji_core.scheduling.triggers import require_admission


def worker_subject(run_id):
    return "run.worker:" + run_id


def agent_subject(run_id):
    return "run.agent:" + run_id


class RunCredentialIssuer:
    def __init__(
        self, *, signing_key_resolver, encryption_key_resolver, public_key_resolver
    ):
        """Resolvers are deployment secret-store ports: ref -> PEM/key bytes."""
        self.signing_key_resolver = signing_key_resolver
        self.encryption_key_resolver = encryption_key_resolver
        self.public_key_resolver = public_key_resolver

    def _template(self, tx, identity):
        template = row(
            tx.connection.execute(
                """SELECT t.* FROM vnext.scheduler_identity_template t
            JOIN vnext.scheduler_receiver r ON (r.tenant_id,r.project_id,r.task_id,r.credential_template_ref)=
            (t.tenant_id,t.project_id,t.task_id,t.template_ref)
            WHERE r.tenant_id=%s AND r.project_id=%s AND r.task_id=%s AND r.runtime_attempt=%s
            AND r.receiver_id=%s AND r.enabled AND t.enabled""",
                (*tx.owner, identity.runtime_attempt.root, identity.receiver_id),
            )
        )
        if template is None or template["clearance"] > tx.permissions["clearance"]:
            raise DomainError("credential_template_unavailable", 503)
        return template

    def _secret(self, resolver, ref):
        try:
            value = resolver(ref)
            if not isinstance(value, bytes) or not value:
                raise ValueError("missing configured key")
            return value
        except (LookupError, ValueError, TypeError, OSError) as error:
            raise DomainError("credential_key_unavailable", 503) from error

    def _sign(self, template, claims):
        try:
            key = RSAKey.import_key(
                self._secret(self.signing_key_resolver, template["signing_key_ref"])
            )
            token = jwt.encode(
                {"alg": "RS256", "kid": template["signing_kid"]}, claims, key
            )
            verifier = TokenVerifier(
                public_key_pem=self._secret(
                    self.public_key_resolver, template["signing_key_ref"]
                ),
                issuer=template["issuer"],
                audience=template["audience"],
            )
            return token, verifier.verify(token)
        except (JoseError, ValueError, TypeError, AuthenticationError) as error:
            if isinstance(error, DomainError):
                raise
            raise DomainError("credential_signing_unavailable", 503) from error

    def prepare(self, tx, *, identity, tool_definition_refs, expires_at):
        require_admission(tx)
        identity = RunIdentity.model_validate(identity)
        if (identity.tenant_id, identity.project_id, identity.task_id) != tx.owner:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        template = self._template(tx, identity)
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None or int(expires_at.timestamp()) <= int(
            now.timestamp()
        ):
            raise DomainError("STALE_EXECUTION", 409)
        # JWT expiry has second precision; metadata uses that same instant.
        expires_at = datetime.fromtimestamp(int(expires_at.timestamp()), timezone.utc)
        binding = RunCredentialBinding(
            identity=identity,
            subject=worker_subject(identity.agent_run_id),
            token_id=str(uuid4()),
            expires_at=expires_at,
            purposes=["model_request", "tool_request"],
            session_lineage="run:" + identity.agent_run_id,
            allowed_tool_refs=list(tool_definition_refs),
        )
        claims = {
            "iss": template["issuer"],
            "aud": template["audience"],
            "sub": binding.subject,
            "tenant_id": identity.tenant_id,
            "roles": ["worker"],
            "jti": binding.token_id,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        # Use the existing P02 verifier against deployment's published public key
        # before publishing a credential reference; configuration errors fail closed.
        token, principal = self._sign(template, claims)
        if (
            principal.subject != binding.subject
            or principal.token_id != binding.token_id
            or principal.tenant_id != identity.tenant_id
            or principal.roles != frozenset({"worker"})
        ):
            raise DomainError("credential_binding_mismatch", 409)
        encryption_key = self._secret(
            self.encryption_key_resolver, template["encryption_key_ref"]
        )
        if not isinstance(encryption_key, bytes) or len(encryption_key) != 32:
            raise DomainError("credential_encryption_unavailable", 503)
        credential_ref, nonce = str(uuid4()), os.urandom(12)
        document = binding.model_dump(mode="json")
        aad = canonical_json_bytes(
            {
                "credential_ref": credential_ref,
                "binding": document,
                "encryption_key_ref": template["encryption_key_ref"],
            }
        )
        ciphertext = AESGCM(encryption_key).encrypt(nonce, token.encode("utf-8"), aad)
        tx.connection.execute(
            """SELECT vnext.stage_scheduler_credential(%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                *tx.owner,
                template["template_ref"],
                json_text(document),
                credential_ref,
                nonce,
                ciphertext,
            ),
        ).fetchone()
        return binding, credential_ref

    def bind_admitted_run(self, tx, *, binding, credential_ref):
        require_admission(tx)
        binding = RunCredentialBinding.model_validate(binding)
        tx.connection.execute(
            "SELECT vnext.bind_scheduler_credential(%s,%s,%s,%s,%s)",
            (*tx.owner, credential_ref, json_text(binding.model_dump(mode="json"))),
        ).fetchone()

    def retrieve(self, tx, *, credential_ref, identity):
        """P10 registered receiver only, in its actual observe transaction.

        The returned bearer belongs in the Worker delivery channel, never an
        Outbox, ordinary response, topology projection or trace.
        """
        identity = RunIdentity.model_validate(identity)
        if (
            tx.purpose != "observe"
            or not tx.permissions.get("can_observe")
            or "agent" in tx.access.principal.roles
            or not tx.access.principal.roles.intersection({"controller", "reconciler"})
            or (identity.tenant_id, identity.project_id, identity.task_id) != tx.owner
        ):
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        value = row(
            tx.connection.execute(
                "SELECT * FROM vnext.read_scheduler_credential(%s,%s,%s,%s)",
                (*tx.owner, credential_ref),
            )
        )
        if not value:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        document = strict_json_loads(value["binding_json"])
        binding = RunCredentialBinding.model_validate(document)
        if binding.identity != identity or binding.expires_at <= datetime.now(
            timezone.utc
        ):
            raise DomainError("STALE_EXECUTION", 409)
        aad = canonical_json_bytes(
            {
                "credential_ref": credential_ref,
                "binding": document,
                "encryption_key_ref": value["encryption_key_ref"],
            }
        )
        key = self._secret(self.encryption_key_resolver, value["encryption_key_ref"])
        return (
            AESGCM(key)
            .decrypt(bytes(value["nonce"]), bytes(value["ciphertext"]), aad)
            .decode("utf-8")
        )

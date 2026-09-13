"""Owner-only isolated deployment prerequisites; never insert Runs or results."""

from contextlib import contextmanager
from hashlib import sha256
import json
import os

import psycopg
from psycopg import sql

from deployment_common import read_file
from wuji_core.admission.registry import register_task_config, register_tool_definition, register_executor
from wuji_core.blackboard.claims import ClaimService
from wuji_core.http import canonical_json_bytes, strict_json_loads
from wuji_core.http.auth import TokenVerifier
from wuji_core.persistence.schema import migrate
from wuji_core.persistence.uow import AccessContext, UnitOfWork


def initialize(config):
    params = config["database"]
    tls = {"sslmode":"verify-full", "sslrootcert":config["ca_file"], "connect_timeout":5}
    roles = config["roles"]
    if set(roles) != {"wuji_migration", "wuji_app", "wuji_pod"}:
        raise ValueError("only the isolated deployment database roles are supported")
    with psycopg.connect(**params, **tls, autocommit=True) as admin:
        for role, password in roles.items():
            if not admin.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                admin.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)))
        admin.execute(sql.SQL("GRANT CONNECT,CREATE ON DATABASE {} TO wuji_migration").format(sql.Identifier(params["dbname"])))
        admin.execute("GRANT wuji_app TO wuji_pod")
    migration_params = {**params, "user":"wuji_migration", "password":roles["wuji_migration"]}
    with psycopg.connect(**migration_params, **tls, autocommit=True) as connection:
        migrate(connection, application_role="wuji_app")
        tenant, project, task = owner = tuple(config["owner"])
        definition = config["definition"]
        raw = canonical_json_bytes(definition).decode()
        if connection.execute("SELECT 1 FROM vnext.task WHERE tenant_id=%s AND project_id=%s AND task_id=%s", owner).fetchone():
            raise ValueError("Task prerequisites already exist; do not overwrite an execution")
        with connection.transaction():
            connection.execute("INSERT INTO vnext.tenant(tenant_id) VALUES(%s)", (tenant,))
            connection.execute("INSERT INTO vnext.project(tenant_id,project_id) VALUES(%s,%s)", (tenant,project))
            connection.execute("INSERT INTO vnext.task(tenant_id,project_id,task_id,definition_json,definition_digest) VALUES(%s,%s,%s,%s,%s)", (*owner,raw,sha256(raw.encode()).hexdigest()))
            for subject, flags in config["task_access"].items():
                connection.execute("""INSERT INTO vnext.task_access(tenant_id,project_id,task_id,subject,
                    can_read,can_write,can_capture,can_settle,can_model_output,can_control,can_observe,can_admit,clearance)
                    VALUES(%s,%s,%s,%s,true,%s,%s,%s,false,%s,%s,%s,1)""",
                    (*owner,subject,flags.get("write",False),flags.get("capture",False),flags.get("settle",False),
                     flags.get("control",False),flags.get("observe",False),flags.get("admit",False)))
            connection.execute("""INSERT INTO vnext.knowledge_actor(tenant_id,project_id,task_id,subject,producer_kind,qualified_human)
                VALUES(%s,%s,%s,%s,'human',true)""", (*owner,config["operator_subject"]))
            connection.execute("INSERT INTO vnext.task_assessment_policy(tenant_id,project_id,task_id,policy_version) VALUES(%s,%s,%s,'deployment-v1')",owner)
            for key,tier,tenant_binding in (("deployment-global","global",None),
                    ("model:"+config["admission"]["model"]["ref"],"model",None),("tenant:"+tenant,"tenant",tenant)):
                connection.execute("INSERT INTO vnext.capacity_pool(pool_key,tier,tenant_id,capacity,published_ref) VALUES(%s,%s,%s,2,'deployment-v1')",(key,tier,tenant_binding))
                connection.execute("INSERT INTO vnext.task_capacity_pool(tenant_id,project_id,task_id,pool_key) VALUES(%s,%s,%s,%s)",(*owner,key))
            register_tool_definition(connection,tenant_id=tenant,definition=config["tool"])
            register_executor(connection,owner=owner,executor=config["executor"])
            register_task_config(connection,owner=owner,config=config["admission"])
            identity=config["identity"]
            connection.execute("""INSERT INTO vnext.scheduler_identity_template(tenant_id,project_id,task_id,
                template_ref,issuer,audience,signing_key_ref,signing_kid,encryption_key_ref,clearance,enabled)
                VALUES(%s,%s,%s,'deployment-worker-v1',%s,%s,'signing-key','deployment-key','encryption-key',1,true)""",
                (*owner,identity["issuer"],identity["audience"]))
            connection.execute("""INSERT INTO vnext.task_pod_controller(tenant_id,project_id,task_id,controller_subject,login_role,enabled)
                VALUES(%s,%s,%s,%s,'wuji_pod',true)""",(*owner,config["pod_controller_subject"]))

    @contextmanager
    def app_connection():
        with psycopg.connect(**{**params,"user":"wuji_app","password":roles["wuji_app"]}, **tls, autocommit=True) as connection:
            yield connection

    identity=config["identity"]
    verifier=TokenVerifier(public_key_pem=read_file(config["public_key_file"]),issuer=identity["issuer"],audience=identity["audience"])
    actor=AccessContext(verifier.verify(read_file(config["operator_token_file"]).decode().strip()),"deployment-bootstrap")
    # The one initial Intent is produced by the real public-domain service.
    result=ClaimService(UnitOfWork(app_connection)).propose_intent(actor,task,{
        "client_ref":"read-version", "question":"Read version.txt once through the registered Kali workspace tool.",
        "basis_refs":[], "expected_output":"wuji.agent-payload.v2"},idempotency_key="deployment-read-version")
    if result.canonical_ref is None:
        raise ValueError("initial Intent was not admitted")
    print(json.dumps({"event":"deployment_prerequisites_created", "task_id":task,
        "intent_ref":result.canonical_ref.model_dump(mode="json")}))


if __name__ == "__main__":
    initialize(strict_json_loads(read_file(os.environ.get("WUJI_BOOTSTRAP_CONFIG","/run/wuji/bootstrap/config.json"))))

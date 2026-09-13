"""P09 incremental persistent Work-consideration fairness migration."""

from psycopg import sql

HEAD = "vnext_0011_p09_dispatch_fairness"


def upgrade(connection, application_role):
    connection.execute("""ALTER TABLE vnext.scheduler_work
        ADD COLUMN consideration_round bigint NOT NULL DEFAULT 0
        CHECK(consideration_round>=0)""")
    connection.execute(
        """CREATE POLICY scheduler_fairness_update ON vnext.scheduler_work
        FOR UPDATE USING(
          vnext.in_scope(tenant_id,project_id,task_id)
          AND current_setting('wuji.admit',true)='true'
          AND COALESCE(current_setting('wuji.request_purpose',true),'')=''
          AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE
            (a.tenant_id,a.project_id,a.task_id)=
            (scheduler_work.tenant_id,scheduler_work.project_id,scheduler_work.task_id)
            AND a.subject=current_setting('wuji.subject',true)
            AND a.can_read AND a.can_admit))
        WITH CHECK(
          vnext.in_scope(tenant_id,project_id,task_id)
          AND current_setting('wuji.admit',true)='true'
          AND COALESCE(current_setting('wuji.request_purpose',true),'')=''
          AND EXISTS(SELECT 1 FROM vnext.task_access a WHERE
            (a.tenant_id,a.project_id,a.task_id)=
            (scheduler_work.tenant_id,scheduler_work.project_id,scheduler_work.task_id)
            AND a.subject=current_setting('wuji.subject',true)
            AND a.can_read AND a.can_admit))"""
    )
    connection.execute(
        sql.SQL(
            "GRANT UPDATE(consideration_round) ON vnext.scheduler_work TO {}"
        ).format(sql.Identifier(application_role))
    )
    connection.execute("ALTER TABLE vnext.scheduler_receiver ADD COLUMN pod_uid text")
    # An existing 0010 registration has no trustworthy runtime-produced Pod UID.
    # Disable it so deployment must republish observed metadata before admission.
    connection.execute("""UPDATE vnext.scheduler_receiver SET enabled=false
        WHERE enabled AND (pod_uid IS NULL OR btrim(pod_uid)='')""")
    connection.execute(
        """ALTER TABLE vnext.scheduler_receiver
        ADD CONSTRAINT scheduler_receiver_enabled_pod_uid
        CHECK(NOT enabled OR (pod_uid IS NOT NULL AND length(pod_uid) BETWEEN 1 AND 256))"""
    )
    connection.execute("""CREATE FUNCTION vnext.scheduler_receiver_authorized(
        t text,p text,k text,a numeric) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
        SELECT COALESCE(vnext.in_scope(t,p,k),false)
          AND current_setting('wuji.admit',true)='true'
          AND COALESCE(current_setting('wuji.request_purpose',true),'')=''
          AND EXISTS(SELECT 1 FROM vnext.task_access caller
            WHERE caller.tenant_id=t AND caller.project_id=p AND caller.task_id=k
            AND caller.subject=current_setting('wuji.subject',true)
            AND caller.can_read AND caller.can_admit)
          AND EXISTS(SELECT 1 FROM vnext.scheduler_receiver r
            JOIN vnext.scheduler_identity_template i
              ON (i.tenant_id,i.project_id,i.task_id,i.template_ref)=
                 (r.tenant_id,r.project_id,r.task_id,r.credential_template_ref)
            JOIN vnext.task_access receiver_access
              ON (receiver_access.tenant_id,receiver_access.project_id,
                  receiver_access.task_id,receiver_access.subject)=
                 (r.tenant_id,r.project_id,r.task_id,r.receiver_subject)
            WHERE r.tenant_id=t AND r.project_id=p AND r.task_id=k
              AND r.runtime_attempt=a AND r.enabled AND i.enabled
              AND receiver_access.can_read AND receiver_access.can_observe
              AND r.pod_uid IS NOT NULL AND length(r.pod_uid) BETWEEN 1 AND 256) $$""")
    connection.execute(
        "REVOKE EXECUTE ON FUNCTION vnext.scheduler_receiver_authorized(text,text,text,numeric) FROM PUBLIC"
    )
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION vnext.scheduler_receiver_authorized(text,text,text,numeric) TO {}"
        ).format(sql.Identifier(application_role))
    )
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))

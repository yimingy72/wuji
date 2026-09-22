"""Keep approval intake membership fail-closed for both Session codecs."""

from wuji_core.persistence.native_session_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0035_native_approval_membership"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0034_native_session_v2":
        raise ValueError("native approval migration parent changed")
    connection.execute(
        """DO $$ DECLARE body text;
        old_expr text := $q$NOT (manifest.manifest_json::jsonb->'pending_operation_refs' ? NEW.tool_call_id)$q$;
        BEGIN
          body:=pg_get_functiondef('vnext.guard_approval_intake_insert()'::regprocedure);
          IF strpos(body,old_expr)=0 THEN RAISE EXCEPTION 'approval membership guard changed'; END IF;
          body:=replace(body,old_expr,$q$NOT COALESCE(
            (CASE WHEN manifest.manifest_json::jsonb->>'schema_version'='wuji.session.native.v2'
              THEN manifest.manifest_json::jsonb->'pending_approval_refs'
              ELSE manifest.manifest_json::jsonb->'pending_operation_refs'
            END) ? NEW.tool_call_id, false)$q$);
          EXECUTE body;
        END $$"""
    )
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))

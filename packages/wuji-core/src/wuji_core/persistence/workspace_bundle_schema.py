"""M3 immutable workspace bundle publications and per-asset CAS metadata."""

from psycopg import sql

from wuji_core.persistence.core_process_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0038_workspace_bundle"
O = "tenant_id,project_id,task_id"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0037_core_process":
        raise ValueError("Workspace bundle migration parent changed")
    app = sql.Identifier(application_role)
    connection.execute(
        """ALTER TABLE vnext.publication
        ADD source_tool_attempt_id text,
        ADD manifest_artifact_id text,
        ADD manifest_artifact_revision numeric,
        ADD asset_id text,
        ADD asset_revision numeric,
        ADD parent_publication_id text,
        ADD CHECK(
          (kind<>'workspace_bundle.v1' AND num_nonnulls(
            source_tool_attempt_id,manifest_artifact_id,
            manifest_artifact_revision,asset_id,asset_revision,
            parent_publication_id)=0)
          OR
          (kind='workspace_bundle.v1' AND source_tool_attempt_id IS NOT NULL
            AND manifest_artifact_id IS NOT NULL
            AND manifest_artifact_revision IS NOT NULL
            AND asset_id IS NOT NULL AND asset_revision IS NOT NULL
            AND asset_revision>=1 AND asset_revision=trunc(asset_revision)
            AND ((asset_revision=1 AND parent_publication_id IS NULL)
              OR (asset_revision>1 AND parent_publication_id IS NOT NULL))))"""
    )
    connection.execute(
        f"ALTER TABLE vnext.publication ADD FOREIGN KEY({O},source_tool_attempt_id) "
        f"REFERENCES vnext.tool_attempt({O},tool_attempt_id),"
        f"ADD FOREIGN KEY({O},manifest_artifact_id,manifest_artifact_revision) "
        f"REFERENCES vnext.artifact({O},entity_id,revision),"
        f"ADD UNIQUE({O},asset_id,publication_id)"
    )
    connection.execute(
        f"ALTER TABLE vnext.publication ADD FOREIGN KEY({O},asset_id,parent_publication_id) "
        f"REFERENCES vnext.publication({O},asset_id,publication_id)"
    )
    connection.execute(
        f"CREATE UNIQUE INDEX workspace_publication_source ON vnext.publication({O},source_tool_attempt_id) "
        "WHERE kind='workspace_bundle.v1'"
    )
    connection.execute(
        f"CREATE UNIQUE INDEX workspace_asset_revision ON vnext.publication({O},asset_id,asset_revision) "
        "WHERE kind='workspace_bundle.v1'"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_workspace_publication() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
          IF NEW.kind<>'workspace_bundle.v1' THEN RETURN NEW; END IF;
          IF current_user=pg_get_userbyid((SELECT relowner FROM pg_class
             WHERE oid=TG_RELID)) THEN RETURN NEW; END IF;
          IF current_setting('wuji.model_output',true)<>'true'
             OR NOT EXISTS(
               SELECT 1 FROM vnext.tool_attempt a
               JOIN vnext.tool_call c USING(tenant_id,project_id,task_id,tool_call_id)
               JOIN vnext.tool_definition d
                 ON d.tenant_id=a.tenant_id AND d.ref=c.tool_definition_version
               JOIN vnext.run_writer w
                 ON (w.tenant_id,w.project_id,w.task_id,w.agent_run_id)=
                    (a.tenant_id,a.project_id,a.task_id,a.agent_run_id)
               WHERE (a.tenant_id,a.project_id,a.task_id,a.tool_attempt_id)=
                 (NEW.tenant_id,NEW.project_id,NEW.task_id,
                  NEW.source_tool_attempt_id)
                 AND w.subject=current_setting('wuji.subject',true)
                 AND NOT w.revoked
                 AND d.document_json::jsonb->>'name'='workspace_publish'
                 AND d.document_json::jsonb->'allowed_target_kinds'=
                   '["workspace_bundle"]'::jsonb)
          THEN RAISE EXCEPTION 'workspace publication requires its admitted publish attempt'
            USING ERRCODE='42501'; END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER workspace_publication_authority BEFORE INSERT ON vnext.publication "
        "FOR EACH ROW EXECUTE FUNCTION vnext.guard_workspace_publication()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.guard_workspace_publication_ref() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE parent record; BEGIN
          SELECT kind,access_level,xmin::text AS created_xid INTO parent
          FROM vnext.publication WHERE
            (tenant_id,project_id,task_id,publication_id)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.publication_id);
          IF parent.kind='workspace_bundle.v1' AND
             (parent.created_xid<>pg_current_xact_id()::text
              OR NEW.access_level<>parent.access_level)
          THEN RAISE EXCEPTION 'workspace publication membership is immutable'
            USING ERRCODE='42501'; END IF;
          RETURN NEW;
        END $$"""
    )
    connection.execute(
        "CREATE TRIGGER workspace_publication_ref_immutable BEFORE INSERT "
        "ON vnext.publication_ref FOR EACH ROW EXECUTE FUNCTION "
        "vnext.guard_workspace_publication_ref()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.check_workspace_publication() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        DECLARE member_level integer; parent_level integer:=0; BEGIN
          IF NEW.kind<>'workspace_bundle.v1' THEN RETURN NULL; END IF;
          SELECT max(a.access_level) INTO member_level
          FROM vnext.publication_ref r JOIN vnext.artifact a
            ON (a.tenant_id,a.project_id,a.task_id,a.entity_id,a.revision)=
               (r.tenant_id,r.project_id,r.task_id,r.artifact_id,
                r.artifact_revision)
          WHERE (r.tenant_id,r.project_id,r.task_id,r.publication_id)=
            (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.publication_id);
          IF NEW.parent_publication_id IS NOT NULL THEN
            SELECT access_level INTO parent_level FROM vnext.publication
            WHERE (tenant_id,project_id,task_id,publication_id)=
              (NEW.tenant_id,NEW.project_id,NEW.task_id,
               NEW.parent_publication_id);
          END IF;
          IF member_level IS NULL OR NEW.access_level<member_level
             OR NEW.access_level<parent_level
             OR NOT EXISTS(SELECT 1 FROM vnext.publication_ref r
               WHERE (r.tenant_id,r.project_id,r.task_id,r.publication_id,
                      r.artifact_id,r.artifact_revision)=
                 (NEW.tenant_id,NEW.project_id,NEW.task_id,NEW.publication_id,
                  NEW.manifest_artifact_id,NEW.manifest_artifact_revision))
          THEN RAISE EXCEPTION 'workspace publication members are incomplete'
            USING ERRCODE='23514'; END IF;
          RETURN NULL;
        END $$"""
    )
    connection.execute(
        "CREATE CONSTRAINT TRIGGER workspace_publication_complete "
        "AFTER INSERT ON vnext.publication DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION vnext.check_workspace_publication()"
    )
    connection.execute(
        """CREATE FUNCTION vnext.workspace_bundle_head(asset text)
        RETURNS TABLE(publication_id text,accessible boolean)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
        DECLARE head record; BEGIN
          IF asset IS NULL OR asset='' OR NOT EXISTS(
            SELECT 1 FROM vnext.task_access a
            WHERE a.tenant_id=current_setting('wuji.tenant',true)
              AND a.project_id=current_setting('wuji.project',true)
              AND a.task_id=current_setting('wuji.task',true)
              AND a.subject=current_setting('wuji.subject',true)
              AND a.can_read)
          THEN RAISE EXCEPTION 'workspace head not found'
            USING ERRCODE='42501'; END IF;
          SELECT p.publication_id,p.access_level INTO head
          FROM vnext.publication p
          WHERE p.tenant_id=current_setting('wuji.tenant',true)
            AND p.project_id=current_setting('wuji.project',true)
            AND p.task_id=current_setting('wuji.task',true)
            AND p.kind='workspace_bundle.v1' AND p.asset_id=asset
          ORDER BY p.asset_revision DESC LIMIT 1;
          IF head IS NULL THEN RETURN; END IF;
          publication_id:=CASE WHEN head.access_level<=
            current_setting('wuji.clearance',true)::integer
            THEN head.publication_id ELSE NULL END;
          accessible:=publication_id IS NOT NULL;
          RETURN NEXT;
        END $$"""
    )
    connection.execute(
        "REVOKE ALL ON FUNCTION vnext.guard_workspace_publication() FROM PUBLIC"
    )
    connection.execute(
        "REVOKE ALL ON FUNCTION vnext.check_workspace_publication() FROM PUBLIC"
    )
    connection.execute(
        "REVOKE ALL ON FUNCTION vnext.guard_workspace_publication_ref() FROM PUBLIC"
    )
    connection.execute(
        "REVOKE ALL ON FUNCTION vnext.workspace_bundle_head(text) FROM PUBLIC"
    )
    connection.execute(
        sql.SQL(
            "GRANT EXECUTE ON FUNCTION vnext.workspace_bundle_head(text) TO {}"
        ).format(app)
    )
    connection.execute(
        sql.SQL(
            "GRANT INSERT(source_tool_attempt_id,manifest_artifact_id,"
            "manifest_artifact_revision,asset_id,asset_revision,"
            "parent_publication_id) ON vnext.publication TO {}"
        ).format(app)
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,)
    )

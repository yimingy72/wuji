"""P16 incremental: an authorized purge leaves an explicit evidence tombstone.

AC-067 says a purge must not look like intact evidence. Purging is therefore a
recorded, attributed act: an append-only ``artifact_purge`` row names the exact
bytes that were removed, why, and by which authority, while the artifact itself
becomes ``tombstoned`` (data unreadable, digest still known).

Two guards stay in the database:

- the producer requires both the retention capability and the control decision
  bit (``wuji.gc`` *and* ``wuji.purge``), so neither "owns data" nor "can press
  stop" alone destroys evidence;
- a live lease still blocks every tombstone, because bytes a writer is about to
  publish must not disappear; but an *explicit* purge may retire content that a
  publication or observation still cites -- that is exactly what the recorded
  tombstone is for. Ordinary garbage collection keeps refusing those.
"""

from psycopg import sql

from wuji_core.persistence.delivery_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0027_p16_artifact_purge"

_TABLES = (
    """CREATE TABLE vnext.artifact_purge(
      tenant_id text NOT NULL, project_id text NOT NULL, task_id text NOT NULL,
      purge_id text NOT NULL, artifact_id text NOT NULL,
      artifact_revision numeric NOT NULL, artifact_sha256 text NOT NULL,
      reason text NOT NULL,
      authority text NOT NULL CHECK(authority IN ('operator','retention_policy')),
      access_level integer NOT NULL DEFAULT 0,
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      PRIMARY KEY(tenant_id,project_id,task_id,purge_id),
      FOREIGN KEY(tenant_id,project_id,task_id)
        REFERENCES vnext.task(tenant_id,project_id,task_id),
      FOREIGN KEY(tenant_id,project_id,task_id,artifact_id,artifact_revision)
        REFERENCES vnext.artifact(tenant_id,project_id,task_id,entity_id,revision))""",
)

_POLICIES = (
    "ALTER TABLE vnext.artifact_purge ENABLE ROW LEVEL SECURITY",
    """CREATE POLICY scoped_read ON vnext.artifact_purge
       FOR SELECT USING(vnext.in_scope(tenant_id,project_id,task_id,access_level))""",
)

_PURGE = """CREATE FUNCTION vnext.purge_artifact(
  t text, p text, k text, purge_key text, artifact_key text, artifact_revision numeric,
  reason text, authority_key text, level integer)
  RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
  saved vnext.artifact_purge;
  record_row vnext.artifact;
BEGIN
  IF t IS NULL OR p IS NULL OR k IS NULL
     OR current_setting('wuji.purge',true) IS DISTINCT FROM 'true'
     OR current_setting('wuji.gc',true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'purge requires retention and control authority' USING ERRCODE='42501';
  END IF;
  IF purge_key IS NULL OR length(purge_key) NOT BETWEEN 1 AND 256
     OR artifact_key IS NULL OR length(artifact_key) NOT BETWEEN 1 AND 256
     OR artifact_revision IS NULL OR artifact_revision < 1
        OR artifact_revision <> trunc(artifact_revision)
     OR reason IS NULL OR length(reason) NOT BETWEEN 1 AND 2048
     OR authority_key IS NULL OR authority_key NOT IN ('operator','retention_policy') THEN
    RAISE EXCEPTION 'invalid purge input' USING ERRCODE='22023';
  END IF;
  SELECT * INTO saved FROM vnext.artifact_purge g
    WHERE g.tenant_id=t AND g.project_id=p AND g.task_id=k AND g.purge_id=purge_key;
  IF FOUND THEN
    IF saved.artifact_id IS DISTINCT FROM artifact_key
       OR saved.artifact_revision IS DISTINCT FROM artifact_revision
       OR saved.reason IS DISTINCT FROM reason
       OR saved.authority IS DISTINCT FROM authority_key THEN
      RAISE EXCEPTION 'purge key reused with different content' USING ERRCODE='23505';
    END IF;
    RETURN saved.purge_id;
  END IF;
  SELECT * INTO record_row FROM vnext.artifact a
    WHERE a.tenant_id=t AND a.project_id=p AND a.task_id=k
      AND a.entity_id=artifact_key AND a.revision=artifact_revision FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'artifact absent' USING ERRCODE='42501';
  END IF;
  -- The artifact's own level decides whether this caller may even see it; a
  -- lower caller-supplied level must never widen the purge.
  IF NOT COALESCE(vnext.in_scope(t,p,k,record_row.access_level),false)
     OR record_row.access_level > COALESCE(level,0) THEN
    RAISE EXCEPTION 'purge out of scope' USING ERRCODE='42501';
  END IF;
  IF record_row.state = 'tombstoned' THEN
    RAISE EXCEPTION 'artifact already tombstoned' USING ERRCODE='55000';
  END IF;
  INSERT INTO vnext.artifact_purge(tenant_id,project_id,task_id,purge_id,artifact_id,
    artifact_revision,artifact_sha256,reason,authority,access_level)
  VALUES(t,p,k,purge_key,artifact_key,artifact_revision,record_row.sha256,reason,authority_key,
    record_row.access_level);
  -- The artifact trigger still refuses a tombstone for anything retained.
  UPDATE vnext.artifact a SET state='tombstoned'
    WHERE a.tenant_id=t AND a.project_id=p AND a.task_id=k
      AND a.entity_id=artifact_key AND a.revision=artifact_revision;
  RETURN purge_key;
END $$"""

# t, p, k, purge_key, artifact_key (text), revision (numeric), reason,
# authority_key (text), level (integer)
_SIGNATURE = ",".join(["text"] * 5 + ["numeric", "text", "text", "integer"])


def statements():
    # Imported here on purpose: ``schema`` imports this module, so the shared
    # trigger builder can only be loaded once the migration is actually run.
    from wuji_core.persistence.knowledge_schema import artifact_update_statement

    # The trigger learns the purge distinction here and stays the single place
    # that decides whether a tombstone is allowed.
    return (
        _TABLES
        + _POLICIES
        + (artifact_update_statement(), _PURGE)
    )


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0026_p16_report_delivery":
        raise ValueError("P16 purge migration parent changed")
    for statement in statements():
        connection.execute(statement)
    app = sql.Identifier(application_role)
    connection.execute(
        sql.SQL("GRANT SELECT ON vnext.artifact_purge TO {}").format(app)
    )
    connection.execute(
        sql.SQL("REVOKE EXECUTE ON FUNCTION vnext.purge_artifact(" + _SIGNATURE + ") FROM PUBLIC")
    )
    connection.execute(
        sql.SQL("GRANT EXECUTE ON FUNCTION vnext.purge_artifact(" + _SIGNATURE + ") TO {}").format(app)
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )

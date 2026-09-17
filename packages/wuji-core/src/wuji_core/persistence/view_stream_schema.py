"""P15 incremental: one saved view can advance and be streamed.

P13 froze a projection view at ``view_revision=1``: every live read built a new
materialization and a new view, so a client could never follow one view. P15's
authorized ViewStream needs the opposite: the same view advances when the Task's
event sequence moves on, and every advance is recorded as its own
materialization plus an opaque stream cursor.

This migration only widens what the application role may do under the existing
guards:

- ``projection_view.view_revision`` may advance (the fixed ``=1`` check is
  replaced by ``>=1``), while the row still belongs to one subject, one query
  digest and one access digest;
- an UPDATE policy requires ``wuji.snapshot``, the acting subject, a
  materialization that already exists for the new snapshot, and a strictly
  non-decreasing expiry, so a stream can never extend its own lifetime;
- ``projection_cursor`` accepts the ``stream`` kind, scoped to a view;
- ``vnext.task_for_view`` resolves the Task of a view for the current tenant and
  subject only, so the frozen ``/views/{view_id}/events`` path needs no Task
  parameter.
"""

from psycopg import sql

from wuji_core.persistence.report_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0025_p15_view_stream"

_VIEW_REVISION = (
    "ALTER TABLE vnext.projection_view DROP CONSTRAINT projection_view_view_revision_check",
    "ALTER TABLE vnext.projection_view ADD CONSTRAINT projection_view_view_revision_check"
    " CHECK(view_revision>=1 AND view_revision=trunc(view_revision))",
)

_CURSOR_KIND = (
    "ALTER TABLE vnext.projection_cursor DROP CONSTRAINT projection_cursor_kind_check",
    "ALTER TABLE vnext.projection_cursor ADD CONSTRAINT projection_cursor_kind_check"
    " CHECK(kind IN ('page','index','stream'))",
    "ALTER TABLE vnext.projection_cursor DROP CONSTRAINT projection_cursor_check",
    "ALTER TABLE vnext.projection_cursor ADD CONSTRAINT projection_cursor_view_check"
    " CHECK(kind='index' OR view_id IS NOT NULL)",
)

_UPDATE_POLICY = (
    """CREATE POLICY projection_update ON vnext.projection_view FOR UPDATE USING (
      vnext.projection_reader(tenant_id,project_id,task_id,subject)
      AND current_setting('wuji.snapshot',true)='true'
      AND subject=current_setting('wuji.subject',true)
    ) WITH CHECK (
      vnext.projection_reader(tenant_id,project_id,task_id,subject)
      AND current_setting('wuji.snapshot',true)='true'
      AND subject=current_setting('wuji.subject',true)
      AND EXISTS(SELECT 1 FROM vnext.projection_materialization p
        WHERE (p.tenant_id,p.project_id,p.task_id,p.snapshot_id)=
          (projection_view.tenant_id,projection_view.project_id,
           projection_view.task_id,projection_view.snapshot_id)
        AND p.subject=projection_view.subject
        AND p.access_digest=projection_view.access_digest
        AND p.projection_version=projection_view.projection_version
        AND p.expires_at>=projection_view.expires_at)
    )""",
)

_TASK_FOR_VIEW = """CREATE FUNCTION vnext.task_for_view(view_key text)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
  SELECT v.task_id FROM vnext.projection_view v
  JOIN vnext.task_access acl
    ON (acl.tenant_id,acl.project_id,acl.task_id)=(v.tenant_id,v.project_id,v.task_id)
   AND acl.subject=v.subject
  WHERE v.view_id=view_key
    AND v.tenant_id=current_setting('wuji.tenant',true)
    AND v.subject=current_setting('wuji.subject',true)
    AND acl.can_read
  LIMIT 1
$$"""

_TASK_FOR_VIEW_SIGNATURE = "text"


def statements():
    return (*_VIEW_REVISION, *_CURSOR_KIND, *_UPDATE_POLICY, _TASK_FOR_VIEW)


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0024_p12_reports":
        raise ValueError("P15 view stream migration parent changed")
    for statement in statements():
        connection.execute(statement)
    app = sql.Identifier(application_role)
    connection.execute(
        sql.SQL("GRANT UPDATE ON vnext.projection_view TO {}").format(app)
    )
    connection.execute(
        sql.SQL("REVOKE EXECUTE ON FUNCTION vnext.task_for_view(" + _TASK_FOR_VIEW_SIGNATURE + ") FROM PUBLIC")
    )
    connection.execute(
        sql.SQL("GRANT EXECUTE ON FUNCTION vnext.task_for_view(" + _TASK_FOR_VIEW_SIGNATURE + ") TO {}").format(app)
    )
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )

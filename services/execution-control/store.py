"""Short PostgreSQL transactions for trusted execution control."""
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
import json
from sqlalchemy import create_engine, text

def utcnow(): return datetime.now(timezone.utc)
def dump(value): return json.dumps(value,default=str,ensure_ascii=False,separators=(",",":"))

class Store:
    def __init__(self,dsn):
        self.engine=create_engine(dsn,pool_pre_ping=True,pool_size=8,max_overflow=8)
    @contextmanager
    def tx(self):
        with self.engine.begin() as c: yield c
    def rows(self,query,params=None):
        with self.tx() as c:return [dict(x) for x in c.execute(text(query),params or {}).mappings()]
    def one(self,query,params=None):
        rows=self.rows(query,params)
        return rows[0] if rows else None
    def execute(self,query,params=None):
        with self.tx() as c:return c.execute(text(query),params or {}).rowcount
    def task(self,task_id):
        return self.one("SELECT * FROM tasks WHERE id=:id AND task_kind='web_assessment'",{"id":task_id})
    def execution(self,task_id):
        return self.one("SELECT * FROM task_executions WHERE task_id=:id",{"id":task_id})
    def event(self,c,task_id,summary,updates=None):
        row=c.execute(text("SELECT * FROM tasks WHERE id=:id FOR UPDATE"),{"id":task_id}).mappings().one()
        allowed={"state","execution_epoch","active_calls","unknown_calls","egress_state","cleanup_state",
                 "assessment_outcome","stop_reason"}
        updates=updates or {}
        if set(updates)-allowed:raise ValueError("invalid task update")
        params={"id":task_id,**updates}
        assignments="".join(f", {name}=:{name}" for name in updates)
        current=c.execute(text("UPDATE tasks SET version=version+1,event_sequence=event_sequence+1,"
            "updated_at=clock_timestamp()"+assignments+" WHERE id=:id RETURNING version,event_sequence"),params).mappings().one()
        c.execute(text("INSERT INTO task_events(event_id,tenant_id,project_id,task_id,sequence,aggregate_version,event_type,trace_id,summary)"
                      " VALUES(:event,:tenant,:project,:task,:sequence,:version,'task.changed',:trace,:summary)"),
                  {"event":uuid4(),"tenant":row["tenant_id"],"project":row["project_id"],"task":task_id,
                   "sequence":current["event_sequence"],"version":current["version"],"trace":uuid4(),"summary":summary[:500]})
    def stop_requested(self,task_id,reason):
        with self.tx() as c:
            row=c.execute(text("SELECT state,execution_epoch FROM tasks WHERE id=:id FOR UPDATE"),{"id":task_id}).mappings().one()
            if row["state"] in {"completed","cancelled","cancelling","completing"}:return
            self.event(c,task_id,"执行许可已关闭",{"state":"completing","execution_epoch":row["execution_epoch"]+1,
                       "egress_state":"revoking","stop_reason":reason})
    def permitted(self,task_id,epoch,attempt,*,provisioning=False):
        task=self.task(task_id)
        if not task or task["execution_epoch"]!=int(epoch):return False
        if task["state"] not in ({"running","provisioning"} if provisioning else {"running"}):return False
        ex=self.execution(task_id)
        if not ex or ex["epoch"]!=int(epoch):return False
        if utcnow()>=datetime.fromisoformat(task["creation_config"]["authorization"]["valid_until"].replace("Z","+00:00")):return False
        identity=self.one("""
          SELECT 1 FROM task_executions ex JOIN command_receipts cr ON cr.id=ex.start_command_id
          JOIN users u ON u.id=cr.user_id JOIN projects p ON p.id=ex.project_id
          JOIN tenants t ON t.id=ex.tenant_id
          JOIN project_memberships pm ON pm.project_id=p.id AND pm.tenant_id=t.id AND pm.user_id=u.id
          JOIN tenant_memberships tm ON tm.tenant_id=t.id AND tm.user_id=u.id
          JOIN model_versions mv ON mv.id=:model AND mv.tenant_id=t.id
          WHERE ex.task_id=:task AND u.enabled AND p.enabled AND t.enabled AND pm.enabled AND tm.enabled
            AND pm.role='operator' AND tm.role='operator' AND mv.state IN ('published','retired')
            AND mv.sync_state='synced'""",{"task":task_id,"model":task["creation_config"]["model"]["id"]})
        runtime=self.one("SELECT state FROM runtime_attempts WHERE task_id=:task AND attempt=:attempt",
                         {"task":task_id,"attempt":int(attempt)})
        return bool(identity and runtime and runtime["state"] not in {"stopped","unknown"})

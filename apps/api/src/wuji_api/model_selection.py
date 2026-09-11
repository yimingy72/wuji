"""Shared transaction lock and secret-free selectable model snapshots."""
import hashlib
from sqlalchemy import text
from wuji_api.model_config import ProfileConfig
class ModelUnavailable(Exception): pass
async def model_version_lock(connection, tenant_id, version_id):
    key = int.from_bytes(hashlib.sha256(f"wuji-model-selection-v1:{tenant_id}:{version_id}".encode()).digest()[:8], "big", signed=True)
    await connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key":key})
async def selectable_model(connection, tenant_id, version_id):
    if version_id is None: raise ModelUnavailable
    row = (await connection.execute(text("SELECT id,definition_id,number,name,config,state_revision FROM model_versions WHERE tenant_id=:tenant AND id=:id AND kind='profile' AND state='published' AND sync_state='synced'"),{"tenant":tenant_id,"id":version_id})).mappings().one_or_none()
    if row is None: raise ModelUnavailable
    config = ProfileConfig.model_validate(row["config"])
    if config.pricing is None or config.context_window is None or config.max_output_tokens is None: raise ModelUnavailable
    return {"id":str(row["id"]),"definition_id":str(row["definition_id"]),"number":row["number"],"name":row["name"],"state_revision":row["state_revision"],"config":config.model_dump(mode="json")}
def model_summary(snapshot):
    return {key:snapshot[key] for key in ("id","name","number")}

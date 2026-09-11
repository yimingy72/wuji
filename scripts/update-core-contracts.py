"""Refresh only core feature contracts from authoritative Pydantic DTOs."""
from pathlib import Path
import sys
# scripts/platform is the lifecycle package, not Python's platform module.
sys.path = [p for p in sys.path if Path(p).resolve() != Path(__file__).resolve().parent]
from copy import deepcopy
import json
import yaml
from pydantic import TypeAdapter
from wuji_api.main import create_app
from wuji_api.drafts import SaveDraftRequest, TaskDraftResponse, TaskDraftPageResponse, NewDraftContent
from wuji_api.tasks import TaskResponse, WebTaskResponse, TaskPageResponse, TaskSnapshotResponse
from wuji_api.task_creation import NewCreateTaskRequest, TaskCreationPreview, CreationConfigSnapshot
from wuji_api.scenario_profiles import ScenarioProfilePage
from wuji_api.executions import AgentRunPage, ToolCallPage, ArtifactPage, BlackBoardSnapshot, TaskResult
from wuji_api.tasks import TaskControlRequest, CommandReceiptResponse

root=Path(__file__).resolve().parents[1]
path=root/"packages/contracts/openapi.yaml"
api=yaml.safe_load(path.read_text())
rename={"TaskResponse":"LegacyTask","WebTaskResponse":"WebTask","TaskPageResponse":"TaskPage",
        "TaskSnapshotResponse":"TaskSnapshot","TaskDraftResponse":"SavedTaskDraft",
        "TaskDraftPageResponse":"SavedTaskDraftPage","ErrorResponse":"Error",
        "CommandReceiptResponse":"CommandReceipt","CreateTaskRequest":"CreateTask",
        "HTTPValidationError":"Error"}
rename["TaskControlRequest"]="TaskControl"
def remap(value):
    if isinstance(value,list): return [remap(x) for x in value]
    if not isinstance(value,dict): return value
    result={}
    for key,item in value.items():
        if key in {"discriminator","$defs"}: continue
        if key=="$ref":
            name=item.rsplit("/",1)[-1]
            item="#/components/schemas/"+rename.get(name,name)
        result[key]=remap(item)
    return result
models={ "LegacyTask":TaskResponse,"WebTask":WebTaskResponse,"TaskPage":TaskPageResponse,
         "TaskSnapshot":TaskSnapshotResponse,"SavedTaskDraft":TaskDraftResponse,
         "SavedTaskDraftPage":TaskDraftPageResponse,"SaveDraftRequest":SaveDraftRequest,
         "NewCreateTaskRequest":NewCreateTaskRequest,"TaskCreationPreview":TaskCreationPreview,
         "CreationConfigSnapshot":CreationConfigSnapshot,"ScenarioProfilePage":ScenarioProfilePage}
schemas=api["components"]["schemas"]
models.update(AgentRunPage=AgentRunPage,ToolCallPage=ToolCallPage,ArtifactPage=ArtifactPage,
              BlackBoardSnapshot=BlackBoardSnapshot,TaskResult=TaskResult,TaskControl=TaskControlRequest,
              CommandReceipt=CommandReceiptResponse)
for public,model in models.items():
    schema=model.model_json_schema(ref_template="#/components/schemas/{model}")
    for name,value in schema.pop("$defs",{}).items():
        schemas[rename.get(name,name)]=remap(value)
    schemas[public]=remap(schema)
schemas["Task"]={"oneOf":[{"$ref":"#/components/schemas/LegacyTask"},{"$ref":"#/components/schemas/WebTask"}]}
schemas["SaveTaskDraftRequest"]={"$ref":"#/components/schemas/SaveDraftRequest"}
v2=TypeAdapter(NewDraftContent).json_schema(ref_template="#/components/schemas/{model}")
for name,value in v2.pop("$defs",{}).items(): schemas[rename.get(name,name)]=remap(value)
schemas["DraftContentV2"]=remap(v2)
schemas["WebDraftContentV2"]={"$ref":"#/components/schemas/WebDraftV2"}
source=create_app().openapi()
for full,methods in source["paths"].items():
    if not full.startswith("/api/v1/projects/"):continue
    relative=full.removeprefix("/api/v1")
    if not ("/task-drafts" in full or full.endswith("/scenario-profiles")
            or full.endswith("/task-creation-previews")
            or full.endswith("/tasks") or "/tasks/{task_id}" in full):continue
    converted=remap(methods)
    for method,operation in converted.items():
        if not isinstance(operation,dict):continue
        operation["summary"]=operation.get("summary",operation.get("operationId","Core operation"))
        for status,response in operation.get("responses",{}).items():
            response.setdefault("headers",{})["Cache-Control"]={"schema":{"type":"string","const":"no-store"}}
        for p in operation.get("parameters",[]):
            if p.get("name")=="X-CSRF-Token":p["required"]=True
    api["paths"][relative]=converted
def refs(value):
    if isinstance(value,list):
        for item in value: yield from refs(item)
    elif isinstance(value,dict):
        if "$ref" in value and value["$ref"].startswith("#/components/schemas/"):
            yield value["$ref"].rsplit("/",1)[-1]
        for item in value.values():yield from refs(item)
original={rename.get(name,name):remap(value) for name,value in source["components"]["schemas"].items()}
while missing:=set(refs(api))-set(schemas):
    for name in missing:
        if name not in original:raise RuntimeError(f"missing authoritative schema: {name}")
        schemas[name]=original[name]
path.write_text(yaml.safe_dump(api,allow_unicode=True,sort_keys=False,width=110))
print("Core contracts refreshed; generate TypeScript/validators next.")

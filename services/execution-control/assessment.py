"""Durable W1 observations, rule decisions and bounded completion feedback."""
import base64
import hashlib
import json
from uuid import UUID,uuid4,uuid5
from sqlalchemy import text
from wuji_api.assessments import HttpExchange,VerificationSubmit
from assessment_rules import PROFILE_ID,RULE_ID,CLAIM,canonical_url,discover,evaluate,item_id
from store import dump

def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(",",":")).encode()).hexdigest()
def identity(row):
    return {k:row[k] for k in ("tenant_id","project_id","task_id")}
def rows(c,sql,params):
    return [dict(row) for row in c.execute(text(sql),params).mappings()]
def one(c,sql,params):
    values=rows(c,sql,params)
    return values[0] if values else None

class AssessmentError(ValueError):pass

class WebAssessment:
    def __init__(self,core):
        self.core=core
        self.store=core.store
        self.artifacts=core.artifacts

    def enabled(self,task_id):
        ex=self.store.execution(task_id)
        return bool(ex and ex["execution_snapshot"]["profile_id"]==PROFILE_ID)

    def latest(self,task_id,c=None):
        query="SELECT * FROM assessment_plans WHERE task_id=:task ORDER BY revision DESC LIMIT 1"
        return one(c,query,{"task":task_id}) if c is not None else self.store.one(query,{"task":task_id})

    def view(self,task_id,c=None):
        plan=self.latest(task_id,c)
        if not plan:return {"state":"not_assessed"}
        return {**plan["snapshot"],"state":"available","plan_id":str(plan["id"]),"revision":plan["revision"],"progress_digest":plan["progress_digest"]}

    def _artifact(self,call,artifact_id,data,name,mime):
        saved=self.artifacts.write(call["task_id"],artifact_id,data,mime)
        return {**identity(call),"id":artifact_id,"call":call["id"],"name":name,"mime":mime,
                "size":saved["size"],"sha":saved["sha256"],"key":saved["storage_key"]}

    @staticmethod
    def _save_artifact(c,params):
        c.execute(text("""INSERT INTO task_artifacts(id,tenant_id,project_id,task_id,tool_call_id,kind,name,mime,size,sha256,storage_key)
          VALUES(:id,:tenant_id,:project_id,:task_id,:call,'http.observation',:name,:mime,:size,:sha,:key)
          ON CONFLICT(id) DO NOTHING"""),params)

    def capture(self,call,result):
        exchange=HttpExchange.model_validate(result["exchange"]).model_dump(mode="json")
        body=base64.b64decode(exchange.pop("body_base64"),validate=True)
        if len(body)!=exchange["body_bytes"] or hashlib.sha256(body).hexdigest()!=exchange["body_sha256"]:
            raise AssessmentError("observation digest mismatch")
        if canonical_url(exchange["url"])!=canonical_url(call["args"]["url"]) or exchange["method"]!=call["args"].get("method","GET"):
            raise AssessmentError("observation request mismatch")
        if any(exchange["request_headers"].get(k)!=v for k,v in call["args"].get("headers",{}).items()):
            raise AssessmentError("observed headers mismatch")
        sensitive={"set-cookie","cookie","authorization","proxy-authorization","www-authenticate","proxy-authenticate"}
        for key in sensitive:
            if key in exchange["response_headers"]:
                del exchange["response_headers"][key]
                if key not in exchange["redacted_headers"]:exchange["redacted_headers"].append(key)
        if len(dump(exchange).encode())>65536:raise AssessmentError("observation metadata too large")
        observation_id=uuid5(UUID(str(call["id"])),"http-observation")
        artifact_id=uuid5(UUID(str(call["id"])),"http-metadata")
        body_id=uuid5(UUID(str(call["id"])),"http-body")
        envelope={"tool_call_id":str(call["id"]),"exchange":exchange,"body_artifact_id":str(body_id)}
        body_record=self._artifact(call,body_id,body,"HTTP响应正文","application/octet-stream")
        metadata_record=self._artifact(call,artifact_id,dump(envelope).encode(),"HTTP交换元数据","application/json")
        with self.store.tx() as c:
            c.execute(text("SELECT id FROM tasks WHERE id=:id FOR UPDATE"),{"id":call["task_id"]})
            self._save_artifact(c,body_record);self._save_artifact(c,metadata_record)
            c.execute(text("""INSERT INTO observations(id,tenant_id,project_id,task_id,tool_call_id,agent_run_id,runtime_attempt,
                artifact_id,body_artifact_id,target_url,method,metadata)
                VALUES(:id,:tenant_id,:project_id,:task_id,:call,:run,:attempt,:artifact,:body,:url,:method,CAST(:metadata AS jsonb))
                ON CONFLICT(tool_call_id) DO NOTHING"""),
                {**identity(call),"id":observation_id,"call":call["id"],"run":call["agent_run_id"],"attempt":call["runtime_attempt"],
                 "artifact":artifact_id,"body":body_id,"url":canonical_url(exchange["url"]),"method":exchange["method"],"metadata":dump(exchange)})
            self.refresh(c,call["task_id"])
        excerpt=body[:8192].decode("utf-8",errors="replace")
        return {"ok":exchange["complete"],"observation_id":str(observation_id),"artifact_id":str(artifact_id),
                "body_artifact_id":str(body_id),"exchange":exchange,"body_excerpt":excerpt,
                "excerpt_truncated":len(body)>8192}

    def _read(self,c,artifact_id,task_id):
        record=one(c,"SELECT * FROM task_artifacts WHERE id=:id AND task_id=:task AND state='available'",{"id":artifact_id,"task":task_id})
        if not record:raise AssessmentError("evidence unavailable")
        content=self.artifacts.read(record["storage_key"])
        if hashlib.sha256(content).hexdigest()!=record["sha256"] or len(content)!=record["size"]:
            raise AssessmentError("evidence integrity failed")
        return content

    def checked_observation(self,c,observation):
        envelope=json.loads(self._read(c,observation["artifact_id"],observation["task_id"]))
        if (envelope["exchange"]!=observation["metadata"] or envelope["tool_call_id"]!=str(observation["tool_call_id"])
                or envelope["body_artifact_id"]!=str(observation["body_artifact_id"])):
            raise AssessmentError("evidence binding mismatch")
        body=self._read(c,observation["body_artifact_id"],observation["task_id"])
        metadata=observation["metadata"]
        if len(body)!=metadata["body_bytes"] or hashlib.sha256(body).hexdigest()!=metadata["body_sha256"]:
            raise AssessmentError("body evidence mismatch")
        return metadata,body

    def refresh(self,c,task_id,final=False):
        task=one(c,"SELECT * FROM tasks WHERE id=:id",{"id":task_id})
        entry=canonical_url(task["creation_config"]["actual_input"]["entry_url"])
        old=self.latest(task_id,c)
        observed=rows(c,"SELECT * FROM observations WHERE task_id=:task ORDER BY created_at,id",{"task":task_id})
        candidates=[o for o in observed if o["target_url"]==entry and o["method"]=="GET"]
        candidates.sort(key=lambda o:not o["metadata"]["complete"])
        resources=[entry];discovery_state="pending";limitations=[]
        if candidates:
            metadata,body=self.checked_observation(c,candidates[0])
            resources,discovery_state,limitations=discover(entry,body,metadata,task["creation_config"]["authorization"])
        results=rows(c,"""SELECT r.*,v.target_url,v.coverage_item_id FROM verification_result_revisions r
            JOIN verification_runs v ON v.id=r.verification_run_id AND v.task_id=r.task_id
            WHERE r.task_id=:task ORDER BY r.created_at,r.id""",{"task":task_id})
        superseded={str(r["supersedes_result_id"]) for r in results if r["supersedes_result_id"]}
        items=[]
        for url in resources:
            applicable=[r for r in results if r["target_url"]==url and str(r["id"]) not in superseded]
            item={"id":item_id(task_id,url),"target_url":url,"rule_id":RULE_ID,"state":"pending",
                  "verdict":None,"verification_run_id":None,"result_id":None,"reason":None}
            strong=[r for r in applicable if r["verdict"] in {"confirmed","not_reproduced"}]
            if strong:
                result=strong[-1]
                conflicting=len({r["verdict"] for r in strong})>1
                item.update(state="inconclusive" if conflicting else "evaluated",
                    verdict="inconclusive" if conflicting else result["verdict"],
                    verification_run_id=str(result["verification_run_id"]),result_id=str(result["id"]),
                    reason="conflicting_evidence" if conflicting else result["reason"])
            elif applicable:
                result=applicable[-1]
                item.update(state="blocked" if result["verdict"]=="unassessed" else "inconclusive",
                    verdict=result["verdict"],verification_run_id=str(result["verification_run_id"]),
                    result_id=str(result["id"]),reason=result["reason"])
            if final and item["state"]=="pending":item.update(state="not_run",reason=task["stop_reason"] or "execution_ended")
            items.append(item)
        states={i["state"] for i in items}
        outcome=("complete" if states=={"evaluated"} and discovery_state=="complete" else
                 "partial" if "evaluated" in states or "blocked" in states or "not_run" in states else
                 "inconclusive" if "inconclusive" in states else "not_assessed")
        meaningful_observations=[]
        for observation in observed:
            m=observation["metadata"]
            meaningful_observations.append(sha({**{k:m[k] for k in
                ("url","method","status","body_sha256","complete","termination")},
                "request_headers":{k:v for k,v in m["request_headers"].items() if k in {"accept","origin"}},
                "response_headers":{k:v for k,v in m["response_headers"].items() if k in
                    {"content-type","access-control-allow-origin","access-control-allow-credentials"}}}))
        meaningful_observations=sorted(set(meaningful_observations))
        material={"observations":meaningful_observations,"items":[{k:i[k] for k in ("target_url","state","verdict","reason")} for i in items],
                  "discovery_state":discovery_state}
        progress=sha(material)
        snapshot={"state":"available","profile_id":PROFILE_ID,"outcome":outcome,"discovery_state":discovery_state,
                  "items":items,"limitations":limitations}
        if old and old["snapshot"]==snapshot and old["progress_digest"]==progress:return old
        revision=1 if old is None else old["revision"]+1
        plan_id=uuid4()
        c.execute(text("""INSERT INTO assessment_plans(id,tenant_id,project_id,task_id,revision,progress_digest,snapshot)
            VALUES(:id,:tenant,:project,:task,:revision,:digest,CAST(:snapshot AS jsonb))"""),
            {"id":plan_id,"tenant":task["tenant_id"],"project":task["project_id"],"task":task_id,
             "revision":revision,"digest":progress,"snapshot":dump(snapshot)})
        self.store.event(c,task_id,"有限评估记录已更新")
        return {"id":plan_id,"revision":revision,"progress_digest":progress,"snapshot":snapshot}

    def submit(self,call,run,args):
        request=VerificationSubmit.model_validate(args)
        with self.store.tx() as c:
            task=one(c,"SELECT * FROM tasks WHERE id=:id FOR UPDATE",{"id":run["task_id"]})
            previous=one(c,"SELECT result FROM tool_calls WHERE id=:id",{"id":call["id"]})
            if previous["result"] is not None:return previous["result"]
            if task["state"]!="running" or task["execution_epoch"]!=run["execution_epoch"]:
                raise AssessmentError("execution permission changed")
            observed=[]
            for call_id in request.tool_call_ids:
                observation=one(c,"""SELECT o.* FROM observations o JOIN tool_calls tc ON tc.id=o.tool_call_id
                    WHERE o.tool_call_id=:id AND o.task_id=:task AND o.tenant_id=:tenant AND o.project_id=:project AND tc.state='exited'""",
                    {"id":call_id,"task":run["task_id"],"tenant":run["tenant_id"],"project":run["project_id"]})
                if not observation:raise AssessmentError("observation outside task or unfinished")
                self.checked_observation(c,observation);observed.append(observation)
            targets={o["target_url"] for o in observed}
            if len(targets)!=1:raise AssessmentError("verification requires one resource")
            target=targets.pop()
            plan=self.refresh(c,run["task_id"])
            if target not in {i["target_url"] for i in plan["snapshot"]["items"]}:
                raise AssessmentError("resource outside finite assessment plan")
            if request.supersedes_result_id:
                prior=one(c,"""SELECT r.id FROM verification_result_revisions r JOIN verification_runs v
                    ON v.id=r.verification_run_id AND v.task_id=r.task_id
                    WHERE r.id=:id AND r.task_id=:task AND v.target_url=:url AND v.rule_id=:rule""",
                    {"id":request.supersedes_result_id,"task":run["task_id"],"url":target,"rule":request.rule_id})
                if not prior:raise AssessmentError("invalid correction reference")
            verdict,reason,limits=evaluate([o["metadata"] for o in observed])
            verification_id=uuid5(UUID(str(call["id"])),"verification")
            result_id=uuid5(verification_id,"result:1")
            common=identity(run)
            c.execute(text("""INSERT INTO verification_runs(id,tenant_id,project_id,task_id,coverage_item_id,target_url,
                rule_id,claim,agent_run_id,intent_id,submission_call_id)
                VALUES(:id,:tenant_id,:project_id,:task_id,:item,:url,:rule,:claim,:run,:intent,:call)"""),
                {**common,"id":verification_id,"item":item_id(run["task_id"],target),"url":target,"rule":RULE_ID,
                 "claim":CLAIM,"run":run["id"],"intent":run["intent_id"],"call":call["id"]})
            c.execute(text("""INSERT INTO verification_result_revisions(id,tenant_id,project_id,task_id,
                verification_run_id,revision,verdict,reason,limitations,supersedes_result_id)
                VALUES(:id,:tenant_id,:project_id,:task_id,:run,1,:verdict,:reason,CAST(:limits AS jsonb),:supersedes)"""),
                {**common,"id":result_id,"run":verification_id,"verdict":verdict,"reason":reason,
                 "limits":dump(limits+request.limitations),"supersedes":request.supersedes_result_id})
            relation={"confirmed":"supports","not_reproduced":"refutes"}.get(verdict,"limits")
            for observation in observed:
                c.execute(text("""INSERT INTO evidence_links(id,tenant_id,project_id,task_id,verification_result_id,
                    observation_id,artifact_id,relation,selector)
                    VALUES(:id,:tenant_id,:project_id,:task_id,:result,:observation,:artifact,:relation,CAST(:selector AS jsonb))"""),
                    {**common,"id":uuid4(),"result":result_id,"observation":observation["id"],"artifact":observation["artifact_id"],
                     "relation":relation,"selector":dump({"headers":["access-control-allow-origin","access-control-allow-credentials"],
                        "request_headers":["origin"],"status":True,"complete":True})})
            updated=self.refresh(c,run["task_id"])
            result={"verification_run_id":str(verification_id),"result_id":str(result_id),"verdict":verdict,
                    "reason":reason,"assessment_revision":updated["revision"]}
            c.execute(text("UPDATE tool_calls SET result=CAST(:result AS jsonb) WHERE id=:id"),{"id":call["id"],"result":dump(result)})
            return result

    def read_tool(self,task_id):
        with self.store.tx() as c:
            view=self.view(task_id,c)
            observations=rows(c,"SELECT * FROM observations WHERE task_id=:task ORDER BY created_at DESC,id DESC LIMIT 50",{"task":task_id})
            result=[]
            for o in observations:
                m=o["metadata"]
                result.append({"id":str(o["id"]),"tool_call_id":str(o["tool_call_id"]),"target_url":o["target_url"],
                    "method":o["method"],"request_headers":m["request_headers"],"response_status":m["status"],
                    "complete":m["complete"],"termination":m["termination"],"artifact_id":str(o["artifact_id"]),
                    "body_artifact_id":str(o["body_artifact_id"])})
            return {"assessment":view,"observations":result,"observations_limit":50}

    def evidence(self,task_id,args):
        if set(args)-{"observation_id","offset","limit"}:raise AssessmentError("unexpected evidence parameter")
        identifier=UUID(args["observation_id"]);offset=args.get("offset",0);limit=args.get("limit",8192)
        if type(offset) is not int or type(limit) is not int or offset<0 or not 1<=limit<=8192:
            raise AssessmentError("invalid evidence slice")
        with self.store.tx() as c:
            observed=one(c,"SELECT * FROM observations WHERE id=:id AND task_id=:task",{"id":identifier,"task":task_id})
            if not observed:raise AssessmentError("observation not visible")
            metadata,body=self.checked_observation(c,observed)
            fragment=body[offset:offset+limit]
            return {"observation_id":str(identifier),"exchange":metadata,"offset":offset,
                "body_base64":base64.b64encode(fragment).decode(),"body_text":fragment.decode("utf-8",errors="replace"),
                "has_more":offset+len(fragment)<len(body),"artifact_id":str(observed["artifact_id"]),
                "body_artifact_id":str(observed["body_artifact_id"])}

    def review(self,ex,run,args):
        review_id=uuid5(UUID(str(run["id"])),"complete:"+sha(args))
        with self.store.tx() as c:
            task=one(c,"SELECT * FROM tasks WHERE id=:id FOR UPDATE",{"id":run["task_id"]})
            old=one(c,"SELECT * FROM completion_reviews WHERE id=:id",{"id":review_id})
            if old:return old
            if task["state"]!="running" or task["execution_epoch"]!=run["execution_epoch"]:
                raise AssessmentError("completion permission changed")
            if run["output"] is None:raise AssessmentError("persisted output required")
            plan=self.refresh(c,run["task_id"]);view=plan["snapshot"]
            missing=[i["id"] for i in view["items"] if i["state"] in {"pending","inconclusive"}]
            if view["discovery_state"]=="pending":missing.append("entry_discovery")
            active=one(c,"""SELECT (SELECT count(*) FROM agent_runs WHERE task_id=:task AND id<>:run AND
                (state IN ('registered','running','unknown') OR result_state IN ('pending','unknown'))) +
                (SELECT count(*) FROM tool_calls WHERE task_id=:task AND state IN ('registered','running','unknown')) AS count""",
                {"task":run["task_id"],"run":run["id"]})["count"]
            attempts=0
            if active:decision,reason="needs_followup","waiting_execution"
            elif missing:
                attempts=one(c,"SELECT count(*) AS count FROM completion_reviews WHERE task_id=:task AND progress_digest=:digest AND reason='missing_evidence'",
                    {"task":run["task_id"],"digest":plan["progress_digest"]})["count"]+1
                decision,reason=("needs_followup","missing_evidence") if attempts<2 else ("stop_with_results","no_progress")
            else:
                decision="stop_with_results"
                reason="assessment_complete" if view["outcome"]=="complete" else "assessment_partial"
            value={**identity(run),"id":review_id,"run":run["id"],"digest":sha(args),
                "progress":plan["progress_digest"],"decision":decision,"reason":reason,"missing":dump(missing),
                "attempt":attempts,"trigger":"pending" if decision=="needs_followup" else "settled"}
            c.execute(text("""INSERT INTO completion_reviews(id,tenant_id,project_id,task_id,agent_run_id,
                request_digest,progress_digest,decision,reason,missing,attempt_number,trigger_state)
                VALUES(:id,:tenant_id,:project_id,:task_id,:run,:digest,:progress,:decision,:reason,CAST(:missing AS jsonb),:attempt,:trigger)"""),value)
            self.store.event(c,run["task_id"],"完成提案已评审："+reason)
            return one(c,"SELECT * FROM completion_reviews WHERE id=:id",{"id":review_id})

    def pending_review(self,task_id):
        return self.store.one("SELECT * FROM completion_reviews WHERE task_id=:task AND trigger_state='pending' ORDER BY created_at DESC,id DESC LIMIT 1",{"task":task_id})

    def final_result(self,task_id):
        with self.store.tx() as c:
            c.execute(text("SELECT id FROM tasks WHERE id=:id FOR UPDATE"),{"id":task_id})
            plan=self.refresh(c,task_id,final=True)
            snapshot=plan["snapshot"]
            counts={s:sum(i["state"]==s for i in snapshot["items"]) for s in ("evaluated","blocked","inconclusive","not_run")}
            artifact_ids=[str(r["id"]) for r in rows(c,"SELECT id FROM task_artifacts WHERE task_id=:task ORDER BY created_at,id",{"task":task_id})]
            return {"goal_status":"unknown","summary":f"有限计划共{len(snapshot['items'])}项：已评估{counts['evaluated']}项，前提不足{counts['blocked']}项，不确定{counts['inconclusive']}项，未执行{counts['not_run']}项。",
                    "limitations":snapshot["limitations"]+["本批仅进行有限HTTP配置检查，使用合成模型，不证明总Goal、全站覆盖或真实模型自主效果。"],
                    "artifact_ids":artifact_ids,"assessment":{"plan_id":str(plan["id"]),"revision":plan["revision"],"outcome":snapshot["outcome"]}}

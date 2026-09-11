"""Pure rules over observations; never request a target or call a model."""
import hashlib
import json
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from uuid import UUID, uuid5
from wuji_api.scope_policy import normalize_origin
from wuji_api.task_authorization import permits_url

PROFILE_ID="closed-web-assessment-v1"
RULE_ID="cors-reflection-v1"
CLAIM="在匿名GET条件下观察到对两个不同Origin反射来源并允许凭据的跨源响应配置"
PROFILE={"id":PROFILE_ID,"version":1,"rule_id":RULE_ID,"max_linked_resources":10,
         "goal_policy":"unassessed","max_unchanged_completion_proposals":2}
PROFILE["digest"]=hashlib.sha256(json.dumps(PROFILE,sort_keys=True).encode()).hexdigest()

def canonical_url(value):
    u=urlsplit(value)
    if u.scheme not in {"http","https"} or u.username or u.password or u.fragment:
        raise ValueError("invalid observation URL")
    origin=normalize_origin(f"{u.scheme}://{u.netloc}/")
    return origin+(u.path or "/")+("?" + u.query if u.query else "")

def item_id(task_id,url):
    return str(uuid5(UUID(str(task_id)),RULE_ID+":"+canonical_url(url)))

class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            for key,value in attrs:
                if key=="href" and value is not None:self.links.append(value)

def discover(entry,body,metadata,authorization):
    resources=[canonical_url(entry)]
    if not metadata["complete"]:
        return resources,"incomplete",["入口响应不完整，未接受链接发现结果。"]
    if not (metadata["status"] and 200<=metadata["status"]<300):
        return resources,"incomplete",["入口未返回可解析的成功响应。"]
    content_type=metadata["response_headers"].get("content-type","").split(";",1)[0].strip().lower()
    if content_type not in {"text/html","application/xhtml+xml"}:
        return resources,"incomplete",["入口不是HTML，本批不解析其他内容中的资源链接。"]
    try:
        parser=Links();parser.feed(body.decode("utf-8"));parser.close()
    except (UnicodeError,ValueError):
        return resources,"incomplete",["入口HTML无法按UTF-8解析。"]
    limited=False;excluded=False
    entry_origin=normalize_origin(f"{urlsplit(entry).scheme}://{urlsplit(entry).netloc}/")
    for href in parser.links:
        try:
            target=urlsplit(urljoin(entry,href))
            normalized=canonical_url(urlunsplit(target._replace(fragment="")))
            origin=normalize_origin(f"{target.scheme}://{target.netloc}/")
            if origin!=entry_origin or not permits_url(authorization,normalized):
                excluded=True;continue
        except (ValueError,TypeError):
            excluded=True;continue
        if normalized in resources:continue
        if len(resources)==11:
            limited=True;continue
        resources.append(normalized)
    limitations=[]
    if excluded:limitations.append("外域、无效或未获授权的链接未纳入有限计划，也未被探测。")
    if limited:limitations.append("直接链接超过10个资源，本批仅记录前10个，不代表全站覆盖。")
    return resources,"incomplete" if limited else "complete",limitations

def evaluate(metadata):
    if any(m["status"] in (401,403) for m in metadata):
        return "unassessed","anonymous_precondition_missing",["匿名身份未满足此资源的访问前提。"]
    if any(not m["complete"] for m in metadata):
        return "inconclusive","incomplete_exchange",["存在截断、超时或未完整收到的响应。"]
    if any(m["status"] is None or not 200<=m["status"]<300 for m in metadata):
        return "unassessed","response_precondition_missing",["本次响应未满足成功GET对照前提。"]
    if len(metadata)!=2 or any(m["method"]!="GET" for m in metadata):
        return "inconclusive","get_pair_required",["需要同一资源的两组完整GET观察。"]
    origins=[m["request_headers"].get("origin","") for m in metadata]
    if not all(origins) or origins[0]==origins[1]:
        return "inconclusive","distinct_origins_required",["需要两个不同的Origin请求值。"]
    matched=all(m["response_headers"].get("access-control-allow-origin")==origin and
                m["response_headers"].get("access-control-allow-credentials")=="true"
                for m,origin in zip(metadata,origins))
    if matched:
        return "confirmed","reflected_credentials_observed",["仅确认本次响应配置，不证明读取了真实用户数据或完整漏洞影响。"]
    return "not_reproduced","reflection_not_observed",["本次两组完整对照未观察到该组合，不证明站点整体安全。"]

class FixtureEvidenceEvaluator:
    @staticmethod
    def complete(calls):
        observed=any(c["tool"]=="fixture_http" and (c["result"] or {}).get("ok") is True
            and "WUJI_HTTP_FIXTURE_V1" in (c["result"] or {}).get("body","")
            and (c["result"] or {}).get("artifact_id") for c in calls)
        writes=[c for c in calls if c["tool"]=="workspace_write" and (c["result"] or {}).get("ok") is True]
        reads=[c for c in calls if c["tool"]=="workspace_read" and (c["result"] or {}).get("ok") is True]
        shared=any(w["agent_run_id"]!=r["agent_run_id"] and w["args"].get("path")==r["args"].get("path")
            and w["args"].get("content")==r["result"].get("content")
            and str(w["args"].get("path","")).startswith("/workspace/shared/")
            and w["result"].get("artifact_id") and r["result"].get("artifact_id") for w in writes for r in reads)
        return bool(observed and shared)

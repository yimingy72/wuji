import { useSyncExternalStore } from 'react';
import { available, creationIssues, entry, type Draft, type DraftContent, type Profile, type Service, type Task, type Scenario } from './domain';
const uid=()=>crypto.randomUUID();
const tenant='10000000-0000-4000-8000-000000000001';
export const projects=[{id:'a',name:'研发验证项目'},{id:'b',name:'业务评估项目'}];
export type Role='both'|'operator'|'viewer'|'admin'|'signed-out';
export type Pending={key:string;userId:string;projectId:string;draftId:string;state:'submitting'|'unknown';frozen:Draft|null;model:Profile;inspected:boolean;missOnce:boolean};
export type Outcome={draftId:string;state:'failed'|'succeeded';message:string};
type ServicePending={key:string;userId:string;state:'submitting'|'unknown'};
type State={servicePending:ServicePending|null;role:Role;project:string;drafts:Draft[];tasks:Task[];services:Service[];profiles:Profile[];pending:Record<string,Pending>;outcome:Outcome|null;generation:number;createMode:'success'|'lost'|'reject';serviceLost:boolean;checkUnknown:boolean;blockPending:boolean;queryMiss:boolean;revision:number};
function seed():State {
  const service:Service={id:uid(),tenant_id:tenant,definition_id:uid(),kind:'service',number:1,name:'演示模型服务',config:{protocol:'openai',base_url:'https://gateway.example.test/api/openai'},state:'draft',state_revision:1,sync_state:'synced',created_at:new Date().toISOString(),keyConfigured:true};
  const profile:Profile={id:uid(),tenant_id:tenant,definition_id:uid(),kind:'profile',number:1,name:'通用评估',config:{service_version_id:service.id,model_id:'qwen-flash',context_window:32768,max_output_tokens:4096,timeout_seconds:30,pricing:{source:'演示价目，仅用于交互评审',input_per_million:'1',output_per_million:'2',cache_mode:'standard_input',cache_read_per_million:null,cache_creation_per_million:null}},state:'published',state_revision:2,sync_state:'synced',created_at:new Date().toISOString(),check:'succeeded',block:'none'};
  return {servicePending:null,role:'both',project:'a',drafts:[],tasks:[],services:[service],profiles:[profile],pending:{},outcome:null,generation:0,createMode:'success',serviceLost:false,checkUnknown:false,blockPending:true,queryMiss:false,revision:0};
}
let state=seed(); const listeners=new Set<()=>void>();
// Simulated server records outlive client command bodies, but never a page reload.
const serviceReceipts=new Map<string,Service>();
const receipts=new Map<string,{taskId:string|null;rejected:boolean}>();
const user=()=>`demo-${state.role}`;
const commandScope=(project=state.project)=>`${user()}:${project}`;
function patch(value:Partial<State>) { state={...state,...value,revision:state.revision+1}; listeners.forEach(f=>f()); }
export const useStore=()=>useSyncExternalStore(f=>{listeners.add(f);return()=>{listeners.delete(f);};},()=>state);
export const getState=()=>state;
export const canWrite=()=>['both','operator'].includes(state.role);
export const canAdmin=()=>['both','admin'].includes(state.role);
export const canRead=()=>['both','operator','viewer'].includes(state.role);
export const currentUser=user;
export const pending=()=>state.pending[commandScope()];
export function configure(value:Partial<Pick<State,'createMode'|'serviceLost'|'checkUnknown'|'blockPending'|'queryMiss'>>) {patch(value);}
export function changeContext(role:Role,project=state.project) { patch({role,project,generation:state.generation+1,pending:role!==state.role?{}:state.pending,servicePending:role!==state.role?null:state.servicePending,profiles:state.profiles.map(p=>p.check==='checking'?{...p,check:'unknown'}:p),outcome:null}); }
export function reset() {const generation=state.generation+1;receipts.clear();serviceReceipts.clear();state={...seed(),generation};patch({});}
function baseContent(scenario:Scenario):DraftContent {
 const common={schema_version:'1.0' as const,scenario,name:'',objective:'',starting_point:'',constraints:'',reference_ids:[],model_profile_version_id:state.profiles.filter(available).length===1?state.profiles.find(available)!.id:null,runtime_profile_version_id:null,budget_usd:null};
 return {...common,...(scenario==='web_single'?{entry_url:null,include_subdomains:false,additional_origins:[]}:scenario==='ctf'?{challenge:'',entry_url:null}:scenario==='comprehensive'?{assets:[],access_notes:''}:scenario==='exercise'?{organization_name:'',known_domains:[]}:{repository_url:null,source_reference_id:null,revision:null})} as DraftContent;
}
export function newDraft(scenario:Scenario='web_single') {const d:Draft={id:uid(),userId:user(),projectId:state.project,content:baseContent(scenario),includes:[],excludes:[],validUntil:'',confirmed:false,savedAt:null,dirty:true};patch({drafts:[d,...state.drafts],outcome:null});return d;}
export function updateDraft(id:string,value:Partial<Draft>,scopeChanged=false) {patch({drafts:state.drafts.map(d=>d.id===id&&d.userId===user()?{...d,...value,dirty:true,...(scopeChanged?{confirmed:false}:{})}:d),outcome:null});}
export function updateContent(id:string,value:Record<string,unknown>) {const d=state.drafts.find(d=>d.id===id);if(d)updateDraft(id,{content:{...d.content,...value} as DraftContent});}
export function setEntry(id:string,value:string) {const d=state.drafts.find(d=>d.id===id);if(!d)return;const e=entry(value);const old='entry_url' in d.content?entry(d.content.entry_url??''):null;let includes=d.includes; if(e&&(!includes.length||includes[0]?.host===old?.host)) {const first=includes[0]; includes=[{id:first?.id??uid(),host:e.host,scheme:e.scheme,port:e.port,descendants:e.host===old?.host?first?.descendants??false:false},...includes.slice(1)];}updateDraft(id,{content:{...d.content,entry_url:value,name:!d.content.name||d.content.name===`${old?.host} · Web 评估`?e?`${e.host} · Web 评估`:d.content.name:d.content.name} as DraftContent,includes},true);}
export function switchScenario(id:string,scenario:Scenario) {const d=state.drafts.find(x=>x.id===id);if(!d)return;const c=baseContent(scenario);updateDraft(id,{content:{...c,name:d.content.name,objective:d.content.objective,starting_point:d.content.starting_point,constraints:d.content.constraints,budget_usd:d.content.budget_usd,model_profile_version_id:d.content.model_profile_version_id},includes:[],excludes:[],validUntil:'',confirmed:false});}
export function saveDraft(id:string) {if(!canWrite())return;patch({drafts:state.drafts.map(d=>d.id===id&&d.userId===user()?{...d,savedAt:new Date().toISOString(),dirty:false}:d)});}
const delay=()=>new Promise<void>(r=>setTimeout(r,500));
export async function submit(id:string,retry=false):Promise<string|null> {
 const d=state.drafts.find(x=>x.id===id&&x.userId===user()&&x.projectId===state.project);if(!d||!canWrite())return null;
 const scope=commandScope();let p=state.pending[scope];
 if(p&&!retry)return null;if(retry&&(!p?.frozen||p.state==='submitting'))return null;
 if(!p) {const issues=creationIssues(d,state.profiles);if(issues.length){patch({outcome:{draftId:id,state:'failed',message:issues[0]!}});return null;}
 p={key:uid(),userId:user(),projectId:state.project,draftId:id,state:'submitting',frozen:structuredClone(d),model:structuredClone(state.profiles.find(x=>x.id===d.content.model_profile_version_id)!),inspected:false,missOnce:state.queryMiss};}
 const record=p;const generation=state.generation;const mode=retry?'success':state.createMode;
 patch({pending:{...state.pending,[scope]:{...p,state:'submitting'}},outcome:null,createMode:'success',queryMiss:false});
 // Accept once into the server ledger, before a possibly lost client response.
 if(!receipts.has(record.key)) {
  if(mode==='reject')receipts.set(record.key,{taskId:null,rejected:true});
  else {const task:Task={id:uid(),projectId:record.projectId,createdAt:new Date().toISOString(),state:'ready',draft:structuredClone(record.frozen!),model:structuredClone(record.model)};receipts.set(record.key,{taskId:task.id,rejected:false});patch({tasks:[task,...state.tasks]});}
 }
 await delay();
 if(generation!==state.generation||!state.pending[scope]) {if(state.pending[scope])patch({pending:{...state.pending,[scope]:{...state.pending[scope]!,state:'unknown'}}});return null;}
 if(mode==='lost'){patch({pending:{...state.pending,[scope]:{...record,state:'unknown'}}});return null;}
 return finishReceipt(scope,record);
}
function finishReceipt(scope:string,p:Pending) {
 const receipt=receipts.get(p.key);if(!receipt){patch({pending:{...state.pending,[scope]:{...p,state:'unknown'}}});return null;}
 if(!receipt.rejected&&!state.tasks.some(t=>t.id===receipt.taskId&&t.projectId===p.projectId))return null;
 const next={...state.pending};delete next[scope];
 patch({pending:next,outcome:{draftId:p.draftId,state:receipt.rejected?'failed':'succeeded',message:receipt.rejected?'本次创建已被明确拒绝，未创建任务。请检查授权后重新提交。':'任务已创建'}});
 return receipt.taskId;
}
export async function reconcile():Promise<string|null> {const scope=commandScope(),p=state.pending[scope],gen=state.generation;if(!p||p.state==='submitting')return null;await delay();if(gen!==state.generation||state.pending[scope]?.key!==p.key)return null;if(p.missOnce){patch({pending:{...state.pending,[scope]:{...p,missOnce:false}}});return null;}return finishReceipt(scope,p);}
export function inspectList(){const p=pending();if(p)patch({pending:{...state.pending,[commandScope()]:{...p,inspected:true}}});}
export function simulateReload(){const p=pending();if(p)patch({pending:{...state.pending,[commandScope()]:{...p,frozen:null,state:'unknown'}},generation:state.generation+1});}
export function abandon(){const p=pending();if(!p?.inspected||p.state==='submitting')return;const next={...state.pending};delete next[commandScope()];patch({pending:next,outcome:null});}
export function cancelTask(id:string){if(canWrite())patch({tasks:state.tasks.map(t=>t.id===id&&t.projectId===state.project?{...t,state:'cancelled'}:t)});}
export function addService(service:Service){if(canAdmin())patch({services:[service,...state.services.filter(v=>v.id!==service.id)]});}
export function addProfile(profile:Profile){if(canAdmin())patch({profiles:[profile,...state.profiles]});}
export async function checkProfile(id:string,lookup=false){if(!canAdmin())return;const p=state.profiles.find(p=>p.id===id);if(!p||p.state==='revoked')return;const gen=state.generation;if(lookup)return;const unknown=state.checkUnknown;patch({profiles:state.profiles.map(p=>p.id===id?{...p,check:'checking'}:p)});await delay();if(gen!==state.generation)return;patch({profiles:state.profiles.map(p=>p.id===id?{...p,check:unknown?'unknown':'succeeded'}:p)});}
export function profileCommand(id:string,action:'publish'|'retire'|'revoke'|'confirm-block') {if(!canAdmin())return;patch({profiles:state.profiles.map(p=>{
 if(p.id!==id)return p;
 if(action==='publish'&&(p.state==='revoked'||p.check!=='succeeded'||!p.config.pricing||!p.config.context_window||!p.config.max_output_tokens))return p;
 if(action==='confirm-block')return p.state==='revoked'?{...p,block:'confirmed',sync_state:'synced'}:p;
 return {...p,state:action==='publish'?'published':action==='retire'?'retired':'revoked',state_revision:p.state_revision+1,block:action==='revoke'?(state.blockPending?'pending':'confirmed'):p.block,sync_state:action==='revoke'&&state.blockPending?'unknown':p.sync_state};})});}

export async function beginService(version:Service) {
 if(!canAdmin()||state.servicePending)return false;
 const key=uid(),gen=state.generation;const lost=state.serviceLost;
 serviceReceipts.set(key,structuredClone(version));
 patch({servicePending:{key,userId:user(),state:'submitting'},serviceLost:false});
 await delay();
 if(gen!==state.generation||getState().servicePending?.key!==key)return false;
 if(lost){patch({servicePending:{key,userId:user(),state:'unknown'}});return false;}
 addService(version);patch({servicePending:null});return true;
}
export async function resolveService() {
 const p=state.servicePending,gen=state.generation;
 if(!p||p.userId!==user()||!canAdmin())return false;
 await delay();
 if(gen!==state.generation||state.servicePending?.key!==p.key)return false;
 const v=serviceReceipts.get(p.key);if(!v)return false;
 addService(v);patch({servicePending:null});return true;
}

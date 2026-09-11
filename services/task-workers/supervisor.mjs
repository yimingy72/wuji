import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
const role=process.argv[2];if(!['agent','kali'].includes(role))throw Error('role');
const configPath=process.env.WUJI_CONFIG||'/config/binding.json';
const cfg=JSON.parse(await fs.readFile(configPath,'utf8'));
const creds=process.env.WUJI_CREDENTIALS||'/run/wuji/credentials';
const state=process.env.WUJI_STATE||(role==='agent'?'/var/lib/wuji/agent':'/workspace/.wuji');
await fs.mkdir(state,{recursive:true,mode:0o700});
const token=(await fs.readFile(path.join(creds,role==='agent'?'backend_token':'router_token'),'utf8')).trim();
const leaseToken=(await fs.readFile(path.join(creds,'lease_token'),'utf8')).trim();
const entries=new Map();let leaseUntil=0;let leaseBusy=false;
const now=()=>new Date().toISOString();const digest=x=>crypto.createHash('sha256').update(x).digest('hex');
const saves=new Map();
const save=r=>{const data=JSON.stringify(r);const operation=(saves.get(r.id)||Promise.resolve()).catch(()=>{}).then(async()=>{const p=path.join(state,r.id,'status.json');await fs.writeFile(p+'.tmp',data);await fs.rename(p+'.tmp',p);});saves.set(r.id,operation);return operation;};
for(const id of await fs.readdir(state)){try{const r=JSON.parse(await fs.readFile(path.join(state,id,'status.json'),'utf8'));if(r.state!=='exited')r.state='unknown';entries.set(id,{record:r});await save(r);}catch{}}
async function cancel(e){e.record.cancel_requested=true;await save(e.record);if(e.child){try{process.kill(-e.child.pid,'SIGTERM');}catch{}e.killTimer=setTimeout(()=>{try{process.kill(-e.child.pid,'SIGKILL');}catch{}},5000);}}
async function lease(){if(leaseBusy)return;leaseBusy=true;try{const u=new URL('/internal/v1/runtime/lease',cfg.control_url);for(const k of ['task_id','runtime_attempt','execution_epoch'])u.searchParams.set(k,String(cfg[k]));const r=await fetch(u,{headers:{Authorization:`Bearer ${leaseToken}`},signal:AbortSignal.timeout(3000)});const body=await r.json();if(r.ok&&body.allowed===true)leaseUntil=Math.min(Date.parse(body.expires_at),Date.now()+15000);else leaseUntil=0;}catch{}finally{leaseBusy=false;}}
await lease();setInterval(lease,5000).unref();
setInterval(()=>{for(const e of entries.values())if(e.child&&!e.record.cancel_requested&&(Date.now()>=leaseUntil||Date.now()>=e.deadline))void cancel(e);},250).unref();
const kaliTools=['http_request','fixture_http','workspace_read','workspace_write','workspace_list','fixture_wait'];
const allowed=['http_request','fixture_http','workspace_read','workspace_write','workspace_list','fixture_wait','task_read','graph_read','tool_wait','tool_cancel'];
if(cfg.profile_id==='closed-web-assessment-v1')allowed.push('graph_refresh','assessment_read','evidence_read','verification_submit');
const publicRecord=r=>({...r});
function nativeSettings(assignment){
 const settings={retry:{enabled:false,maxRetries:0,provider:{maxRetries:0}}};
 const policy=assignment.context_policy;
 if(policy===null||policy===undefined)return settings;
 const exactKeys=(value,keys)=>value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join(',')===keys.slice().sort().join(',');
 if(cfg.profile_id!=='closed-web-assessment-v1'||assignment.profile_id!=='closed-web-assessment-v1'||!exactKeys(policy,['compaction'])||!exactKeys(policy.compaction,['enabled','reserveTokens','keepRecentTokens']))throw Error('context_policy_denied');
 const compact=policy.compaction;
 if(compact.enabled!==true||compact.reserveTokens!==16384||compact.keepRecentTokens!==512)throw Error('context_policy_denied');
 settings.compaction={enabled:true,reserveTokens:16384,keepRecentTokens:512};
 return settings;
}
async function launch(id,b){
 const identity=role==='agent'?b.assignment:b;
 for(const key of ['task_id','execution_epoch','runtime_attempt'])if(identity?.[key]!==cfg[key])throw Error('binding_mismatch');
 if(role==='agent')for(const key of ['tenant_id','project_id'])if(identity?.[key]!==cfg[key])throw Error('binding_mismatch');
 if(role==='agent'&&('settings' in b||'settings' in identity))throw Error('dynamic_settings_denied');
 const settings=role==='agent'?nativeSettings(identity):null;
 const hash=digest(JSON.stringify(b));const old=entries.get(id);if(old){if(old.record.request_digest!==hash)throw Error('id_conflict');return old;}
 if(Date.now()>=leaseUntil)throw Error('permit_expired');
 if(!b.operation_id)throw Error('operation_required');
 if(role==='agent'&&(!['bootstrap','reason','explore'].includes(b.phase)||!Array.isArray(b.tool_names)||b.tool_names.some(x=>!allowed.includes(x))||!b.tool_token))throw Error('invalid_run');
 if(role==='kali'&&!kaliTools.includes(b.tool))throw Error('invalid_tool');
 const deadline=Math.min(Date.parse(role==='agent'?b.deadline:b.expires_at),Date.now()+(role==='agent'?90000:60000));if(!Number.isFinite(deadline)||deadline<=Date.now())throw Error('expired');
 const dir=path.join(state,id);await fs.mkdir(dir,{mode:0o700});
 const r={id,state:'registered',returncode:null,pid:null,started_at:null,finished_at:null,cancel_requested:false,output_digest:null,request_digest:hash};const e={record:r,deadline};entries.set(id,e);await save(r);
 let executable=process.execPath,args,env={PATH:process.env.PATH,HOME:dir,WUJI_CONFIG:configPath,WUJI_WORKSPACE:process.env.WUJI_WORKSPACE||'/workspace'};
 if(role==='agent'){
 const {tool_token,...clean}=b;await fs.writeFile(path.join(dir,'tool_token'),tool_token,{mode:0o600});await fs.writeFile(path.join(dir,'run.json'),JSON.stringify(clean),{mode:0o600});
 const piDir=path.join(dir,'pi');await fs.mkdir(piDir,{mode:0o700});
 await fs.writeFile(path.join(piDir,'settings.json'),JSON.stringify(settings),{mode:0o600});
 env={...env,PI_CODING_AGENT_DIR:piDir,WUJI_RUN_DIR:dir,WUJI_MODEL_KEY_FILE:path.join(creds,'model_key')};
 executable=path.join(import.meta.dirname,'node_modules/.bin/pi');args=['--mode','json','--print','--no-extensions','--no-skills','--no-prompt-templates','--no-themes','--no-context-files','--no-builtin-tools','-e',path.join(import.meta.dirname,'trusted-extension.ts'),'--provider','wuji','--model',b.model.model_id,'--session',path.join(dir,'session.jsonl'),b.prompt];
 }else{await fs.writeFile(path.join(dir,'call.json'),JSON.stringify(b),{mode:0o600});args=[path.join(import.meta.dirname,'helper.mjs'),path.join(dir,'call.json')];}
 const out=await fs.open(path.join(dir,'output'),'a',0o600);const err=await fs.open(path.join(dir,'stderr'),'a',0o600);
 try{const child=spawn(executable,args,{cwd:dir,env,stdio:['ignore',out.fd,err.fd],detached:true});e.child=child;r.pid=child.pid??null;r.started_at=now();r.state='running';
 child.once('error',()=>{r.state='unknown';void save(r);});
 child.once('close',async(code,signal)=>{clearTimeout(e.killTimer);e.child=null;r.state='exited';r.returncode=code??(signal==='SIGKILL'?137:143);r.finished_at=now();const output=await fs.readFile(path.join(dir,'output'));r.output_digest=digest(output);if(role==='kali'){try{r.result=JSON.parse(output.toString());}catch{r.result={ok:false,error:'process_stopped'};}}await save(r);});
 await save(r);
 }catch{r.state='unknown';await save(r);}finally{await out.close();await err.close();}
 return e;
}
let launchQueue=Promise.resolve();
async function serializedLaunch(id,b){const operation=launchQueue.then(()=>launch(id,b));launchQueue=operation.catch(()=>{});return operation;}
const server=http.createServer(async(req,res)=>{const reply=(status,body)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(body));};
 try{if(req.headers.authorization!==`Bearer ${token}`)return reply(401,{error:'unauthorized'});const match=req.url.match(new RegExp(`^/${role==='agent'?'runs':'calls'}/([a-zA-Z0-9_-]{1,100})(/(output|cancel))?$`));if(!match)return reply(404,{error:'not_found'});const [,id,,action]=match;
 if(req.method==='PUT'&&!action){let body='';for await(const c of req){body+=c;if(body.length>2097152)return reply(413,{error:'too_large'});}return reply(200,publicRecord((await serializedLaunch(id,JSON.parse(body))).record));}
 const e=entries.get(id);if(!e)return reply(404,{error:'not_found'});
 if(req.method==='POST'&&action==='cancel'){await cancel(e);return reply(200,publicRecord(e.record));}
 if(req.method==='GET'&&action==='output'&&role==='agent'){const output=await fs.readFile(path.join(state,id,'output'),'utf8').catch(()=> '');return reply(200,{...publicRecord(e.record),output});}
 if(req.method==='GET'&&!action)return reply(200,publicRecord(e.record));return reply(405,{error:'method_not_allowed'});
 }catch{return reply(409,{error:'request_rejected'});}});
server.listen(Number(process.env.PORT||(role==='agent'?8001:8003)),'0.0.0.0');
for(const sig of ['SIGTERM','SIGINT'])process.on(sig,async()=>{server.close();leaseUntil=0;await Promise.all([...entries.values()].map(cancel));setTimeout(()=>process.exit(0),5500);});

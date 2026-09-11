import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import {spawn} from 'node:child_process';
const root=await fs.mkdtemp(path.join(os.tmpdir(),'wuji-workers-'));
const workspace=path.join(root,'workspace');await fs.mkdir(workspace);await fs.mkdir(path.join(workspace,'.wuji'));
const cfg=path.join(root,'binding.json');await fs.writeFile(cfg,JSON.stringify({fixture_origins:[]}));
async function helper(tool,args){const input=path.join(root,crypto.randomUUID()+'.json');await fs.writeFile(input,JSON.stringify({tool,args}));const p=spawn(process.execPath,['services/task-workers/helper.mjs',input],{env:{...process.env,WUJI_CONFIG:cfg,WUJI_WORKSPACE:workspace}});let output='';p.stdout.on('data',c=>output+=c);await new Promise(r=>p.on('close',r));return JSON.parse(output);}
test('shared file handoff and path/target boundaries',async()=>{assert.equal((await helper('workspace_write',{path:'shared/proof.txt',content:'handoff'})).ok,true);assert.equal((await helper('workspace_read',{path:'shared/proof.txt'})).content,'handoff');assert.equal((await helper('workspace_read',{path:'../binding.json'})).ok,false);assert.equal((await helper('workspace_write',{path:'.wuji/control',content:'bad'})).ok,false);await fs.symlink(root,path.join(workspace,'escape'));assert.equal((await helper('workspace_read',{path:'escape/binding.json'})).ok,false);assert.equal((await helper('fixture_http',{url:'http://example.com'})).ok,false);});
test('durable same-key receipt and actual cancellation',async()=>{
 const control=http.createServer((req,res)=>{res.setHeader('content-type','application/json');res.end(JSON.stringify({allowed:true,expires_at:new Date(Date.now()+15000).toISOString()}));});await new Promise(r=>control.listen(0,'127.0.0.1',r));
 const binding={task_id:'task',runtime_attempt:'attempt',execution_epoch:1,fixture_origins:[],control_url:`http://127.0.0.1:${control.address().port}`};await fs.writeFile(cfg,JSON.stringify(binding));const creds=path.join(root,'creds');await fs.mkdir(creds);await fs.writeFile(path.join(creds,'router_token'),'router');await fs.writeFile(path.join(creds,'lease_token'),'lease');
 const reserve=http.createServer();await new Promise(r=>reserve.listen(0,'127.0.0.1',r));const port=reserve.address().port;await new Promise(r=>reserve.close(r));
 const proc=spawn(process.execPath,['services/task-workers/supervisor.mjs','kali'],{env:{...process.env,WUJI_CONFIG:cfg,WUJI_WORKSPACE:workspace,WUJI_CREDENTIALS:creds,WUJI_STATE:path.join(root,'state'),PORT:String(port)}});
 const api=async(method,route,body)=>{const r=await fetch(`http://127.0.0.1:${port}${route}`,{method,headers:{authorization:'Bearer router','content-type':'application/json'},body:body?JSON.stringify(body):undefined});return {status:r.status,body:await r.json()};};
 try{for(let i=0;i<50;i++){try{await api('GET','/calls/missing');break;}catch{await new Promise(r=>setTimeout(r,50));}}
 const body={...binding,agent_run_id:'run',operation_id:'op',tool:'fixture_wait',args:{seconds:30},expires_at:new Date(Date.now()+60000).toISOString()};const first=await api('PUT','/calls/call',body);assert.equal(first.body.state,'running');assert.equal((await api('PUT','/calls/call',body)).body.pid,first.body.pid);assert.equal((await api('PUT','/calls/call',{...body,args:{seconds:1}})).status,409);await api('POST','/calls/call/cancel');let stopped;for(let i=0;i<100;i++){stopped=(await api('GET','/calls/call')).body;if(stopped.state==='exited')break;await new Promise(r=>setTimeout(r,50));}assert.equal(stopped.state,'exited');assert.equal(stopped.cancel_requested,true);assert.ok(stopped.finished_at);assert.notEqual(stopped.returncode,0);
 }finally{proc.kill('SIGTERM');await new Promise(r=>proc.on('close',r));await new Promise(r=>control.close(r));}
});

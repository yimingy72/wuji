import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';
import {once} from 'node:events';

const helper=path.resolve('services/task-workers/helper.mjs');
async function setup(origins){
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'wuji-http-observation-'));
 await fs.writeFile(path.join(dir,'binding.json'),JSON.stringify({fixture_origins:origins}));
 return {dir,async start(args){
  const input=path.join(dir,crypto.randomUUID()+'.json');await fs.writeFile(input,JSON.stringify({tool:'http_request',args}));
  const proc=spawn(process.execPath,[helper,input],{env:{...process.env,WUJI_CONFIG:path.join(dir,'binding.json'),WUJI_WORKSPACE:dir}});
  let output='';proc.stdout.on('data',c=>output+=c);
  const result=once(proc,'close').then(([code])=>({code,...JSON.parse(output)}));
  return {proc,result};
 },async close(){await fs.rm(dir,{recursive:true,force:true});}};
}
function verify(result){
 const e=result.exchange;assert.equal(e.schema_version,'http.exchange.v1');const bytes=Buffer.from(e.body_base64,'base64');assert.equal(bytes.length,e.body_bytes);assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),e.body_sha256);assert.ok(Date.parse(e.finished_at)>=Date.parse(e.started_at));return e;
}
test('lab observations: reflected origin, allowlist and anonymous account',async()=>{
 const lab=spawn('python3',['services/web-assessment-lab/server.py'],{env:{...process.env,PORT:'0'}});
 const [line]=await once(lab.stdout,'data');const origin='http://127.0.0.1:'+String(line).trim().split(':')[1];const context=await setup([origin]);
 try{
  const request=async(p,headers={},method='GET')=>(await context.start({url:origin+p,method,headers})).result;
  const home=verify(await request('/'));assert.match(Buffer.from(home.body_base64,'base64').toString(),/\/catalog\/a/);
  const a=verify(await request('/catalog/a',{Origin:'http://localhost:43210'}));assert.equal(a.response_headers['access-control-allow-origin'],'http://localhost:43210');assert.equal(a.response_headers['access-control-allow-credentials'],'true');
  const b=verify(await request('/catalog/b',{Origin:'http://localhost:43210'}));assert.equal(b.response_headers['access-control-allow-origin'],undefined);
  const trusted=verify(await request('/catalog/b',{Origin:'https://trusted.example.invalid'},'OPTIONS'));assert.equal(trusted.response_headers['access-control-allow-origin'],'https://trusted.example.invalid');
  const account=verify(await request('/account/view'));assert.equal(account.status,401);assert.equal(account.complete,true);
  const head=verify(await request('/catalog/a',{},'HEAD'));assert.equal(head.body_bytes,0);
 }finally{lab.kill();await once(lab,'close');await context.close();}
});
test('request boundary, response limits/redaction, redirect and cancellation preserve observations',async()=>{
 let signalStart;let touched=0;
 const server=http.createServer((req,res)=>{
  touched++;
  if(req.url==='/large'){res.end(Buffer.alloc(1048576+12,97));return;}
  if(req.url==='/headers'){res.setHeader('x-large','x'.repeat(9000));res.end();return;}
  if(req.url==='/redirect'){res.writeHead(302,{Location:'/never-follow'});res.end();return;}
  if(req.url==='/slow'){res.writeHead(200,{'content-type':'text/plain'});res.write('observed-prefix');signalStart?.();return;}
  res.setHeader('Set-Cookie','sensitive-value');res.setHeader('WWW-Authenticate','sensitive-challenge');res.setHeader('X-Public','visible');res.end('observed');
 });await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const origin='http://127.0.0.1:'+server.address().port;const context=await setup([origin]);
 try{
  for(const args of [{url:'http://127.0.0.1:1/',method:'GET'},{url:origin+'/#fragment',method:'GET'},{url:origin.replace('://','://user@')+'/',method:'GET'},{url:origin+'/',method:'POST'},{url:origin+'/',method:'GET',body:'forbidden'},{url:origin+'/',method:'GET',headers:{Cookie:'secret'}},{url:origin+'/',method:'GET',headers:{Accept:'a',accept:'b'}},{url:origin+'/',method:'GET',headers:{Origin:'a\r\nb'}}]){
   const result=await(await context.start(args)).result;assert.equal(result.ok,false);assert.equal(result.exchange,undefined);
  }
  assert.equal(touched,0);
  const normal=verify(await(await context.start({url:origin+'/',method:'GET'})).result);assert.equal(normal.response_headers['set-cookie'],undefined);assert.deepEqual(normal.redacted_headers,['set-cookie','www-authenticate']);assert.equal(normal.response_headers['x-public'],'visible');
  const large=verify(await(await context.start({url:origin+'/large',method:'GET'})).result);assert.equal(large.termination,'size_limit');assert.equal(large.body_bytes,1048576);assert.equal(large.complete,false);
  const headers=verify(await(await context.start({url:origin+'/headers',method:'GET'})).result);assert.equal(headers.termination,'size_limit');
  const before=touched;const redirect=verify(await(await context.start({url:origin+'/redirect',method:'GET'})).result);assert.equal(redirect.status,302);assert.equal(touched,before+1);
  const started=new Promise(r=>signalStart=r);const slow=await context.start({url:origin+'/slow',method:'GET'});await started;await new Promise(r=>setTimeout(r,80));slow.proc.kill('SIGTERM');const cancelled=verify(await slow.result);assert.equal(cancelled.termination,'cancelled');assert.equal(Buffer.from(cancelled.body_base64,'base64').toString(),'observed-prefix');
 }finally{server.closeAllConnections();await new Promise(r=>server.close(r));await context.close();}
});

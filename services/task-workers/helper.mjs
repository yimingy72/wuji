import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import https from 'node:https';
import crypto from 'node:crypto';
import zlib from 'node:zlib';
const input=JSON.parse(await fs.readFile(process.argv[2],'utf8'));
const config=JSON.parse(await fs.readFile(process.env.WUJI_CONFIG||'/config/binding.json','utf8'));
const root=await fs.realpath(process.env.WUJI_WORKSPACE||'/workspace');
async function safe(name,write=false){
 if(typeof name!=='string'||name.includes('\0'))throw Error('invalid_path');
 const target=path.resolve(root,name.replace(/^\/workspace\/?/,''));
 if(target!==root&&!target.startsWith(root+'/'))throw Error('outside_workspace');
 const parts=path.relative(root,target).split('/').filter(Boolean);if(parts[0]==='.wuji')throw Error('reserved_path');let current=root;
 for(let i=0;i<parts.length;i++){current=path.join(current,parts[i]);try{const s=await fs.lstat(current);if(s.isSymbolicLink())throw Error('symlink_forbidden');}catch(e){if(e.code!=='ENOENT'||!write)throw e;if(i<parts.length-1)await fs.mkdir(current);}}
 return target;
}
const HTTP_BODY_LIMIT=1048576;
const HTTP_HEADER_LIMIT=8192;
const secretHeaders=new Set(['set-cookie','cookie','authorization','proxy-authorization','www-authenticate','proxy-authenticate']);
function httpRequest(args){
 if(!args||typeof args!=='object'||Array.isArray(args)||Object.keys(args).some(k=>!['url','method','headers'].includes(k)))throw Error('invalid_http_args');
 if(typeof args.url!=='string'||/[\s\x00-\x1f\x7f]/.test(args.url)||args.url.includes('#'))throw Error('invalid_url');
 const url=new URL(args.url);
 if(url.username||url.password||args.url.split('/')[2]?.includes('@')||!['http:','https:'].includes(url.protocol)||!config.fixture_origins.includes(url.origin))throw Error('destination_denied');
 if(!['GET','HEAD','OPTIONS'].includes(args.method))throw Error('method_denied');
 const headers={};const names=new Set();
 if(args.headers!==undefined&&(!args.headers||typeof args.headers!=='object'||Array.isArray(args.headers)))throw Error('invalid_headers');
 for(const [name,value] of Object.entries(args.headers||{})){
  const lower=name.toLowerCase();
  if(!['accept','origin'].includes(lower)||names.has(lower)||typeof value!=='string'||/[\x00-\x1f\x7f]/.test(value))throw Error('header_denied');
  names.add(lower);headers[lower]=value;
 }
 if(Buffer.byteLength(args.method+' '+url.pathname+url.search+' HTTP/1.1\r\nhost: '+url.host+'\r\nconnection: close\r\n\r\n')+Object.entries(headers).reduce((n,[k,v])=>n+Buffer.byteLength(k+': '+v+'\r\n'),0)>HTTP_HEADER_LIMIT)throw Error('headers_too_large');
 return new Promise(resolve=>{
  const exchange={schema_version:'http.exchange.v1',url:url.href,method:args.method,request_headers:headers,status:null,response_headers:{},body_base64:'',body_bytes:0,body_sha256:'',body_encoding:'client-decoded',started_at:new Date().toISOString(),finished_at:null,complete:false,termination:'network_error',redacted_headers:[]};
  const chunks=[];let request;let body;let settled=false;
  const finish=termination=>{
   if(settled)return;settled=true;clearTimeout(timer);process.removeListener('SIGTERM',cancel);
   const bytes=Buffer.concat(chunks);exchange.body_base64=bytes.toString('base64');exchange.body_bytes=bytes.length;exchange.body_sha256=crypto.createHash('sha256').update(bytes).digest('hex');exchange.finished_at=new Date().toISOString();exchange.complete=termination==='complete';exchange.termination=termination;
   if(termination!=='complete'){request?.destroy();body?.destroy();}
   resolve({ok:exchange.complete,exchange});
  };
  const cancel=()=>finish('cancelled');process.once('SIGTERM',cancel);
  const timer=setTimeout(()=>finish('timeout'),30000);
  request=(url.protocol==='https:'?https:http).request(url,{method:args.method,headers:{...headers,connection:'close'},maxHeaderSize:HTTP_HEADER_LIMIT,agent:false,rejectUnauthorized:true},response=>{
   exchange.status=response.statusCode??null;
   for(const [name,value] of Object.entries(response.headers)){
    if(secretHeaders.has(name)){exchange.redacted_headers.push(name);continue;}
    exchange.response_headers[name]=Array.isArray(value)?value.join(', '):String(value??'');
   }
   exchange.redacted_headers.sort();
   body=response;
   const encoding=(response.headers['content-encoding']||'identity').toLowerCase();
   if(args.method!=='HEAD'){
    if(encoding==='gzip')body=response.pipe(zlib.createGunzip());
    else if(encoding==='deflate')body=response.pipe(zlib.createInflate());
    else if(encoding==='br')body=response.pipe(zlib.createBrotliDecompress());
    else if(encoding!=='identity'){finish('network_error');return;}
   }
   response.on('error',()=>finish('network_error'));
   body.on('data',chunk=>{
    const remaining=HTTP_BODY_LIMIT-exchange.body_bytes;
    const bytes=Buffer.from(chunk);const keep=bytes.subarray(0,remaining);chunks.push(keep);exchange.body_bytes+=keep.length;
    if(bytes.length>remaining)finish('size_limit');
   });
   body.once('end',()=>finish('complete'));body.once('error',()=>finish('network_error'));
  });
  exchange.request_headers=Object.fromEntries(Object.entries(request.getHeaders()).map(([name,value])=>[name.toLowerCase(),String(value)]));
  request.once('error',error=>finish(error.code==='HPE_HEADER_OVERFLOW'?'size_limit':'network_error'));
  request.end();
 });
}
try{
 const a=input.args||{};let result;
 switch(input.tool){
 case 'http_request':result=await httpRequest(a);if(!result.ok)process.exitCode=1;break;
 case 'workspace_write':{if(typeof a.content!=='string'||Buffer.byteLength(a.content)>1048576)throw Error('invalid_content');const p=await safe(a.path,true);const temporary=p+'.pending-'+process.pid;try{await fs.writeFile(temporary,a.content,{flag:'wx',mode:0o600});await fs.rename(temporary,p);}finally{await fs.unlink(temporary).catch(()=>{});}result={path:a.path,bytes:Buffer.byteLength(a.content)};break;}
 case 'workspace_read':{const p=await safe(a.path);if((await fs.stat(p)).size>1048576)throw Error('file_too_large');result={path:a.path,content:await fs.readFile(p,'utf8')};break;}
 case 'workspace_list':result={path:a.path,entries:(await fs.readdir(await safe(a.path))).slice(0,1000)};break;
 case 'fixture_wait':{const seconds=Number(a.seconds);if(!Number.isFinite(seconds)||seconds<0||seconds>60)throw Error('invalid_wait');await new Promise(r=>setTimeout(r,seconds*1000));result={waited_seconds:seconds};break;}
 case 'fixture_http':{const u=new URL(a.url);if(u.username||u.password||!['http:','https:'].includes(u.protocol)||!config.fixture_origins.includes(u.origin))throw Error('destination_denied');if(a.method&&a.method!=='GET')throw Error('method_denied');const r=await fetch(u,{redirect:'manual',signal:AbortSignal.timeout(30000)});if(r.status>=300&&r.status<400)throw Error('redirect_denied');let size=0;const chunks=[];for await(const c of r.body){size+=c.length;if(size>1048576)throw Error('response_too_large');chunks.push(c);}result={url:u.href,status:r.status,body:Buffer.concat(chunks).toString('utf8')};break;}
 default:throw Error('tool_denied');
 }
 process.stdout.write(JSON.stringify({ok:true,...result}));
}catch{process.stdout.write(JSON.stringify({ok:false,error:'controlled_tool_failed'}));process.exitCode=1;}

import fs from 'node:fs/promises';
import path from 'node:path';
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
try{
 const a=input.args||{};let result;
 switch(input.tool){
 case 'workspace_write':{if(typeof a.content!=='string'||Buffer.byteLength(a.content)>1048576)throw Error('invalid_content');const p=await safe(a.path,true);const temporary=p+'.pending-'+process.pid;try{await fs.writeFile(temporary,a.content,{flag:'wx',mode:0o600});await fs.rename(temporary,p);}finally{await fs.unlink(temporary).catch(()=>{});}result={path:a.path,bytes:Buffer.byteLength(a.content)};break;}
 case 'workspace_read':{const p=await safe(a.path);if((await fs.stat(p)).size>1048576)throw Error('file_too_large');result={path:a.path,content:await fs.readFile(p,'utf8')};break;}
 case 'workspace_list':result={path:a.path,entries:(await fs.readdir(await safe(a.path))).slice(0,1000)};break;
 case 'fixture_wait':{const seconds=Number(a.seconds);if(!Number.isFinite(seconds)||seconds<0||seconds>60)throw Error('invalid_wait');await new Promise(r=>setTimeout(r,seconds*1000));result={waited_seconds:seconds};break;}
 case 'fixture_http':{const u=new URL(a.url);if(u.username||u.password||!['http:','https:'].includes(u.protocol)||!config.fixture_origins.includes(u.origin))throw Error('destination_denied');if(a.method&&a.method!=='GET')throw Error('method_denied');const r=await fetch(u,{redirect:'manual',signal:AbortSignal.timeout(30000)});if(r.status>=300&&r.status<400)throw Error('redirect_denied');let size=0;const chunks=[];for await(const c of r.body){size+=c.length;if(size>1048576)throw Error('response_too_large');chunks.push(c);}result={url:u.href,status:r.status,body:Buffer.concat(chunks).toString('utf8')};break;}
 default:throw Error('tool_denied');
 }
 process.stdout.write(JSON.stringify({ok:true,...result}));
}catch{process.stdout.write(JSON.stringify({ok:false,error:'controlled_tool_failed'}));process.exitCode=1;}

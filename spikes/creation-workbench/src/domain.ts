import type { components } from '@wuji/contracts/types';
export type DraftContent = components['schemas']['SavedTaskDraft']['content'];
export type ServiceConfig = components['schemas']['ServiceConfig'];
export type ProfileConfig = components['schemas']['ProfileConfig'];
export type Pricing = components['schemas']['ModelPricing'];
export type NativeVersion = components['schemas']['ModelVersion'];
export type Scenario = DraftContent['scenario'];
export const scenarios: { value: Scenario; name: string; hint: string }[] = [
  { value:'web_single', name:'Web 单点', hint:'单个系统，明确域名与授权边界' },
  { value:'ctf', name:'CTF', hint:'题目说明与靶机入口' },
  { value:'comprehensive', name:'综合渗透', hint:'资产集合与接入条件' },
  { value:'exercise', name:'攻防演练', hint:'单位信息与已知资产' },
  { value:'code_audit', name:'代码审计', hint:'源码地址与版本' },
];
export type Pair = `${'http'|'https'}:${number}`;
export interface Include { id: string; host: string; descendants: boolean; scheme: 'http'|'https'; port: number }
export interface Exclude { id: string; host: string; descendants: boolean; endpoints: 'all' | Pair[] }
// New interaction fields stay outside the generated D1 content contract.
export interface Draft { id:string; userId:string; projectId:string; content:DraftContent; goalTemplate:{scenario:Scenario;version:1;objective:string;criteria:readonly string[]}; completionCriteria:string; supplementalHints:string; includes:Include[]; excludes:Exclude[]; validUntil:string; confirmed:boolean; savedAt:string|null; dirty:boolean }
export interface Service extends Omit<NativeVersion,'kind'|'config'> { kind:'service'; config:ServiceConfig; keyConfigured:boolean }
export interface Profile extends Omit<NativeVersion,'kind'|'config'> { kind:'profile'; config:ProfileConfig; check:'never'|'checking'|'succeeded'|'failed'|'unknown'; block:'none'|'pending'|'confirmed' }
export interface Task { id:string; projectId:string; createdAt:string; state:'ready'|'cancelled'; draft:Draft; model:Profile }
export const isIP = (host:string) => host.includes(':') || /^\d+\.\d+\.\d+\.\d+$/.test(host);
export function host(value:string):string|null {
  const v=value.trim().toLowerCase();
  if (!v || /[\s/@?#]/.test(v)) return null;
  if (v.includes(':')) { try { return new URL(`http://${v.startsWith('[')?v:`[${v}]`}/`).hostname.replace(/^\[|\]$/g,''); } catch { return null; } }
  if (/^[\d.]+$/.test(v)) return v.split('.').length===4 && v.split('.').every(p=>/^(0|[1-9]\d{0,2})$/.test(p)&&Number(p)<=255) ? v : null;
  return v.length<=253 && v.split('.').every(p=>/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(p)) ? v : null;
}
export function entry(value:string):{host:string;scheme:'http'|'https';port:number;url:string}|null {
  try {
    if (!/^https?:\/\//i.test(value) || /[\s\\]/.test(value)) return null;
    const u=new URL(value); if (!['https:','http:'].includes(u.protocol)||u.username||u.password||value.includes('#')) return null;
    const authority=value.split('/')[2]??'';
    const raw=authority.startsWith('[')?authority.slice(0,authority.indexOf(']')+1):authority.split(':')[0]??'';
    const normalized=host(raw); if (!normalized) return null;
    return { host:normalized,scheme:u.protocol==='https:'?'https':'http',port:Number(u.port||(u.protocol==='https:'?443:80)),url:u.href };
  } catch { return null; }
}
export const pair=(r:Include):Pair=>`${r.scheme}:${r.port}`;
export const pairLabel=(p:Pair)=>p.toUpperCase();
export function matches(pattern:string,descendants:boolean,target:string) {
  return pattern===target || (descendants&&!isIP(pattern)&&target.endsWith('.'+pattern));
}
export function scopeIssues(d:Draft):string[] {
  const issues:string[]=[];
  const url='entry_url' in d.content ? entry(d.content.entry_url??'') : null;
  const includes=d.includes.map(r=>({...r,host:host(r.host)}));
  const excludes=d.excludes.map(r=>({...r,host:host(r.host)}));
  if (!url) issues.push('请填写有效的 HTTP 或 HTTPS 测试地址');
  if (!includes.length) issues.push('请至少添加一个包含对象');
  if (includes.some(r=>!r.host||!Number.isInteger(r.port)||r.port<1||r.port>65535)) issues.push('请补全包含对象的主机和端口');
  if (excludes.some(r=>!r.host||(r.endpoints!=='all'&&!r.endpoints.length))) issues.push('请补全排除对象及适用协议／端口');
  const denied=(target:string,p:Pair)=>excludes.some(r=>r.host&&matches(r.host,r.descendants,target)&&(r.endpoints==='all'||r.endpoints.includes(p)));
  if (url) {
    if (!includes.some(r=>r.host&&matches(r.host,r.descendants,url.host)&&r.scheme===url.scheme&&r.port===url.port)) issues.push('测试地址不在包含范围内');
    else if (denied(url.host,`${url.scheme}:${url.port}`)) issues.push('测试地址已被排除，请修改排除规则');
  }
  const nonempty=includes.some(r=>r.host&&!excludes.some(x=>x.host&&(x.endpoints==='all'||x.endpoints.includes(pair(r as Include)))&&
    matches(x.host,x.descendants,r.host!)&&(!r.descendants||isIP(r.host!)||x.descendants)));
  if (includes.length&&!nonempty) issues.push('排除后有效范围为空');
  return [...new Set(issues)];
}
export const available=(p:Profile)=>p.state==='published'&&p.sync_state==='synced';
export function creationIssues(d:Draft,profiles:Profile[]) {
  const issues=scopeIssues(d);
  if (d.content.scenario!=='web_single') issues.push('当前场景可保存草稿，暂不开放创建');
  if (!d.content.name?.trim()) issues.push('请填写任务名称');
  if (!d.content.objective?.trim()) issues.push('请填写任务目标');
  if (!d.completionCriteria.trim()) issues.push('请填写完成条件');
  if (!d.validUntil || !Number.isFinite(Date.parse(d.validUntil)) || Date.parse(d.validUntil)<=Date.now()) issues.push('请选择尚未到期的授权截止时间');
  if (!profiles.some(p=>p.id===d.content.model_profile_version_id&&available(p))) issues.push('请选择可用的已发布模型方案');
  if (!d.content.budget_usd || !/^(0|[1-9]\d{0,11})(\.\d{1,6})?$/.test(d.content.budget_usd) || !/[1-9]/.test(d.content.budget_usd)) issues.push('请填写大于 0 的 USD 金额上限');
  if (!d.confirmed) issues.push('请确认本次授权范围');
  return [...new Set(issues)];
}
export function profileLabel(p:Profile) { return `${p.name} · V${p.number}`; }
export function modelState(p:Profile) {
  if(p.state==='revoked') return p.block==='confirmed'?'平台已禁用，网关已确认阻断':'平台已禁用，网关阻断待确认';
  if(p.state==='retired') return '已停止发布';
  if(p.state==='published') return '已发布';
  return ({never:'未检查',checking:'检查中',succeeded:'检查成功，未发布',failed:'检查失败',unknown:'检查结果待确认'} as const)[p.check];
}
export const cacheLabel=(p?:Pricing|null)=>!p?'未配置价格':p.cache_mode==='standard_input'?'按普通输入单价计费':'缓存单独计价';
export function pricingIssues(p:Pricing|null|undefined) {
  if (!p) return [];
  const amount=(s:unknown)=>typeof s==='string'&&/^(0|[1-9]\d{0,11})(\.\d{1,12})?$/.test(s);
  const issues=[];
  if (!p.source.trim()) issues.push('请填写价格来源');
  if (!amount(p.input_per_million)||!amount(p.output_per_million)) issues.push('请填写有效的输入和输出单价');
  if (![p.input_per_million,p.output_per_million].some(x=>/[1-9]/.test(x??''))) issues.push('输入与输出单价不能同时为零');
  if (!['standard_input','separate'].includes(p.cache_mode)) issues.push('请明确选择缓存计价模式');
  if(p.cache_mode==='separate'&&(!amount(p.cache_read_per_million)||!amount(p.cache_creation_per_million))) issues.push('请填写缓存读取和缓存创建单价');
  return issues;
}

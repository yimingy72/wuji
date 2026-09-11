import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from 'react';
import { Alert, Button, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { available, cacheLabel, isIP, modelState, pair, pairLabel, profileLabel, type Draft, type Profile } from './domain';
import { abandon, getState, inspectList, pending, reconcile, submit, useStore } from './store';
import { App } from 'antd';
import s from './workbench.module.css';
export function Field({label,hint,required,children,wide=false}:{label:string;hint?:ReactNode;required?:boolean;children:ReactNode;wide?:boolean}) {
 const id=useId();return <div className={`${s.field} ${wide?s.wide:''}`}><label htmlFor={id}>{label}{required&&<span className={s.required}> *</span>}</label>
 {isValidElement(children)?cloneElement(children as ReactElement<{id?:string;'aria-label'?:string}>,{id,'aria-label':label}):children}{hint&&<span className={s.hint}>{hint}</span>}</div>;
}
export function ScopeSummary({draft,compact=false}:{draft:Draft;compact?:boolean}) {
 return <div className={compact?s.scopeCompact:s.scopeSummary}><section><h3>包含对象</h3>{!draft.includes.length?<p className={s.muted}>尚未设置</p>:draft.includes.map(r=><div className={s.scopeLine} key={r.id}><code>{r.host||'未填写主机'}</code><span>{r.descendants&&!isIP(r.host)?'自身及全部下级子域':'仅该主机'}</span><b>{pairLabel(pair(r))}</b></div>)}</section>
 <section><h3>排除对象</h3>{!draft.excludes.length?<p className={s.muted}>无排除项</p>:draft.excludes.map(r=><div className={`${s.scopeLine} ${s.excluded}`} key={r.id}><code>{r.host||'未填写主机'}</code><span>{r.descendants&&!isIP(r.host)?'自身及全部下级子域':'仅该主机'}</span><b>{r.endpoints==='all'?'本任务全部协议／端口':r.endpoints.map(pairLabel).join('、')||'未选择协议／端口'}</b></div>)}</section>
 <section><h3>授权截止时间</h3><p>{draft.validUntil?new Date(draft.validUntil).toLocaleString('zh-CN',{hour12:false}):'尚未填写'}</p></section></div>;
}
export function ModelStatus({profile}:{profile:Profile}) {return <Tag color={profile.state==='revoked'?'error':available(profile)?'success':profile.check==='unknown'?'warning':'default'}>{modelState(profile)}</Tag>;}
export function DraftSummary({draft,model}:{draft:Draft;model?:Profile}) {return <><div className={s.summaryTitle}>任务摘要</div><h2 className={s.summaryName}>{draft.content.name||'未命名任务'}</h2><p className={s.muted}>{draft.content.objective||'尚未填写测试目标'}</p><ScopeSummary draft={draft} compact/>
 <dl className={s.facts}><dt>模型方案</dt><dd>{model?profileLabel(model):'尚未选择'}{model&&!available(model)&&<div className={s.invalidText}>原选择已不可用</div>}</dd><dt>模型金额上限</dt><dd>{draft.content.budget_usd?`$ ${draft.content.budget_usd} USD`:'尚未填写'}</dd></dl></>;}
export function PriceSummary({profile}:{profile:Profile}) {const p=profile.config.pricing;return <div className={s.priceSummary}><span>价格来源：{p?.source||'未配置'}</span><span>缓存计价：{cacheLabel(p)}</span>{p&&<span>输入 ${p.input_per_million} · 输出 ${p.output_per_million} / 百万 Token{p.cache_mode==='separate'?` · 缓存读取 $${p.cache_read_per_million} · 创建 $${p.cache_creation_per_million}`:''}</span>}</div>;}
export function PendingNotice() {
 useStore();const p=pending();const navigate=useNavigate();const {modal,message}=App.useApp();if(!p)return null;
 const query=async()=>{const id=await reconcile();if(id)navigate(`/tasks/${id}`);else if(pending())void message.info('当前尚未查到可确认结果，请保留原提交标识继续核对。');};
 return <div className={s.pending}><Alert type={p.state==='submitting'?'info':'warning'} showIcon title={p.state==='submitting'?'正在提交任务':'提交结果待确认'} description={p.state==='submitting'?'原提交已保留，请等待结果。':'尚未确认创建结果，请使用原提交标识核对。不要重新创建同一任务。'}/><div className={s.actions}>
 <Button disabled={p.state==='submitting'} onClick={()=>void query()}>核对结果</Button>
 <Button onClick={()=>{inspectList();navigate('/tasks');}}>查看任务列表</Button>
 {p.frozen&&<Button disabled={p.state==='submitting'} onClick={async()=>{const id=await submit(p.draftId,true);if(id)navigate(`/tasks/${id}`);}}>重试原提交</Button>}
 {p.inspected&&<Button type="text" disabled={p.state==='submitting'} onClick={()=>modal.confirm({title:'放弃此次核对？',content:'这不会删除或取消可能已经创建的任务。确认已查看任务列表后，再发起新的操作。',okText:'确认放弃核对',cancelText:'继续核对',onOk:()=>abandon()})}>放弃此次核对</Button>}
 <details className={s.diagnostic}><summary>提交标识</summary><code>{p.key}</code></details>
 </div>{!p.frozen&&<p className={s.hint}>原请求已不在当前页面，只能核对已有结果。</p>}</div>;
}
export function ErrorList({items}:{items:string[]}) {return items.length?<Alert type="warning" showIcon title={items.length===1?items[0]:'创建前请完成以下内容'} description={items.length>1?<ul className={s.errorList}>{items.map(i=><li key={i}>{i}</li>)}</ul>:undefined}/>:null;}
export function getModel(d:Draft){return getState().profiles.find(p=>p.id===d.content.model_profile_version_id);}

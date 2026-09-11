import { AuthorizationSummary } from './AuthorizationSummary';
import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Checkbox, Collapse, DatePicker, Input, Modal, Select, Steps } from 'antd';
import dayjs from 'dayjs';
import dateLocale from 'antd/es/date-picker/locale/zh_CN';
import 'dayjs/locale/zh-cn';
dayjs.locale('zh-cn');
import { Link, useBlocker, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ApiRequestError, getProjectModels, getSavedDraft, getSavedDrafts, getScenarioProfiles, previewCreation, saveDraft, type DraftContent, type DraftContentV2, type SavedTaskDraft, type ScenarioProfile, type Session, type TaskCreationPreview, type WebDraftContentV2 } from '../../api';
import { projectQueryOptions, projectRequest, readTaskSnapshot, refreshTaskLists } from '../../queries';
import { beginCommand, clearPendingCommand, usePendingCommand } from '../../pendingCommand';
import { isExplicitCommandRejection, PendingCommandNotice, sendFrozenCommand } from '../../tasks';
import { PrivatePage } from '../../pages';
import styles from './creation.module.css';

function defaultContent(profile: ScenarioProfile): DraftContentV2 {
  const common = {schema_version: '2.0' as const, name: '', objective: profile.objective, goal_template: {id: profile.id, version: profile.version, digest: profile.digest}, completion_criteria: [...profile.completion_criteria], supplemental_hints: '', reference_ids: [], model_profile_version_id: null, runtime_profile_version_id: null, budget_usd: null};
  switch (profile.scenario) {
    case 'web_single': return {...common, scenario: 'web_single', entry_url: null, authorization: null};
    case 'ctf': return {...common, scenario: 'ctf', challenge: '', entry_url: null};
    case 'comprehensive': return {...common, scenario: 'comprehensive', assets: [], access_notes: ''};
    case 'exercise': return {...common, scenario: 'exercise', organization_name: '', known_domains: []};
    case 'code_audit': return {...common, scenario: 'code_audit', repository_url: null, source_reference_id: null, revision: null};
  }
}
function Field({label, children}: {label: string; children: React.ReactNode}) {return <label className={styles.field}><span>{label}</span>{children}</label>;}
function parseEndpoint(value: string) {try {const u = new URL(value); if (!['http:', 'https:'].includes(u.protocol)) return null; return {host: u.hostname.replace(/^\[|\]$/g, ''), include_subdomains: false, endpoint: {scheme: u.protocol === 'https:' ? 'https' as const : 'http' as const, port: Number(u.port || (u.protocol === 'https:' ? 443 : 80))}};} catch {return null;}}

function AuthorizationEditor({content, onChange}: {content: WebDraftContentV2; onChange: (value: WebDraftContentV2) => void}) {
  const scope = {schema_version: '1.0' as const, ...content.authorization, includes: content.authorization?.includes ?? [], excludes: content.authorization?.excludes ?? [], valid_until: content.authorization?.valid_until ?? null};
  const update = (authorization: NonNullable<WebDraftContentV2['authorization']>) => onChange({...content, authorization});
  return <><h2>对象与范围</h2><p>测试地址中的路径仅作为入口。授权只用于本任务。</p><h3>包含</h3>{scope.includes.map((rule, index) => <div key={index} className={styles.rule}>
    <Field label="主机"><Input value={rule.host} onChange={e => update({...scope, includes: scope.includes.map((r, i) => i === index ? {...r, host: e.target.value} : r)})} /></Field>
    <Select aria-label="包含协议" value={rule.endpoint.scheme} options={[{value: 'http', label: 'HTTP'}, {value: 'https', label: 'HTTPS'}]} onChange={scheme => update({...scope, includes: scope.includes.map((r, i) => i === index ? {...r, endpoint: {...r.endpoint, scheme}} : r)})} />
    <Field label="端口"><Input type="number" min={1} max={65535} value={rule.endpoint.port} onChange={e => update({...scope, includes: scope.includes.map((r, i) => i === index ? {...r, endpoint: {...r.endpoint, port: Number(e.target.value)}} : r)})} /></Field>
    <Checkbox checked={rule.include_subdomains} onChange={e => update({...scope, includes: scope.includes.map((r, i) => i === index ? {...r, include_subdomains: e.target.checked} : r)})}>包含子域</Checkbox><Button onClick={() => update({...scope, includes: scope.includes.filter((_, i) => i !== index)})}>移除</Button>
  </div>)}<Button onClick={() => update({...scope, includes: [...scope.includes, {host: '', include_subdomains: false, endpoint: {scheme: 'https', port: 443}}]})}>添加包含项</Button>
  <h3>排除</h3>{scope.excludes.map((rule, index) => <div key={index} className={styles.rule}><Field label="排除主机"><Input value={rule.host} onChange={e => update({...scope, excludes: scope.excludes.map((r, i) => i === index ? {...r, host: e.target.value} : r)})} /></Field><Checkbox checked={rule.include_subdomains} onChange={e => update({...scope, excludes: scope.excludes.map((r, i) => i === index ? {...r, include_subdomains: e.target.checked} : r)})}>包含子域</Checkbox><Select aria-label="排除协议端口" mode="multiple" style={{minWidth: 230}} value={rule.endpoints === 'all_included' ? ['all_included'] : rule.endpoints.map(e => `${e.scheme}:${e.port}`)} options={[{value: 'all_included', label: '全部包含协议端口'}, ...Array.from(new Map(scope.includes.map(r => [`${r.endpoint.scheme}:${r.endpoint.port}`, {value: `${r.endpoint.scheme}:${r.endpoint.port}`, label: `${r.endpoint.scheme}:${r.endpoint.port}`}])).values())]} onChange={values => update({...scope, excludes: scope.excludes.map((r, i) => i === index ? {...r, endpoints: values.includes('all_included') ? 'all_included' : scope.includes.filter(inc => values.includes(`${inc.endpoint.scheme}:${inc.endpoint.port}`)).map(inc => inc.endpoint)} : r)})} /><Button onClick={() => update({...scope, excludes: scope.excludes.filter((_, i) => i !== index)})}>移除</Button></div>)}<Button onClick={() => update({...scope, excludes: [...scope.excludes, {host: '', include_subdomains: true, endpoints: 'all_included'}]})}>添加排除项</Button>
  <Field label="授权截止时间"><DatePicker aria-label="授权截止时间" placeholder="请选择日期和时间" showTime locale={dateLocale} format="YYYY-MM-DD HH:mm" value={scope.valid_until ? dayjs(scope.valid_until).locale('zh-cn') : null} onChange={value => update({...scope, valid_until: value?.toISOString() ?? null})} /></Field><p>时区：{Intl.DateTimeFormat().resolvedOptions().timeZone}</p></>;
}

function CreationEditor({session, projectId, initialDraftId}: {session: Session; projectId: string; initialDraftId?: string}) {
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const step = Math.max(0, Math.min(3, Number(search.get('step')) || 0));
  const [draftId] = useState(initialDraftId ?? crypto.randomUUID());
  const [fresh] = useState(search.get('new') === '1');
  const [saved, setSaved] = useState<SavedTaskDraft | null>(null);
  const [content, setContent] = useState<DraftContent | null>(null);
  const [preview, setPreview] = useState<TaskCreationPreview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(false);
  const [savedMessage, setSavedMessage] = useState('');
  const [modelCursor, setModelCursor] = useState<string | null>(null);
  const draftsByScenario = useRef(new Map<DraftContentV2['scenario'], DraftContentV2>());
  const controller = useRef(new AbortController());
  const creating = useRef(false);
  const pending = usePendingCommand(projectId, session.user_id);
  const dirty = content !== null && JSON.stringify(content) !== JSON.stringify(saved?.content);
  const blocker = useBlocker(({currentLocation, nextLocation}) => dirty && !creating.current && currentLocation.pathname !== nextLocation.pathname);
  useEffect(() => {const current = new AbortController(); controller.current = current; return () => current.abort();}, []);
  useEffect(() => {const fn = (e: BeforeUnloadEvent) => {if (dirty && !creating.current) {e.preventDefault(); e.returnValue = '';}}; window.addEventListener('beforeunload', fn); return () => window.removeEventListener('beforeunload', fn);}, [dirty]);
  const profiles = useQuery({queryKey: ['private', 'tasks', session.user_id, session.permissions_version, projectId, 'scenario-profiles'], queryFn: ({signal}) => projectRequest(session, projectId, () => getScenarioProfiles(projectId, signal))});
  const models = useQuery({queryKey: ['private', 'tasks', session.user_id, session.permissions_version, projectId, 'selectable-models', modelCursor], queryFn: ({signal}) => projectRequest(session, projectId, () => getProjectModels(projectId, modelCursor, signal))});
  useEffect(() => {if ((!initialDraftId || fresh) && !content && profiles.data) {const web = profiles.data.items.find(p => p.scenario === 'web_single'); if (web) setContent(defaultContent(web));}}, [content, initialDraftId, fresh, profiles.data]);
  const load = async () => {const signal = controller.current.signal; setBusy(true); try {const draft = await projectRequest(session, projectId, () => getSavedDraft(projectId, draftId, signal)); setSaved(draft); setContent(draft.content); setConflict(false); setPreview(null); setConfirmed(false);} catch {if (!signal.aborted) setError('草稿读取失败或当前身份不可访问。');} finally {if (!signal.aborted) setBusy(false);}};
  useEffect(() => {if (initialDraftId && !fresh) void load();}, [initialDraftId]);
  const change = (value: DraftContent) => {if (pending || busy) return; setContent(value); setPreview(null); setConfirmed(false); setSavedMessage('');};
  const switchScenario = (scenario: DraftContentV2['scenario']) => {
    if (!content || content.schema_version !== '2.0' || pending) return;
    draftsByScenario.current.set(content.scenario, content);
    const previous = draftsByScenario.current.get(scenario); const profile = profiles.data?.items.find(p => p.scenario === scenario);
    if (previous || profile) {change(previous ?? defaultContent(profile!)); setSearch({step: '0', ...(!saved && fresh ? {new: '1'} : {})}, {replace: true, defaultShouldRevalidate: false});}
  };
  const persist = async (): Promise<SavedTaskDraft | null> => {
    if (!content || pending || busy) return null;
    setBusy(true); setError('');
    try {const draft = await projectRequest(session, projectId, () => saveDraft(projectId, draftId, content, saved?.version ?? 0, session.csrf_token, controller.current.signal)); setSaved(draft); setContent(draft.content); setConflict(false); setSavedMessage('草稿已保存'); setSearch({step: String(step)}, {replace: true, defaultShouldRevalidate: false}); return draft;}
    catch (e) {if (!controller.current.signal.aborted) {setConflict(e instanceof ApiRequestError && e.status === 409); setError(e instanceof ApiRequestError ? e.message : '保存未完成，保留当前输入。');} return null;}
    finally {if (!controller.current.signal.aborted) setBusy(false);}
  };
  const copyAsNew = async (nextContent: DraftContent) => {
    if (pending || busy) return;
    const id = crypto.randomUUID();
    setBusy(true); setError('');
    try {
      await projectRequest(session, projectId, () => saveDraft(projectId, id, nextContent, 0, session.csrf_token, controller.current.signal));
      creating.current = true;
      navigate(`/projects/${projectId}/drafts/${id}`, {replace: true});
    } catch (e) {if (!controller.current.signal.aborted) setError(e instanceof ApiRequestError ? e.message : '新草稿保存未完成，原输入已保留。');}
    finally {if (!controller.current.signal.aborted) setBusy(false);}
  };
  const goTo = async (next: number) => {
    if (pending || busy) return;
    if (next === 3) {const draft = await persist(); if (!draft) return; setBusy(true); try {const result = await projectRequest(session, projectId, () => previewCreation(projectId, draft, session.csrf_token, controller.current.signal)); setPreview(result); setConfirmed(false);} catch (e) {if (!controller.current.signal.aborted) setError(e instanceof ApiRequestError ? e.message : '预览未完成'); return;} finally {if (!controller.current.signal.aborted) setBusy(false);}}
    setSearch({step: String(next), ...(!saved && fresh && next !== 3 ? {new: '1'} : {})}, {replace: true, defaultShouldRevalidate: false});
  };
  const create = async () => {
    if (!preview?.can_create || !confirmed || pending || busy) return;
    const request = {creation_kind: 'saved_web_draft' as const, draft_id: preview.draft_id, draft_version: preview.draft_version, preview_id: preview.preview_id, input_digest: preview.input_digest, scope_confirmation: {accepted: true as const, authorization_digest: preview.authorization_digest}};
    setBusy(true); setError('');
    try {const frozen = {kind: 'create' as const, request}; const marker = beginCommand(session.user_id, projectId, 'create', null, frozen); let accepted = false;
      try {const receipt = await sendFrozenCommand(session, marker, frozen, controller.current.signal); accepted = true; await readTaskSnapshot(session, projectId, receipt.task_id, controller.current.signal); clearPendingCommand(marker); await refreshTaskLists(projectId); creating.current = true; navigate(`/projects/${projectId}/tasks/${receipt.task_id}`);}
      catch (e) {if (!accepted && isExplicitCommandRejection(e)) clearPendingCommand(marker); throw e;}
    } catch (e) {if (!controller.current.signal.aborted) setError(e instanceof Error ? e.message : '创建响应不明，请核对原提交。');}
    finally {if (!controller.current.signal.aborted) setBusy(false);}
  };
  if (!content) return <section className={styles.page}><h1>创建任务</h1><p>{error || (profiles.error ? '场景模板读取失败' : '正在读取创建信息…')}</p><Button onClick={() => initialDraftId ? void load() : void profiles.refetch()}>重试读取</Button></section>;
  const profile = profiles.data?.items.find(p => p.scenario === content.scenario);
  const customized = content.schema_version === '2.0' && profile && (content.objective !== profile.objective || JSON.stringify(content.completion_criteria) !== JSON.stringify(profile.completion_criteria));
  return <section className={styles.page}><Link to={`/projects/${projectId}/tasks`}>返回任务列表</Link><header className={styles.heading}><h1>创建任务</h1><div><span>{savedMessage || (dirty ? '有未保存修改' : '已保存')}</span><Button disabled={Boolean(pending) || conflict} loading={busy} onClick={() => void persist()}>保存草稿</Button></div></header>
    <PendingCommandNotice session={session} projectId={projectId} />
    {error && <Alert showIcon type="error" title={error} />}
    {conflict && <Alert type="warning" title="草稿版本已变化，当前输入已保留" action={<div><Button onClick={() => void load()}>载入服务端版本</Button><Button onClick={() => void copyAsNew(content)}>复制为新草稿</Button></div>} />}
    {saved?.last_created_task_id && <p><Link to={`/projects/${projectId}/tasks/${saved.last_created_task_id}`}>查看最近创建的任务</Link></p>}
    {content.schema_version === '1.0' ? <><Alert type="warning" title="旧版草稿保持原语义" description="原起点与限制不会自动转换为补充线索。请核对原内容，另建新版草稿填写授权和完成条件。" /><h2>{content.name || '未命名草稿'}</h2><p>{content.objective}</p><h3>原起点</h3><p>{content.starting_point || '无'}</p><h3>原限制</h3><pre>{content.constraints || '无'}</pre><pre>{JSON.stringify(content, null, 2)}</pre><Button onClick={() => {if (profile) void copyAsNew(defaultContent(profile));}}>另建新版草稿</Button></> : <>
      <Steps current={step} size="small" items={['场景与目标', '对象与范围', '模型与预算', '确认并创建'].map((title,index) => ({title,status:index===step?'process' as const:'wait' as const}))} onChange={value => {if (content.scenario === 'web_single') void goTo(value);}} />
      <div className={styles.editor}><fieldset disabled={Boolean(pending) || busy} className={styles.fields}>
      {step === 0 && <><h2>任务类型</h2><div className={styles.scenarios}>{profiles.data?.items.map(p => <button key={p.id} type="button" aria-pressed={p.scenario === content.scenario} onClick={() => switchScenario(p.scenario)}><strong>{p.name}</strong>{!p.can_create && <small>可保存草稿</small>}</button>)}</div>
        {(content.scenario === 'web_single' || content.scenario === 'ctf') && <Field label={content.scenario === 'web_single' ? '测试地址（URL）' : '靶机入口（可选）'}><Input value={content.entry_url ?? ''} onChange={e => {const entry = parseEndpoint(e.target.value); const oldEntry = parseEndpoint(content.entry_url ?? ''); const name = (!content.name || content.name === `${oldEntry?.host} 授权验证`) ? (entry ? `${entry.host} 授权验证` : content.name) : content.name; change(content.scenario === 'web_single' ? {...content, entry_url: e.target.value || null, name, authorization: (!content.authorization || ((content.authorization.includes ?? []).length === 1 && content.authorization.includes?.[0]?.host === oldEntry?.host && !content.authorization.valid_until && !(content.authorization.excludes ?? []).length)) ? (entry ? {schema_version: '1.0', includes: [entry], excludes: [], valid_until: null} : null) : content.authorization} : {...content, entry_url: e.target.value || null, name});}} /></Field>}
        {content.scenario === 'ctf' && <Field label="题目说明"><Input.TextArea rows={4} value={content.challenge} onChange={e => change({...content, challenge: e.target.value})} /></Field>}
        {content.scenario === 'comprehensive' && <><Field label="资产（每行一个）"><Input.TextArea value={content.assets?.join('\n')} onChange={e => change({...content, assets: e.target.value.split('\n')})} /></Field><Field label="接入说明"><Input.TextArea value={content.access_notes} onChange={e => change({...content, access_notes: e.target.value})} /></Field></>}
        {content.scenario === 'exercise' && <><Field label="单位名称"><Input value={content.organization_name} onChange={e => change({...content, organization_name: e.target.value})} /></Field><Field label="已知域名（每行一个）"><Input.TextArea value={content.known_domains?.join('\n')} onChange={e => change({...content, known_domains: e.target.value.split('\n')})} /></Field></>}
        {content.scenario === 'code_audit' && <><Field label="源码仓库 URL"><Input value={content.repository_url ?? ''} disabled={Boolean(content.source_reference_id)} onChange={e => change({...content, repository_url: e.target.value || null})} /></Field><Field label="版本或提交"><Input value={content.revision ?? ''} onChange={e => change({...content, revision: e.target.value || null})} /></Field></>}
        <Collapse ghost items={[{key: 'name', label: `任务名称：${content.name || '自动建议，可修改'}`, children: <Field label="任务名称"><Input maxLength={120} value={content.name} onChange={e => change({...content, name: e.target.value})} /></Field>}]} />
        <div className={styles.heading}><h2>任务目标与完成条件</h2><Button disabled={!profile || !customized} onClick={() => profile && change({...content, objective: profile.objective, completion_criteria: [...profile.completion_criteria], goal_template: {id: profile.id, version: profile.version, digest: profile.digest}})}>恢复默认</Button></div><p>{profile?.name} · V{content.goal_template?.version ?? '自定义'}{customized ? ' · 已自定义' : ''}</p>
        <Field label="任务目标"><Input.TextArea rows={4} maxLength={8000} value={content.objective} onChange={e => change({...content, objective: e.target.value})} /></Field><Field label="完成条件（每行一条）"><Input.TextArea rows={5} value={content.completion_criteria?.join('\n')} onChange={e => change({...content, completion_criteria: e.target.value.split('\n')})} /></Field><Field label="补充线索（可选）"><Input.TextArea rows={3} maxLength={8000} value={content.supplemental_hints} onChange={e => change({...content, supplemental_hints: e.target.value})} /></Field>
      </>}
      {step === 1 && content.scenario === 'web_single' && <AuthorizationEditor content={content} onChange={change} />}
      {step === 2 && <><h2>模型与预算</h2>{models.error && <Alert type="error" title="模型方案读取失败" />}<Field label="模型方案"><Select value={content.model_profile_version_id} placeholder="选择已发布模型方案" options={models.data?.items.map(m => ({value: m.id, label: `${m.name} · V${m.number}`}))} onChange={id => change({...content, model_profile_version_id: id})} /></Field>{content.model_profile_version_id && !models.data?.items.some(m => m.id === content.model_profile_version_id) && <Alert type="warning" title="原模型版本不在当前可用列表中" description="保留原选择，请核对方案状态或选择其他版本。" />}{models.data?.next_cursor && <Button onClick={() => setModelCursor(models.data!.next_cursor)}>下一页模型</Button>}{modelCursor && <Button onClick={() => setModelCursor(null)}>返回首批模型</Button>}<Field label="金额预算（USD）"><Input value={content.budget_usd ?? ''} inputMode="decimal" placeholder="填写正数金额" onChange={e => change({...content, budget_usd: e.target.value || null})} /></Field></>}
      {step === 3 && <><h2>确认任务</h2>{preview ? <><h3>{preview.normalized_content.name}</h3><p>{preview.normalized_content.objective}</p>{preview.normalized_content.schema_version === '2.0' && <ul>{preview.normalized_content.completion_criteria?.map((c, i) => <li key={i}>{c}</li>)}</ul>}{preview.normalized_content.schema_version === '2.0' && preview.normalized_content.scenario === 'web_single' && <AuthorizationSummary authorization={preview.normalized_content.authorization} />}<p>模型：{preview.model_snapshot ? `${preview.model_snapshot.name} · V${preview.model_snapshot.number}` : '不可用'}</p>{preview.model_snapshot?.config.pricing && <p>公司价格：输入 {preview.model_snapshot.config.pricing.input_per_million} / 输出 {preview.model_snapshot.config.pricing.output_per_million} USD / 百万 token · {preview.model_snapshot.config.pricing.source}</p>}<p>金额上限：{preview.normalized_content.budget_usd ?? '未填写'} USD</p>{preview.blockers.map(b => <Alert key={b.code} type="warning" title={b.message} />)}<Checkbox checked={confirmed} onChange={e => setConfirmed(e.target.checked)}>我确认有权授权以上包含、排除、协议端口及期限，仅用于本任务。</Checkbox></> : <Button onClick={() => void goTo(3)}>保存并重新预览</Button>}</>}
      </fieldset></div>
      <footer className={styles.actions}>{content.scenario !== 'web_single' ? <Alert type="info" title="此场景当前支持保存草稿" /> : <>{step > 0 && <Button disabled={busy || Boolean(pending)} onClick={() => void goTo(step - 1)}>上一步</Button>}{step < 3 ? <Button type="primary" loading={busy} disabled={Boolean(pending)} onClick={() => void goTo(step + 1)}>{step === 2 ? '保存并预览' : '下一步'}</Button> : <Button type="primary" loading={busy} disabled={Boolean(pending) || !preview?.can_create || !confirmed} onClick={() => void create()}>创建待启动任务</Button>}</>}</footer>
    </>}
    <Modal open={blocker.state === 'blocked'} title="草稿有未保存修改" okText="保存后离开" cancelText="继续填写" onCancel={() => blocker.state === 'blocked' && blocker.reset()} onOk={async () => {if (await persist()) blocker.state === 'blocked' && blocker.proceed();}}><p>刷新只恢复服务端已保存的内容。</p><Button danger onClick={() => blocker.state === 'blocked' && blocker.proceed()}>放弃未保存修改并离开</Button></Modal>
  </section>;
}

function CreationContent({session, projectId, draftId}: {session: Session; projectId: string; draftId?: string}) {
  const project = useQuery(projectQueryOptions(session, projectId));
  if (!project.data) return <p>正在读取项目…</p>;
  if (!project.data.permissions.includes('task.create')) return <Alert type="error" title="当前身份不能创建任务" />;
  return <CreationEditor key={`${session.user_id}:${session.permissions_version}:${projectId}:${draftId ?? 'new'}`} session={session} projectId={projectId} initialDraftId={draftId} />;
}
export function NewCreationPage() {const {projectId = ''} = useParams(); const navigate = useNavigate(); const [id] = useState(() => crypto.randomUUID()); useEffect(() => {navigate(`/projects/${projectId}/drafts/${id}?new=1`, {replace: true});}, [id, navigate, projectId]); return null;}
export function CreationPage() {const {projectId = '', draftId} = useParams(); return <PrivatePage>{session => <CreationContent session={session} projectId={projectId} draftId={draftId} />}</PrivatePage>;}

function DraftList({session, projectId}: {session: Session; projectId: string}) {
  const [cursor, setCursor] = useState<string | null>(null);
  const drafts = useQuery({queryKey: ['private', 'tasks', session.user_id, session.permissions_version, projectId, 'drafts', cursor], queryFn: ({signal}) => projectRequest(session, projectId, () => getSavedDrafts(projectId, cursor, signal))});
  return <section className={styles.page}><div className={styles.heading}><h1>个人草稿</h1><Link to={`/projects/${projectId}/tasks/new`}>新建任务</Link></div><Link to={`/projects/${projectId}/tasks`}>任务列表</Link>{drafts.error && <Alert type="error" title="草稿读取失败" action={<Button onClick={() => {setCursor(null); void drafts.refetch();}}>重试</Button>} />}{drafts.data?.items.length === 0 && <p>尚无保存的草稿</p>}{drafts.data?.items.map(d => <article className={styles.draft} key={d.id}><Link to={`/projects/${projectId}/drafts/${d.id}`}>{d.content.name || '未命名草稿'}</Link><span>{new Date(d.updated_at).toLocaleString('zh-CN')} · V{d.version}</span>{d.last_created_task_id && <Link to={`/projects/${projectId}/tasks/${d.last_created_task_id}`}>最近创建任务</Link>}</article>)}<div className={styles.actions}><Button disabled={!cursor} onClick={() => setCursor(null)}>返回首批</Button><Button disabled={!drafts.data?.next_cursor} onClick={() => setCursor(drafts.data!.next_cursor)}>下一页</Button></div></section>;
}
export function DraftsPage() {const {projectId = ''} = useParams(); return <PrivatePage>{session => <DraftList key={`${session.user_id}:${session.permissions_version}:${projectId}`} session={session} projectId={projectId} />}</PrivatePage>;}

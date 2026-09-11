import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button } from 'antd';
import { artifactContentPath, getAssessment, getObservations, getVerification, getVerifications, type Observation, type Session, type Task } from '../../api';
import { projectRequest } from '../../queries';
import styles from './execution.module.css';

type Context = {session: Session; projectId: string; task: Task; visible: boolean};
const verdictLabels = {unassessed: '尚未评估', confirmed: '已确认', not_reproduced: '未复现', inconclusive: '不确定'};
const coverageLabels = {pending: '待评估', evaluated: '已评估', blocked: '前提不足', inconclusive: '不确定', not_run: '未执行'};
const outcomeLabels = {not_assessed: '尚未评估', complete: '有限计划已评估', partial: '有限计划部分评估', inconclusive: '评估不确定'};
const terminationLabels = {complete: '完整接收', size_limit: '达到大小上限', timeout: '超时', cancelled: '已取消', network_error: '网络错误'};
const reasons: Record<string,string> = {anonymous_precondition_missing:'匿名身份未满足访问前提',response_precondition_missing:'响应未满足成功对照前提',incomplete_exchange:'响应不完整，证据不足',get_pair_required:'需要两组完整 GET 观察',distinct_origins_required:'需要两个不同 Origin 的对照',reflected_credentials_observed:'两组响应均反射来源并允许凭据',reflection_not_observed:'完整对照未观察到该响应组合',conflicting_evidence:'已有有效证据相互矛盾',no_progress:'证据没有进展，已部分结束',user_cancelled:'用户取消后未执行'};
const reasonText = (value:string) => reasons[value] ?? value;
const relationLabels = {supports: '支持', refutes: '反证', limits: '限制'};

function useRead<T>(context: Context, resource: string, read: (signal: AbortSignal) => Promise<T>) {
  return useQuery({
    queryKey: ['private', 'execution-observation', context.session.user_id, context.session.permissions_version, context.projectId, context.task.id, 'assessment', resource, context.task.version],
    queryFn: ({signal}) => projectRequest(context.session, context.projectId, () => read(signal)),
    enabled: context.visible,
    retry: false,
    refetchInterval: context.visible && !['ready', 'queued', 'completed', 'cancelled'].includes(context.task.state) ? 5000 : false,
    refetchIntervalInBackground: false,
  });
}
function ReadState({pending, error, retry, children}: {pending: boolean; error: Error | null; retry: () => void; children: ReactNode}) {
  return <>{pending && <p role="status">正在读取评估记录…</p>}{error && <Alert type="warning" title="评估记录暂时无法读取" action={<Button onClick={retry}>重新读取</Button>} />}{children}</>;
}
function usePage() {
  const [cursor, setCursor] = useState<string | null>(null);
  const [previous, setPrevious] = useState<(string | null)[]>([]);
  return {cursor, controls: (next: string | null | undefined) => <footer className={styles.pagination}>
    <span>{next ? '还有更多记录未加载' : cursor ? '当前末页，前页记录未在此页显示' : '当前首批记录'}</span>
    <Button disabled={!previous.length} onClick={() => {setCursor(previous.at(-1) ?? null); setPrevious(previous.slice(0, -1));}}>上一页</Button>
    <Button disabled={!next} onClick={() => {setPrevious([...previous, cursor]); setCursor(next ?? null);}}>下一页</Button>
  </footer>};
}
function ObservationMetadata({observation, ...context}: Context & {observation: Observation}) {
  return <article className={styles.record}>
    <h4>HTTP 观察</h4><code>{observation.id}</code>
    <p>{observation.method} <code>{observation.target_url}</code></p>
    <p>响应状态：{observation.response_status ?? '未取得状态码'} · {terminationLabels[observation.termination]} · {observation.complete ? '响应完整' : '响应不完整'}</p>
    <p>正文 {observation.body_bytes} 字节 · 客户端解码后字节</p><code>SHA-256 {observation.body_sha256}</code>
    <p>工具调用：<code>{observation.tool_call_id}</code></p>
    <p>{new Date(observation.started_at).toLocaleString('zh-CN')} → {new Date(observation.finished_at).toLocaleString('zh-CN')}</p>
    <details><summary>请求与响应头</summary><h4>请求头</h4><pre>{JSON.stringify(observation.request_headers, null, 2)}</pre><h4>响应头</h4><pre>{JSON.stringify(observation.response_headers, null, 2)}</pre>{observation.redacted_headers.length > 0 && <p>已剔除：{observation.redacted_headers.join('、')}</p>}</details>
    <a href={artifactContentPath(context.projectId, context.task.id, observation.artifact_id)} download>读取交换元数据</a>
    <a href={artifactContentPath(context.projectId, context.task.id, observation.body_artifact_id)} download>读取响应正文</a>
  </article>;
}
function EvidenceObservation({observationId, ...context}: Context & {observationId: string}) {
  const query = useRead(context, `observation:${observationId}`, signal => getObservations(context.projectId, context.task.id, null, signal, observationId));
  const observation = query.data?.items.find(item => item.id === observationId);
  return <ReadState pending={query.isPending} error={query.error} retry={() => void query.refetch()}>
    {observation ? <ObservationMetadata {...context} observation={observation} /> : query.data && <p>尚未读到引用的观察。观察 ID：<code>{observationId}</code>。请重新核对，不能据此判定观察不存在。</p>}
  </ReadState>;
}
function Verification({verificationId, ...context}: Context & {verificationId: string}) {
  const query = useRead(context, `verification:${verificationId}`, signal => getVerification(context.projectId, context.task.id, verificationId, signal));
  const [selectedResult, setSelectedResult] = useState<string | null>(null);
  const [selectedObservation, setSelectedObservation] = useState<string | null>(null);
  const result = query.data?.results.find(item => item.id === (selectedResult ?? query.data?.verification.latest_result?.id));
  const evidence = query.data?.evidence.filter(item => item.verification_result_id === result?.id);
  return <ReadState pending={query.isPending} error={query.error} retry={() => void query.refetch()}>
    {query.data && <>
      <h3>验证主张</h3><p>{query.data.verification.claim}</p><code>{verificationId}</code>
      <p>资源：<code>{query.data.verification.target_url}</code></p>
      <nav className={styles.tabs} aria-label="验证结果版本">{query.data.results.map(item => <Button key={item.id} aria-pressed={result?.id === item.id} onClick={() => {setSelectedResult(item.id); setSelectedObservation(null);}}>修订 {item.revision} · {verdictLabels[item.verdict]}</Button>)}</nav>
      {!result && <p>尚无验证结果。</p>}
      {result && <>
        <h4>{verdictLabels[result.verdict]} · 修订 {result.revision}</h4><p>{reasonText(result.reason)}</p>
        {result.supersedes_result_id && <p>替代结果：<code>{result.supersedes_result_id}</code>；旧版本保留。</p>}
        {result.limitations.length > 0 && <ul>{result.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>}
        <h4>证据关联</h4>{evidence?.length === 0 && <p>此修订尚无证据关联。</p>}
        {evidence?.map(link => <article key={link.id} className={styles.record}>
          <p>{relationLabels[link.relation]} · 观察 <code>{link.observation_id}</code></p>
          <details><summary>证据定位信息</summary><pre>{JSON.stringify(link.selector, null, 2)}</pre></details>
          <a href={artifactContentPath(context.projectId, context.task.id, link.artifact_id)} download>读取关联证据</a>
          <Button aria-pressed={selectedObservation === link.observation_id} onClick={() => setSelectedObservation(link.observation_id)}>查看观察与两份产物</Button>
        </article>)}
        {selectedObservation && evidence?.some(link => link.observation_id === selectedObservation) && <EvidenceObservation key={selectedObservation} {...context} observationId={selectedObservation} />}
      </>}
    </>}
  </ReadState>;
}
function Verifications({coverageItemId, ...context}: Context & {coverageItemId: string}) {
  const {cursor, controls} = usePage();
  const [selected, setSelected] = useState<string | null>(null);
  const query = useRead(context, `verifications:${coverageItemId}:${cursor ?? 'first'}`, signal => getVerifications(context.projectId, context.task.id, cursor, signal, coverageItemId));
  return <ReadState pending={query.isPending} error={query.error} retry={() => void query.refetch()}>
    <h3>主张与验证记录</h3>
    {query.data?.items.length === 0 && <p>此资源尚无验证记录；不表示未复现。</p>}
    {query.data?.items.map(item => <article key={item.id} className={styles.record}>
      <p>{item.claim}</p><p>{item.latest_result ? `${verdictLabels[item.latest_result.verdict]} · 修订 ${item.latest_result.revision}` : '尚无结果'}</p>
      <Button aria-pressed={item.id === selected} onClick={() => setSelected(item.id)}>查看结果版本与证据链</Button>
    </article>)}
    {controls(query.data?.next_cursor)}
    {selected && <Verification key={selected} {...context} verificationId={selected} />}
  </ReadState>;
}
export function AssessmentPanel(context: Context) {
  const query = useRead(context, 'plan', signal => getAssessment(context.projectId, context.task.id, signal));
  const [coverageItemId, setCoverageItemId] = useState<string | null>(null);
  return <ReadState pending={query.isPending} error={query.error} retry={() => void query.refetch()}>
    {query.data?.state === 'not_assessed' && <p>此任务尚无评估记录。</p>}
    {query.data?.state === 'available' && <>
      <header className={styles.sectionHeading}><h3>{outcomeLabels[query.data.outcome]}</h3><span>计划修订 {query.data.revision}</span></header>
      <p>有限计划：<code>{query.data.plan_id}</code></p>
      <p>资源发现：{{pending: '待发现', complete: '本次有限发现已完成', incomplete: '发现不完整'}[query.data.discovery_state]}</p>
      {(query.data.limitations ?? []).length > 0 && <><h4>评估限制</h4><ul>{(query.data.limitations ?? []).map((item, index) => <li key={index}>{item}</li>)}</ul></>}
      <div className={styles.split}><div>
        <h3>计划资源与覆盖状态</h3>
        {(query.data.items ?? []).map(item => <article key={item.id} className={styles.record}>
          <code>{item.target_url}</code><p>跨源响应配置 · {coverageLabels[item.state]}{item.verdict ? ` · ${verdictLabels[item.verdict]}` : ''}</p>
          {item.reason && <p>{reasonText(item.reason)}</p>}
          <Button aria-pressed={coverageItemId === item.id} onClick={() => setCoverageItemId(item.id)}>查看此资源的主张与验证</Button>
        </article>)}
      </div><aside className={styles.inspector}>{coverageItemId ? <Verifications key={coverageItemId} {...context} coverageItemId={coverageItemId} /> : <p>选择计划资源，查看主张、验证结果版本和 HTTP 证据链。</p>}</aside></div>
    </>}
  </ReadState>;
}

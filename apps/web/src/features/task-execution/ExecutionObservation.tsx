import { useEffect, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button } from 'antd';
import { artifactContentPath, getAgentRuns, getArtifacts, getBlackboard, getTaskResult, getToolCalls, type Session, type Task } from '../../api';
import { projectRequest, queryClient } from '../../queries';
import styles from './execution.module.css';

type Context = {session: Session; projectId: string; task: Task; visible: boolean};
type Tab = 'agents' | 'tools' | 'facts' | 'artifacts' | 'result';
const tabs: {id: Tab; label: string}[] = [
  {id: 'agents', label: 'Agent 执行'},
  {id: 'tools', label: '工具调用'},
  {id: 'facts', label: 'Fact'},
  {id: 'artifacts', label: '证据'},
  {id: 'result', label: '结果'},
];
const phases = {bootstrap: '任务初始化', reason: '证据推理', explore: '探索执行'};
const knownStates: Record<string, string> = {
  pending: '待处理', registered: '已登记', running: '运行中', exited: '已退出',
  unknown: '待核对', succeeded: '成功', failed: '失败', cancelled: '已取消',
  cancelling: '取消核对中', persisted: '已保存', synced: '已同步', available: '可读取',
  not_required: '无需清理', completed: '已完成',
};
const label = (state: string) => knownStates[state] ?? state;
const isActive = (task: Task) => !['ready', 'queued', 'completed', 'cancelled'].includes(task.state);
const queryPrefix = (context: Context) => ['private', 'execution-observation', context.session.user_id, context.session.permissions_version, context.projectId, context.task.id] as const;

function useObservation<T>(context: Context, resource: string, cursor: string | null, read: (signal: AbortSignal) => Promise<T>) {
  return useQuery({
    queryKey: [...queryPrefix(context), resource, cursor, context.task.version],
    queryFn: ({signal}) => projectRequest(context.session, context.projectId, () => read(signal)),
    enabled: context.visible,
    retry: false,
    refetchInterval: context.visible && isActive(context.task) ? 5_000 : false,
    refetchIntervalInBackground: false,
  });
}

function Resource({pending, error, refresh, children}: {pending: boolean; error: Error | null; refresh: () => void; children: ReactNode}) {
  return <>
    {pending && <p role="status">正在读取记录…</p>}
    {error && <Alert showIcon type="warning" title="本次记录同步未完成" description="保留最后读取的记录，可重新核对。" action={<Button onClick={refresh}>重新读取</Button>} />}
    {children}
  </>;
}
function useCursor() {
  const [cursor, setCursor] = useState<string | null>(null);
  const [history, setHistory] = useState<(string | null)[]>([]);
  return {cursor, navigation: (next: string | null | undefined) => <div className={styles.pagination}>
    <Button disabled={!history.length} onClick={() => {setCursor(history.at(-1) ?? null); setHistory(history.slice(0, -1));}}>上一页</Button>
    <Button disabled={!next} onClick={() => {setHistory([...history, cursor]); setCursor(next ?? null);}}>下一页</Button>
  </div>};
}

function Agents(context: Context) {
  const {cursor, navigation} = useCursor();
  const query = useObservation(context, 'agents', cursor, signal => getAgentRuns(context.projectId, context.task.id, cursor, signal));
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    {query.data?.items.length === 0 && <p>尚无 Agent 执行记录。</p>}
    {query.data?.items.map(run => <article key={run.id} className={styles.record}>
      <header><strong>{phases[run.phase]}</strong><span>{label(run.state)}</span></header>
      <code>{run.id}</code><p>结果同步：{label(run.result_state)}</p>
      {run.outcome && <p>{run.outcome}</p>}
      <time dateTime={run.updated_at}>{new Date(run.updated_at).toLocaleString('zh-CN')}</time>
    </article>)}
    {navigation(query.data?.next_cursor)}
  </Resource>;
}
function Tools(context: Context) {
  const {cursor, navigation} = useCursor();
  const query = useObservation(context, 'tools', cursor, signal => getToolCalls(context.projectId, context.task.id, cursor, signal));
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    {query.data?.items.length === 0 && <p>尚无实际工具调用。</p>}
    {query.data?.items.map(call => <article key={call.id} className={styles.record}>
      <header><strong>{call.tool}</strong><span>{label(call.state)}</span></header>
      <code>{call.id}</code><p>AgentRun：<code>{call.agent_run_id}</code></p>
      {call.cancel_requested && <p>已请求停止，实际状态以调用回执为准。</p>}
      {call.result ? <pre aria-label="工具结果摘录">{JSON.stringify(call.result, null, 2).slice(0, 4000)}</pre> : <p>尚未取得工具结果。</p>}
      <time dateTime={call.updated_at}>{new Date(call.updated_at).toLocaleString('zh-CN')}</time>
    </article>)}
    {navigation(query.data?.next_cursor)}
  </Resource>;
}
function Facts(context: Context) {
  const query = useObservation(context, 'facts', null, signal => getBlackboard(context.projectId, context.task.id, signal));
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    {query.data?.state === 'pending' && <p>黑板尚未同步。</p>}
    {query.data?.state === 'available' && <>
      {query.data.captured_at && <p>读取时间：{new Date(query.data.captured_at).toLocaleString('zh-CN')}</p>}
      {query.data.graph?.facts.length === 0 && <p>尚无原生 Fact；不表示已完成测试。</p>}
      {query.data.graph?.facts.map(fact => <article key={fact.id} className={styles.record}><code>{fact.id}</code><p>{fact.description}</p></article>)}
    </>}
  </Resource>;
}
function Artifacts(context: Context) {
  const {cursor, navigation} = useCursor();
  const query = useObservation(context, 'artifacts', cursor, signal => getArtifacts(context.projectId, context.task.id, cursor, signal));
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    {query.data?.items.length === 0 && <p>尚无登记证据。</p>}
    {query.data?.items.map(artifact => <article key={artifact.id} className={styles.record}>
      <header><strong>{artifact.name}</strong><span>{label(artifact.state)}</span></header>
      <p>{artifact.kind} · {artifact.mime} · {artifact.size} 字节</p><code>SHA-256 {artifact.sha256}</code>
      {artifact.state === 'available' && <a href={artifactContentPath(context.projectId, context.task.id, artifact.id)} download={artifact.name}>读取证据</a>}
    </article>)}
    {navigation(query.data?.next_cursor)}
  </Resource>;
}
function Result(context: Context) {
  const query = useObservation(context, 'result', null, signal => getTaskResult(context.projectId, context.task.id, signal));
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    {query.data && <>
      <h3>目标状态：{{unknown: '尚未判定', met: '已达成', not_met: '未达成'}[query.data.goal_status]}</h3>
      {query.data.state === 'pending' && <p>结果仍待同步。</p>}
      <p className={styles.summary}>{query.data.summary || '尚无结果摘要。'}</p>
      {query.data.limitations.length > 0 && <><h3>未测与限制</h3><ul>{query.data.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></>}
      <p>模型费用：{query.data.model_spend === null ? '尚未报告' : `${query.data.model_spend} USD`}</p>
      <p>费用状态：{query.data.cost_state === 'reported' ? '已报告，尚非最终结算' : label(query.data.cost_state)}</p>
      <p>资源清理：{label(context.task.cleanup_state)}</p>
      <p>结束原因：{context.task.stop_reason ?? '尚未结束'}</p>
      {query.data.artifact_ids.length > 0 && <><h3>结果证据</h3><ul>{query.data.artifact_ids.map(id => <li key={id}><a href={artifactContentPath(context.projectId, context.task.id, id)} download>读取证据 {id}</a></li>)}</ul></>}
    </>}
  </Resource>;
}

export function ExecutionObservation({session, projectId, task}: Omit<Context, 'visible'>) {
  const [tab, setTab] = useState<Tab>('agents');
  const [visible, setVisible] = useState(() => !document.hidden);
  const context = {session, projectId, task, visible};
  useEffect(() => {
    const visibilityChanged = () => {
      setVisible(!document.hidden);
      if (document.hidden) void queryClient.cancelQueries({queryKey: ['private', 'execution-observation', session.user_id, session.permissions_version, projectId, task.id]});
    };
    document.addEventListener('visibilitychange', visibilityChanged);
    return () => document.removeEventListener('visibilitychange', visibilityChanged);
  }, [session.user_id, session.permissions_version, projectId, task.id]);
  return <section className={styles.panel} aria-labelledby="execution-observation-title">
    <header className={styles.heading}><h2 id="execution-observation-title">执行与结果</h2><span>{isActive(task) ? '运行中每 5 秒核对' : '当前记录'}</span></header>
    <nav className={styles.tabs} aria-label="执行记录类型">{tabs.map(item => <Button key={item.id} type={item.id === tab ? 'primary' : 'default'} aria-pressed={item.id === tab} onClick={() => setTab(item.id)}>{item.label}</Button>)}</nav>
    <div className={styles.body}>
      {tab === 'agents' && <Agents {...context} />}
      {tab === 'tools' && <Tools {...context} />}
      {tab === 'facts' && <Facts {...context} />}
      {tab === 'artifacts' && <Artifacts {...context} />}
      {tab === 'result' && <Result {...context} />}
    </div>
  </section>;
}

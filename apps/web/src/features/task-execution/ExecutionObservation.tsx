import { AssessmentPanel } from './AssessmentPanel';
import { TopologyContainer } from '../topology/TopologyContainer';
import { useEffect, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button } from 'antd';
import { artifactContentPath, getAgentRuns, getArtifacts, getBlackboard, getTaskResult, getToolCalls, type Session, type Task } from '../../api';
import { projectRequest, queryClient } from '../../queries';
import styles from './execution.module.css';

type Context = {session: Session; projectId: string; task: Task; visible: boolean};
type ToolCall = Awaited<ReturnType<typeof getToolCalls>>['items'][number];
type Selection = {kind: 'fact' | 'intent'; id: string} | null;
type MainView = 'topology' | 'blackboard' | 'timeline' | 'workspace';
type WorkspaceView = 'agents' | 'tools' | 'artifacts' | 'result' | 'assessment';
const phases = {bootstrap: '任务初始化', reason: '证据推理', explore: '探索执行'};
const knownStates: Record<string, string> = {
  pending: '待处理', registered: '已登记', running: '运行中', exited: '已退出',
  unknown: '待核对', succeeded: '成功', failed: '失败', cancelled: '已取消',
  cancelling: '取消核对中', persisted: '已保存', synced: '已同步', available: '可读取',
  not_required: '无需清理', completed: '已完成', reviewed: '已评审', needs_followup: '待补充证据',
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
  return {cursor, navigation: (next: string | null | undefined) => <footer className={styles.pagination}>
    <span>{next ? '还有更多记录未加载' : cursor ? '当前为末页；前页记录不在此页显示' : '当前已加载首批记录'}</span>
    <Button disabled={!history.length} onClick={() => {setCursor(history.at(-1) ?? null); setHistory(history.slice(0, -1));}}>上一页</Button>
    <Button disabled={!next} onClick={() => {setHistory([...history, cursor]); setCursor(next ?? null);}}>下一页</Button>
  </footer>};
}
function Agents({intentId, onSelectRun, ...context}: Context & {intentId?: string; onSelectRun: (id: string) => void}) {
  const {cursor, navigation} = useCursor();
  const query = useObservation(context, `agents:${intentId ?? 'all'}`, cursor, signal => getAgentRuns(context.projectId, context.task.id, cursor, signal, intentId));
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    {query.data?.items.length === 0 && <p>当前筛选下尚无 Agent 执行记录。</p>}
    {query.data?.items.map(run => <article key={run.id} className={styles.record}>
      <header><strong>{phases[run.phase]}</strong><span>{label(run.state)}</span></header>
      <code>{run.id}</code><p>结果同步：{label(run.result_state)}</p>
      {run.outcome && <p>{label(run.outcome)}</p>}
      <time dateTime={run.updated_at}>{new Date(run.updated_at).toLocaleString('zh-CN')}</time>
      <Button onClick={() => onSelectRun(run.id)}>查看此次执行的工具与文件</Button>
    </article>)}
    {navigation(query.data?.next_cursor)}
  </Resource>;
}
function Artifacts({toolCallId, ...context}: Context & {toolCallId?: string}) {
  const {cursor, navigation} = useCursor();
  const query = useObservation(context, `artifacts:${toolCallId ?? 'all'}`, cursor, signal => getArtifacts(context.projectId, context.task.id, cursor, signal, toolCallId));
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    {query.data?.items.length === 0 && <p>当前筛选下尚无登记证据。</p>}
    {query.data?.items.map(artifact => <article key={artifact.id} className={styles.record}>
      <header><strong>{artifact.name}</strong><span>{label(artifact.state)}</span></header>
      <p>{artifact.kind} · {artifact.mime} · {artifact.size} 字节</p><code>SHA-256 {artifact.sha256}</code>
      {artifact.tool_call_id && <p>来源工具调用：<code>{artifact.tool_call_id}</code></p>}
      {artifact.state === 'available' && <a href={artifactContentPath(context.projectId, context.task.id, artifact.id)} download={artifact.name}>读取证据</a>}
    </article>)}
    {navigation(query.data?.next_cursor)}
  </Resource>;
}
function ToolDetails({call, ...context}: Context & {call: ToolCall}) {
  const path = typeof call.args.path === 'string' ? call.args.path : typeof call.result?.path === 'string' ? call.result.path : null;
  return <aside className={styles.inspector} aria-label="工具调用详情">
    <h3>{call.tool}</h3><code>{call.id}</code><p>执行状态：{label(call.state)}</p>
    <p>AgentRun：<code>{call.agent_run_id}</code></p>
    {path && <p>工作路径：<code>{path}</code></p>}
    {call.cancel_requested && <p>已请求停止，实际状态以调用回执为准。</p>}
    {call.result ? <><h4>结果摘录</h4><pre>{JSON.stringify(call.result, null, 2).slice(0, 4000)}</pre>{JSON.stringify(call.result).length > 4000 && <p>当前仅显示结果摘录。</p>}</> : <p>尚未取得工具结果。</p>}
    <h4>此次工具调用的证据</h4><Artifacts key={call.id} {...context} toolCallId={call.id} />
  </aside>;
}
function Tools({agentRunId, ...context}: Context & {agentRunId?: string}) {
  const {cursor, navigation} = useCursor();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const query = useObservation(context, `tools:${agentRunId ?? 'all'}`, cursor, signal => getToolCalls(context.projectId, context.task.id, cursor, signal, agentRunId));
  const selected = query.data?.items.find(call => call.id === selectedId);
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    <div className={styles.split}><div>
      {query.data?.items.length === 0 && <p>当前筛选下尚无实际工具调用。</p>}
      {query.data?.items.map(call => <article key={call.id} className={styles.record}>
        <header><strong>{call.tool}</strong><span>{label(call.state)}</span></header>
        <code>{call.id}</code>
        {typeof call.args.path === 'string' && <p>工作路径：<code>{call.args.path}</code></p>}
        <time dateTime={call.updated_at}>{new Date(call.updated_at).toLocaleString('zh-CN')}</time>
        <Button aria-pressed={call.id === selectedId} onClick={() => setSelectedId(call.id)}>查看结果与关联证据</Button>
      </article>)}
      {navigation(query.data?.next_cursor)}
    </div>{selected ? <ToolDetails {...context} call={selected} /> : <aside className={styles.inspector}><p>选择工具调用，查看真实结果、工作路径与登记证据。</p></aside>}</div>
  </Resource>;
}
function Blackboard({selection, onSelect, onSelectRun, ...context}: Context & {selection: Selection; onSelect: (value: Selection) => void; onSelectRun: (id: string) => void}) {
  const query = useObservation(context, 'blackboard', null, signal => getBlackboard(context.projectId, context.task.id, signal));
  const graph = query.data?.graph;
  const fact = selection?.kind === 'fact' ? graph?.facts.find(item => item.id === selection.id) : undefined;
  const intent = selection?.kind === 'intent' ? graph?.intents.find(item => item.id === selection.id) : undefined;
  const related = fact ? graph?.intents.filter(item => item.from.includes(fact.id) || item.to === fact.id) : graph?.intents;
  const factButton = (id: string) => <button type="button" className={styles.node} key={id} aria-pressed={selection?.kind === 'fact' && selection.id === id} onClick={() => onSelect({kind: 'fact', id})}><small>Fact</small><span>{graph?.facts.find(item => item.id === id)?.description ?? id}</span></button>;
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    {query.data?.state === 'pending' && <p>黑板尚未同步。</p>}
    {graph && <div className={styles.split}>
      <div>
        <header className={styles.sectionHeading}><h3>{fact ? '直接关联的探索' : '当前黑板关系'}</h3>{selection && <Button onClick={() => onSelect(null)}>清除节点选择</Button>}</header>
        {query.data?.captured_at && <p className={styles.muted}>快照时间：{new Date(query.data.captured_at).toLocaleString('zh-CN')}</p>}
        <div className={styles.factStrip}>{graph.facts.map(item => factButton(item.id))}</div>
        {related?.length === 0 && <p>当前快照中没有此范围的 Intent 关系。</p>}
        {related?.map(item => <article key={item.id} className={styles.relation} aria-label="Fact 到 Intent 到 Fact 关系">
          <div className={styles.inputs}>{item.from.length ? item.from.map(id => factButton(id)) : <span className={styles.muted}>无前置 Fact</span>}</div>
          <span aria-hidden="true">→</span>
          <button className={`${styles.node} ${styles.intent}`} type="button" aria-pressed={selection?.kind === 'intent' && selection.id === item.id} onClick={() => onSelect({kind: 'intent', id: item.id})}><small>Intent · {item.concluded_at ? '已结束' : item.worker ? '已认领' : '待认领'}</small><span>{item.description}</span></button>
          <span aria-hidden="true">→</span>
          <div>{item.to ? factButton(item.to) : <span className={styles.muted}>尚无结果 Fact</span>}</div>
        </article>)}
      </div>
      <aside className={styles.inspector} aria-label="黑板节点详情">
        {fact ? <><h3>Fact</h3><code>{fact.id}</code><p>{fact.description}</p><p>左侧显示与此 Fact 直接关联的探索。</p></> : intent ? <>
          <h3>Intent</h3><code>{intent.id}</code><p>{intent.description}</p>
          <p>创建者：{intent.creator}</p><p>认领者：{intent.worker ?? '尚未认领'}</p><p>创建时间：{new Date(intent.created_at).toLocaleString('zh-CN')}</p>
          {intent.concluded_at && <p>结束时间：{new Date(intent.concluded_at).toLocaleString('zh-CN')}</p>}
          <h4>实际 AgentRun</h4><Agents key={intent.id} {...context} intentId={intent.id} onSelectRun={onSelectRun} />
        </> : <p>选择 Fact 查看直接关系；选择 Intent 查看实际执行。</p>}
        {graph.hints.length > 0 && <details><summary>补充线索</summary>{graph.hints.map(hint => <article key={hint.id} className={styles.record}><p>{hint.content}</p><small>{hint.creator} · {new Date(hint.created_at).toLocaleString('zh-CN')}</small></article>)}</details>}
      </aside>
    </div>}
  </Resource>;
}
function Result({onAssessment, ...context}: Context & {onAssessment: () => void}) {
  const query = useObservation(context, 'result', null, signal => getTaskResult(context.projectId, context.task.id, signal));
  return <Resource pending={query.isPending} error={query.error} refresh={() => void query.refetch()}>
    {query.data && <>
      {query.data.assessment && <Button onClick={onAssessment}>查看有限计划评估 · 修订 {query.data.assessment.revision}</Button>}
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

export function ExecutionObservation({session, projectId, task, timeline}: Omit<Context, 'visible'> & {timeline: ReactNode}) {
  const [view, setView] = useState<MainView>('topology');
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>('agents');
  const [selection, setSelection] = useState<Selection>(null);
  const [agentRunId, setAgentRunId] = useState<string | undefined>();
  const [visible, setVisible] = useState(() => !document.hidden);
  const context = {session, projectId, task, visible};
  const selectRun = (id: string) => {setAgentRunId(id); setWorkspaceView('tools'); setView('workspace');};
  useEffect(() => {
    const visibilityChanged = () => {
      setVisible(!document.hidden);
      if (document.hidden) void queryClient.cancelQueries({queryKey: ['private', 'execution-observation', session.user_id, session.permissions_version, projectId, task.id]});
    };
    document.addEventListener('visibilitychange', visibilityChanged);
    return () => document.removeEventListener('visibilitychange', visibilityChanged);
  }, [session.user_id, session.permissions_version, projectId, task.id]);
  return <section className={styles.panel} aria-label="任务工作台">
    <header className={styles.heading}>
      <nav className={styles.tabs} aria-label="任务主视图">{([{id: 'topology', label: '拓扑'}, {id: 'blackboard', label: '黑板'}, {id: 'timeline', label: '时间线'}, {id: 'workspace', label: '工作区'}] as const).map(item => <Button key={item.id} type={item.id === view ? 'primary' : 'default'} aria-pressed={item.id === view} onClick={() => setView(item.id)}>{item.label}</Button>)}</nav>
      <span>{isActive(task) ? '运行中每 5 秒核对' : '当前记录'}</span>
    </header>
    <div className={styles.body}>
      {view === 'topology' && <TopologyContainer taskId={task.id} mode="live" />}
      {view === 'blackboard' && <Blackboard {...context} selection={selection} onSelect={setSelection} onSelectRun={selectRun} />}
      {view === 'timeline' && <><p className={styles.muted}>已读取的真实任务事件；历史查看不会重新执行。</p>{timeline}</>}
      {view === 'workspace' && <>
        <nav className={styles.tabs} aria-label="工作区记录">{([{id: 'agents', label: '执行记录'}, {id: 'tools', label: '工具与文件'}, {id: 'artifacts', label: '登记证据'}, {id: 'result', label: '结果'}, {id: 'assessment', label: '评估'}] as const).map(item => <Button key={item.id} type={item.id === workspaceView ? 'primary' : 'default'} aria-pressed={item.id === workspaceView} onClick={() => setWorkspaceView(item.id)}>{item.label}</Button>)}</nav>
        {agentRunId && workspaceView === 'tools' && <div className={styles.filter}><span>当前 AgentRun：<code>{agentRunId}</code></span><Button onClick={() => setAgentRunId(undefined)}>查看全部工具调用</Button></div>}
        {workspaceView === 'agents' && <Agents {...context} onSelectRun={selectRun} />}
        {workspaceView === 'tools' && <Tools key={agentRunId ?? 'all'} {...context} agentRunId={agentRunId} />}
        {workspaceView === 'artifacts' && <Artifacts {...context} />}
        {workspaceView === 'result' && <Result {...context} onAssessment={() => setWorkspaceView('assessment')} />}
        {workspaceView === 'assessment' && <AssessmentPanel {...context} />}
      </>}
    </div>
  </section>;
}

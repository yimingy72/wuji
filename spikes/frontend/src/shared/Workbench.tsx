import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Input, Segmented, Tabs } from 'antd';
import { AimOutlined, ArrowRightOutlined, CheckOutlined, ClockCircleOutlined, CodeOutlined, DeploymentUnitOutlined, FileTextOutlined, PlusOutlined, SearchOutlined, StopOutlined } from '@ant-design/icons';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { artifactPath, cancelDemoTask, hasDemoEvidence, rawFixture, taskPath, taskQuery, type Task } from './model';
import { Status } from './ui';
import styles from '../prototype.module.css';

export function EvidenceCode() {
  return <pre className={styles.codePreview}><code>{rawFixture.artifact_preview.text.split('\n').map((line, index) => <span className={styles.codeLine} key={index}><span className={styles.lineNumber} aria-hidden="true">{index + 1}</span><span className={line.startsWith('HTTP/') ? styles.httpStatus : undefined}>{line || ' '}</span></span>)}</code></pre>;
}

export function ScopeDetails() {
  const scope = rawFixture.scope;
  return <dl className={styles.propertyList}>
    <dt>Scope</dt><dd><span className={styles.scopeBadge}>v{scope.binding.version}</span></dd>
    <dt>Origin</dt><dd className={styles.mono}>{scope.origins[0]}</dd>
    <dt>允许路径</dt><dd className={styles.mono}>{scope.allowed_path_prefixes.join(', ')}</dd>
    <dt>排除路径</dt><dd className={styles.mono}>{scope.excluded_path_prefixes.map(path => <div key={path}>{path}</div>)}</dd>
    <dt>方法</dt><dd className={styles.mono}>{scope.allowed_methods.join(' / ')}</dd>
    <dt>请求上限</dt><dd className={styles.mono}>{scope.limits.max_total_requests}</dd>
    <dt>速率 / 并发</dt><dd className={styles.mono}>{scope.limits.requests_per_second} req/s · {scope.limits.max_concurrent_requests}</dd>
    <dt>授权截止</dt><dd className={styles.mono}>09-09 20:00 <span className={styles.muted}>UTC+8</span></dd>
  </dl>;
}

function ExecutionLog({ task }: { task: Task }) {
  const evidence = hasDemoEvidence();
  const rows = [
    { time: '10:57:00', title: '任务已接受', source: 'PLATFORM', detail: `task/${task.id.slice(-6)} · scope v${task.scope.version}`, done: true },
    ...(evidence ? [{ time: '10:57:08', title: '执行环境就绪', source: 'RUNTIME', detail: 'HTTP Adapter · ready', done: true }] : []),
    { time: '11:00:00', title: evidence ? '观察记录已保存' : task.state === 'queued' ? '等待执行端调度' : '未产生观察记录', source: evidence ? 'ARTIFACT' : 'SCHEDULER', detail: evidence ? rawFixture.artifact.name : 'pending dispatch', done: evidence },
    ...(task.state === 'reconciling' ? [{ time: '11:00:12', title: '调用状态待核对', source: 'ROUTER', detail: `unknown_calls=${task.execution.unknown_calls}`, done: false }] : []),
    ...(['cancelling', 'cancelled'].includes(task.state) ? [{ time: '11:00:12', title: task.state === 'cancelled' ? '执行停止已确认' : '取消请求已接受', source: 'CONTROL', detail: task.state === 'cancelled' ? 'active_calls=0 · egress=revoked' : 'new_grants=blocked · awaiting receipt', done: task.state === 'cancelled' }] : []),
  ];
  return <><div className={styles.logColumnHead}><span>时间</span><span>事件</span><span>来源</span></div><ol className={styles.executionLog}>{rows.map((row, index) => <li key={`${row.source}-${index}`}>
    <time>{row.time}</time><div className={styles.logEvent}><span className={row.done ? styles.logDone : styles.logPending}>{row.done ? <CheckOutlined aria-hidden="true" /> : <ClockCircleOutlined aria-hidden="true" />}</span><div><strong>{row.title}</strong><code>{row.detail}</code></div></div><span className={styles.logSource}>{row.source}</span>
  </li>)}</ol></>;
}

function ExecutionNodes({ task }: { task: Task }) {
  const stopped = ['cancelled', 'completed', 'failed'].includes(task.state);
  return <div className={styles.executionNodes} aria-label="执行组件">
    <div><DeploymentUnitOutlined aria-hidden="true" /><strong>Runtime</strong><small>{task.cleanup_state === 'cleaned' ? '已清理' : task.cleanup_state === 'cleanup_pending' ? '待清理' : hasDemoEvidence() ? '就绪' : '待创建'}</small></div>
    <ArrowRightOutlined aria-hidden="true" className={styles.nodeArrow} />
    <div data-active={!stopped && task.state !== 'queued'}><CodeOutlined aria-hidden="true" /><strong>HTTP Adapter</strong><small>{stopped ? '已停止' : task.state === 'cancelling' ? '停止中' : task.execution.unknown_calls ? '待核对' : task.execution.active_calls ? `${task.execution.active_calls} 个活动调用` : '待调度'}</small></div>
    <ArrowRightOutlined aria-hidden="true" className={styles.nodeArrow} />
    <div><FileTextOutlined aria-hidden="true" /><strong>Evidence</strong><small>{hasDemoEvidence() ? '1 份证据' : '等待产物'}</small></div>
  </div>;
}

function EvidenceInspector() {
  const available = hasDemoEvidence();
  return <aside className={styles.inspector} aria-label="证据检查器">
    <div className={styles.panelHeading}><h2><FileTextOutlined aria-hidden="true" /> 证据检查器</h2><span className={styles.count}>{available ? '01' : '00'}</span></div>
    {available ? <>
      <div className={styles.artifactHeading}><code>public-index.response.txt</code><span className={styles.redacted}>已脱敏</span></div>
      <Tabs size="small" className={styles.inspectorTabs} items={[
        { key: 'response', label: '响应正文', children: <EvidenceCode /> },
        { key: 'metadata', label: '元数据', children: <dl className={styles.propertyList}><dt>类型</dt><dd className={styles.mono}>{rawFixture.artifact.media_type}</dd><dt>大小</dt><dd>{rawFixture.artifact.size_bytes} B</dd><dt>采集时间</dt><dd>09-09 11:00</dd><dt>SHA-256</dt><dd className={styles.mono}>{rawFixture.artifact.sha256}</dd></dl> },
      ]} />
      <Link className={styles.fullEvidenceLink} to={artifactPath}>查看完整证据 <ArrowRightOutlined aria-hidden="true" /></Link>
    </> : <div className={styles.panelEmpty}><FileTextOutlined aria-hidden="true" /><span>尚未产生证据</span></div>}
  </aside>;
}

export function Workbench() {
  const navigate = useNavigate();
  const { data } = useQuery(taskQuery);
  const [search, setSearch] = useSearchParams();
  const [filter, setFilter] = useState('');
  const [category, setCategory] = useState('all');
  const [submitting, setSubmitting] = useState(false);
  if (!data) return <p role="status">正在加载任务…</p>;
  const task = structuredClone(data);
  const scene = search.get('scene');
  if (scene === 'unknown') { task.state = 'reconciling'; task.allowed_actions = ['cancel']; task.execution = { active_calls: 0, unknown_calls: 1, egress_state: 'unknown' }; }
  if (scene === 'cleanup') { task.state = 'cancelled'; task.cleanup_state = 'cleanup_pending'; task.allowed_actions = []; task.execution = { active_calls: 0, unknown_calls: 0, egress_state: 'revoked' }; }
  const terminal = ['cancelled', 'completed', 'failed'].includes(task.state);
  const visible = scene !== 'empty' && task.name.includes(filter) && (category === 'all' || (category === 'ended' ? terminal : !terminal));
  async function cancel() {
    if (submitting) return;
    setSubmitting(true);
    await cancelDemoTask(task);
    if (scene) setSearch({});
    setSubmitting(false);
  }
  return <div className={styles.workbenchPage}>
    <div className={styles.workspaceTitle}><div><h1>任务工作台</h1><span className={styles.workspaceKind}>HTTP / 受控工具</span></div><Button type="primary" icon={<PlusOutlined aria-hidden="true" />} onClick={() => navigate('/tasks/new')}>创建任务</Button></div>
    <div className={styles.workbenchGrid}>
      <aside className={styles.queue} aria-label="任务队列">
        <div className={styles.panelHeading}><h2>任务队列</h2><span className={styles.count}>{scene === 'empty' ? '00' : '01'}</span></div>
        <div className={styles.queueFilter}><Input aria-label="任务名称" prefix={<SearchOutlined aria-hidden="true" />} value={filter} onChange={e => setFilter(e.target.value)} placeholder="搜索任务" allowClear /><Segmented block size="small" options={[{ label: '全部', value: 'all' }, { label: '活动', value: 'active' }, { label: '已结束', value: 'ended' }]} value={category} onChange={value => setCategory(String(value))} /></div>
        <div className={styles.queueItems}>{visible ? <Link className={styles.taskItem} to={taskPath} aria-current="page"><div className={styles.taskItemTop}><span className={styles.taskId}>TASK-{task.id.slice(-6)}</span><Status state={task.state} /></div><strong>{task.name}</strong><span className={styles.taskTarget}>training.example</span><div className={styles.taskItemBottom}><span>HTTP</span><span>Scope v{task.scope.version}</span></div></Link> : <div className={styles.queueEmpty}>没有匹配任务{filter && <Button type="link" onClick={() => setFilter('')}>清除筛选</Button>}</div>}</div>
        <div className={styles.queueScope}><h3><AimOutlined aria-hidden="true" /> 当前范围 <span>v{task.scope.version}</span></h3><code>training.example</code><span className={styles.scopePath}>/public/</span><dl><dt>请求限额</dt><dd>200</dd><dt>速率</dt><dd>2 req/s</dd><dt>并发</dt><dd>2</dd></dl></div>
      </aside>
      {visible ? <>
        <section className={styles.executionPanel} aria-label="任务执行">
          <div className={styles.taskHeading}><div><div className={styles.taskEyeline}><code>TASK-{task.id.slice(-6)}</code><Status state={task.state} /></div><h2>{task.name}</h2><code className={styles.taskUrl}>{task.target_url}</code></div>{task.allowed_actions.includes('cancel') && <Button danger size="small" icon={<StopOutlined aria-hidden="true" />} loading={submitting} onClick={() => void cancel()}>取消任务</Button>}</div>
          <div className={styles.taskStats}><span>活动调用 <strong>{task.execution.active_calls}</strong></span><span>待核对 <strong>{task.execution.unknown_calls}</strong></span><span>资源清理 <strong>{task.cleanup_state === 'cleaned' ? '已清理' : task.cleanup_state === 'cleanup_pending' ? '清理待完成' : '待完成'}</strong></span></div>
          {task.state === 'cancelling' && <div className={styles.callout} role="status">取消请求已接受，等待停止回执</div>}
          {task.state === 'reconciling' && <div className={styles.callout} role="status">有 1 个调用结果不明</div>}
          {task.cleanup_state === 'cleanup_pending' && <div className={styles.callout} role="status">执行已停止，资源清理仍待完成</div>}
          <ExecutionNodes task={task} />
          <Tabs className={styles.executionTabs} items={[{ key: 'log', label: '执行记录', children: <ExecutionLog task={task} /> }, { key: 'scope', label: '范围与限额', children: <ScopeDetails /> }]} />
          <div className={styles.executionFooter}><span><span className={styles.stateDot} />{task.state === 'running' ? '执行中' : task.state === 'queued' ? '等待调度' : '状态已同步'}</span><code>更新于 11:00:00 <span>/</span> UTC+8</code></div>
        </section>
        <EvidenceInspector />
      </> : <div className={styles.noSelection}><DeploymentUnitOutlined aria-hidden="true" /><h2>没有匹配任务</h2><Button onClick={() => { setCategory('all'); setFilter(''); }}>重置筛选</Button></div>}
    </div>
  </div>;
}

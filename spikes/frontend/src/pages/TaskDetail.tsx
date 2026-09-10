import { useMemo, useState } from 'react';
import { Alert, Button, Input, Modal, Segmented, Tabs, Tag } from 'antd';
import { ArrowLeftOutlined, ArrowRightOutlined, CheckCircleOutlined, ClockCircleOutlined, CloseCircleOutlined, FileSearchOutlined, PauseOutlined, PlayCircleOutlined, QuestionCircleOutlined, ReloadOutlined, SafetyCertificateOutlined, StopOutlined } from '@ant-design/icons';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { evidence, getTask, stateLabel, type DemoEvidence, type DemoMode, type DemoTaskState } from '../shared/model';
import { Status } from '../shared/ui';
import styles from '../prototype.module.css';

const validStates: DemoTaskState[] = ['ready', 'queued', 'running', 'pausing', 'paused', 'cancelling', 'cancelled', 'completed'];

function EvidenceInspector({ selected, onOpen }: { selected?: DemoEvidence; onOpen: () => void }) {
  return <aside className={styles.inspector} aria-label="证据检查器">
    <div className={styles.panelHeading}><h2><FileSearchOutlined /> 证据检查器</h2><span className={styles.count}>{selected ? '01' : '00'}</span></div>
    {selected ? <>
      <div className={styles.artifactHeading}><div><code>{selected.id}</code><strong>{selected.title}</strong></div><Tag color="success">合成证据</Tag></div>
      <Tabs size="small" className={styles.inspectorTabs} items={[
        { key: 'content', label: '内容', children: <pre className={styles.codePreview}><code>{selected.body}</code></pre> },
        { key: 'trace', label: '来源', children: <dl className={styles.propertyList}><dt>采集来源</dt><dd>{selected.source}</dd><dt>记录时间</dt><dd className={styles.mono}>{selected.capturedAt}</dd><dt>数据边界</dt><dd>{selected.note}</dd><dt>目标</dt><dd className={styles.mono}>app.example.test</dd></dl> },
      ]} />
      <Button type="link" className={styles.fullEvidenceLink} onClick={onOpen}>查看完整证据 <ArrowRightOutlined /></Button>
    </> : <div className={styles.panelEmpty}><FileSearchOutlined /><strong>选择一条执行记录</strong><span>证据会在这里联动显示</span></div>}
  </aside>;
}

export function Component() {
  const navigate = useNavigate();
  const { taskId = 'DEMO-HTTP-1042' } = useParams();
  const [search, setSearch] = useSearchParams();
  const mode: DemoMode = search.get('mode') === 'agent' ? 'agent' : 'http';
  const rawState = search.get('state');
  const state: DemoTaskState = validStates.includes(rawState as DemoTaskState) ? rawState as DemoTaskState : 'ready';
  const task = getTask(mode, taskId);
  const environmentBusy = search.get('environment') === 'busy';
  const cleanupPending = search.get('cleanup') === 'pending';
  const [selectedKey, setSelectedKey] = useState<string | undefined>(state === 'running' || state === 'completed' ? 'response' : undefined);
  const [contextTab, setContextTab] = useState('plan');
  const [mainTab, setMainTab] = useState(state === 'completed' || state === 'cancelled' ? 'result' : 'timeline');
  const [cancelOpen, setCancelOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [questionStatus, setQuestionStatus] = useState<'open' | 'answered' | 'skipped'>('open');
  const [hints, setHints] = useState<string[]>(['只读验证身份边界', '结论必须关联原始依据']);
  const [hint, setHint] = useState('');
  const hasExecution = search.get('executed') === '1' || ['running', 'pausing', 'paused', 'completed'].includes(state);
  const selectedEvidence = hasExecution && selectedKey ? evidence[selectedKey] : undefined;
  const completedItems = hasExecution ? (mode === 'http' ? 1 : questionStatus === 'answered' ? 3 : 2) : 0;

  function transition(nextState: DemoTaskState, options?: { cleanup?: 'pending' | 'cleaned'; environment?: 'ready' }) {
    setSearch(previous => {
      const next = new URLSearchParams(previous);
      next.set('mode', mode); next.set('state', nextState);
      if (hasExecution || nextState === 'running' || nextState === 'completed') next.set('executed', '1');
      if (options?.cleanup) next.set('cleanup', options.cleanup);
      if (options?.environment === 'ready') next.delete('environment');
      return next;
    });
    if (nextState === 'running' && !selectedKey) setSelectedKey('response');
    if (nextState === 'completed' || nextState === 'cancelled') setMainTab('result');
  }

  function openEvidence(key: string) {
    setSelectedKey(key);
    setMainTab('timeline');
  }

  const timeline = useMemo(() => [
    { time: '14:32:10', title: '任务配置已冻结', detail: 'Scope v4 · 预算快照已保存', done: true },
    ...((state !== 'ready' && state !== 'cancelled') || hasExecution ? [{ time: '14:33:02', title: '启动请求已接受', detail: '排队等待受管环境', done: true }] : []),
    ...(hasExecution ? [{ time: '14:34:08', title: '入口响应已保存', detail: 'GET /public/ · 200 · EVD-7A21', evidence: 'response', done: true }] : []),
    ...(hasExecution && mode === 'agent' ? [{ time: '14:35:12', title: '公开入口边界已记录', detail: '计划项 02 · EVD-7A2C', evidence: 'surface', done: true }] : []),
    ...(questionStatus !== 'open' && mode === 'agent' ? [{ time: '14:36:40', title: questionStatus === 'answered' ? '操作员回答已应用' : '问题已跳过', detail: '保持只读边界 · EVD-7A39', evidence: 'decision', done: true }] : []),
    ...(state === 'paused' || state === 'pausing' ? [{ time: '14:37:18', title: state === 'paused' ? '执行已暂停' : '暂停请求已接受', detail: state === 'paused' ? '活动调用 0 · 等待恢复' : '等待活动调用停止', done: state === 'paused' }] : []),
    ...(state === 'cancelling' || state === 'cancelled' ? [{ time: '14:38:02', title: state === 'cancelled' ? (hasExecution ? '执行停止已确认' : '未启动任务已取消') : '取消请求已接受', detail: hasExecution ? (state === 'cancelled' ? '新调用 0 · 出口已撤销' : '不再授予新调用') : '未建立运行环境 · 无需清理', done: state === 'cancelled' }] : []),
  ], [state, hasExecution, mode, questionStatus]);

  return <div className={styles.detailPage}>
    <Link to="/tasks" className={styles.back}><ArrowLeftOutlined /> 任务列表</Link>
    <header className={styles.detailHeader}>
      <div><div className={styles.taskEyeline}><code>{taskId}</code><Status state={state} />{mode === 'agent' && <Tag color="purple">完整规划演示</Tag>}</div><h1>{task.draft.name}</h1><code>{task.draft.target}</code></div>
      <div className={styles.taskActions}>
        {state === 'ready' && <><Button onClick={() => navigate(`/tasks/new?mode=${mode}&relatedTo=${taskId}`)}>基于此任务调整</Button><Button danger icon={<StopOutlined />} onClick={() => setCancelOpen(true)}>取消</Button><Button type="primary" icon={<PlayCircleOutlined />} disabled={environmentBusy} onClick={() => transition('queued')}>启动</Button></>}
        {state === 'running' && <><Button icon={<PauseOutlined />} onClick={() => transition('pausing')}>暂停</Button><Button danger icon={<StopOutlined />} onClick={() => setCancelOpen(true)}>取消</Button></>}
        {state === 'paused' && <><Button type="primary" icon={<PlayCircleOutlined />} onClick={() => transition('running')}>恢复</Button><Button danger icon={<StopOutlined />} onClick={() => setCancelOpen(true)}>取消</Button></>}
        {state === 'queued' && <Button danger icon={<StopOutlined />} onClick={() => setCancelOpen(true)}>取消</Button>}
        {state === 'completed' && <Button type="primary" icon={<ReloadOutlined />} onClick={() => navigate(`/tasks/new?mode=${mode}&relatedTo=${taskId}`)}>创建关联复测</Button>}
      </div>
    </header>
    <div className={styles.statusMetrics}>
      <span><small>当前阶段</small><strong>{stateLabel[state]}</strong></span>
      <span><small>计划覆盖</small><strong>{`已观察 ${completedItems} / ${mode === 'agent' ? 5 : 1}`}</strong></span>
      <span><small>预算使用</small><strong>{hasExecution ? (mode === 'agent' ? `${Math.min(3, task.draft.requests)} / ${task.draft.requests} 请求 · ${Math.min(25000, task.draft.tokens)} / ${task.draft.tokens} Token` : `1 / ${task.draft.requests} 请求`) : `0 / ${task.draft.requests} 请求`}</strong></span>
      <span><small>资源清理</small><strong>{state === 'cancelled' ? (!hasExecution ? '无需清理' : cleanupPending ? '待完成' : '已清理') : state === 'completed' ? '已清理' : '未开始'}</strong></span>
    </div>

    {environmentBusy && state === 'ready' && <Alert className={styles.detailAlert} type="warning" showIcon title="环境暂时繁忙，任务已保留在待启动" description="切换到就绪的合成环境后仍需显式启动。" action={<Button size="small" onClick={() => transition('ready', { environment: 'ready' })}>选择就绪环境</Button>} />}
    {state === 'queued' && <Alert className={styles.detailAlert} type="info" showIcon title="启动请求已接受，正在排队" description="接受不等于已开始执行。" action={<Button size="small" onClick={() => transition('running')}>模拟环境就绪</Button>} />}
    {state === 'pausing' && <Alert className={styles.detailAlert} type="warning" showIcon title="暂停请求已接受" description="等待活动调用停止；页面保持连接不代表已经暂停。" action={<Button size="small" onClick={() => transition('paused')}>接收暂停回执</Button>} />}
    {state === 'cancelling' && <Alert className={styles.detailAlert} type="warning" showIcon title="取消请求已接受" description="保留已有证据，等待停止核实。" action={<Button size="small" onClick={() => transition('cancelled', { cleanup: 'pending' })}>接收停止回执</Button>} />}
    {state === 'cancelled' && cleanupPending && <Alert className={styles.detailAlert} type="warning" showIcon title="执行已停止，资源清理仍待完成" action={<Button size="small" onClick={() => transition('cancelled', { cleanup: 'cleaned' })}>接收清理回执</Button>} />}

    <div className={styles.detailGrid}>
      <aside className={styles.contextPane} aria-label="任务上下文">
        <div className={styles.panelHeading}><h2>任务上下文</h2><span className={styles.count}>{mode === 'agent' ? '05' : '01'}</span></div>
        <Segmented block size="small" className={styles.contextSwitch} value={contextTab} onChange={value => setContextTab(String(value))} options={mode === 'agent' ? [{ label: '计划', value: 'plan' }, { label: '黑板', value: 'blackboard' }, { label: '配置', value: 'config' }] : [{ label: '计划', value: 'plan' }, { label: '配置', value: 'config' }]} />
        {contextTab === 'plan' && <div className={styles.planList}>
          {(mode === 'http' ? [
            { key: 'response', title: '采集入口响应', status: hasExecution ? '完成' : '等待启动' },
          ] : [
            { key: 'response', title: '确认入口与响应基线', status: hasExecution ? '完成' : '等待启动' },
            { key: 'surface', title: '梳理公开页面边界', status: hasExecution ? '完成' : '等待' },
            { key: 'decision', title: '核对身份观察方式', status: !hasExecution ? '待执行' : questionStatus === 'open' ? '需回答' : '已处理' },
            { key: '', title: '验证会话边界', status: state === 'completed' ? '未覆盖' : '待执行' },
            { key: '', title: '汇总结论与限制', status: state === 'completed' ? '完成' : '待执行' },
          ]).map((item, index) => <button key={`${item.title}-${index}`} disabled={!item.key || !hasExecution} onClick={() => item.key && openEvidence(item.key)}><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{item.title}</strong><small>{item.status}</small></div>{item.key && hasExecution && <ArrowRightOutlined />}</button>)}
        </div>}
        {contextTab === 'blackboard' && mode === 'agent' && <div className={styles.blackboard}>
          <section><header><strong>事实 Facts</strong><span>{hasExecution ? '2' : '0'}</span></header>{hasExecution ? <><button onClick={() => openEvidence('response')}>入口返回 200 <small>EVD-7A21</small></button><button onClick={() => openEvidence('surface')}>管理写路径在排除范围 <small>EVD-7A2C</small></button></> : <small>执行后从已保存证据形成事实。</small>}</section>
          <section><header><strong>意图 Intents</strong><span>2</span></header><button disabled={!hasExecution} onClick={() => hasExecution && openEvidence('response')}>入口是否返回预期响应配置 {hasExecution && <small>EVD-7A21 支持</small>}</button><button disabled={!hasExecution} onClick={() => hasExecution && openEvidence('surface')}>身份页是否保持未授权边界 {hasExecution && <small>EVD-7A2C 支持</small>}</button></section>
          <section><header><strong>提示 Hints</strong><span>{hints.length}</span></header>{hints.map((item, index) => <div key={`${item}-${index}`}>{item}</div>)}<Input aria-label="添加演示提示" value={hint} placeholder="补充当前目标的提示" onChange={event => setHint(event.target.value)} onPressEnter={() => { if (hint.trim()) { setHints(current => [...current, hint.trim()]); setHint(''); } }} /><Button size="small" disabled={!hint.trim()} onClick={() => { setHints(current => [...current, hint.trim()]); setHint(''); }}>添加提示</Button><small>仅保留在当前内存，不提升权限。</small></section>
        </div>}
        {contextTab === 'config' && <dl className={styles.contextConfig}><dt>对象</dt><dd className={styles.mono}>{task.draft.target}</dd><dt>授权</dt><dd>项目测试授权 · v4</dd><dt>范围</dt><dd>{task.draft.includePath}<small>排除 {task.draft.excludePath}</small></dd><dt>身份</dt><dd>{task.draft.identity}</dd>{mode === 'agent' && <><dt>资料</dt><dd>{task.draft.reference}</dd><dt>模型</dt><dd>{task.draft.modelProfile}</dd></>}<dt>环境</dt><dd>{environmentBusy ? '隔离环境 · 暂时繁忙' : task.draft.environment}</dd><dt>预算</dt><dd>{task.draft.requests} 请求 · {Math.round(task.draft.duration / 60)} 分钟</dd></dl>}
      </aside>

      <section className={styles.activityPane} aria-label="任务活动">
        <Tabs activeKey={mainTab} onChange={setMainTab} items={[
          { key: 'timeline', label: '执行时间线', children: <div className={styles.timeline}>
            {state === 'ready' && <div className={styles.readyPanel}><SafetyCertificateOutlined /><h2>配置已冻结，等待启动</h2><p>创建没有建立运行环境，也没有排队执行。</p><dl><dt>授权</dt><dd>当前有效</dd><dt>环境</dt><dd>{environmentBusy ? '暂时繁忙' : '已知就绪'}</dd><dt>预算</dt><dd>尚未消耗</dd></dl></div>}
            {state !== 'ready' && timeline.map((item, index) => <button key={`${item.time}-${index}`} className={styles.timelineRow} disabled={!item.evidence} data-selected={item.evidence === selectedKey} onClick={() => item.evidence && setSelectedKey(item.evidence)}><time>{item.time}</time><span className={item.done ? styles.logDone : styles.logPending}>{item.done ? <CheckCircleOutlined /> : <ClockCircleOutlined />}</span><div><strong>{item.title}</strong><small>{item.detail}</small></div>{item.evidence && <FileSearchOutlined />}</button>)}
            {mode === 'agent' && state === 'running' && questionStatus === 'open' && <div className={styles.questionCard}><header><QuestionCircleOutlined /><div><strong>需要你确认观察边界</strong><small>影响计划项 03 · 不影响已取得证据</small></div><Tag color="warning">待处理</Tag></header><p>测试身份可查看账户页。是否保持只读，仅核对页面与响应边界？</p><Input.TextArea rows={2} value={question} placeholder="补充说明（不会改变授权或工具权限）" onChange={event => setQuestion(event.target.value)} /><div><Button onClick={() => setQuestionStatus('skipped')}>跳过该项</Button><Button type="primary" disabled={!question.trim()} onClick={() => { setQuestionStatus('answered'); setSelectedKey('decision'); }}>提交回答</Button></div></div>}
            {state === 'running' && <div className={styles.timelineFooter}><span>{mode === 'agent' ? `已观察 ${completedItems} / 5 项计划` : '已取得 1 份响应证据'}</span><Button type="primary" onClick={() => transition('completed', { cleanup: 'cleaned' })}>完成演示并查看结果</Button></div>}
          </div> },
          { key: 'result', label: '结果', disabled: !['completed', 'cancelled'].includes(state), children: <ResultPanel mode={mode} state={state} hasExecution={hasExecution} completedItems={completedItems} target={task.draft.target} identity={task.draft.identity} cleanupPending={cleanupPending} onEvidence={openEvidence} onRetest={() => navigate(`/tasks/new?mode=${mode}&relatedTo=${taskId}`)} /> },
        ]} />
      </section>
      <EvidenceInspector selected={selectedEvidence} onOpen={() => selectedEvidence && navigate(`/evidence/${selectedEvidence.id}?key=${selectedKey}&mode=${mode}&task=${taskId}`)} />
    </div>
    <Modal title="取消任务" open={cancelOpen} okText="确认取消" cancelText="返回" okButtonProps={{ danger: true }} onCancel={() => setCancelOpen(false)} onOk={() => { setCancelOpen(false); transition(hasExecution ? 'cancelling' : 'cancelled'); }}>
      <p>{hasExecution ? '取消后不再授予新调用；已有证据保留。任务要等停止回执后才显示“已取消”，清理结果单独确认。' : '任务尚未执行，确认后直接取消，不产生证据，也无需资源清理。'}</p>
    </Modal>
  </div>;
}

function ResultPanel({ mode, state, hasExecution, completedItems, target, identity, cleanupPending, onEvidence, onRetest }: { mode: DemoMode; state: DemoTaskState; hasExecution: boolean; completedItems: number; target: string; identity: string; cleanupPending: boolean; onEvidence: (key: string) => void; onRetest: () => void }) {
  const cancelled = state === 'cancelled';
  return <div className={styles.resultPanel}>
    <div className={styles.resultHero}>{cancelled ? <CloseCircleOutlined /> : <CheckCircleOutlined />}<div><span>{cancelled ? '任务已取消' : mode === 'http' ? 'HTTP 观察已完成' : '评估演示已结束'}</span><h2>{hasExecution ? '已保存观察依据' : '任务未执行，没有观察结果'}</h2><p>{hasExecution ? '按已取得的依据核对，未覆盖项仍保持明确标记。' : '外部调用为 0，未产生证据。'}</p></div></div>
    <div className={styles.resultColumns}><section><h3>覆盖</h3><ul><li>已观察 {completedItems} / {mode === 'http' ? 1 : 5} 项</li><li>对象：{target}</li><li>身份：{identity}</li></ul></section><section><h3>限制</h3><ul><li>{mode === 'http' ? '仅记录 HTTP 响应，不构成漏洞评估' : '会话验证及其风险结论尚未完成'}</li><li>未访问明确排除的写路径</li><li>所有证据均为 example.test 合成演示数据</li></ul></section></div>
    {cleanupPending && <Alert type="warning" showIcon title="资源清理待完成；不影响已保存证据" />}
    {hasExecution && <div className={styles.findingRow}><div><Tag color="blue">观察事实</Tag><strong>示例入口响应包含 CSP 与 nosniff 头</strong><span>依据 EVD-7A21</span></div><Button onClick={() => onEvidence('response')}>查看依据</Button></div>}
    {mode === 'agent' && hasExecution && <div className={styles.findingRow}><div><Tag color="gold">限制</Tag><strong>写入型验证未执行</strong><span>范围排除的路径未请求</span></div><Button onClick={() => onEvidence('surface')}>查看依据</Button></div>}
    <div className={styles.resultActions}><div><span>{mode === 'http' ? '观察记录' : '结果快照'}</span><strong>{hasExecution ? '合成演示 · 含未覆盖项' : '未执行'}</strong></div><Button type="primary" icon={<ReloadOutlined />} onClick={onRetest}>创建关联复测</Button></div>
  </div>;
}

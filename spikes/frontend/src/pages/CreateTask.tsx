import { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, Button, Collapse, Input, InputNumber, Select, Steps, Tag } from 'antd';
import { ArrowLeftOutlined, ArrowRightOutlined, CheckCircleOutlined, CloudServerOutlined, DatabaseOutlined, ExperimentOutlined, SaveOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { beginSyntheticRecovery, createTask, getDraft, saveDraft, updateDraft, type DemoMode, type PrototypeDraft } from '../shared/model';
import styles from '../prototype.module.css';

const stepItems = [{ title: '场景与目标' }, { title: '对象与范围' }, { title: '运行配置' }, { title: '确认任务' }];

function validTarget(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.hostname.endsWith('.example.test') && !url.username && !url.password;
  } catch { return false; }
}

function ConfigurationSummary({ draft }: { draft: PrototypeDraft }) {
  return <dl className={styles.summaryList}>
    <dt>资料</dt><dd>{draft.reference}</dd><dt>测试身份</dt><dd>{draft.identity}</dd>
    {draft.mode === 'agent' && <><dt>模型方案</dt><dd>{draft.modelProfile}</dd></>}
    <dt>执行环境</dt><dd>{draft.environment}</dd>
    <dt>预算上限</dt><dd>{draft.duration >= 60 ? `${Math.round(draft.duration / 60)} 分钟` : `${draft.duration} 秒`} · {draft.requests} 次请求{draft.mode === 'agent' ? ` · ${draft.tokens.toLocaleString()} Token` : ''}</dd>
  </dl>;
}

export function Component() {
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const mode: DemoMode = search.get('mode') === 'agent' ? 'agent' : 'http';
  const relatedTo = search.get('relatedTo') ?? undefined;
  const [draft, setDraft] = useState<PrototypeDraft>(() => getDraft(mode));
  const [step, setStep] = useState(0);
  const [saved, setSaved] = useState(false);
  const [nameError, setNameError] = useState('');
  const [recoveryError, setRecoveryError] = useState('');
  const rangeBlocked = useMemo(() => {
    if (!validTarget(draft.target)) return false;
    const url = new URL(draft.target);
    return url.hostname !== 'app.example.test' || url.pathname.startsWith('/private');
  }, [draft.target]);
  const targetError = draft.target.includes('@') ? '地址中不能包含账号或凭据，请使用测试身份引用。' : !validTarget(draft.target) ? '原型只接受 HTTPS 的 example.test 合成地址。' : '';
  const environmentBusy = draft.environment.includes('繁忙');

  function change(next: Partial<PrototypeDraft>) {
    const value = { ...draft, ...next };
    setDraft(value);
    updateDraft(mode, value);
    setSaved(false);
  }

  function switchMode(nextMode: DemoMode) {
    updateDraft(mode, draft);
    const next = new URLSearchParams(search);
    next.set('mode', nextMode);
    setSearch(next);
    setDraft(getDraft(nextMode));
    setStep(0);
    setSaved(false);
  }

  function next() {
    if (step === 0 && !draft.name.trim()) { setNameError('请填写任务名称。'); return; }
    if (step === 1 && (targetError || rangeBlocked)) return;
    setNameError('');
    setStep(value => Math.min(3, value + 1));
  }

  function doSave() {
    updateDraft(mode, draft);
    saveDraft(mode);
    setSaved(true);
  }

  function doCreate() {
    const task = createTask(draft, relatedTo);
    navigate(`/tasks/${task.id}?mode=${mode}&state=ready${environmentBusy ? '&environment=busy' : ''}`);
  }

  function loseCreateResponse() {
    if (!beginSyntheticRecovery()) {
      setRecoveryError('浏览器无法保存合成命令记录，请允许当前标签页存储后重试。');
      return;
    }
    window.location.assign('/recovery?checked=1');
  }

  return <div className={styles.createPage}>
    <Link to="/tasks" className={styles.back}><ArrowLeftOutlined aria-hidden="true" /> 任务列表</Link>
    <div className={styles.pageHeading}><div><h1>{relatedTo ? '创建关联复测' : '创建任务'}</h1><p>{mode === 'http' ? '首批 HTTP 闭环' : '完整 Agent 体验 · 规划演示'}</p></div><Tag color={mode === 'http' ? 'blue' : 'purple'}>{mode === 'http' ? 'HTTP' : 'AGENT 规划演示'}</Tag></div>
    <div className={styles.createShell}>
      <aside className={styles.createRail}>
        <div className={styles.pathSwitch} role="group" aria-label="演示路径">
          <button type="button" data-active={mode === 'http'} onClick={() => switchMode('http')}><CloudServerOutlined /><span>首批 HTTP<small>固定受控观察</small></span></button>
          <button type="button" data-active={mode === 'agent'} onClick={() => switchMode('agent')}><ExperimentOutlined /><span>完整 Agent<small>目标驱动规划演示</small></span></button>
        </div>
        <Steps orientation="vertical" size="small" current={step} items={stepItems} onChange={current => { if (current <= step) setStep(current); }} />
        <div className={styles.createSynopsis}><span>当前任务</span><strong>{draft.name || '未命名任务'}</strong><code>{draft.target}</code><small>输入仅保留在当前页面内存</small></div>
      </aside>
      <section className={styles.stepPanel} aria-live="polite">
        {step === 0 && <>
          <div className={styles.sectionHeading}><div><span>01</span><h2>场景与目标</h2></div><p>{mode === 'http' ? '固定方法观察一个授权入口，不使用 Agent 或模型。' : '目标影响探索计划；所有动作仍受范围、能力和预算约束。'}</p></div>
          <div className={styles.field}><label htmlFor="task-name">任务名称</label><Input id="task-name" value={draft.name} maxLength={120} status={nameError ? 'error' : undefined} aria-describedby={nameError ? 'name-error' : undefined} onChange={event => { change({ name: event.target.value }); setNameError(''); }} />{nameError && <p id="name-error" className={styles.error} role="alert">{nameError}</p>}</div>
          <div className={styles.field}><label htmlFor="task-goal">希望得到什么结果</label><Input.TextArea id="task-goal" rows={4} value={draft.goal} onChange={event => change({ goal: event.target.value })} /></div>
          <Collapse size="small" items={[{ key: 'criteria', label: '完成标准与方法边界', children: <div className={styles.advancedFields}><div className={styles.field}><label htmlFor="task-completion">完成标准</label><Input.TextArea id="task-completion" rows={2} value={draft.completion} onChange={event => change({ completion: event.target.value })} /></div><p className={styles.boundaryNote}>{mode === 'http' ? '仅允许一次受控 GET/HEAD；不会按自然语言生成计划。' : '自由文本不能开放新工具、扩大范围或写入目标数据。'}</p></div> }]} />
        </>}

        {step === 1 && <>
          <div className={styles.sectionHeading}><div><span>02</span><h2>对象与授权范围</h2></div><p>确认规范化对象、可访问部分和明确排除项。</p></div>
          <div className={styles.field}><label htmlFor="task-target">测试对象</label><Input id="task-target" className={styles.mono} value={draft.target} status={targetError || rangeBlocked ? 'error' : undefined} onChange={event => change({ target: event.target.value })} /><small>仅供交互演示：必须使用 example.test，不会发起网络请求。</small></div>
          {targetError && <Alert type="error" showIcon title={targetError} />}
          {rangeBlocked && <Alert type="warning" showIcon title="对象不在当前授权内" description="演示授权仅覆盖 app.example.test。仍可保存草稿，但不能创建任务。" action={<Button size="small" onClick={() => change({ target: mode === 'http' ? 'https://app.example.test/public/' : 'https://app.example.test/' })}>恢复授权对象</Button>} />}
          {!targetError && !rangeBlocked && <div className={styles.authorizationCard}><SafetyCertificateOutlined /><div><strong>项目测试授权 · v4</strong><span>覆盖 app.example.test · 有效至 2026-09-30</span></div><Tag color="success">范围匹配</Tag></div>}
          <Collapse size="small" items={[{ key: 'scope', label: '缩小范围与排除项', children: <div className={styles.advancedGrid}><div className={styles.field}><label htmlFor="include-path">纳入路径</label><Input id="include-path" className={styles.mono} value={draft.includePath} onChange={event => change({ includePath: event.target.value })} /></div><div className={styles.field}><label htmlFor="exclude-path">排除路径</label><Input id="exclude-path" className={styles.mono} value={draft.excludePath} onChange={event => change({ excludePath: event.target.value })} /></div><Button size="small" onClick={() => change({ target: 'https://outside.example.test/private/' })}>演示范围阻断</Button></div> }]} />
        </>}

        {step === 2 && <>
          <div className={styles.sectionHeading}><div><span>03</span><h2>运行配置</h2></div><p>{mode === 'http' ? '匿名、无资料、无模型；只需确认环境和预算。' : '选择已发布的资料、身份、模型方案与受管环境。'}</p></div>
          <Collapse defaultActiveKey={mode === 'agent' ? ['sources'] : []} size="small" items={[
            { key: 'sources', label: <span className={styles.collapseLabel}><DatabaseOutlined />资料与身份 <small>{draft.reference} · {draft.identity}</small></span>, children: mode === 'http' ? <p className={styles.boundaryNote}>公开 HTTP 观察不需要资料；使用匿名身份。</p> : <div className={styles.advancedGrid}><div className={styles.field}><label htmlFor="reference">固定资料版本</label><Select id="reference" value={draft.reference} onChange={value => change({ reference: value })} options={[{ value: 'Example API 说明 · v3.2（演示）', label: 'Example API 说明 · v3.2（已处理）' }, { value: '公开路由清单 · v1.4（演示）', label: '公开路由清单 · v1.4（已处理）' }]} /></div><div className={styles.field}><label htmlFor="identity">测试身份</label><Select id="identity" value={draft.identity} onChange={value => change({ identity: value })} options={[{ value: '审阅者测试身份（演示引用）', label: '审阅者测试身份 · 可用' }, { value: '匿名访问', label: '匿名访问' }]} /></div><p className={styles.boundaryNote}>这里只选择合成逻辑引用，不提供 Secret 输入。</p></div> },
            { key: 'runtime', label: <span className={styles.collapseLabel}><CloudServerOutlined />{mode === 'agent' ? '模型与环境' : '执行环境'} <small>{draft.environment}</small></span>, children: <div className={styles.advancedGrid}>{mode === 'agent' && <div className={styles.field}><label htmlFor="model-profile">模型方案</label><Select id="model-profile" value={draft.modelProfile} onChange={value => change({ modelProfile: value })} options={[{ value: '项目分析方案 · v2（规划演示）', label: '项目分析方案 · v2' }, { value: '项目严谨复核方案 · v1（规划演示）', label: '项目严谨复核方案 · v1' }]} /></div>}<div className={styles.field}><label htmlFor="environment">执行环境</label><Select id="environment" value={draft.environment} onChange={value => change({ environment: value })} options={[{ value: mode === 'http' ? '项目受管 HTTP 环境' : '隔离 Web 评估环境（演示）', label: mode === 'http' ? '项目受管 HTTP 环境 · 就绪' : '隔离 Web 评估环境 · 就绪' }, { value: '隔离环境（演示繁忙）', label: '隔离环境 · 暂时繁忙' }]} /></div>{environmentBusy && <Alert type="warning" showIcon title="环境暂时繁忙" description="配置完整，可以创建；恢复容量前不能启动。" />}</div> },
            { key: 'budget', label: <span className={styles.collapseLabel}>预算 <small>{draft.duration >= 60 ? `${Math.round(draft.duration / 60)} 分钟` : `${draft.duration} 秒`} · {draft.requests} 请求{mode === 'agent' ? ` · ${draft.tokens.toLocaleString()} Token` : ''}</small></span>, children: <div className={styles.budgetGrid}><div className={styles.field}><label htmlFor="duration">最长运行</label><InputNumber id="duration" min={mode === 'http' ? 10 : 300} max={mode === 'http' ? 180 : 1800} value={draft.duration} addonAfter="秒" onChange={value => change({ duration: Number(value ?? draft.duration) })} /></div><div className={styles.field}><label htmlFor="requests">目标请求上限</label><InputNumber id="requests" min={1} max={mode === 'http' ? 50 : 300} value={draft.requests} addonAfter="次" onChange={value => change({ requests: Number(value ?? draft.requests) })} /></div>{mode === 'agent' && <div className={styles.field}><label htmlFor="tokens">任务 Token 上限</label><InputNumber id="tokens" min={10000} max={200000} step={10000} value={draft.tokens} addonAfter="Token" onChange={value => change({ tokens: Number(value ?? draft.tokens) })} /></div>}<p className={styles.boundaryNote}>请求速率、并发和模型重试都计入同一任务上限。</p></div> },
          ]} />
        </>}

        {step === 3 && <>
          <div className={styles.sectionHeading}><div><span>04</span><h2>确认任务</h2></div><p>创建后进入待启动；不会排队、调用目标或消耗预算。</p></div>
          <div className={styles.confirmCard}><div className={styles.confirmTitle}><div><Tag color={mode === 'http' ? 'blue' : 'purple'}>{mode === 'http' ? 'HTTP 观察' : 'Web 观察评估 · 规划演示'}</Tag><h3>{draft.name}</h3></div><CheckCircleOutlined /></div><dl className={styles.confirmList}><dt>目标</dt><dd>{draft.goal}</dd><dt>对象</dt><dd><code>{draft.target}</code><small>纳入 {draft.includePath} · 排除 {draft.excludePath}</small></dd><dt>完成标准</dt><dd>{draft.completion}</dd></dl><ConfigurationSummary draft={draft} /><div className={styles.createdState}><span>创建后状态</span><strong>待启动</strong><small>启动时重新核验授权、环境和预算</small></div></div>
          {environmentBusy && <Alert type="warning" showIcon title="可以创建，暂不能启动" description="任务会保留在待启动；在详情中可切换到就绪环境。" />}
          <div className={styles.recoveryAction}><span>异常演示</span><Button type="link" onClick={loseCreateResponse}>模拟创建响应丢失</Button></div>
          {recoveryError && <Alert type="error" showIcon title={recoveryError} />}
        </>}

        {saved && <Alert className={styles.inlineNotice} type="success" showIcon title="草稿已保存到本次内存会话" description="未创建任务，也未调用任何外部系统。" />}
        <div className={styles.stepActions}>
          <Button icon={<SaveOutlined />} onClick={doSave}>保存草稿</Button>
          <span />
          {step > 0 && <Button onClick={() => setStep(value => value - 1)}>上一步</Button>}
          {step < 3 ? <Button type="primary" onClick={next} disabled={step === 1 && (!!targetError || rangeBlocked)}>下一步 <ArrowRightOutlined /></Button> : <Button type="primary" onClick={doCreate}>创建任务</Button>}
        </div>
      </section>
    </div>
  </div>;
}

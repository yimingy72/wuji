import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button, Input, Select } from 'antd';
import { ArrowLeftOutlined, ArrowRightOutlined, CheckCircleOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { initialDraft, taskPath, createDemoTask, type Draft } from '../shared/model';
import { ScopeDetails } from '../shared/Workbench';
import styles from '../prototype.module.css';

export function Component() {
  const navigate = useNavigate();
  const [draft, setDraft] = useState<Draft>(() => structuredClone(initialDraft));
  const [previewed, setPreviewed] = useState(false);
  const [error, setError] = useState('');
  function preview() {
    if (!draft.name.trim()) { setError('请填写任务名称'); setPreviewed(false); return; }
    setError(''); setPreviewed(true);
  }
  async function create() {
    if (!previewed) return;
    await createDemoTask(draft);
    navigate(taskPath);
  }
  return <div className={styles.createPage}>
    <Link to="/tasks" className={styles.back}><ArrowLeftOutlined aria-hidden="true" /> 工作台</Link>
    <div className={styles.pageHeading}><h1>创建任务</h1><span className={styles.scopeBadge}>HTTP OBSERVE</span></div>
    <div className={styles.createGrid}>
      <form onSubmit={e => { e.preventDefault(); preview(); }} className={styles.form}>
        <h2>任务设置</h2>
        <label htmlFor="task-name">任务名称</label>
        <Input id="task-name" value={draft.name} maxLength={120} aria-invalid={!!error} status={error ? 'error' : undefined} aria-describedby={error ? 'name-error' : undefined} onChange={e => { setDraft({ ...draft, name: e.target.value }); setPreviewed(false); setError(''); }} />
        {error && <p id="name-error" role="alert" className={styles.error}>{error}</p>}
        <label htmlFor="task-target">目标地址</label>
        <Input id="task-target" className={styles.mono} readOnly value={draft.target_url} />
        <label htmlFor="task-method">观察方法</label>
        <Select id="task-method" className={styles.methodSelect} virtual={false} value={draft.method} options={[{ value: 'GET', label: 'GET' }, { value: 'HEAD', label: 'HEAD' }]} onChange={(method: Draft['method']) => { setDraft({ ...draft, method }); setPreviewed(false); }} />
        <Button htmlType="submit">预览有效范围 <ArrowRightOutlined aria-hidden="true" /></Button>
      </form>
      <section className={styles.scopePanel} aria-label="有效范围" aria-live="polite">
        <h2><span><SafetyCertificateOutlined aria-hidden="true" /> 授权范围</span><span className={styles.scopeBadge}>已批准</span></h2>
        <ScopeDetails />
        {previewed ? <div className={styles.previewResult}><span><CheckCircleOutlined aria-hidden="true" /> 范围预览通过 · {draft.method}</span><Button type="primary" onClick={() => void create()}>创建任务</Button></div>
          : <div className={styles.previewEmpty}><SafetyCertificateOutlined aria-hidden="true" /> 等待范围预览</div>}
      </section>
    </div>
  </div>;
}

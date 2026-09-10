import { useMemo, useState } from 'react';
import { Button, Input, Segmented, Tag } from 'antd';
import { ArrowRightOutlined, ClockCircleOutlined, FileDoneOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { getSavedDraftMode, type DemoTaskState } from '../shared/model';
import { Status } from '../shared/ui';
import styles from '../prototype.module.css';

type Row = { id: string; name: string; target: string; mode: 'http' | 'agent'; state: DemoTaskState | 'draft'; updated: string; meta: string };

const rows: Row[] = [
  { id: 'DEMO-AGENT-DRAFT', name: '公开接口边界复核', target: 'app.example.test', mode: 'agent', state: 'draft', updated: '刚刚', meta: '步骤 2 / 4' },
  { id: 'DEMO-HTTP-1042', name: 'app.example.test · HTTP 观察', target: 'app.example.test/public/', mode: 'http', state: 'ready', updated: '14:18', meta: 'Scope v4' },
  { id: 'DEMO-AGENT-2031', name: 'app.example.test · Web 观察评估', target: 'app.example.test', mode: 'agent', state: 'running', updated: '14:36', meta: '计划 3 / 5' },
  { id: 'DEMO-AGENT-1988', name: '身份边界观察', target: 'app.example.test/account/', mode: 'agent', state: 'completed', updated: '昨天 18:42', meta: '3 份证据' },
];

export function Component() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState('');
  const [segment, setSegment] = useState('all');
  const savedMode = getSavedDraftMode();
  const visibleRows = useMemo(() => rows.filter(row => {
    const matchesText = `${row.name} ${row.target}`.toLowerCase().includes(filter.toLowerCase());
    const matchesState = segment === 'all' || (segment === 'active' ? ['ready', 'queued', 'running', 'paused'].includes(row.state) : segment === 'draft' ? row.state === 'draft' : ['completed', 'cancelled'].includes(row.state));
    return matchesText && matchesState;
  }), [filter, segment]);

  return <div className={styles.listPage}>
    <div className={styles.workspaceTitle}><div><h1>任务</h1><span className={styles.workspaceKind}>创建、观察与结果</span></div><div className={styles.titleActions}><Button onClick={() => navigate('/recovery')}>命令恢复</Button><Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/tasks/new?mode=http')}>创建任务</Button></div></div>
    <div className={styles.pathBanner}>
      <div><strong>两条演示路径</strong><span>同一生命周期，不同能力边界</span></div>
      <button onClick={() => navigate('/tasks/new?mode=http')}><CloudPath kind="HTTP" title="首批闭环" detail="匿名 · 固定受控方法 · 无模型" /></button>
      <button onClick={() => navigate('/tasks/new?mode=agent')}><CloudPath kind="AGENT" title="完整体验" detail="资料 · 身份 · 目标驱动计划（演示）" /></button>
    </div>
    {savedMode && <div className={styles.savedStrip}><FileDoneOutlined /><span>本次内存会话有一份{savedMode === 'http' ? ' HTTP' : ' Agent'} 草稿</span><Button type="link" onClick={() => navigate(`/tasks/new?mode=${savedMode}&resume=1`)}>继续填写</Button></div>}
    <section className={styles.taskTable}>
      <div className={styles.tableToolbar}><Input aria-label="搜索任务" prefix={<SearchOutlined />} placeholder="搜索名称或对象" allowClear value={filter} onChange={event => setFilter(event.target.value)} /><Segmented value={segment} onChange={value => setSegment(String(value))} options={[{ label: '全部', value: 'all' }, { label: '活动', value: 'active' }, { label: '草稿', value: 'draft' }, { label: '已结束', value: 'ended' }]} /></div>
      <div className={styles.tableHead}><span>任务</span><span>路径 / 对象</span><span>状态</span><span>更新</span><span /></div>
      <div className={styles.tableBody}>{visibleRows.map(row => {
        const href = row.state === 'draft' ? '/tasks/new?mode=agent&resume=1' : `/tasks/${row.id}?mode=${row.mode}&state=${row.state}`;
        return <Link key={row.id} className={styles.tableRow} to={href}>
          <span><code>{row.id}</code><strong>{row.name}</strong></span>
          <span><Tag color={row.mode === 'http' ? 'blue' : 'purple'}>{row.mode === 'http' ? 'HTTP' : 'AGENT 规划演示'}</Tag><code>{row.target}</code></span>
          <span>{row.state === 'draft' ? <span className={styles.draftStatus}><ClockCircleOutlined />草稿</span> : <Status state={row.state} />}<small>{row.meta}</small></span>
          <time>{row.updated}</time><ArrowRightOutlined />
        </Link>;
      })}{visibleRows.length === 0 && <div className={styles.tableEmpty}>没有匹配任务 <Button type="link" onClick={() => { setFilter(''); setSegment('all'); }}>清除筛选</Button></div>}</div>
    </section>
  </div>;
}

function CloudPath({ kind, title, detail }: { kind: string; title: string; detail: string }) {
  return <><span>{kind}</span><div><strong>{title}</strong><small>{detail}</small></div><ArrowRightOutlined /></>;
}

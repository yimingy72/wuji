import { Alert, Button, Tag } from 'antd';
import { ArrowLeftOutlined, CheckCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { readSyntheticRecovery } from '../shared/model';
import styles from '../prototype.module.css';

export function Component() {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const record = readSyntheticRecovery();
  const checked = search.get('checked') === '1';
  return <div className={styles.recoveryPage}>
    <Link to="/tasks" className={styles.back}><ArrowLeftOutlined /> 任务列表</Link>
    <div className={styles.pageHeading}><div><h1>命令恢复</h1><p>提交响应丢失后，按原命令核对一次。</p></div><Tag>交互预览</Tag></div>
    <section className={styles.recoveryCard}>
      {record && checked ? <><div className={styles.recoveryIcon}><CheckCircleOutlined /></div><span className={styles.eyebrow}>原命令已核对</span><h2>已找到待启动任务</h2><p>刷新后读取的是固定合成命令记录。页面没有再次创建，也没有自动启动。</p><dl><dt>原命令</dt><dd className={styles.mono}>{record.commandId}</dd><dt>任务</dt><dd className={styles.mono}>{record.taskId}</dd><dt>状态</dt><dd>待启动</dd><dt>外部调用</dt><dd>0</dd></dl><Button type="primary" onClick={() => navigate(`/tasks/${record.taskId}?mode=http&state=ready`)}>打开已恢复任务</Button></> : <><div className={styles.recoveryIcon}><ReloadOutlined /></div><span className={styles.eyebrow}>恢复规则</span><h2>{record ? '检测到一条合成命令记录' : '当前没有待核对命令'}</h2><p>从创建确认页选择“模拟创建响应丢失”，页面会刷新并用同一命令编号核对。只保存预置的合成编号，不保存名称、目标、描述或回答。</p>{record ? <Button type="primary" onClick={() => window.location.assign('/recovery?checked=1')}>刷新并核对原命令</Button> : <Button type="primary" onClick={() => navigate('/tasks/new?mode=http')}>前往创建演示</Button>}</>}
    </section>
    <Alert type="info" showIcon title="恢复记录不能作为执行许可" description="找到任务后仍停留在待启动；必须由用户显式启动。" />
  </div>;
}

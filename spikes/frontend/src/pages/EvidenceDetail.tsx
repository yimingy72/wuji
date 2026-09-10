import { Button, Tag } from 'antd';
import { ArrowLeftOutlined, CopyOutlined, FileTextOutlined } from '@ant-design/icons';
import { Link, useSearchParams } from 'react-router-dom';
import { evidence } from '../shared/model';
import { Notice } from '../shared/ui';
import styles from '../prototype.module.css';

export function Component() {
  const [search] = useSearchParams();
  const key = search.get('key') ?? 'response';
  const item = evidence[key];
  const taskId = search.get('task') ?? 'DEMO-HTTP-1042';
  const mode = search.get('mode') === 'agent' ? 'agent' : 'http';
  const [copied, setCopied] = useState(false);
  if (!item) return <Notice title="证据不存在" body="请返回任务选择已发布的合成证据。" />;
  return <div className={styles.evidencePage}>
    <Link to={`/tasks/${taskId}?mode=${mode}&state=running`} className={styles.back}><ArrowLeftOutlined /> 返回任务</Link>
    <div className={styles.pageHeading}><div><h1>{item.title}</h1><code>{item.id} · {item.source}</code></div><Tag color="success">合成证据</Tag></div>
    <div className={styles.evidenceGrid}>
      <section className={styles.evidenceBody} aria-label="证据内容">
        <div className={styles.evidenceToolbar}><FileTextOutlined /><span>{item.kind.toUpperCase()}</span><span>UTF-8</span><Button size="small" icon={<CopyOutlined />} onClick={async () => { try { await navigator.clipboard.writeText(item.body); setCopied(true); } catch { setCopied(false); } }}>{copied ? '已复制' : '复制内容'}</Button></div>
        <pre className={styles.codePreview}><code>{item.body}</code></pre>
      </section>
      <aside className={styles.evidenceProperties} aria-label="证据属性">
        <h2>证据属性</h2><dl className={styles.propertyList}><dt>来源任务</dt><dd><Link to={`/tasks/${taskId}?mode=${mode}&state=running`}>{taskId}</Link></dd><dt>采集来源</dt><dd>{item.source}</dd><dt>记录时间</dt><dd className={styles.mono}>2026-09-10 {item.capturedAt} UTC+8</dd><dt>目标</dt><dd className={styles.mono}>app.example.test</dd><dt>数据说明</dt><dd>{item.note}</dd><dt>保留状态</dt><dd>演示会话内可读</dd></dl>
      </aside>
    </div>
  </div>;
}

import { useState } from 'react';

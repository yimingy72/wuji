import { useSearchParams, Link } from 'react-router-dom';
import { ArrowLeftOutlined, FileTextOutlined } from '@ant-design/icons';
import { taskPath, rawFixture, initialTask, hasDemoEvidence } from '../shared/model';
import { Notice } from '../shared/ui';
import { EvidenceCode } from '../shared/Workbench';
import styles from '../prototype.module.css';

export function Component() {
  const [search] = useSearchParams();
  if (search.get('scene') === 'empty' || !hasDemoEvidence()) return <Notice title="证据暂不可用" body="当前证据尚未发布或已过期。" />;
  return <div className={styles.evidencePage}>
    <Link to={taskPath} className={styles.back}><ArrowLeftOutlined aria-hidden="true" /> 返回任务</Link>
    <div className={styles.pageHeading}><div><h1>HTTP 响应证据</h1><code>{rawFixture.artifact.name}</code></div><span className={styles.redacted}>已脱敏</span></div>
    <div className={styles.evidenceGrid}>
      <section className={styles.evidenceBody} aria-label="响应正文">
        <div className={styles.evidenceToolbar}><FileTextOutlined aria-hidden="true" /><span>RESPONSE</span><span>{rawFixture.artifact.media_type}</span><span>UTF-8</span></div>
        <EvidenceCode />
      </section>
      <aside className={styles.evidenceProperties} aria-label="证据属性">
        <h2>证据属性</h2>
        <dl className={styles.propertyList}>
          <dt>来源任务</dt><dd><Link to={taskPath}>{initialTask.name}</Link></dd>
          <dt>证据编号</dt><dd className={styles.mono}>ART-{rawFixture.artifact.id.slice(-6)}</dd>
          <dt>采集时间</dt><dd className={styles.mono}>09-09 11:00 UTC+8</dd>
          <dt>文件大小</dt><dd className={styles.mono}>{rawFixture.artifact.size_bytes} B</dd>
          <dt>内容类型</dt><dd className={styles.mono}>{rawFixture.artifact.media_type}</dd>
          <dt>Scope</dt><dd><span className={styles.scopeBadge}>v{initialTask.scope.version}</span></dd>
          <dt>SHA-256</dt><dd className={styles.mono}>{rawFixture.artifact.sha256}</dd>
        </dl>
      </aside>
    </div>
  </div>;
}

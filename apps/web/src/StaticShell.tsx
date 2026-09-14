import { ApiOutlined, LoginOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { Alert, Tag } from 'antd';
import { useAppearance } from './Appearance';
import { hasApiConfiguration, hasAuthConfiguration, webConfig } from './config';
import styles from './workbench.module.css';

function ConfigState({ label, configured, value }: {
  readonly label: string;
  readonly configured: boolean;
  readonly value: string;
}) {
  return (
    <div className={styles.integrationItem}>
      <div className={styles.integrationIcon} aria-hidden="true">
        {label === 'API base URL' ? <ApiOutlined /> : <LoginOutlined />}
      </div>
      <div>
        <strong>{label}</strong>
        <p>{configured ? value : '未配置'}</p>
      </div>
      <Tag color={configured ? 'green' : 'gold'}>{configured ? '已配置' : '待接入'}</Tag>
    </div>
  );
}

export function StaticShellPage() {
  const { paletteId } = useAppearance();
  return (
    <div className={styles.shell}>
      <a className={styles.skip} href="#main-content">跳到主要内容</a>
      <aside className={styles.rail} aria-label="Wuji 工作台">
        <div className={styles.brand} aria-label="Wuji 工作台">W<span>·</span></div>
        <div className={styles.railMark} aria-hidden="true"><SafetyCertificateOutlined /></div>
      </aside>
      <div className={styles.workspace}>
        <header className={styles.topbar}>
          <div>
            <span className={styles.eyebrow}>WUJI VNEXT</span>
            <strong>独立静态工作台</strong>
          </div>
          <Tag color="blue">主题：{paletteId}</Tag>
        </header>
        <main id="main-content" tabIndex={-1} className={styles.main}>
          <section className={styles.staticShellPage} aria-labelledby="static-shell-title">
            <span className={styles.eyebrow}>DEPLOYMENT SHELL</span>
            <h1 id="static-shell-title">工作台已就绪</h1>
            <p className={styles.lede}>
              当前页面是可部署的 vNext 静态壳。任务、运行、拓扑和身份数据将在对应服务接通后按真实响应显示。
            </p>
            <Alert
              showIcon
              type={hasApiConfiguration && hasAuthConfiguration ? 'success' : 'info'}
              title={hasApiConfiguration && hasAuthConfiguration ? 'API 与身份入口已显式配置' : '等待 API 与身份入口接入'}
              description="未接通时不会请求旧 API/Cairn，也不会填充示例任务或运行状态。"
            />
            <div className={styles.integrationPanel} aria-label="运行时配置">
              <ConfigState label="API base URL" configured={hasApiConfiguration} value={webConfig.apiBaseUrl} />
              <ConfigState label="身份入口" configured={hasAuthConfiguration} value={webConfig.authEntrypoint} />
            </div>
          </section>
        </main>
        <footer className={styles.statusbar}>
          <span>工作区 <strong>VNEXT</strong></span>
          <span>STATIC SHELL <span aria-hidden="true">/</span> 未连接运行数据</span>
        </footer>
      </div>
    </div>
  );
}

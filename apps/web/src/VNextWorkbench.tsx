import { useEffect, useMemo, useState } from 'react';
import { LoginOutlined, LogoutOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { Alert, Button, Descriptions, Select, Spin, Tag } from 'antd';
import { palettes, type PaletteId } from '@wuji/theme';
import { useAppearance } from './Appearance';
import { apiUrl, webConfig } from './config';
import { TopologyContainer } from './features/topology/TopologyContainer';
import type { TopologySelection, TopologySnapshotInput } from './features/topology/contracts';
import { CompletionPanel } from './features/completion/CompletionPanel';
import { RecordPanel } from './features/topology/panels/RecordPanel';
import { SnapshotSelector, type ViewChoice } from './features/topology/panels/SnapshotSelector';
import { selectedRecordRef } from './features/topology/record';
import styles from './workbench.module.css';

interface BrowserSession {
  readonly authenticated: true;
  readonly display_name: string;
  readonly tenant_id: string;
  readonly project_id: string;
  readonly task_id: string;
  readonly expires_at: string;
}

type SessionState =
  | { readonly status: 'checking' }
  | { readonly status: 'signed-out' }
  | { readonly status: 'authenticated'; readonly session: BrowserSession }
  | { readonly status: 'error'; readonly message: string };

function isBrowserSession(value: unknown): value is BrowserSession {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
  const record = value as Record<string, unknown>;
  return Object.keys(record).length === 6
    && record.authenticated === true
    && ['display_name', 'tenant_id', 'project_id', 'task_id', 'expires_at']
      .every((key) => typeof record[key] === 'string' && record[key] !== '');
}

async function readSession(signal?: AbortSignal): Promise<BrowserSession | null> {
  const response = await fetch(apiUrl('/auth/session'), {
    credentials: 'include',
    headers: { Accept: 'application/json' },
    signal,
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error('身份服务暂时不可用');
  const value: unknown = await response.json();
  if (!isBrowserSession(value)) throw new Error('身份响应无法确认');
  return value;
}

async function beginLocalSession(): Promise<BrowserSession> {
  const response = await fetch(apiUrl(webConfig.authEntrypoint), {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error('本地测试身份建立失败');
  const value: unknown = await response.json();
  if (!isBrowserSession(value)) throw new Error('身份响应无法确认');
  return value;
}

async function endLocalSession(): Promise<void> {
  const response = await fetch(apiUrl('/auth/logout'), {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok && response.status !== 401) throw new Error('退出请求未完成');
}

export function VNextWorkbenchPage() {
  const { paletteId, choosePalette } = useAppearance();
  const [state, setState] = useState<SessionState>({ status: 'checking' });
  const [busy, setBusy] = useState(false);
  const [snapshot, setSnapshot] = useState<TopologySnapshotInput | null>(null);
  const [selection, setSelection] = useState<TopologySelection | null>(null);
  const [viewChoice, setViewChoice] = useState<ViewChoice>({ mode: 'live', snapshotId: null });

  useEffect(() => {
    const controller = new AbortController();
    void readSession(controller.signal).then((session) => {
      if (!controller.signal.aborted) {
        setState(session ? { status: 'authenticated', session } : { status: 'signed-out' });
      }
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        setState({ status: 'error', message: error instanceof Error ? error.message : '身份读取失败' });
      }
    });
    return () => controller.abort();
  }, []);

  const login = async () => {
    setBusy(true);
    try {
      setState({ status: 'authenticated', session: await beginLocalSession() });
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : '身份建立失败' });
    } finally {
      setBusy(false);
    }
  };

  const logout = async () => {
    setBusy(true);
    try {
      await endLocalSession();
      setState({ status: 'signed-out' });
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : '退出失败' });
    } finally {
      setBusy(false);
    }
  };

  const session = state.status === 'authenticated' ? state.session : null;
  const taskId = session?.task_id ?? webConfig.taskId;
  const selectedRef = useMemo(
    () => selectedRecordRef(snapshot, selection),
    [selection, snapshot],
  );

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
            <strong>受权拓扑工作台</strong>
          </div>
          <div className={styles.headerRight}>
            <Select<PaletteId>
              aria-label="工作台配色"
              className={styles.paletteSelect}
              value={paletteId}
              virtual={false}
              options={palettes.map((palette) => ({ value: palette.id, label: palette.name }))}
              onChange={choosePalette}
            />
            {session && (
              <Button
                type="text"
                icon={<LogoutOutlined />}
                loading={busy}
                onClick={() => void logout()}
              >退出</Button>
            )}
          </div>
        </header>
        <main id="main-content" tabIndex={-1} className={styles.main}>
          <section className={styles.readonlyWorkbench} aria-labelledby="vnext-workbench-title">
            <header className={styles.readonlyHeading}>
              <div>
                <span className={styles.eyebrow}>LOCAL KUBERNETES · CONTROLLED VIEW</span>
                <h1 id="vnext-workbench-title">任务拓扑</h1>
                <p>浏览器会话经服务器映射为短寿命内部身份，当前入口开放受权读取与个人布局保存。</p>
              </div>
              <Tag color={session ? 'green' : 'gold'}>{session ? '身份已建立' : '等待身份'}</Tag>
            </header>

            {state.status === 'checking' && (
              <div className={styles.centerStatus}><Spin description="正在核对浏览器会话" /></div>
            )}
            {state.status === 'signed-out' && (
              <Alert
                showIcon
                type="info"
                title="进入本地测试工作台"
                description="此入口只映射当前隔离 Kubernetes Task，不会把内部 bearer 写入浏览器。"
                action={(
                  <Button
                    type="primary"
                    icon={<LoginOutlined />}
                    loading={busy}
                    onClick={() => void login()}
                  >建立会话</Button>
                )}
              />
            )}
            {state.status === 'error' && (
              <Alert
                showIcon
                type="error"
                title="身份入口暂时不可用"
                description={state.message}
                action={<Button onClick={() => void login()} loading={busy}>重试</Button>}
              />
            )}
            {session && (
              <>
                <Descriptions
                  className={styles.readonlyIdentity}
                  size="small"
                  bordered
                  column={{ xs: 1, sm: 1, md: 2 }}
                  items={[
                    { key: 'identity', label: '身份', children: session.display_name },
                    { key: 'expires', label: '会话到期', children: new Date(session.expires_at).toLocaleString('zh-CN') },
                    { key: 'project', label: 'Project', children: <code>{session.project_id}</code> },
                    { key: 'task', label: 'Task', children: <code>{session.task_id}</code> },
                  ]}
                />
                <SnapshotSelector
                  taskId={taskId}
                  value={viewChoice}
                  onChange={(next) => {
                    setSelection(null);
                    setSnapshot(null);
                    setViewChoice(next);
                  }}
                />
                <div className={styles.readonlyTopologyGrid}>
                  <TopologyContainer
                    taskId={taskId}
                    mode={viewChoice.mode}
                    snapshotId={viewChoice.snapshotId}
                    selection={selection}
                    onSelect={setSelection}
                    onSnapshotChange={setSnapshot}
                  />
                  <RecordPanel
                    taskId={taskId}
                    snapshotId={snapshot?.snapshot_id ?? null}
                    ref={selectedRef}
                  />
                </div>
                <CompletionPanel
                  taskId={taskId}
                  onChanged={() => setSelection(null)}
                />
              </>
            )}
          </section>
        </main>
        <footer className={styles.statusbar}>
          <span>工作区 <strong>VNEXT</strong></span>
          <span>K8S API <span aria-hidden="true">/</span> PERSONAL LAYOUT</span>
        </footer>
      </div>
    </div>
  );
}

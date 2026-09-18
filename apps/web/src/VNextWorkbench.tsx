import { useCallback, useEffect, useState } from 'react';
import { LoginOutlined, LogoutOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { Alert, Button, Input, Select, Spin } from 'antd';
import { palettes, type PaletteId } from '@wuji/theme';
import { useAppearance } from './Appearance';
import { webConfig } from './config';
import {
  beginLocalWorkbenchSession,
  endWorkbenchSession,
  readWorkbenchSession,
  type WorkbenchSession,
} from './v2WorkbenchApi';
import { FirstUseWorkbench } from './features/first-use/FirstUseWorkbench';
import styles from './workbench.module.css';

type SessionState =
  | { readonly status: 'checking' }
  | { readonly status: 'signed-out' }
  | { readonly status: 'authenticated'; readonly session: WorkbenchSession }
  | { readonly status: 'error'; readonly message: string };

export function VNextWorkbenchPage() {
  const { paletteId, choosePalette } = useAppearance();
  const [state, setState] = useState<SessionState>({ status: 'checking' });
  const [busy, setBusy] = useState(false);
  const [accessCode, setAccessCode] = useState('');

  const checkSession = useCallback((signal?: AbortSignal) => readWorkbenchSession(signal ?? new AbortController().signal), []);

  useEffect(() => {
    const controller = new AbortController();
    void checkSession(controller.signal).then((session) => {
      if (!controller.signal.aborted) setState(session ? { status: 'authenticated', session } : { status: 'signed-out' });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: 'error', message: error instanceof Error ? error.message : '身份读取失败' });
    });
    return () => controller.abort();
  }, [checkSession]);

  const login = async () => {
    setBusy(true);
    try {
      if (!webConfig.authEntrypoint) throw new Error('本地身份入口未配置');
      if (!accessCode) throw new Error('请输入本地访问码');
      const session = await beginLocalWorkbenchSession(webConfig.authEntrypoint, accessCode, new AbortController().signal);
      setState({ status: 'authenticated', session });
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : '身份建立失败' });
    } finally {
      setAccessCode('');
      setBusy(false);
    }
  };

  const logout = useCallback(async () => {
    const session = state.status === 'authenticated' ? state.session : null;
    setBusy(true);
    try {
      await endWorkbenchSession('/auth/logout', session?.csrf_token, new AbortController().signal);
      try { sessionStorage.removeItem('wuji.first-use.v2.create-key'); } catch { /* storage is non-authoritative */ }
      setAccessCode('');
      setState({ status: 'signed-out' });
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : '退出失败' });
    } finally {
      setBusy(false);
    }
  }, [state]);

  const onSessionExpired = useCallback(() => {
    try { sessionStorage.removeItem('wuji.first-use.v2.create-key'); } catch { /* storage is non-authoritative */ }
    setAccessCode('');
    setState({ status: 'signed-out' });
  }, []);

  const session = state.status === 'authenticated' ? state.session : null;
  const loginPrompt = (
    <div>
      <Input.Password
        aria-label="本地访问码"
        autoComplete="off"
        value={accessCode}
        onChange={(event) => setAccessCode(event.target.value)}
        placeholder="输入本机受限入口访问码"
      />
      <Button type="primary" icon={<LoginOutlined />} loading={busy} disabled={!accessCode} onClick={() => void login()} style={{ marginTop: 12 }}>建立会话</Button>
    </div>
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
            <span className={styles.eyebrow}>WUJI FIRST-USE</span>
            <strong>受权真实工作台</strong>
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
            {session && <Button type="text" icon={<LogoutOutlined />} loading={busy} onClick={() => void logout()}>退出</Button>}
          </div>
        </header>
        <main id="main-content" tabIndex={-1} className={styles.main}>
          {state.status === 'checking' && <div className={styles.centerStatus} role="status"><Spin description="正在核对受信浏览器会话" /></div>}
          {state.status === 'signed-out' && <section className={styles.readonlyWorkbench} aria-labelledby="first-use-login-title"><Alert showIcon type="info" title="进入本地受权工作台" description={<div><p>身份来自服务端的 local_single_operator 会话；浏览器字段不能改变主体、Project 或 Task 权限。</p>{loginPrompt}</div>} /><h1 id="first-use-login-title">等待身份</h1></section>}
          {state.status === 'error' && <section className={styles.readonlyWorkbench}><Alert showIcon type="error" title="身份入口暂时不可用" description={<div><p>{state.message}</p>{loginPrompt}</div>} /></section>}
          {session && <FirstUseWorkbench session={session} onSessionExpired={onSessionExpired} onLogout={logout} />}
        </main>
        <footer className={styles.statusbar}><span>工作区 <strong>FIRST-USE</strong></span><span>SERVER SESSION <span aria-hidden="true">/</span> TASK CONTROL</span></footer>
      </div>
    </div>
  );
}

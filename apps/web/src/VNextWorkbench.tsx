import { Activity, useCallback, useEffect, useState } from 'react';
import { LoginOutlined, LogoutOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { Alert, Button, Input, Select, Spin } from 'antd';
import { palettes, type PaletteId } from '@wuji/theme';
import { useAppearance } from './Appearance';
import { webConfig } from './config';
import {
  beginLocalWorkbenchSession,
  beginPasswordWorkbenchSession,
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
  const [retainedSession, setRetainedSession] = useState<WorkbenchSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [accessCode, setAccessCode] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);
  const passwordMode = webConfig.authMode === 'local_password';
  const legacyMode = webConfig.authMode === 'local_single_operator';

  const checkSession = useCallback((signal?: AbortSignal) => readWorkbenchSession(signal ?? new AbortController().signal), []);

  useEffect(() => {
    const controller = new AbortController();
    void checkSession(controller.signal).then((session) => {
      if (!controller.signal.aborted) {
        if (session) setRetainedSession(session);
        setState(session ? { status: 'authenticated', session } : { status: 'signed-out' });
      }
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: 'error', message: error instanceof Error ? error.message : '身份读取失败' });
    });
    return () => controller.abort();
  }, [checkSession]);

  const login = async () => {
    setBusy(true);
    setLoginError(null);
    try {
      if (!webConfig.authEntrypoint || (!passwordMode && !legacyMode)) throw new Error('登录方式未配置');
      const signal = new AbortController().signal;
      const session = passwordMode
        ? await beginPasswordWorkbenchSession(webConfig.authEntrypoint, username, password, signal)
        : await beginLocalWorkbenchSession(webConfig.authEntrypoint, accessCode, signal);
      setRetainedSession(session);
      setState({ status: 'authenticated', session });
    } catch (error) {
      setLoginError(passwordMode ? '用户名或密码不正确，或登录服务暂时不可用。' : (error instanceof Error ? error.message : '登录失败'));
      if (state.status !== 'error') setState({ status: 'signed-out' });
    } finally {
      setAccessCode('');
      setPassword('');
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
      setPassword('');
      setRetainedSession(null);
      setState({ status: 'signed-out' });
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : '退出失败' });
    } finally {
      setBusy(false);
    }
  }, [state]);

  const onSessionExpired = useCallback(() => {
    setAccessCode('');
    setPassword('');
    setState({ status: 'signed-out' });
  }, []);

  const session = state.status === 'authenticated' ? state.session : null;
  const loginPrompt = (
    <form onSubmit={(event) => { event.preventDefault(); void login(); }}>
      {loginError && <Alert showIcon type="error" title={loginError} style={{ marginBottom: 12 }} />}
      {passwordMode ? <>
        <Input aria-label="用户名" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="用户名" />
        <Input.Password aria-label="密码" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="密码" style={{ marginTop: 12 }} />
      </> : <Input.Password aria-label="本地访问码" autoComplete="off" value={accessCode} onChange={(event) => setAccessCode(event.target.value)} placeholder="本地访问码" />}
      <Button htmlType="submit" type="primary" icon={<LoginOutlined />} loading={busy} disabled={passwordMode ? !username || !password : !legacyMode || !accessCode} style={{ marginTop: 12 }}>登录</Button>
    </form>
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
            <span className={styles.eyebrow}>WUJI</span>
            <strong>Wuji</strong>
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
          {state.status === 'checking' && <div className={styles.centerStatus} role="status"><Spin description="正在检查登录状态" /></div>}
          {state.status === 'signed-out' && <section className={styles.loginPage} aria-labelledby="wuji-login-title"><div className={styles.loginPanel}><h1 id="wuji-login-title">登录 Wuji</h1>{loginPrompt}</div></section>}
          {state.status === 'error' && <section className={styles.loginPage}><div className={styles.loginPanel}><Alert className={styles.loginAlert} showIcon type="error" title="登录服务暂时不可用" description={state.message} />{loginPrompt}</div></section>}
          <Activity mode={session && retainedSession ? 'visible' : 'hidden'}>
            {retainedSession && <FirstUseWorkbench session={session ?? retainedSession} onSessionExpired={onSessionExpired} onLogout={logout} />}
          </Activity>
        </main>
        <footer className={styles.statusbar}><span><strong>WUJI</strong></span><span>LOCAL DEVELOPMENT</span></footer>
      </div>
    </div>
  );
}

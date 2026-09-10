import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
  ArrowLeftOutlined,
  FolderOpenOutlined,
  LogoutOutlined,
  ProjectOutlined,
  RightOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Alert, Button, Empty, Select, Spin, Tooltip } from 'antd';
import { useQuery } from '@tanstack/react-query';
import {
  Link,
  Navigate,
  Outlet,
  useLocation,
  useNavigate,
  useParams,
  useRouteError,
  useSearchParams,
} from 'react-router-dom';
import { palettes, type PaletteId } from '@wuji/theme';
import { ApiRequestError, isApiError, type Project, type Session } from './api';
import { AppearanceProvider, useAppearance } from './Appearance';
import {
  logout,
  leaveUnavailableProject,
  projectPageQueryOptions,
  projectQueryOptions,
  refreshSession,
  selectKnownProject,
  sessionQueryOptions,
} from './queries';
import { beginLoginPath, loginPath, normalizeReturnTo } from './routing';
import { ApprovedScopesPanel } from './scopes';
import { useIdentitySnapshot } from './state';
import styles from './workbench.module.css';

const loginErrors = {
  UNAUTHENTICATED: '登录未完成，请重新发起登录。',
  FORBIDDEN: '当前身份尚未获得平台访问权限。',
  SERVICE_UNAVAILABLE: '身份服务暂时不可用，请稍后重试。',
  INTERNAL_ERROR: '登录处理失败，请稍后重试。',
} as const;
const traceIdPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const paletteOptions = palettes.map((palette) => ({ value: palette.id, label: palette.name }));

function renderPaletteLabel(value: unknown, label: ReactNode) {
  const palette = palettes.find((candidate) => candidate.id === value);
  if (!palette) return label;
  return (
    <span className={styles.paletteOption}>
      <span
        aria-hidden="true"
        className={styles.paletteSwatch}
        style={{ background: palette.colors.canvas, color: palette.colors.accent }}
      />
      {label}
    </span>
  );
}

function isLoginErrorCode(value: string | null): value is keyof typeof loginErrors {
  return value !== null && Object.prototype.hasOwnProperty.call(loginErrors, value);
}

function errorCopy(error: unknown): { title: string; body: string; traceId: string | null } {
  if (error instanceof ApiRequestError) {
    if (error.contractFailure) {
      return { title: '响应无法读取', body: '平台返回的数据格式无法识别。', traceId: error.traceId };
    }
    if (error.status === 403) {
      return { title: '当前操作无权限', body: '请联系项目管理员核对访问权限。', traceId: error.traceId };
    }
    if (error.status === 404) {
      return { title: '内容不可访问', body: '该项目不存在或你已失去访问权限。', traceId: error.traceId };
    }
    if (error.status === 410) {
      return { title: '列表已更新', body: '当前翻页位置已失效，请从第一页重新查看。', traceId: error.traceId };
    }
    if (error.status === 0 || error.status === 503) {
      return { title: '平台暂时不可用', body: '连接未完成，请稍后重试。', traceId: error.traceId };
    }
  }
  return { title: '页面加载失败', body: '请求未完成，请重试。', traceId: null };
}

function ErrorNotice({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const copy = errorCopy(error);
  return (
    <Alert
      role="alert"
      className={styles.alert}
      type="error"
      showIcon
      title={copy.title}
      description={(
        <div>
          <p>{copy.body}</p>
          {copy.traceId && <code className={styles.trace}>追踪编号 {copy.traceId}</code>}
        </div>
      )}
      action={onRetry ? <Button onClick={onRetry}>重试</Button> : undefined}
    />
  );
}

interface ShellProps {
  readonly children: ReactNode;
  readonly session?: Session | null;
}

function AppShell({ children, session = null }: ShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { paletteId, choosePalette } = useAppearance();
  const previousPath = useRef(location.pathname);

  useEffect(() => {
    if (previousPath.current !== location.pathname) {
      document.getElementById('main-content')?.focus();
      previousPath.current = location.pathname;
    }
  }, [location.pathname]);

  const beginLogout = async () => {
    const result = await logout();
    if (result === 'complete') navigate('/login', { replace: true });
  };

  return (
    <div className={styles.shell}>
      <a className={styles.skip} href="#main-content">跳到主要内容</a>
      <aside className={styles.rail}>
        <Link className={styles.brand} to="/projects" aria-label="Wuji 工作台">W<span>·</span></Link>
        <nav aria-label="主要导航">
          <Tooltip title="项目" placement="right">
            <Link
              to="/projects"
              aria-label="项目"
              aria-current={location.pathname.startsWith('/projects') ? 'page' : undefined}
            >
              <ProjectOutlined aria-hidden="true" />
            </Link>
          </Tooltip>
        </nav>
      </aside>
      <div className={styles.workspace}>
        <header className={styles.topbar}>
          <div className={styles.breadcrumb}>
            <strong>WUJI</strong>
            <span>/</span>
            <FolderOpenOutlined aria-hidden="true" />
            <span>{location.pathname === '/login' ? '登录' : '项目工作区'}</span>
          </div>
          <div className={styles.headerRight}>
            <Select<PaletteId>
              aria-label="工作台配色"
              className={styles.paletteSelect}
              value={paletteId}
              virtual={false}
              options={paletteOptions}
              labelRender={(option) => renderPaletteLabel(option.value, option.label)}
              optionRender={(option) => renderPaletteLabel(option.value, option.label)}
              onChange={choosePalette}
            />
            {session && (
              <>
                <span className={styles.identity} title={session.display_name}>
                  <UserOutlined aria-hidden="true" />
                  <span>{session.display_name}</span>
                </span>
                <Tooltip title="退出登录">
                  <Button
                    className={styles.logoutButton}
                    type="text"
                    aria-label="退出登录"
                    icon={<LogoutOutlined aria-hidden="true" />}
                    onClick={() => void beginLogout()}
                  />
                </Tooltip>
              </>
            )}
          </div>
        </header>
        <main id="main-content" tabIndex={-1} className={styles.main}>{children}</main>
        <footer className={styles.statusbar}>
          <span>工作区 <strong>PLATFORM</strong></span>
          <span>AUTHORIZED ACCESS <span aria-hidden="true">/</span> v0.3</span>
        </footer>
      </div>
    </div>
  );
}

function LoadingPage({ label }: { label: string }) {
  return (
    <AppShell>
      <div className={styles.centerStatus} role="status">
        <Spin description={label} />
      </div>
    </AppShell>
  );
}

export function HydrateFallbackPage() {
  return (
    <AppearanceProvider>
      <LoadingPage label="正在打开工作台" />
    </AppearanceProvider>
  );
}

function LogoutPrivacyScreen() {
  const identity = useIdentitySnapshot();
  const navigate = useNavigate();
  const [retrying, setRetrying] = useState(false);

  const retry = async () => {
    setRetrying(true);
    const result = await logout();
    setRetrying(false);
    if (result === 'complete') navigate('/login', { replace: true });
  };

  return (
    <AppShell>
      <section className={styles.privacy}>
        {identity.status === 'logout-pending' ? (
          <div role="status" className={styles.centerStatus}>
            <Spin description="正在确认退出" />
          </div>
        ) : (
          <Alert
            role="alert"
            type="warning"
            showIcon
            title="退出未完成"
            description="平台尚未确认当前会话已撤销。"
            action={<Button loading={retrying} onClick={() => void retry()}>重试退出</Button>}
          />
        )}
      </section>
    </AppShell>
  );
}

function usePrivateSession(): Session | null {
  const identity = useIdentitySnapshot();
  const query = useQuery({
    ...sessionQueryOptions(),
    enabled: identity.status === 'authenticated',
  });
  return query.data ?? identity.session;
}

export function PrivatePage({ children }: { children: (session: Session) => ReactNode }) {
  const identity = useIdentitySnapshot();
  const session = usePrivateSession();
  const location = useLocation();

  useEffect(() => {
    if (identity.status !== 'authenticated') return;
    const recheckSession = () => { void refreshSession().catch(() => undefined); };
    window.addEventListener('focus', recheckSession);
    return () => window.removeEventListener('focus', recheckSession);
  }, [identity.status]);

  if (identity.status === 'logout-pending' || identity.status === 'logout-failed') {
    return <LogoutPrivacyScreen />;
  }
  if (identity.status === 'checking') return <LoadingPage label="正在确认会话" />;
  if (!session || identity.status === 'signed-out') {
    return <Navigate to={loginPath(location.pathname)} replace />;
  }
  return <AppShell session={session}>{children(session)}</AppShell>;
}

export function LoginPage() {
  const identity = useIdentitySnapshot();
  const [search] = useSearchParams();
  const returnTo = normalizeReturnTo(search.get('return_to'));
  const session = useQuery({
    ...sessionQueryOptions(),
    enabled: identity.status === 'checking' || identity.status === 'authenticated',
  });
  const callbackError = search.get('error');
  const traceId = search.get('trace_id');
  const safeCallbackError = isLoginErrorCode(callbackError) && traceIdPattern.test(traceId ?? '')
    ? callbackError
    : null;

  if (!safeCallbackError && identity.status === 'authenticated' && (session.data || identity.session)) {
    return <Navigate to={returnTo} replace />;
  }

  return (
    <AppShell>
      <section className={styles.loginPage} aria-labelledby="login-title">
        <div className={styles.loginPanel}>
          <div className={styles.eyebrow}>WUJI PLATFORM</div>
          <h1 id="login-title">进入工作台</h1>
          {safeCallbackError && (
            <Alert
              role="alert"
              className={styles.loginAlert}
              type={safeCallbackError === 'FORBIDDEN' ? 'warning' : 'error'}
              showIcon
              title={loginErrors[safeCallbackError]}
              description={<code className={styles.trace}>追踪编号 {traceId}</code>}
            />
          )}
          {session.error && !isApiError(session.error, 401) && (
            <ErrorNotice error={session.error} onRetry={() => void session.refetch()} />
          )}
          <Button className={styles.loginButton} type="primary" href={beginLoginPath(returnTo)}>
            使用组织账号登录
          </Button>
        </div>
      </section>
    </AppShell>
  );
}

function ProjectsContent({ session }: { session: Session }) {
  const [cursor, setCursor] = useState<string | null>(null);
  const [previousCursors, setPreviousCursors] = useState<(string | null)[]>([]);
  const [cursorVersion, setCursorVersion] = useState(session.permissions_version);
  const permissionsVersion = session.permissions_version;
  const effectiveCursor = cursorVersion === permissionsVersion ? cursor : null;
  const page = useQuery(projectPageQueryOptions(session, effectiveCursor));

  useEffect(() => {
    setCursor(null);
    setPreviousCursors([]);
    setCursorVersion(permissionsVersion);
  }, [permissionsVersion]);

  useEffect(() => {
    if (isApiError(page.error, 410) && effectiveCursor !== null) {
      setCursor(null);
      setPreviousCursors([]);
      setCursorVersion(permissionsVersion);
      void refreshSession().catch(() => undefined);
    }
  }, [effectiveCursor, page.error, permissionsVersion]);

  const goNext = () => {
    if (!page.data?.next_cursor) return;
    setPreviousCursors((previous) => [...previous, effectiveCursor]);
    setCursor(page.data.next_cursor);
  };

  const goPrevious = () => {
    const previous = previousCursors.at(-1);
    if (previous === undefined) return;
    setPreviousCursors((items) => items.slice(0, -1));
    setCursor(previous);
  };

  return (
    <>
      <ProjectUnavailableNotice />
      <section className={styles.projectPage} aria-labelledby="projects-title">
        <header className={styles.pageHeading}>
        <div>
          <span className={styles.eyebrow}>PROJECT ACCESS</span>
          <h1 id="projects-title">项目</h1>
        </div>
        <div className={styles.sessionLine}>
          <span>当前身份</span>
          <strong>{session.display_name}</strong>
        </div>
        </header>
        <div className={styles.projectPanel}>
        <div className={styles.panelHeader}>
          <h2>可访问项目</h2>
          <span>项目列表</span>
        </div>
        {page.isPending ? (
          <div className={styles.panelStatus} role="status"><Spin description="正在读取项目" /></div>
        ) : page.error && !isApiError(page.error, 410) ? (
          <div className={styles.panelStatus}><ErrorNotice error={page.error} onRetry={() => void page.refetch()} /></div>
        ) : page.data?.items.length === 0 ? (
          <div className={styles.panelStatus} role="status">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前身份没有可访问的项目" />
          </div>
        ) : (
          <nav aria-label="项目列表" className={styles.projectList}>
            {page.data?.items.map((project) => (
              <Link
                key={`${project.tenant_id}:${project.id}`}
                to={`/projects/${project.id}`}
                className={styles.projectRow}
                onClick={() => selectKnownProject(project)}
              >
                <span className={styles.projectMark} aria-hidden="true"><ProjectOutlined /></span>
                <span className={styles.projectIdentity}>
                  <strong>{project.name}</strong>
                  <code>{project.id}</code>
                </span>
                <span className={styles.tenantIdentity}>
                  <span>租户</span>
                  <code>{project.tenant_id}</code>
                </span>
                <span className={styles.rowPermission}>
                  {project.permissions.includes('project.read') ? '可读取' : '无可用权限'}
                </span>
                <RightOutlined aria-hidden="true" />
              </Link>
            ))}
          </nav>
        )}
        <footer className={styles.pagination} aria-label="项目分页">
          <span>{effectiveCursor === null ? '当前为起始批次' : '当前为后续批次'}</span>
          <div>
            <Button className={styles.pageButton} disabled={previousCursors.length === 0} onClick={goPrevious}>上一页</Button>
            <Button className={styles.pageButton} disabled={!page.data?.next_cursor} onClick={goNext}>下一页</Button>
          </div>
        </footer>
        </div>
      </section>
    </>
  );
}

export function ProjectsPage() {
  return <PrivatePage>{(session) => <ProjectsContent session={session} />}</PrivatePage>;
}

function ProjectContent({ session, projectId }: { session: Session; projectId: string }) {
  const navigate = useNavigate();
  const project = useQuery(projectQueryOptions(session, projectId));

  useEffect(() => {
    if (isApiError(project.error, 404)) {
      leaveUnavailableProject(projectId);
      navigate('/projects?notice=project-unavailable', { replace: true });
    }
  }, [navigate, project.error, projectId]);

  if (project.isPending) {
    return <div className={styles.centerStatus} role="status"><Spin description="正在读取项目" /></div>;
  }
  if (project.error) {
    return <ErrorNotice error={project.error} onRetry={() => void project.refetch()} />;
  }
  if (!project.data.permissions.includes('project.read')) {
    return (
      <Alert
        role="alert"
        type="error"
        showIcon
        title="当前项目无可用权限"
        description="请返回项目列表选择其他项目。"
        action={<Button onClick={() => navigate('/projects')}>返回项目列表</Button>}
      />
    );
  }

  return <ProjectWorkspace session={session} project={project.data} />;
}

function ProjectWorkspace({ session, project }: { session: Session; project: Project }) {
  const navigate = useNavigate();
  const canPreview = project.permissions.includes('task.preview');
  const canReadTasks = project.permissions.includes('task.read');
  return (
    <section className={styles.projectWorkspace} aria-labelledby="project-title">
      <Link className={styles.backLink} to="/projects">
        <ArrowLeftOutlined aria-hidden="true" />
        返回项目列表
      </Link>
      <header className={styles.workspaceHeading}>
        <div>
          <span className={styles.eyebrow}>PROJECT WORKSPACE</span>
          <h1 id="project-title">{project.name}</h1>
          <p data-testid="project-canary">项目 {project.name} · {project.id}</p>
        </div>
        <div className={styles.inlineActions}>
          {canReadTasks && <Button onClick={() => navigate(`/projects/${project.id}/tasks`)}>任务列表</Button>}
          {canPreview && (
            <Button type="primary" onClick={() => navigate(`/projects/${project.id}/tasks/new`)}>
              新建任务
            </Button>
          )}
        </div>
      </header>
      <div className={styles.workspacePanel}>
        <aside className={styles.projectSummary}>
          <div className={styles.summaryLabel}>项目标识</div>
          <code>{project.id}</code>
          <div className={styles.summaryLabel}>租户标识</div>
          <code>{project.tenant_id}</code>
        </aside>
        <div className={styles.projectDetail}>
          <div className={styles.permissionPanel}>
            <header>
              <div>
                <h2>项目访问</h2>
                <p>{canPreview ? '该身份可以查看项目并提交任务预览。' : '该身份可以只读查看项目与批准范围。'}</p>
              </div>
              <SafetyCertificateOutlined aria-hidden="true" />
            </header>
            <dl>
              <dt>身份</dt>
              <dd>{session.display_name}</dd>
              <dt>项目查看</dt>
              <dd><span className={styles.permissionState}>已授权</span></dd>
              <dt>任务预览</dt>
              <dd>{canPreview ? <span className={styles.permissionState}>已授权</span> : '只读身份不可提交'}</dd>
              <dt>任务查看</dt>
              <dd>{canReadTasks ? <span className={styles.permissionState}>已授权</span> : '当前身份不可查看'}</dd>
              <dt>会话到期</dt>
              <dd><time dateTime={session.expires_at}>{new Date(session.expires_at).toLocaleString('zh-CN')}</time></dd>
            </dl>
          </div>
          <ApprovedScopesPanel session={session} projectId={project.id} />
        </div>
      </div>
    </section>
  );
}

export function ProjectPage() {
  const { projectId = '' } = useParams();
  return <PrivatePage>{(session) => <ProjectContent session={session} projectId={projectId} />}</PrivatePage>;
}

export function ProjectUnavailableNotice() {
  const [search, setSearch] = useSearchParams();
  if (search.get('notice') !== 'project-unavailable') return null;
  return (
    <Alert
      role="alert"
      className={styles.routeNotice}
      type="warning"
      showIcon
      title="当前项目不可访问"
      description="项目不存在或访问权限已经失效。"
      closable={{ onClose: () => {
        const next = new URLSearchParams(search);
        next.delete('notice');
        setSearch(next, { replace: true, defaultShouldRevalidate: false });
      } }}
    />
  );
}

export function ProjectsRoute() {
  return <ProjectsPage />;
}

export function RouteErrorPage() {
  const error = useRouteError();
  const identity = useIdentitySnapshot();
  const navigate = useNavigate();
  const session = identity.status === 'authenticated' ? identity.session : null;
  const retry = error instanceof ApiRequestError && (error.status === 0 || error.status === 503)
    ? () => navigate(0)
    : undefined;

  return (
    <AppShell session={session}>
      <section className={styles.routeError}>
        <ErrorNotice error={error} onRetry={retry} />
        <Button onClick={() => navigate('/projects')}>返回项目列表</Button>
      </section>
    </AppShell>
  );
}

export function NotFoundPage() {
  return (
    <AppShell>
      <section className={styles.routeError}>
        <Alert role="alert" type="warning" showIcon title="页面不存在" description="请返回项目列表选择项目。" />
        <Button href="/projects">返回项目列表</Button>
      </section>
    </AppShell>
  );
}

export function RootLayout() {
  return <Outlet />;
}

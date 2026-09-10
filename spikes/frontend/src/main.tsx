import { StrictMode, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Button, Drawer, Select, Tooltip } from 'antd';
import { DeploymentUnitOutlined, FolderOpenOutlined, SettingOutlined, UserOutlined } from '@ant-design/icons';
import { createBrowserRouter, Link, Navigate, Outlet, RouterProvider, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { palettes, isPaletteId } from '@wuji/theme';
import { AppearanceProvider, useAppearance } from './shared/Appearance';
import { Notice } from './shared/ui';
import './shared/fonts.css';
import '@fontsource/ibm-plex-mono/latin-400.css';
import styles from './prototype.module.css';

function Shell() {
  const [search, setSearch] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { paletteId, setPaletteId } = useAppearance();
  const requestedPalette = search.get('theme');
  useLayoutEffect(() => {
    if (isPaletteId(requestedPalette)) setPaletteId(requestedPalette);
  }, [requestedPalette, setPaletteId]);
  const previousPath = useRef(location.pathname);
  useEffect(() => {
    if (previousPath.current !== location.pathname) document.getElementById('main-content')?.focus();
    previousPath.current = location.pathname;
  }, [location.pathname]);

  return <div className={styles.shell}>
    <a className={styles.skip} href="#main-content">跳到主要内容</a>
    <aside className={styles.rail}>
      <Link to="/tasks" className={styles.brand} aria-label="Wuji 交互预览">W<span>·</span></Link>
      <nav aria-label="主要导航">
        <Tooltip title="任务" placement="right"><Link to="/tasks" aria-label="任务" aria-current={location.pathname.startsWith('/tasks') ? 'page' : undefined}><DeploymentUnitOutlined aria-hidden="true" /></Link></Tooltip>
      </nav>
      <div className={styles.railBottom}><Tooltip title="预览设置" placement="right"><Button type="text" aria-label="预览设置" icon={<SettingOutlined aria-hidden="true" />} onClick={() => setSettingsOpen(true)} /></Tooltip></div>
    </aside>
    <div className={styles.workspace}>
      <header className={styles.topbar}>
        <div className={styles.breadcrumb}><strong>WUJI</strong><span>/</span><FolderOpenOutlined aria-hidden="true" /><span>本地验证项目</span><span className={styles.previewBadge}>交互预览</span></div>
        <div className={styles.headerRight}>
          <Select aria-label="工作台配色" className={styles.paletteSelect} value={paletteId} virtual={false}
            options={palettes.map(palette => ({ value: palette.id, label: <span className={styles.paletteOption}><span aria-hidden="true" className={styles.paletteSwatch} style={{ background: palette.colors.canvas, color: palette.colors.accent }} />{palette.name}</span> }))}
            onChange={value => { setPaletteId(value); setSearch(previous => { const next = new URLSearchParams(previous); next.set('theme', value); return next; }, { replace: true }); }} />
          <span className={styles.avatar} aria-label="演示操作员"><UserOutlined aria-hidden="true" /></span>
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className={styles.main}><Outlet /></main>
      <footer className={styles.statusbar}><span>合成数据 <strong>EXAMPLE.TEST</strong></span><span>NO API · NO MODEL · NO TARGET</span></footer>
    </div>
    <Drawer title="交互预览设置" open={settingsOpen} onClose={() => setSettingsOpen(false)} size={360}>
      <div className={styles.settingsStack}>
        <section><h3>数据边界</h3><p>页面不连接 API、模型、集群或目标。表单和问题回答只保留在当前内存中。</p></section>
        <section><h3>演示路径</h3><div className={styles.drawerActions}><Button onClick={() => { navigate('/tasks/new?mode=http'); setSettingsOpen(false); }}>首批 HTTP</Button><Button onClick={() => { navigate('/tasks/new?mode=agent'); setSettingsOpen(false); }}>完整 Agent 规划</Button></div></section>
        <section><h3>命令恢复</h3><p>恢复页仅识别固定的合成命令记录，不保存表单内容。</p><Button type="link" onClick={() => { navigate('/recovery'); setSettingsOpen(false); }}>查看恢复说明</Button></section>
      </div>
    </Drawer>
  </div>;
}

const router = createBrowserRouter([{
  path: '/', element: <Shell />, errorElement: <Notice title="页面加载失败" body="请返回任务列表重新加载。" />,
  children: [
    { index: true, element: <Navigate to="/tasks" replace /> },
    { path: 'tasks', lazy: () => import('./pages/TaskList') },
    { path: 'tasks/new', lazy: () => import('./pages/CreateTask') },
    { path: 'tasks/:taskId', lazy: () => import('./pages/TaskDetail') },
    { path: 'evidence/:evidenceId', lazy: () => import('./pages/EvidenceDetail') },
    { path: 'recovery', lazy: () => import('./pages/Recovery') },
    { path: '*', element: <Notice title="页面不存在" body="请从任务列表进入交互预览。" /> },
  ],
}]);

createRoot(document.getElementById('root')!).render(<StrictMode><AppearanceProvider><RouterProvider router={router} /></AppearanceProvider></StrictMode>);

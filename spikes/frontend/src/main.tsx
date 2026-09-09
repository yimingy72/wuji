import { StrictMode, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Button, Drawer, Select, Tooltip } from 'antd';
import { DeploymentUnitOutlined, FileSearchOutlined, FolderOpenOutlined, SettingOutlined, UserOutlined } from '@ant-design/icons';
import { QueryClientProvider, useQuery } from '@tanstack/react-query';
import { createBrowserRouter, Link, Navigate, Outlet, RouterProvider, useLocation, useSearchParams } from 'react-router-dom';
import { queryClient, taskQuery, initialTask, rawFixture, artifactPath, stopDemoTask } from './shared/model';
import { Notice } from './shared/ui';
import { palettes, isPaletteId } from '@wuji/theme';
import { AppearanceProvider, useAppearance } from './shared/Appearance';
import './shared/fonts.css';
import '@fontsource/ibm-plex-mono/latin-400.css';
import styles from './prototype.module.css';

function Shell() {
  const [search, setSearch] = useSearchParams();
  const location = useLocation();
  const { data: task } = useQuery(taskQuery);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { paletteId, setPaletteId } = useAppearance();
  const requestedPalette = search.get('theme');
  useLayoutEffect(() => {
    if (isPaletteId(requestedPalette)) setPaletteId(requestedPalette);
  }, [requestedPalette, setPaletteId]);
  const scene = search.get('scene') ?? 'default';
  const previousPath = useRef(location.pathname);
  useEffect(() => {
    if (previousPath.current !== location.pathname) document.getElementById('main-content')?.focus();
    previousPath.current = location.pathname;
  }, [location.pathname]);
  return <div className={styles.shell}>
    <a className={styles.skip} href="#main-content">跳到主要内容</a>
    <aside className={styles.rail}>
      <Link to="/tasks" className={styles.brand} aria-label="Wuji 工作台">W<span>·</span></Link>
      <nav aria-label="主要导航">
        <Tooltip title="工作台" placement="right"><Link to="/tasks" aria-label="工作台" aria-current={location.pathname.startsWith('/tasks') ? 'page' : undefined}><DeploymentUnitOutlined aria-hidden="true" /></Link></Tooltip>
        <Tooltip title="证据" placement="right"><Link to={artifactPath} aria-label="证据" aria-current={location.pathname.startsWith('/evidence') ? 'page' : undefined}><FileSearchOutlined aria-hidden="true" /></Link></Tooltip>
      </nav>
      <div className={styles.railBottom}><Tooltip title="演示设置" placement="right"><Button type="text" aria-label="演示设置" icon={<SettingOutlined aria-hidden="true" />} onClick={() => setSettingsOpen(true)} /></Tooltip></div>
    </aside>
    <div className={styles.workspace}>
      <header className={styles.topbar}>
        <div className={styles.breadcrumb}><strong>WUJI</strong><span>/</span><FolderOpenOutlined aria-hidden="true" /><span>本地验证项目</span></div>
        <div className={styles.headerRight}>
          <Select aria-label="工作台配色" className={styles.paletteSelect} value={paletteId} virtual={false}
            options={palettes.map(palette => ({ value: palette.id, label: <span className={styles.paletteOption}><span aria-hidden="true" className={styles.paletteSwatch} style={{ background: palette.colors.canvas, color: palette.colors.accent }} />{palette.name}</span> }))}
            onChange={value => { setPaletteId(value); setSearch(previous => { const next = new URLSearchParams(previous); next.set('theme', value); return next; }, { replace: true }); }} />
          <span className={styles.localBadge}>本地演示</span><span className={styles.avatar} aria-label="演示操作员"><UserOutlined aria-hidden="true" /></span>
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className={styles.main}>
        {scene === 'denied' ? <Notice title="当前项目不可访问" body="项目权限已失效。" />
          : scene === 'error' ? <Notice title="暂时无法获取数据" body="查询失败，任务状态待同步。" /> : <Outlet />}
      </main>
      <footer className={styles.statusbar}><span>工作区 <strong>LOCAL</strong></span><span>HTTP OBSERVE <span className={styles.statusDivider}>/</span> v0.1</span></footer>
    </div>
    <Drawer title="演示设置" open={settingsOpen} onClose={() => setSettingsOpen(false)} size={340}>
      <p className={styles.settingsText}>本地内存数据，不连接平台或测试目标。刷新页面恢复初始状态。</p>
      <label className={styles.settingsLabel}>演示场景<select value={scene} onChange={e => { setSearch(e.target.value === 'default' ? {} : { scene: e.target.value }); setSettingsOpen(false); }}>
        <option value="default">正常流程</option><option value="unknown">结果不明</option><option value="cleanup">清理待完成</option><option value="denied">无权限</option><option value="empty">空结果</option><option value="error">查询失败</option>
      </select></label>
      {scene === 'default' && task?.state === 'cancelling' && <div className={styles.simulator}><Button onClick={async () => { await stopDemoTask(task); setSettingsOpen(false); }}>模拟停止与清理回执</Button></div>}
    </Drawer>
  </div>;
}

const router = createBrowserRouter([{
  path: '/', element: <Shell />, errorElement: <Notice title="页面加载失败" body="请返回任务列表重新加载。" />,
  children: [
    { index: true, element: <Navigate to="/tasks" replace /> },
    { path: 'tasks', loader: () => queryClient.ensureQueryData(taskQuery), lazy: () => import('./pages/TaskList') },
    { path: 'tasks/new', lazy: () => import('./pages/CreateTask') },
    { path: `tasks/${initialTask.id}`, loader: () => queryClient.ensureQueryData(taskQuery), lazy: () => import('./pages/TaskDetail') },
    { path: `evidence/${rawFixture.artifact.id}`, lazy: () => import('./pages/EvidenceDetail') },
    { path: '*', element: <Notice title="页面不存在" body="请从任务列表进入已实现的原型页面。" /> },
  ],
}]);

createRoot(document.getElementById('root')!).render(<StrictMode><AppearanceProvider><QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider></AppearanceProvider></StrictMode>);

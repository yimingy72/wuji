import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AppearanceProvider } from '../../../apps/web/src/Appearance';
import { TopologyFlowCanvas } from '../../../apps/web/src/features/topology/TopologyFlowCanvas';
import type {
  LayoutPreference,
  TopologySelection,
  TopologySnapshotInput,
  ViewMode,
} from '../../../apps/web/src/features/topology/contracts';
import { layout as layoutFixture, snapshot as snapshotFixture } from '../fixtures';

function Fixture() {
  const mode: ViewMode = new URLSearchParams(window.location.search).get('mode') === 'history'
    ? 'history'
    : 'live';
  const [currentSnapshot, setCurrentSnapshot] = useState<TopologySnapshotInput>(
    () => structuredClone(snapshotFixture) as TopologySnapshotInput,
  );
  const [layout, setLayout] = useState<LayoutPreference>(
    () => ({
      ...structuredClone(layoutFixture),
      entries: structuredClone(layoutFixture.entries).map((entry) => (
        entry.anchor.entity_type === 'claim' && entry.anchor.revision === '1'
          ? { ...entry, x: 620, y: 160 }
          : entry.anchor.entity_type === 'intent'
            ? { ...entry, x: 850, y: 480 }
            : entry
      )),
      viewport: { x: 16, y: 20, zoom: 0.72 },
    }) as LayoutPreference,
  );
  const [selection, setSelection] = useState<TopologySelection | null>(null);
  const [layoutEvents, setLayoutEvents] = useState(0);
  const [commands, setCommands] = useState(0);
  const [expansions, setExpansions] = useState(0);

  return (
    <main style={{ minHeight: '100vh', padding: 20, background: 'var(--canvas)', color: 'var(--text)' }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1>任务拓扑</h1>
          <p>固定授权快照 · {mode === 'history' ? '历史' : '当前'}视图</p>
        </div>
        <button
          type="button"
          onClick={() => setCurrentSnapshot((current) => ({
            ...current,
            view_revision: '42',
            nodes: [
              ...current.nodes,
              {
                id: 'claim:claim-1@3',
                ref: { entity_type: 'claim', id: 'claim-1', revision: '3' },
                display_kind: 'claim',
                label: '服务返回第三个修订',
                state: 'unassessed',
                allowed_actions: ['inspect'],
              },
            ],
          }))}
        >新增修订</button>
      </header>
      <TopologyFlowCanvas
        snapshot={currentSnapshot}
        layout={layout}
        mode={mode}
        selection={selection}
        onSelect={setSelection}
        onLayoutChange={(next) => {
          setLayout(next);
          setLayoutEvents((value) => value + 1);
        }}
        onCommandRequested={() => setCommands((value) => value + 1)}
        onExpandRequested={() => setExpansions((value) => value + 1)}
      />
      <dl aria-label="浏览器动作回执">
        <dt>选择</dt>
        <dd data-testid="selection">{selection ? JSON.stringify(selection) : 'none'}</dd>
        <dt>布局修订</dt>
        <dd data-testid="layout-revision">{layout.layout_revision}</dd>
        <dt>布局回调</dt>
        <dd data-testid="layout-events">{layoutEvents}</dd>
        <dt>领域命令</dt>
        <dd data-testid="command-events">{commands}</dd>
        <dt>展开</dt>
        <dd data-testid="expand-events">{expansions}</dd>
      </dl>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AppearanceProvider>
        <Fixture />
      </AppearanceProvider>
    </BrowserRouter>
  </StrictMode>,
);

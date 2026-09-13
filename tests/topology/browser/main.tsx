import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AppearanceProvider } from '../../../apps/web/src/Appearance';
import {
  TopologyContainer,
  type TopologySnapshotReader,
} from '../../../apps/web/src/features/topology/TopologyContainer';
import { TopologyFlowCanvas } from '../../../apps/web/src/features/topology/TopologyFlowCanvas';
import type {
  LayoutPreference,
  TopologySelection,
  TopologySnapshotInput,
  ViewMode,
} from '../../../apps/web/src/features/topology/contracts';
import { layout as layoutFixture, snapshot as snapshotFixture } from '../fixtures';

function snapshotForTask(taskId: 'A' | 'B'): TopologySnapshotInput {
  const fixed = structuredClone(snapshotFixture) as TopologySnapshotInput;
  return {
    ...fixed,
    view_id: `view-task-${taskId.toLowerCase()}`,
    snapshot_id: `snapshot-task-${taskId.toLowerCase()}`,
    query_digest: `sha256:query-task-${taskId.toLowerCase()}`,
    access_scope_digest: `sha256:scope-task-${taskId.toLowerCase()}`,
    nodes: fixed.nodes.map((node) => node.ref.entity_type === 'origin'
      ? { ...node, label: `任务 ${taskId} 授权入口` }
      : node),
  };
}

function deferredSnapshot() {
  let resolve!: (snapshot: TopologySnapshotInput) => void;
  const promise = new Promise<TopologySnapshotInput>((accept) => {
    resolve = accept;
  });
  return { promise, resolve };
}

const taskA = snapshotForTask('A');
const taskB = snapshotForTask('B');
const delayedA = deferredSnapshot();
const delayedB = deferredSnapshot();
const initialReader: TopologySnapshotReader = async () => taskA;
const delayedReader: TopologySnapshotReader = async (taskId) => (
  taskId === 'task-a' ? delayedA.promise : delayedB.promise
);

function RequestIsolationFixture() {
  const [taskId, setTaskId] = useState('task-a');
  const [reader, setReader] = useState<TopologySnapshotReader>(() => initialReader);

  return (
    <main style={{ minHeight: '100vh', padding: 20, background: 'var(--canvas)', color: 'var(--text)' }}>
      <header>
        <h1>请求维度隔离</h1>
        <button type="button" onClick={() => setReader(() => delayedReader)}>更换读取器</button>
        <button type="button" onClick={() => setTaskId('task-b')}>切换任务 B</button>
        <button type="button" onClick={() => delayedA.resolve(taskA)}>完成旧任务 A 请求</button>
        <button type="button" onClick={() => delayedB.resolve(taskB)}>完成任务 B 请求</button>
      </header>
      <TopologyContainer taskId={taskId} mode="live" readSnapshot={reader} />
    </main>
  );
}

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

function BrowserFixture() {
  return new URLSearchParams(window.location.search).get('case') === 'request-isolation'
    ? <RequestIsolationFixture />
    : <Fixture />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AppearanceProvider>
        <BrowserFixture />
      </AppearanceProvider>
    </BrowserRouter>
  </StrictMode>,
);

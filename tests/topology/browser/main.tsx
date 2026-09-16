import { StrictMode, useCallback, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AppearanceProvider } from '../../../apps/web/src/Appearance';
import {
  TopologyContainer,
  type TopologySnapshotReader,
} from '../../../apps/web/src/features/topology/TopologyContainer';
import {
  LayoutRequestError,
  type LayoutReader,
  type LayoutWriter,
} from '../../../apps/web/src/features/topology/layoutApi';
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
      <TopologyContainer taskId={taskId} mode="live" readSnapshot={reader} persistLayout={false} />
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


function layoutServerSeed(): LayoutPreference {
  return {
    schema_version: 'wuji.api.v2',
    view_name: 'knowledge-live',
    layout_revision: '4',
    selection_mode: 'follow_latest',
    entries: [
      { anchor: { entity_type: 'intent', id: 'intent-1', revision: '4' }, x: 850, y: 480, pinned: false },
    ],
    viewport: { x: 16, y: 20, zoom: 0.72 },
  } as LayoutPreference;
}

function LayoutConflictFixture() {
  const serverRef = useRef<LayoutPreference>(layoutServerSeed());
  const [server, setServer] = useState<LayoutPreference>(() => structuredClone(serverRef.current));
  const [attempts, setAttempts] = useState(0);
  const [status, setStatus] = useState('none');

  const readLayout: LayoutReader = useCallback(async () => structuredClone(serverRef.current), []);
  const writeLayout: LayoutWriter = useCallback(async (_taskId, viewName, patch, expectedRevision) => {
    setAttempts((value) => value + 1);
    const current = serverRef.current;
    if (expectedRevision !== current.layout_revision) {
      setStatus(`409 stale ${expectedRevision} != ${current.layout_revision}`);
      throw new LayoutRequestError(409, 'stale', 'STALE_VERSION');
    }
    const next: LayoutPreference = {
      schema_version: 'wuji.api.v2',
      view_name: viewName,
      layout_revision: String(Number(current.layout_revision) + 1),
      selection_mode: patch.selection_mode,
      entries: patch.entries,
      viewport: patch.viewport,
    } as LayoutPreference;
    serverRef.current = next;
    setServer(structuredClone(next));
    setStatus(`200 ${next.layout_revision}`);
    return { view_name: viewName, layout_revision: next.layout_revision, request_id: 'fixture' };
  }, []);

  return (
    <main style={{ minHeight: '100vh', padding: 20, background: 'var(--canvas)', color: 'var(--text)' }}>
      <header>
        <h1>个人布局冲突</h1>
        <button
          type="button"
          onClick={() => {
            const current = serverRef.current;
            const next: LayoutPreference = {
              ...current,
              layout_revision: String(Number(current.layout_revision) + 1),
              entries: current.entries.map((entry) => ({ ...entry, x: entry.x + 25, y: entry.y - 15 })),
              viewport: { x: -10, y: 20, zoom: 0.9 },
            } as LayoutPreference;
            serverRef.current = next;
            setServer(structuredClone(next));
            setStatus('other-tab');
          }}
        >其他标签页保存</button>
      </header>
      <TopologyContainer
        taskId="task-conflict"
        mode="live"
        readSnapshot={initialReader}
        readLayout={readLayout}
        writeLayout={writeLayout}
      />
      <dl aria-label="布局服务回执">
        <dt>服务端修订</dt>
        <dd data-testid="server-revision">{server.layout_revision}</dd>
        <dt>服务端布局</dt>
        <dd data-testid="server-layout">{JSON.stringify(server)}</dd>
        <dt>写入次数</dt>
        <dd data-testid="write-attempts">{attempts}</dd>
        <dt>最后状态</dt>
        <dd data-testid="write-status">{status}</dd>
      </dl>
    </main>
  );
}

function LayoutReloadFailureFixture() {
  const [taskId, setTaskId] = useState<'A' | 'B'>('A');
  const serverRef = useRef<LayoutPreference>(layoutServerSeed());
  // The first page load reads normally; the recovery read after a conflict is
  // the one that fails until the operator allows it again.
  const readFailsRef = useRef(false);
  const [server, setServer] = useState<LayoutPreference>(() => structuredClone(serverRef.current));
  const [writeAttempts, setWriteAttempts] = useState(0);
  const [readAttempts, setReadAttempts] = useState(0);
  const [writeStatus, setWriteStatus] = useState('none');
  const [readStatus, setReadStatus] = useState('none');

  const readLayout: LayoutReader = useCallback(async (requestedTaskId: string) => {
    setReadAttempts((value) => value + 1);
    if (readFailsRef.current) {
      setReadStatus(`503 ${requestedTaskId}`);
      throw new LayoutRequestError(503, '布局读取暂时不可用。', 'CAPABILITY_UNAVAILABLE');
    }
    setReadStatus(`200 ${requestedTaskId}`);
    return structuredClone(serverRef.current);
  }, []);

  const writeLayout: LayoutWriter = useCallback(async (requestedTaskId, viewName, patch, expectedRevision) => {
    setWriteAttempts((value) => value + 1);
    const current = serverRef.current;
    if (expectedRevision !== current.layout_revision) {
      setWriteStatus(`409 ${requestedTaskId}`);
      throw new LayoutRequestError(409, '布局版本过期。', 'STALE_VERSION');
    }
    const next: LayoutPreference = {
      schema_version: 'wuji.api.v2',
      view_name: viewName,
      layout_revision: String(Number(current.layout_revision) + 1),
      selection_mode: patch.selection_mode,
      entries: patch.entries,
      viewport: patch.viewport,
    } as LayoutPreference;
    serverRef.current = next;
    setServer(structuredClone(next));
    setWriteStatus(`200 ${requestedTaskId}`);
    return { view_name: viewName, layout_revision: next.layout_revision, request_id: 'fixture' };
  }, []);

  return (
    <main style={{ minHeight: '100vh', padding: 20, background: 'var(--canvas)', color: 'var(--text)' }}>
      <header>
        <h1>布局重读失败</h1>
        <button
          type="button"
          onClick={() => {
            readFailsRef.current = true;
            const current = serverRef.current;
            const next: LayoutPreference = {
              ...current,
              layout_revision: String(Number(current.layout_revision) + 1),
              entries: current.entries.map((entry) => ({ ...entry, x: entry.x + 25, y: entry.y - 15 })),
            } as LayoutPreference;
            serverRef.current = next;
            setServer(structuredClone(next));
          }}
        >其他标签页保存</button>
        <button type="button" onClick={() => { readFailsRef.current = false; }}>允许读取</button>
        <button type="button" onClick={() => setTaskId((value) => (value === 'A' ? 'B' : 'A'))}>切换任务</button>
      </header>
      <TopologyContainer
        key={taskId}
        taskId={`task-${taskId}`}
        mode="live"
        readSnapshot={initialReader}
        readLayout={readLayout}
        writeLayout={writeLayout}
      />
      <dl aria-label="布局故障回执">
        <dt>服务端修订</dt>
        <dd data-testid="fault-server-revision">{server.layout_revision}</dd>
        <dt>服务端布局</dt>
        <dd data-testid="fault-server-layout">{JSON.stringify(server)}</dd>
        <dt>写入次数</dt>
        <dd data-testid="fault-write-attempts">{writeAttempts}</dd>
        <dt>写入回执</dt>
        <dd data-testid="fault-write-status">{writeStatus}</dd>
        <dt>读取次数</dt>
        <dd data-testid="fault-read-attempts">{readAttempts}</dd>
        <dt>读取回执</dt>
        <dd data-testid="fault-read-status">{readStatus}</dd>
      </dl>
    </main>
  );
}

function BrowserFixture() {
  const fixtureCase = new URLSearchParams(window.location.search).get('case');
  if (fixtureCase === 'request-isolation') return <RequestIsolationFixture />;
  if (fixtureCase === 'layout-conflict') return <LayoutConflictFixture />;
  if (fixtureCase === 'layout-reload-failure') return <LayoutReloadFailureFixture />;
  return <Fixture />;
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

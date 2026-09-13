import type {
  KnowledgeRef,
  LayoutPreference,
  TopologyCommandRequest,
  TopologyExpandRequest,
  TopologySelection,
  TopologySnapshotInput,
  ViewMode,
} from './contracts';
import { resolveSelectedNodeId } from './toFlowElements';
import styles from './topology.module.css';

interface TopologyListViewProps {
  readonly snapshot: TopologySnapshotInput;
  readonly layout: LayoutPreference;
  readonly mode: ViewMode;
  readonly selection: TopologySelection | null;
  readonly onSelect: (selection: TopologySelection | null) => void;
  readonly onCommandRequested: (request: TopologyCommandRequest) => void;
  readonly onExpandRequested: (request: TopologyExpandRequest) => void;
}

function selectionForRef(
  ref: KnowledgeRef,
  selectionMode: LayoutPreference['selection_mode'],
): TopologySelection {
  return selectionMode === 'follow_latest'
    ? { mode: 'follow_latest', anchor: { entity_type: ref.entity_type, id: ref.id } }
    : { mode: 'explicit_revision', ref: { ...ref } };
}

export function TopologyListView({
  snapshot,
  layout,
  mode,
  selection,
  onSelect,
  onCommandRequested,
  onExpandRequested,
}: TopologyListViewProps) {
  const selectedId = resolveSelectedNodeId(snapshot, selection);

  return (
    <div className={styles.listView} role="region" aria-label="任务拓扑列表">
      <ol className={styles.nodeList}>
        {snapshot.nodes.map((node) => {
          const activate = () => onSelect(selectionForRef(node.ref, layout.selection_mode));
          const actions = mode === 'history' ? [] : node.allowed_actions ?? [];
          return (
            <li key={node.id} className={styles.listItem}>
              <button
                type="button"
                className={styles.listSelect}
                aria-pressed={selectedId === node.id}
                aria-label={`${node.display_kind} · ${node.label}`}
                onClick={activate}
              >
                <span className={styles.kind}>{node.display_kind}</span>
                <strong>{node.label}</strong>
                <code>{node.ref.entity_type}:{node.ref.id}@{node.ref.revision}</code>
                <span className={styles.state}>{node.state ?? '未标注状态'}</span>
              </button>
              {actions.includes('expand') && (
                <button
                  type="button"
                  className={styles.inlineAction}
                  onClick={() => onExpandRequested({ ref: { ...node.ref } })}
                >展开关联</button>
              )}
              {actions.filter((action) => action !== 'expand' && action !== 'inspect').map((action) => (
                <button
                  type="button"
                  className={styles.inlineAction}
                  key={action}
                  onClick={() => onCommandRequested({ action, ref: { ...node.ref } })}
                >执行 {action}</button>
              ))}
            </li>
          );
        })}
      </ol>
      <section className={styles.relationList} aria-labelledby="topology-relations-title">
        <h3 id="topology-relations-title">关系</h3>
        {snapshot.edges.length === 0 ? <p>当前视图没有可见关系。</p> : (
          <ul>
            {snapshot.edges.map((edge) => (
              <li key={edge.id}>
                <code>{edge.source}</code>
                <span aria-hidden="true">→</span>
                <code>{edge.target}</code>
                <span>{edge.label ?? edge.edge_type}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

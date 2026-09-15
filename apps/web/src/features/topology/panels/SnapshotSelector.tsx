import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Select, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { apiUrl } from '../../../config';
import type { SnapshotIndex, SnapshotSummary, ViewMode } from '../contracts';
import { parseSnapshotIndex, snapshotHistoryRequestPath } from '../history';
import styles from '../topology.module.css';

export interface ViewChoice {
  readonly mode: ViewMode;
  readonly snapshotId: string | null;
}

async function readSnapshotIndex(
  taskId: string,
  cursor: string | null,
  signal: AbortSignal,
): Promise<SnapshotIndex> {
  let response: Response;
  try {
    response = await fetch(apiUrl(snapshotHistoryRequestPath(taskId, cursor)), {
      credentials: 'include',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error('无法连接快照目录');
  }
  if (!response.ok) throw new Error(response.status === 410 ? '快照目录游标已过期' : '快照目录读取失败');
  return parseSnapshotIndex(await response.json());
}

function mergeSnapshots(
  current: readonly SnapshotSummary[],
  incoming: readonly SnapshotSummary[],
): SnapshotSummary[] {
  const byId = new Map(current.map((item) => [item.snapshot_id, item]));
  for (const item of incoming) byId.set(item.snapshot_id, item);
  return [...byId.values()].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

export interface SnapshotSelectorProps {
  readonly taskId: string;
  readonly value: ViewChoice;
  readonly onChange: (choice: ViewChoice) => void;
}

export function SnapshotSelector({ taskId, value, onChange }: SnapshotSelectorProps) {
  const [items, setItems] = useState<SnapshotSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);

  const load = async (nextCursor: string | null, replace: boolean) => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true);
    setError(null);
    try {
      const page = await readSnapshotIndex(taskId, nextCursor, controller.signal);
      if (controller.signal.aborted) return;
      setItems((current) => mergeSnapshots(replace ? [] : current, page.items));
      setCursor(page.opaque_cursor);
    } catch (reason) {
      if (!controller.signal.aborted) {
        setError(reason instanceof Error ? reason.message : '快照目录读取失败');
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  useEffect(() => {
    setItems([]);
    setCursor(null);
    void load(null, true);
    return () => active.current?.abort();
  }, [taskId]);

  const selected = value.mode === 'live' ? '__live__' : value.snapshotId ?? '__live__';
  const options = [
    { value: '__live__', label: '实时视图' },
    ...items.map((item) => ({
      value: item.snapshot_id,
      label: `${new Date(item.created_at).toLocaleString('zh-CN')} · ${item.snapshot_id.slice(0, 8)}`,
    })),
  ];

  return (
    <section className={styles.snapshotSelector} aria-label="拓扑时间选择">
      <div>
        <strong>视图时间</strong>
        <span>历史模式读取已保存 materialization，不跟随后续状态。</span>
      </div>
      <Select
        aria-label="选择拓扑快照"
        value={selected}
        options={options}
        loading={loading && items.length === 0}
        onChange={(next) => onChange(next === '__live__'
          ? { mode: 'live', snapshotId: null }
          : { mode: 'history', snapshotId: next })}
      />
      <Button
        icon={<ReloadOutlined />}
        loading={loading}
        onClick={() => void load(null, true)}
      >刷新目录</Button>
      {cursor && <Button loading={loading} onClick={() => void load(cursor, false)}>加载更多</Button>}
      <Tag color={value.mode === 'history' ? 'purple' : 'green'}>
        {value.mode === 'history' ? '历史只读' : '实时'}
      </Tag>
      {error && <Alert className={styles.snapshotError} showIcon type="warning" title={error} />}
    </section>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { Alert, Descriptions, Empty, Spin, Tag } from 'antd';
import { apiUrl } from '../../../config';
import type {
  KnowledgeRef,
  RecordView,
} from '../contracts';
import styles from '../topology.module.css';

import { parseRecordView, recordRequestPath } from '../record';

export class RecordReadError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'RecordReadError';
    this.status = status;
  }
}

export async function readRecordView(
  taskId: string,
  ref: KnowledgeRef,
  snapshotId: string,
  signal: AbortSignal,
): Promise<RecordView> {
  let response: Response;
  try {
    response = await fetch(apiUrl(recordRequestPath(taskId, ref, snapshotId)), {
      credentials: 'include',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new RecordReadError(0, '无法连接记录服务');
  }
  if (!response.ok) throw new RecordReadError(response.status, '记录读取未完成');
  try {
    return parseRecordView(await response.json(), ref);
  } catch (error) {
    if (error instanceof Error && error.message === '记录响应不符合固定契约') throw error;
    throw new Error('记录响应不符合固定契约');
  }
}

function errorCopy(error: unknown): { title: string; description: string } {
  if (error instanceof RecordReadError && error.status === 404) {
    return { title: '记录不可访问', description: '该固定修订不存在或当前身份已失去读取权限。' };
  }
  if (error instanceof RecordReadError && error.status === 410) {
    return { title: '快照已失效', description: '当前详情所属的历史快照已过期，请重新读取拓扑。' };
  }
  if (error instanceof Error && error.message === '记录响应不符合固定契约') {
    return { title: '记录响应无法确认', description: '页面没有使用格式不匹配的数据。' };
  }
  return { title: '记录读取失败', description: '当前节点详情暂时无法读取。' };
}

function summaryItems(record: Record<string, unknown>) {
  const preferred = [
    'name', 'question', 'title', 'summary', 'scenario', 'acceptance_state',
    'desired_state', 'observed_state', 'state', 'result_state', 'created_at',
  ];
  return preferred.flatMap((key) => {
    const value = record[key];
    if (!['string', 'number', 'boolean'].includes(typeof value)) return [];
    return [{ key, label: key, children: String(value) }];
  });
}

export interface RecordPanelProps {
  readonly taskId: string;
  readonly snapshotId: string | null;
  readonly ref: KnowledgeRef | null;
}

export function RecordPanel({ taskId, snapshotId, ref }: RecordPanelProps) {
  const [record, setRecord] = useState<RecordView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const refKey = ref ? `${ref.entity_type}:${ref.id}@${ref.revision}` : '';

  useEffect(() => {
    if (!ref || !snapshotId) {
      setRecord(null);
      setError(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setRecord(null);
    void readRecordView(taskId, ref, snapshotId, controller.signal).then((next) => {
      if (!controller.signal.aborted) setRecord(next);
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [refKey, snapshotId, taskId]);

  const copy = useMemo(() => errorCopy(error), [error]);
  if (!ref || !snapshotId) {
    return (
      <aside className={styles.recordPanel} aria-label="记录详情">
        <header><strong>记录详情</strong><span>固定快照</span></header>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择一个节点查看固定修订" />
      </aside>
    );
  }
  if (loading) {
    return (
      <aside className={styles.recordPanel} aria-label="记录详情">
        <header><strong>记录详情</strong><span>{ref.entity_type}@{ref.revision}</span></header>
        <div className={styles.recordStatus}><Spin description="正在读取固定记录" /></div>
      </aside>
    );
  }
  if (!record) {
    return (
      <aside className={styles.recordPanel} aria-label="记录详情">
        <header><strong>记录详情</strong><span>{ref.entity_type}@{ref.revision}</span></header>
        <Alert showIcon type="warning" title={copy.title} description={copy.description} />
      </aside>
    );
  }

  const body = record.record as unknown as Record<string, unknown>;
  return (
    <aside className={styles.recordPanel} aria-label="记录详情">
      <header>
        <div><strong>记录详情</strong><span>{record.ref.id}@{record.ref.revision}</span></div>
        <Tag color="blue">{record.display_kind}</Tag>
      </header>
      <Descriptions
        className={styles.recordSummary}
        size="small"
        bordered
        column={1}
        items={summaryItems(body)}
      />
      {record.assessment && (
        <section className={styles.recordAssessment}>
          <h3>评估</h3>
          <pre>{JSON.stringify(record.assessment, null, 2)}</pre>
        </section>
      )}
      <section className={styles.recordDocument}>
        <h3>公开记录</h3>
        <pre>{JSON.stringify(body, null, 2)}</pre>
      </section>
    </aside>
  );
}

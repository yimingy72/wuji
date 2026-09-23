import { useEffect, useState } from 'react';
import { Alert, Button, Empty, Select, Spin, Tag } from 'antd';
import {
  downloadArtifact, downloadCapturePart, readCaptureItems, readCaptureSessions,
  readCommandInventory, readPublications,
  type CommandInventoryItem, type PublicationInventoryItem,
  type RuntimeCaptureItemPageV1, type RuntimeCaptureSessionPageV1,
} from '../../v2WorkbenchApi';
import styles from './firstUseWorkbench.module.css';

const COMMAND_STATE: Record<CommandInventoryItem['state'], string> = {
  prepared: '已准备', running: '运行中', stopping: '正在停止',
  exited: '已结束', unknown: '待核对',
};

function save(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function message(reason: unknown) {
  return reason instanceof Error ? reason.message : '读取暂时不可用';
}

export function CommandInventory({ taskId }: { readonly taskId: string }) {
  const [items, setItems] = useState<readonly CommandInventoryItem[]>([]);
  const [after, setAfter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const load = async (cursor: string | null, signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const page = await readCommandInventory(taskId, cursor, signal);
      if (!signal.aborted) {
        setItems((current) => cursor ? [...current, ...page.items] : page.items);
        setAfter(page.next_after);
      }
    } catch (reason) {
      if (!signal.aborted) setError(message(reason));
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  };
  useEffect(() => {
    const controller = new AbortController();
    void load(null, controller.signal);
    return () => controller.abort();
  }, [taskId]);

  return <div className={styles.inventory}>
    <Button size="small" loading={loading} onClick={() => void load(null, new AbortController().signal)}>刷新命令</Button>
    {error && <Alert showIcon type="warning" title="命令读取失败" description={error} />}
    {downloadError && <Alert showIcon type="warning" title="输出下载失败" description={downloadError} />}
    {loading && items.length === 0 ? <Spin description="正在读取命令" /> : items.length === 0 ? <Empty description="当前没有命令记录" /> : <ol className={styles.inventoryList}>{items.map((item) => <li key={item.exec_id}>
      <details><summary><span><Tag>{COMMAND_STATE[item.state]}</Tag><strong>{item.command}</strong></span><span>退出码 {item.exit_code ?? '待确认'}</span></summary>
        <p>工作 {item.work_item_id} · 输出 {item.output_completeness} · 来源：执行端报告</p>
        {item.output_refs.map((ref) => <Button key={`${ref.id}:${ref.version}`} size="small" onClick={() => void downloadArtifact(ref.id, ref.version, new AbortController().signal).then((blob) => save(blob, `command-${item.exec_id}-${ref.id}.json`)).catch((reason: unknown) => setDownloadError(message(reason)))}>下载命令记录</Button>)}
      </details>
    </li>)}</ol>}
    {after && <Button loading={loading} onClick={() => void load(after, new AbortController().signal)}>加载更多命令</Button>}
  </div>;
}

export function PublicationInventory({ taskId }: { readonly taskId: string }) {
  const [items, setItems] = useState<readonly PublicationInventoryItem[]>([]);
  const [after, setAfter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const load = async (cursor: string | null, signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const page = await readPublications(taskId, cursor, signal);
      if (!signal.aborted) {
        setItems((current) => cursor ? [...current, ...page.items] : page.items);
        setAfter(page.next_after);
      }
    } catch (reason) {
      if (!signal.aborted) setError(message(reason));
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  };
  useEffect(() => {
    const controller = new AbortController();
    void load(null, controller.signal);
    return () => controller.abort();
  }, [taskId]);

  return <div className={styles.inventory}>
    <Button size="small" loading={loading} onClick={() => void load(null, new AbortController().signal)}>刷新共享版本</Button>
    {error && <Alert showIcon type="warning" title="共享版本读取失败" description={error} />}
    {downloadError && <Alert showIcon type="warning" title="共享清单下载失败" description={downloadError} />}
    {loading && items.length === 0 ? <Spin description="正在读取共享版本" /> : items.length === 0 ? <Empty description="当前没有已发布的共享版本" /> : <ol className={styles.inventoryList}>{items.map((item) => <li key={item.publication_id}>
      <strong>{item.asset_id} · 版本 {item.asset_revision}</strong>
      <span>工作 {item.producer_work_item_id} · {new Date(item.created_at).toLocaleString('zh-CN')}</span>
      <Button size="small" onClick={() => void downloadArtifact(item.manifest_ref.id, item.manifest_ref.version, new AbortController().signal).then((blob) => save(blob, `publication-${item.asset_id}-${item.asset_revision}.json`)).catch((reason: unknown) => setDownloadError(message(reason)))}>下载版本清单</Button>
    </li>)}</ol>}
    {after && <Button loading={loading} onClick={() => void load(after, new AbortController().signal)}>加载更多版本</Button>}
  </div>;
}

export function CaptureInventory({ taskId, focusArtifactRef }: { readonly taskId: string; readonly focusArtifactRef?: { id: string; version: string } | null }) {
  const [sessions, setSessions] = useState<RuntimeCaptureSessionPageV1['sessions']>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [items, setItems] = useState<RuntimeCaptureItemPageV1['items']>([]);
  const [after, setAfter] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    void readCaptureSessions(taskId, controller.signal).then((page) => {
      if (!controller.signal.aborted) {
        setSessions(page.sessions);
        setSessionId(page.sessions[0]?.capture_session_id ?? null);
      }
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(message(reason));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [taskId]);

  const load = async (id: string, cursor: number, signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const page = await readCaptureItems(taskId, id, cursor, signal);
      if (!signal.aborted) {
        setItems((current) => cursor ? [...current, ...page.items] : page.items);
        setAfter(page.next_item_seq);
      }
    } catch (reason) {
      if (!signal.aborted) setError(message(reason));
    } finally { if (!signal.aborted) setLoading(false); }
  };
  useEffect(() => {
    if (!sessionId) return;
    const controller = new AbortController();
    setItems([]);
    setAfter(null);
    void load(sessionId, 0, controller.signal);
    return () => controller.abort();
  }, [taskId, sessionId]);

  useEffect(() => {
    if (!focusArtifactRef || !sessionId) return;
    const item = items.find(({ artifact_refs }) => artifact_refs.some((ref) => ref.id === focusArtifactRef.id && ref.version === focusArtifactRef.version));
    if (item) document.getElementById(`capture-${taskId}-${sessionId}-${item.envelope.item_seq}`)?.scrollIntoView({ block: 'nearest' });
  }, [taskId, sessionId, items, focusArtifactRef?.id, focusArtifactRef?.version]);

  const selected = sessions.find((session) => session.capture_session_id === sessionId);
  const focusFound = !focusArtifactRef || items.some(({ artifact_refs }) => artifact_refs.some((ref) => ref.id === focusArtifactRef.id && ref.version === focusArtifactRef.version));
  return <div className={styles.inventory}>
    {sessionId && <Button size="small" loading={loading} onClick={() => void load(sessionId, 0, new AbortController().signal)}>刷新采集</Button>}
    {error && <Alert showIcon type="warning" title="采集读取失败" description={error} />}
    {focusArtifactRef && !focusFound && !loading && sessions.length > 0 && <Alert showIcon type="info" title="当前采集页未找到该材料" description={after === null ? '请切换采集批次查找原始文件。' : '请加载更多采集记录，或切换批次查找原始文件。'} />}
    {sessions.length > 0 && <div className={styles.inventoryHeader}><Select aria-label="采集批次" value={sessionId} onChange={setSessionId} options={sessions.map((session) => ({ value: session.capture_session_id, label: `批次 ${session.binding.runtime_attempt} · ${session.state}` }))} /><Tag>{selected?.state}</Tag></div>}
    {loading && items.length === 0 ? <Spin description="正在读取采集记录" /> : items.length === 0 ? <Empty description={sessions.length ? '这个批次暂无采集记录' : '当前没有采集批次'} /> : <ol className={styles.inventoryList}>{items.map(({ envelope, artifact_refs }) => {
      const method = typeof envelope.metadata.method === 'string' ? envelope.metadata.method : 'HTTP';
      const url = typeof envelope.metadata.url === 'string' ? envelope.metadata.url : `交换 ${envelope.metadata.exchange_id ?? envelope.item_seq}`;
      const status = typeof envelope.metadata.status_code === 'number' ? envelope.metadata.status_code : null;
      const focused = Boolean(focusArtifactRef && artifact_refs.some((ref) => ref.id === focusArtifactRef.id && ref.version === focusArtifactRef.version));
      return <li key={envelope.item_seq} id={`capture-${taskId}-${sessionId}-${envelope.item_seq}`}>
        <div className={styles.inventoryHeader}><Tag>{envelope.kind === 'http_exchange' ? `${method} ${status ?? '待确认'}` : envelope.kind === 'pcap_segment' ? 'PCAP' : envelope.kind === 'gap' ? '采集缺口' : '采集清单'}</Tag><strong>{envelope.kind === 'http_exchange' ? url : envelope.kind === 'pcap_segment' ? String(envelope.metadata.segment_name ?? `分段 ${envelope.item_seq}`) : envelope.conditions.join('、') || `记录 ${envelope.item_seq}`}</strong><span>{envelope.completeness}</span>{focused && <Tag color="blue">对应材料</Tag>}</div>
        {envelope.parts.length > 0 && <details open={focused}><summary>下载原始数据（{envelope.parts.length} 项）</summary><div className={styles.inventoryParts}>{envelope.parts.map((part) => <Button key={part.part} size="small" onClick={() => void downloadCapturePart(taskId, sessionId!, envelope.item_seq, part.part, new AbortController().signal).then((blob) => save(blob, `capture-${envelope.item_seq}-${part.part}`)).catch((reason: unknown) => setError(message(reason)))}>{part.part} · {part.length} bytes</Button>)}</div></details>}
      </li>;
    })}</ol>}
    {sessionId && after !== null && <Button loading={loading} onClick={() => void load(sessionId, after, new AbortController().signal)}>加载更多采集记录</Button>}
  </div>;
}

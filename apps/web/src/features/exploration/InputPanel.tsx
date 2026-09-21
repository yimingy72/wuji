import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Input, Spin, Tag, Typography } from 'antd';
import { ApiRequestError } from '../../api';
import { answerTaskInput, readTaskInputs, type TaskInputListV1 } from '../../v2WorkbenchApi';

interface InputPanelProps {
  readonly taskId: string;
  readonly csrfToken?: string | null;
  readonly refreshKey: number;
  readonly onChanged: () => void;
  readonly onSessionExpired: () => void;
}

export function InputPanel({ taskId, csrfToken, refreshKey, onChanged, onSessionExpired }: InputPanelProps) {
  const [inputs, setInputs] = useState<TaskInputListV1 | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const keys = useRef(new Map<string, string>());

  useEffect(() => {
    const controller = new AbortController();
    setInputs(null);
    setError(null);
    void readTaskInputs(taskId, controller.signal).then(setInputs).catch((reason: unknown) => {
      if (controller.signal.aborted) return;
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setError(reason instanceof Error ? reason.message : '待补充信息读取失败');
    });
    return () => controller.abort();
  }, [taskId, refreshKey, onSessionExpired]);

  const submit = async (inputRequestId: string) => {
    const text = answers[inputRequestId]?.trim();
    if (!text || busy) return;
    const key = keys.current.get(inputRequestId) ?? crypto.randomUUID();
    keys.current.set(inputRequestId, key);
    setBusy(inputRequestId);
    setError(null);
    try {
      await answerTaskInput(inputRequestId, text, key, csrfToken, new AbortController().signal);
      onChanged();
    } catch (reason) {
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setError(reason instanceof Error ? reason.message : '补充信息提交失败');
    } finally {
      setBusy(null);
    }
  };

  if (error) return <Alert showIcon type="warning" title="补充信息未完成" description={error} />;
  if (!inputs) return <Spin description="正在核对待补充信息" />;
  if (inputs.items.length === 0) return null;
  return <section aria-label="待补充信息">
    <Typography.Title level={5}>待补充信息</Typography.Title>
    {inputs.items.map((item) => <div key={item.input_request_id} style={{ display: 'grid', gap: 8, marginBottom: 12 }}>
      <div><Tag>{item.kind}</Tag><Typography.Text>{item.prompt}</Typography.Text></div>
      {item.kind === 'question' ? <>
        <Input.TextArea rows={3} value={answers[item.input_request_id] ?? ''} onChange={(event) => setAnswers((current) => ({ ...current, [item.input_request_id]: event.target.value }))} maxLength={32768} aria-label={`回答 ${item.prompt}`} />
        <Button type="primary" loading={busy === item.input_request_id} disabled={!answers[item.input_request_id]?.trim()} onClick={() => void submit(item.input_request_id)}>提交补充信息</Button>
      </> : <Typography.Text type="secondary">审批必须通过受控审批入口处理，文本不会改变权限或 Scope。</Typography.Text>}
    </div>)}
  </section>;
}

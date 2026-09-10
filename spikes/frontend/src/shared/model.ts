export type DemoMode = 'http' | 'agent';
export type DemoTaskState = 'ready' | 'queued' | 'running' | 'pausing' | 'paused' | 'cancelling' | 'cancelled' | 'completed';

export type PrototypeDraft = {
  mode: DemoMode;
  name: string;
  goal: string;
  completion: string;
  target: string;
  includePath: string;
  excludePath: string;
  reference: string;
  identity: string;
  modelProfile: string;
  environment: string;
  duration: number;
  requests: number;
  tokens: number;
};

const drafts: Record<DemoMode, PrototypeDraft> = {
  http: {
    mode: 'http', name: 'app.example.test · HTTP 观察',
    goal: '记录入口响应配置和公开内容，列出证据与未检查部分。',
    completion: '保存一次受控响应及范围内可确认的配置事实。',
    target: 'https://app.example.test/public/', includePath: '/public/', excludePath: '/admin/, /account/',
    reference: '无资料', identity: '匿名访问', modelProfile: '不使用模型', environment: '项目受管 HTTP 环境',
    duration: 60, requests: 20, tokens: 0,
  },
  agent: {
    mode: 'agent', name: 'app.example.test · Web 观察评估',
    goal: '梳理公开入口与测试身份可见页面，验证响应边界，记录风险线索、依据和未覆盖项。',
    completion: '完成 5 项计划检查，所有结论关联证据，受阻项明确列出。',
    target: 'https://app.example.test/', includePath: '/', excludePath: '/admin/delete/, /billing/write/',
    reference: 'Example API 说明 · v3.2（演示）', identity: '审阅者测试身份（演示引用）',
    modelProfile: '项目分析方案 · v2（规划演示）', environment: '隔离 Web 评估环境（演示）',
    duration: 900, requests: 120, tokens: 80000,
  },
};

const fixtureDrafts = structuredClone(drafts);

let activeTask: { id: string; draft: PrototypeDraft; createdAt: string; relatedTo?: string } | null = null;
let savedDraftMode: DemoMode | null = null;

export const stateLabel: Record<DemoTaskState, string> = {
  ready: '待启动', queued: '排队中', running: '执行中', pausing: '暂停中', paused: '已暂停',
  cancelling: '取消中', cancelled: '已取消', completed: '已完成',
};

export function getDraft(mode: DemoMode): PrototypeDraft {
  return structuredClone(drafts[mode]);
}

export function updateDraft(mode: DemoMode, next: PrototypeDraft) {
  drafts[mode] = structuredClone(next);
}

export function saveDraft(mode: DemoMode) {
  savedDraftMode = mode;
}

export function getSavedDraftMode() {
  return savedDraftMode;
}

export function createTask(draft: PrototypeDraft, relatedTo?: string) {
  activeTask = { id: draft.mode === 'http' ? 'DEMO-HTTP-1084' : 'DEMO-AGENT-2047', draft: structuredClone(draft), createdAt: '2026-09-10 14:32', relatedTo };
  return activeTask;
}

export function getTask(mode: DemoMode, taskId?: string) {
  if (activeTask?.draft.mode === mode && (!taskId || activeTask.id === taskId)) return structuredClone(activeTask);
  const draft = structuredClone(fixtureDrafts[mode]);
  return {
    id: mode === 'http' ? 'DEMO-HTTP-1042' : 'DEMO-AGENT-2031',
    draft,
    createdAt: '2026-09-10 14:18',
    relatedTo: mode === 'agent' ? 'DEMO-AGENT-1988' : undefined,
  };
}

export type DemoEvidence = {
  id: string;
  title: string;
  kind: 'response' | 'observation' | 'decision';
  source: string;
  capturedAt: string;
  body: string;
  note: string;
};

export const evidence: Record<string, DemoEvidence> = {
  response: {
    id: 'EVD-7A21', title: '入口响应', kind: 'response', source: '受控 GET · /public/', capturedAt: '14:34:08',
    body: 'HTTP/1.1 200 OK\ncontent-type: text/html; charset=utf-8\ncontent-security-policy: default-src \'self\'\nx-content-type-options: nosniff\n\n<!doctype html>\n<title>Example Test App</title>\n<main>Public test fixture</main>',
    note: '合成响应；敏感字段已省略。',
  },
  surface: {
    id: 'EVD-7A2C', title: '公开入口观察', kind: 'observation', source: '计划项 02 · 页面边界', capturedAt: '14:35:12',
    body: '观察事实\n\n/public/ 返回公开夹具页面。\n/account/ 返回 401，未进入身份验证流程。\n/admin/delete/ 被任务范围排除，未请求。',
    note: '事实与未覆盖项分开记录。',
  },
  decision: {
    id: 'EVD-7A39', title: '计划调整依据', kind: 'decision', source: '操作员回答 · 问题 Q-03', capturedAt: '14:36:40',
    body: '操作员选择：保持只读观察。\n\n计划变更：跳过需要写入测试数据的验证项；新增“限制”记录，不扩大方法或授权范围。',
    note: '回答只澄清当前目标，未改变权限。',
  },
};

export const recoveryStorageKey = 'wuji.prototype.synthetic-recovery.v1';
const recoveryRecord = { kind: 'create', commandId: 'CMD-DEMO-0007', taskId: 'DEMO-REC-1007', mode: 'http', createdAt: '2026-09-10T14:40:00+08:00' } as const;

export function beginSyntheticRecovery() {
  try {
    sessionStorage.setItem(recoveryStorageKey, JSON.stringify(recoveryRecord));
    return true;
  } catch {
    return false;
  }
}

export function readSyntheticRecovery() {
  try {
    const saved = sessionStorage.getItem(recoveryStorageKey);
    if (saved) {
      const parsed = JSON.parse(saved) as Partial<typeof recoveryRecord>;
      if (parsed.commandId === recoveryRecord.commandId && parsed.taskId === recoveryRecord.taskId && parsed.kind === recoveryRecord.kind && parsed.mode === recoveryRecord.mode) return recoveryRecord;
    }
  } catch { /* Treat unavailable or malformed storage as no record. */ }
  return null;
}

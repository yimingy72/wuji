import { apiUrl } from '../../config';
import type {
  LayoutAnchor,
  LayoutEntry,
  LayoutPatch,
  LayoutPreference,
  LayoutReceipt,
  ViewMode,
  ViewSelectionMode,
} from './contracts';

const revisionPattern = /^(0|[1-9][0-9]*)$/;
const entityTypes = new Set([
  'origin', 'goal', 'observation', 'artifact', 'claim', 'intent',
  'work_item', 'agent_run', 'verification', 'completion_review', 'finding', 'report',
]);
const layoutViews = new Set(['knowledge-live', 'knowledge-history']);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(value: Record<string, unknown>, keys: ReadonlySet<string>): boolean {
  return Object.keys(value).every((key) => keys.has(key));
}

function isFiniteBoundedNumber(value: unknown, minimum: number, maximum: number): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= minimum && value <= maximum;
}

function isAnchor(value: unknown): value is LayoutAnchor {
  if (!isRecord(value) || !hasOnlyKeys(value, new Set(['entity_type', 'id', 'revision']))) return false;
  return typeof value.entity_type === 'string'
    && entityTypes.has(value.entity_type)
    && typeof value.id === 'string'
    && value.id.length > 0
    && value.id.length <= 256
    && (value.revision === undefined || value.revision === null
      || (typeof value.revision === 'string' && revisionPattern.test(value.revision)));
}

function isEntry(value: unknown): value is LayoutEntry {
  if (!isRecord(value) || !hasOnlyKeys(value, new Set(['anchor', 'x', 'y', 'pinned']))) return false;
  return isAnchor(value.anchor)
    && isFiniteBoundedNumber(value.x, -10_000_000, 10_000_000)
    && isFiniteBoundedNumber(value.y, -10_000_000, 10_000_000)
    && typeof value.pinned === 'boolean';
}

function isViewport(value: unknown): value is LayoutPreference['viewport'] {
  return isRecord(value)
    && Object.keys(value).length === 3
    && isFiniteBoundedNumber(value.x, -10_000_000, 10_000_000)
    && isFiniteBoundedNumber(value.y, -10_000_000, 10_000_000)
    && isFiniteBoundedNumber(value.zoom, 0.2, 2.0);
}

function expectedSelectionMode(viewName: string): ViewSelectionMode {
  if (viewName === 'knowledge-live') return 'follow_latest';
  if (viewName === 'knowledge-history') return 'explicit_revision';
  throw new Error('不支持的布局视图');
}

export function layoutViewName(mode: ViewMode): string {
  return mode === 'history' ? 'knowledge-history' : 'knowledge-live';
}

export function layoutRequestPath(taskId: string, viewName: string): string {
  return `/api/v2/tasks/${encodeURIComponent(taskId)}/layouts/${encodeURIComponent(viewName)}`;
}

export function parseLayoutPreference(value: unknown, expectedViewName: string): LayoutPreference {
  if (!isRecord(value) || !layoutViews.has(expectedViewName)) {
    throw new Error('布局响应不符合固定契约');
  }
  const required = new Set([
    'schema_version', 'view_name', 'layout_revision', 'selection_mode', 'entries', 'viewport',
  ]);
  if (Object.keys(value).length !== required.size || !hasOnlyKeys(value, required)) {
    throw new Error('布局响应不符合固定契约');
  }
  if (value.schema_version !== 'wuji.api.v2'
    || value.view_name !== expectedViewName
    || typeof value.layout_revision !== 'string'
    || !revisionPattern.test(value.layout_revision)
    || value.selection_mode !== expectedSelectionMode(expectedViewName)
    || !Array.isArray(value.entries)
    || value.entries.length > 1000
    || !value.entries.every(isEntry)
    || !isViewport(value.viewport)) {
    throw new Error('布局响应不符合固定契约');
  }
  const anchors = value.entries.map((entry) => {
    const anchor = entry.anchor;
    return `${anchor.entity_type}:${anchor.id}@${anchor.revision ?? ''}`;
  });
  if (new Set(anchors).size !== anchors.length) {
    throw new Error('布局响应不符合固定契约');
  }
  return value as unknown as LayoutPreference;
}

function parseErrorBody(value: unknown): { code?: string; message?: string } {
  if (!isRecord(value)) return {};
  return {
    code: typeof value.code === 'string' ? value.code : undefined,
    message: typeof value.message === 'string' ? value.message : undefined,
  };
}

async function responseBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

export class LayoutRequestError extends Error {
  readonly status: number;
  readonly code: string | null;

  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.name = 'LayoutRequestError';
    this.status = status;
    this.code = code;
  }
}

async function requestError(response: Response): Promise<LayoutRequestError> {
  const parsed = parseErrorBody(await responseBody(response));
  return new LayoutRequestError(
    response.status,
    parsed.message ?? '布局请求未完成',
    parsed.code ?? null,
  );
}

export type LayoutReader = (
  taskId: string,
  viewName: string,
  signal: AbortSignal,
) => Promise<LayoutPreference>;

export type LayoutWriter = (
  taskId: string,
  viewName: string,
  patch: LayoutPatch,
  expectedRevision: string,
  signal: AbortSignal,
) => Promise<LayoutReceipt>;

export const readLayoutPreference: LayoutReader = async (taskId, viewName, signal) => {
  let response: Response;
  try {
    response = await fetch(apiUrl(layoutRequestPath(taskId, viewName)), {
      credentials: 'include',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new LayoutRequestError(0, '无法连接布局服务');
  }
  if (!response.ok) throw await requestError(response);
  try {
    return parseLayoutPreference(await responseBody(response), viewName);
  } catch (error) {
    if (error instanceof LayoutRequestError) throw error;
    throw new LayoutRequestError(response.status, '布局响应不符合固定契约');
  }
};

export const writeLayoutPreference: LayoutWriter = async (
  taskId,
  viewName,
  patch,
  expectedRevision,
  signal,
) => {
  let response: Response;
  try {
    response = await fetch(apiUrl(layoutRequestPath(taskId, viewName)), {
      method: 'PUT',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'If-Match': expectedRevision,
      },
      body: JSON.stringify(patch),
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new LayoutRequestError(0, '无法连接布局服务');
  }
  if (!response.ok) throw await requestError(response);
  const payload = await responseBody(response);
  if (!isRecord(payload)
    || Object.keys(payload).length !== 3
    || payload.view_name !== viewName
    || typeof payload.layout_revision !== 'string'
    || !revisionPattern.test(payload.layout_revision)
    || typeof payload.request_id !== 'string'
    || payload.request_id.length === 0) {
    throw new LayoutRequestError(response.status, '布局回执不符合固定契约');
  }
  return payload as unknown as LayoutReceipt;
};

export function layoutPatch(layout: LayoutPreference): LayoutPatch {
  return {
    schema_version: 'wuji.api.v2',
    selection_mode: layout.selection_mode,
    entries: layout.entries.map((entry) => ({
      anchor: { ...entry.anchor },
      x: entry.x,
      y: entry.y,
      pinned: entry.pinned,
    })),
    viewport: { ...layout.viewport },
  };
}

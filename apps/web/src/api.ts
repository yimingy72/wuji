import type { components } from '@wuji/contracts/types';
import {
  validateScopePage,
  validateError,
  validateProject,
  validateProjectPage,
  validateSession,
  validateTaskPreview,
  type ContractValidator,
} from '@wuji/contracts/validators';

export type ApprovedScope = components['schemas']['ApprovedScope'];
export type ApiErrorBody = components['schemas']['Error'];
export type Limits = components['schemas']['Limits'];
export type Project = components['schemas']['Project'];
export type ProjectPage = components['schemas']['ProjectPage'];
export type ScopePage = components['schemas']['ScopePage'];
export type Session = components['schemas']['Session'];
export type TaskDraft = components['schemas']['TaskDraft'];
export type TaskPreview = components['schemas']['TaskPreview'];

type ErrorCode = ApiErrorBody['code'];

const fallbackCodes: Record<number, ErrorCode> = {
  401: 'UNAUTHENTICATED',
  403: 'FORBIDDEN',
  404: 'NOT_FOUND',
  410: 'CURSOR_EXPIRED',
  422: 'VALIDATION_FAILED',
  503: 'SERVICE_UNAVAILABLE',
};

export class ApiRequestError extends Error {
  readonly status: number;
  readonly code: ErrorCode;
  readonly traceId: string | null;
  readonly contractFailure: boolean;

  constructor(options: {
    status: number;
    code: ErrorCode;
    message: string;
    traceId?: string | null;
    contractFailure?: boolean;
  }) {
    super(options.message);
    this.name = 'ApiRequestError';
    this.status = options.status;
    this.code = options.code;
    this.traceId = options.traceId ?? null;
    this.contractFailure = options.contractFailure ?? false;
  }
}

export class StaleContextError extends Error {
  constructor() {
    super('A newer application context replaced this request');
    this.name = 'StaleContextError';
  }
}

async function responsePayload(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

function httpError(response: Response, payload: unknown): ApiRequestError {
  if (validateError(payload)) {
    return new ApiRequestError({
      status: response.status,
      code: payload.code,
      message: payload.message,
      traceId: payload.trace_id,
    });
  }
  return new ApiRequestError({
    status: response.status,
    code: fallbackCodes[response.status] ?? 'INTERNAL_ERROR',
    message: '平台返回了无法识别的错误响应',
    contractFailure: true,
  });
}

async function getValidated<T>(
  path: string,
  validator: ContractValidator<T>,
  signal: AbortSignal,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiRequestError({
      status: 0,
      code: 'SERVICE_UNAVAILABLE',
      message: '无法连接平台服务',
    });
  }

  const payload = await responsePayload(response);
  if (!response.ok) throw httpError(response, payload);
  if (!validator(payload)) {
    throw new ApiRequestError({
      status: response.status,
      code: 'INTERNAL_ERROR',
      message: '平台响应不符合契约',
      contractFailure: true,
    });
  }
  return payload;
}

export function getSession(signal: AbortSignal): Promise<Session> {
  return getValidated('/api/v1/session', validateSession, signal);
}

export function getProjects(cursor: string | null, signal: AbortSignal): Promise<ProjectPage> {
  const query = new URLSearchParams({ limit: '50' });
  if (cursor) query.set('cursor', cursor);
  return getValidated(`/api/v1/projects?${query.toString()}`, validateProjectPage, signal);
}

export function getProject(projectId: string, signal: AbortSignal): Promise<Project> {
  return getValidated(`/api/v1/projects/${encodeURIComponent(projectId)}`, validateProject, signal);
}

export function getScopes(
  projectId: string,
  cursor: string | null,
  signal: AbortSignal,
): Promise<ScopePage> {
  const query = new URLSearchParams({ limit: '50' });
  if (cursor) query.set('cursor', cursor);
  return getValidated(
    `/api/v1/projects/${encodeURIComponent(projectId)}/scopes?${query.toString()}`,
    validateScopePage,
    signal,
  );
}

export async function postTaskPreview(
  projectId: string,
  draft: TaskDraft,
  csrfToken: string,
  signal: AbortSignal,
): Promise<TaskPreview> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/task-previews`, {
      method: 'POST',
      mode: 'same-origin',
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      body: JSON.stringify(draft),
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiRequestError({
      status: 0,
      code: 'SERVICE_UNAVAILABLE',
      message: '无法连接平台服务',
    });
  }

  const payload = await responsePayload(response);
  if (!response.ok) throw httpError(response, payload);
  if (!validateTaskPreview(payload)) {
    throw new ApiRequestError({
      status: response.status,
      code: 'INTERNAL_ERROR',
      message: '平台响应不符合契约',
      contractFailure: true,
    });
  }
  return payload;
}

export async function postLogout(csrfToken: string, signal: AbortSignal): Promise<void> {
  let response: Response;
  try {
    response = await fetch('/api/v1/auth/logout', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiRequestError({
      status: 0,
      code: 'SERVICE_UNAVAILABLE',
      message: '无法连接平台服务',
    });
  }

  if (response.status === 204) return;
  throw httpError(response, await responsePayload(response));
}

export function shouldRetryRead(failureCount: number, error: Error): boolean {
  if (failureCount >= 1 || error instanceof StaleContextError) return false;
  return error instanceof ApiRequestError && (error.status === 0 || error.status === 503);
}

export function isApiError(error: unknown, status?: number): error is ApiRequestError {
  return error instanceof ApiRequestError && (status === undefined || error.status === status);
}

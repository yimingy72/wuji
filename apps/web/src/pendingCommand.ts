import { useMemo, useSyncExternalStore } from 'react';
import type { CreateTask, NewCreateTaskRequest, TaskControl } from './api';

export type PendingCommandKind = 'create' | 'cancel';

export interface PendingCommand {
  readonly userId: string;
  readonly projectId: string;
  readonly idempotencyKey: string;
  readonly kind: PendingCommandKind;
  readonly resourceId: string | null;
  readonly createdAt: string;
  readonly listInspectedAt: string | null;
}

export type FrozenCommand =
  | { readonly kind: 'create'; readonly request: Readonly<CreateTask | NewCreateTaskRequest> }
  | { readonly kind: 'cancel'; readonly request: Readonly<TaskControl> };

const prefix = 'wuji.pending-command.v1.';
const listeners = new Set<() => void>();
const frozenCommands = new Map<string, FrozenCommand>();

export class PendingStorageError extends Error {
  constructor() {
    super('当前标签页无法保存提交标记');
    this.name = 'PendingStorageError';
  }
}

function storageKey(projectId: string) {
  return `${prefix}${projectId}`;
}

function notify() {
  for (const listener of listeners) listener();
}

function isPendingCommand(value: unknown): value is PendingCommand {
  if (!value || typeof value !== 'object') return false;
  const item = value as Record<string, unknown>;
  return typeof item.userId === 'string'
    && typeof item.projectId === 'string'
    && typeof item.idempotencyKey === 'string'
    && (item.kind === 'create' || item.kind === 'cancel')
    && (item.resourceId === null || typeof item.resourceId === 'string')
    && typeof item.createdAt === 'string'
    && (item.listInspectedAt === null || typeof item.listInspectedAt === 'string');
}

function rawPending(projectId: string): string | null {
  try {
    return sessionStorage.getItem(storageKey(projectId));
  } catch {
    return null;
  }
}

function parsePending(projectId: string, raw: string | null): PendingCommand | null {
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (isPendingCommand(parsed) && parsed.projectId === projectId) return parsed;
    sessionStorage.removeItem(storageKey(projectId));
  } catch {
    return null;
  }
  return null;
}

export function getPendingCommand(projectId: string, userId: string): PendingCommand | null {
  const pending = parsePending(projectId, rawPending(projectId));
  return pending?.userId === userId ? pending : null;
}

export function usePendingCommand(projectId: string, userId: string): PendingCommand | null {
  const raw = useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => rawPending(projectId),
    () => null,
  );
  return useMemo(() => {
    const pending = parsePending(projectId, raw);
    return pending?.userId === userId ? pending : null;
  }, [projectId, raw, userId]);
}

function deepFreeze<T>(value: T): T {
  if (value && typeof value === 'object') {
    for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child);
    Object.freeze(value);
  }
  return value;
}

function freezeCommand(command: FrozenCommand): FrozenCommand {
  return deepFreeze(structuredClone(command));
}

export function beginCommand(
  userId: string,
  projectId: string,
  kind: PendingCommandKind,
  resourceId: string | null,
  command: FrozenCommand,
): PendingCommand {
  if (getPendingCommand(projectId, userId)) throw new PendingStorageError();
  const pending: PendingCommand = {
    userId,
    projectId,
    idempotencyKey: crypto.randomUUID(),
    kind,
    resourceId,
    createdAt: new Date().toISOString(),
    listInspectedAt: null,
  };
  try {
    sessionStorage.setItem(storageKey(projectId), JSON.stringify(pending));
  } catch {
    throw new PendingStorageError();
  }
  frozenCommands.set(pending.idempotencyKey, freezeCommand(command));
  notify();
  return pending;
}

export function getFrozenCommand(pending: PendingCommand): FrozenCommand | null {
  return frozenCommands.get(pending.idempotencyKey) ?? null;
}

export function markPendingListInspected(pending: PendingCommand) {
  const current = getPendingCommand(pending.projectId, pending.userId);
  if (!current || current.idempotencyKey !== pending.idempotencyKey || current.listInspectedAt) return;
  try {
    sessionStorage.setItem(storageKey(pending.projectId), JSON.stringify({
      ...current,
      listInspectedAt: new Date().toISOString(),
    }));
    notify();
  } catch {
    // Failure keeps abandonment unavailable; the command can still be reconciled.
  }
}

export function clearPendingCommand(pending: PendingCommand) {
  try {
    const current = parsePending(pending.projectId, rawPending(pending.projectId));
    if (current?.idempotencyKey === pending.idempotencyKey) {
      sessionStorage.removeItem(storageKey(pending.projectId));
    }
  } catch {
    // The in-memory command is still cleared; future storage reads remain guarded.
  }
  frozenCommands.delete(pending.idempotencyKey);
  notify();
}

export function clearAllPendingCommands() {
  try {
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index);
      if (key?.startsWith(prefix)) sessionStorage.removeItem(key);
    }
  } catch {
    // Logout and account changes still clear all in-memory command bodies.
  }
  frozenCommands.clear();
  notify();
}

export function retainPendingCommandsForUser(userId: string) {
  try {
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index);
      if (!key?.startsWith(prefix)) continue;
      const projectId = key.slice(prefix.length);
      const pending = parsePending(projectId, rawPending(projectId));
      if (!pending || pending.userId !== userId) {
        sessionStorage.removeItem(key);
        if (pending) frozenCommands.delete(pending.idempotencyKey);
      }
    }
  } catch {
    return;
  }
  notify();
}

import { useSyncExternalStore } from 'react';
import type { Project, Session } from './api';

export type SessionStatus =
  | 'checking'
  | 'authenticated'
  | 'signed-out'
  | 'logout-pending'
  | 'logout-failed';

interface ActiveProject {
  readonly id: string;
  readonly tenantId: string | null;
}

export interface IdentitySnapshot {
  readonly status: SessionStatus;
  readonly session: Session | null;
  readonly identityGeneration: number;
  readonly projectGeneration: number;
  readonly activeProject: ActiveProject | null;
}

type SessionAcceptance = 'accepted' | 'permissions-changed' | 'identity-changed' | 'stale';
type Listener = () => void;

let snapshot: IdentitySnapshot = {
  status: 'checking',
  session: null,
  identityGeneration: 0,
  projectGeneration: 0,
  activeProject: null,
};
let logoutCsrfToken: string | null = null;
const listeners = new Set<Listener>();

function emit(next: IdentitySnapshot) {
  snapshot = next;
  for (const listener of listeners) listener();
}

function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getIdentitySnapshot(): IdentitySnapshot {
  return snapshot;
}

export function useIdentitySnapshot(): IdentitySnapshot {
  return useSyncExternalStore(subscribe, getIdentitySnapshot, getIdentitySnapshot);
}

export function acceptSession(
  capturedGeneration: number,
  session: Session,
): SessionAcceptance {
  if (
    snapshot.identityGeneration !== capturedGeneration
    || snapshot.status === 'logout-pending'
    || snapshot.status === 'logout-failed'
  ) {
    return 'stale';
  }

  const previous = snapshot.session;
  if (previous && previous.user_id !== session.user_id) {
    emit({
      status: 'authenticated',
      session,
      identityGeneration: snapshot.identityGeneration + 1,
      projectGeneration: snapshot.projectGeneration + 1,
      activeProject: null,
    });
    return 'identity-changed';
  }

  const permissionsChanged = previous?.permissions_version !== undefined
    && previous.permissions_version !== session.permissions_version;
  emit({
    ...snapshot,
    status: 'authenticated',
    session,
    identityGeneration: permissionsChanged
      ? snapshot.identityGeneration + 1
      : snapshot.identityGeneration,
    projectGeneration: permissionsChanged
      ? snapshot.projectGeneration + 1
      : snapshot.projectGeneration,
    activeProject: permissionsChanged && snapshot.activeProject
      ? { id: snapshot.activeProject.id, tenantId: null }
      : snapshot.activeProject,
  });
  return permissionsChanged ? 'permissions-changed' : 'accepted';
}

export function markUnauthenticated(capturedGeneration: number): boolean {
  if (snapshot.identityGeneration !== capturedGeneration) return false;
  emit({
    status: 'signed-out',
    session: null,
    identityGeneration: snapshot.identityGeneration + 1,
    projectGeneration: snapshot.projectGeneration + 1,
    activeProject: null,
  });
  logoutCsrfToken = null;
  return true;
}

export function selectProject(projectId: string | null, tenantId: string | null = null): number {
  if (projectId === null) {
    if (snapshot.activeProject === null) return snapshot.projectGeneration;
    emit({
      ...snapshot,
      projectGeneration: snapshot.projectGeneration + 1,
      activeProject: null,
    });
    return snapshot.projectGeneration;
  }

  if (snapshot.activeProject?.id === projectId) {
    if (tenantId && snapshot.activeProject.tenantId !== tenantId) {
      emit({ ...snapshot, activeProject: { id: projectId, tenantId } });
    }
    return snapshot.projectGeneration;
  }

  emit({
    ...snapshot,
    projectGeneration: snapshot.projectGeneration + 1,
    activeProject: { id: projectId, tenantId },
  });
  return snapshot.projectGeneration;
}

export function acceptProject(
  capturedGeneration: number,
  project: Project,
): boolean {
  if (
    snapshot.projectGeneration !== capturedGeneration
    || snapshot.activeProject?.id !== project.id
  ) {
    return false;
  }
  if (snapshot.activeProject.tenantId !== project.tenant_id) {
    emit({
      ...snapshot,
      activeProject: { id: project.id, tenantId: project.tenant_id },
    });
  }
  return true;
}

export function clearProject(capturedGeneration: number, projectId: string): boolean {
  if (
    snapshot.projectGeneration !== capturedGeneration
    || snapshot.activeProject?.id !== projectId
  ) {
    return false;
  }
  emit({
    ...snapshot,
    projectGeneration: snapshot.projectGeneration + 1,
    activeProject: null,
  });
  return true;
}

export function beginLogout(): string | null {
  if (snapshot.status === 'logout-pending') return logoutCsrfToken;
  if (snapshot.status === 'logout-failed' && logoutCsrfToken) {
    emit({ ...snapshot, status: 'logout-pending' });
    return logoutCsrfToken;
  }
  if (!snapshot.session) return null;

  logoutCsrfToken = snapshot.session.csrf_token;
  emit({
    status: 'logout-pending',
    session: null,
    identityGeneration: snapshot.identityGeneration + 1,
    projectGeneration: snapshot.projectGeneration + 1,
    activeProject: null,
  });
  return logoutCsrfToken;
}

export function failLogout() {
  if (snapshot.status === 'logout-pending') emit({ ...snapshot, status: 'logout-failed' });
}

export function finishLogout() {
  logoutCsrfToken = null;
  emit({ ...snapshot, status: 'signed-out' });
}

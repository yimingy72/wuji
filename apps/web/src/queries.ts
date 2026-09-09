import { QueryClient, queryOptions } from '@tanstack/react-query';
import {
  ApiRequestError,
  StaleContextError,
  getProject,
  getProjects,
  getSession,
  isApiError,
  postLogout,
  shouldRetryRead,
  type Project,
  type ProjectPage,
  type Session,
} from './api';
import {
  acceptProject,
  acceptSession,
  beginLogout,
  clearProject,
  failLogout,
  finishLogout,
  getIdentitySnapshot,
  markUnauthenticated,
  selectProject,
} from './state';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
    },
    mutations: { retry: false },
  },
});

function sessionKey(snapshot = getIdentitySnapshot()) {
  return [
    'private',
    'session',
    snapshot.identityGeneration,
    snapshot.session?.user_id ?? 'pending-user',
    snapshot.session?.permissions_version ?? 'pending-version',
  ] as const;
}

function projectPageKey(cursor: string | null, session: Session) {
  const snapshot = getIdentitySnapshot();
  return [
    'private',
    'projects',
    snapshot.identityGeneration,
    session.user_id,
    session.permissions_version,
    cursor ?? 'first-page',
  ] as const;
}

function projectKey(projectId: string, session: Session) {
  const snapshot = getIdentitySnapshot();
  return [
    'private',
    'project',
    snapshot.identityGeneration,
    snapshot.projectGeneration,
    session.user_id,
    snapshot.activeProject?.tenantId ?? 'pending-tenant',
    projectId,
  ] as const;
}

async function removeAllPrivateQueries() {
  await queryClient.cancelQueries({ queryKey: ['private'] });
  queryClient.removeQueries({ queryKey: ['private'] });
}

async function removeProjectQueries(identityGeneration?: number) {
  await queryClient.cancelQueries({
    predicate: (query) => query.queryKey[0] === 'private'
      && (query.queryKey[1] === 'projects' || query.queryKey[1] === 'project')
      && (identityGeneration === undefined || query.queryKey[2] === identityGeneration),
  });
  queryClient.removeQueries({
    predicate: (query) => query.queryKey[0] === 'private'
      && (query.queryKey[1] === 'projects' || query.queryKey[1] === 'project')
      && (identityGeneration === undefined || query.queryKey[2] === identityGeneration),
  });
}

interface CapturedContext {
  readonly identityGeneration: number;
  readonly projectGeneration?: number;
  readonly userId?: string;
  readonly permissionsVersion?: number;
}

async function handleReadError(error: unknown, captured: CapturedContext): Promise<never> {
  const current = getIdentitySnapshot();
  if (
    current.identityGeneration !== captured.identityGeneration
    || (captured.projectGeneration !== undefined
      && current.projectGeneration !== captured.projectGeneration)
    || (captured.userId !== undefined && current.session?.user_id !== captured.userId)
    || (captured.permissionsVersion !== undefined
      && current.session?.permissions_version !== captured.permissionsVersion)
  ) {
    throw new StaleContextError();
  }
  if (isApiError(error, 401) && markUnauthenticated(captured.identityGeneration)) {
    await removeAllPrivateQueries();
  }
  throw error;
}

export function sessionQueryOptions() {
  const captured = getIdentitySnapshot();
  return queryOptions<Session, Error>({
    queryKey: sessionKey(captured),
    staleTime: 10_000,
    refetchOnWindowFocus: 'always',
    retry: shouldRetryRead,
    queryFn: async ({ signal }) => {
      try {
        const session = await getSession(signal);
        if (getIdentitySnapshot().identityGeneration !== captured.identityGeneration) {
          throw new StaleContextError();
        }
        const acceptance = acceptSession(captured.identityGeneration, session);
        if (acceptance === 'stale') throw new StaleContextError();

        const acceptedSnapshot = getIdentitySnapshot();
        queryClient.setQueryData(sessionKey(acceptedSnapshot), session);
        if (acceptance === 'permissions-changed' || acceptance === 'identity-changed') {
          await removeProjectQueries(captured.identityGeneration);
        }
        return session;
      } catch (error) {
        return handleReadError(error, { identityGeneration: captured.identityGeneration });
      }
    },
  });
}

export function projectPageQueryOptions(session: Session, cursor: string | null) {
  const captured = getIdentitySnapshot();
  return queryOptions<ProjectPage, Error>({
    queryKey: projectPageKey(cursor, session),
    staleTime: 5_000,
    retry: shouldRetryRead,
    queryFn: async ({ signal }) => {
      try {
        const page = await getProjects(cursor, signal);
        const current = getIdentitySnapshot();
        if (
          current.identityGeneration !== captured.identityGeneration
          || current.session?.user_id !== session.user_id
          || current.session.permissions_version !== session.permissions_version
        ) {
          throw new StaleContextError();
        }
        return page;
      } catch (error) {
        return handleReadError(error, {
          identityGeneration: captured.identityGeneration,
          userId: session.user_id,
          permissionsVersion: session.permissions_version,
        });
      }
    },
  });
}

export function projectQueryOptions(session: Session, projectId: string) {
  const captured = getIdentitySnapshot();
  return queryOptions<Project, Error>({
    queryKey: projectKey(projectId, session),
    staleTime: 5_000,
    retry: shouldRetryRead,
    queryFn: async ({ signal }) => {
      try {
        const project = await getProject(projectId, signal);
        const current = getIdentitySnapshot();
        if (
          current.identityGeneration !== captured.identityGeneration
          || current.projectGeneration !== captured.projectGeneration
          || current.session?.user_id !== session.user_id
        ) {
          throw new StaleContextError();
        }
        if (!acceptProject(captured.projectGeneration, project)) {
          throw new StaleContextError();
        }
        queryClient.setQueryData(projectKey(projectId, session), project);
        return project;
      } catch (error) {
        const current = getIdentitySnapshot();
        if (
          current.identityGeneration !== captured.identityGeneration
          || current.projectGeneration !== captured.projectGeneration
          || current.session?.user_id !== session.user_id
        ) {
          throw new StaleContextError();
        }
        return handleReadError(error, {
          identityGeneration: captured.identityGeneration,
          projectGeneration: captured.projectGeneration,
          userId: session.user_id,
        });
      }
    },
  });
}

export async function loadCurrentSession(): Promise<Session> {
  return queryClient.fetchQuery({ ...sessionQueryOptions(), staleTime: 0 });
}

async function selectRouteProject(projectId: string | null) {
  const before = getIdentitySnapshot().projectGeneration;
  const generation = selectProject(projectId);
  if (generation !== before) {
    await queryClient.cancelQueries({
      predicate: (query) => query.queryKey[0] === 'private' && query.queryKey[1] === 'project',
    });
  }
}

export function prepareProjectsRoute(): Promise<void> {
  return selectRouteProject(null);
}

export function prepareProjectRoute(projectId: string): Promise<void> {
  return selectRouteProject(projectId);
}

export async function enterProjects(session: Session): Promise<ProjectPage> {
  await selectRouteProject(null);
  return queryClient.ensureQueryData(projectPageQueryOptions(session, null));
}

export async function enterProject(session: Session, projectId: string): Promise<Project> {
  await selectRouteProject(projectId);
  return queryClient.ensureQueryData(projectQueryOptions(session, projectId));
}

export function selectKnownProject(project: Project) {
  const before = getIdentitySnapshot().projectGeneration;
  const generation = selectProject(project.id, project.tenant_id);
  if (generation !== before) {
    void queryClient.cancelQueries({
      predicate: (query) => query.queryKey[0] === 'private' && query.queryKey[1] === 'project',
    });
  }
}

export function leaveUnavailableProject(projectId: string) {
  const generation = getIdentitySnapshot().projectGeneration;
  if (!clearProject(generation, projectId)) return;
  queryClient.removeQueries({
    predicate: (query) => query.queryKey[0] === 'private'
      && query.queryKey[1] === 'project'
      && query.queryKey.at(-1) === projectId,
  });
}

export async function refreshSession(): Promise<Session> {
  return queryClient.fetchQuery({ ...sessionQueryOptions(), staleTime: 0 });
}

export async function logout(): Promise<'complete' | 'failed'> {
  const csrfToken = beginLogout();
  if (!csrfToken) return 'complete';
  await removeAllPrivateQueries();

  const controller = new AbortController();
  try {
    await postLogout(csrfToken, controller.signal);
    finishLogout();
    return 'complete';
  } catch (error) {
    if (
      error instanceof ApiRequestError
      && error.status === 401
      && error.code === 'UNAUTHENTICATED'
      && !error.contractFailure
      && error.traceId !== null
    ) {
      finishLogout();
      return 'complete';
    }
    failLogout();
    return 'failed';
  }
}

import {
  QueryClient,
  infiniteQueryOptions,
  queryOptions,
  type InfiniteData,
} from '@tanstack/react-query';
import {
  ApiRequestError,
  StaleContextError,
  getProject,
  getProjects,
  getScopes,
  getSession,
  getCommandByKey,
  getTask,
  getTaskEvents,
  getTasks,
  isApiError,
  postCreateTask,
  postLogout,
  postTaskControl,
  postTaskPreview,
  shouldRetryRead,
  type Project,
  type ProjectPage,
  type CommandReceipt,
  type CreateTask,
  type NewCreateTaskRequest,
  type EventPage,
  type ScopePage,
  type Session,
  type TaskDraft,
  type TaskControl,
  type TaskPage,
  type TaskPreview,
  type TaskSnapshot,
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

function scopePagesKey(projectId: string, session: Session) {
  const snapshot = getIdentitySnapshot();
  return [
    'private',
    'scopes',
    snapshot.identityGeneration,
    snapshot.projectGeneration,
    session.user_id,
    session.permissions_version,
    snapshot.activeProject?.tenantId ?? 'pending-tenant',
    projectId,
  ] as const;
}

function taskPageKey(projectId: string, cursor: string | null, session: Session) {
  const snapshot = getIdentitySnapshot();
  return [
    'private', 'tasks', snapshot.identityGeneration, snapshot.projectGeneration,
    session.user_id, session.permissions_version,
    snapshot.activeProject?.tenantId ?? 'pending-tenant', projectId,
    cursor ?? 'first-page',
  ] as const;
}

async function removeAllPrivateQueries() {
  await queryClient.cancelQueries({ queryKey: ['private'] });
  queryClient.removeQueries({ queryKey: ['private'] });
}

async function removeProjectQueries(identityGeneration?: number) {
  await queryClient.cancelQueries({
    predicate: (query) => query.queryKey[0] === 'private'
      && (
        query.queryKey[1] === 'projects'
        || query.queryKey[1] === 'project'
        || query.queryKey[1] === 'scopes'
        || query.queryKey[1] === 'tasks'
      )
      && (identityGeneration === undefined || query.queryKey[2] === identityGeneration),
  });
  queryClient.removeQueries({
    predicate: (query) => query.queryKey[0] === 'private'
      && (
        query.queryKey[1] === 'projects'
        || query.queryKey[1] === 'project'
        || query.queryKey[1] === 'scopes'
        || query.queryKey[1] === 'tasks'
      )
      && (identityGeneration === undefined || query.queryKey[2] === identityGeneration),
  });
}

interface CapturedContext {
  readonly identityGeneration: number;
  readonly projectGeneration?: number;
  readonly userId?: string;
  readonly permissionsVersion?: number;
  readonly projectId?: string;
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
    || (captured.projectId !== undefined && current.activeProject?.id !== captured.projectId)
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

export function scopePagesQueryOptions(session: Session, projectId: string) {
  const captured = getIdentitySnapshot();
  return infiniteQueryOptions<
    ScopePage,
    Error,
    InfiniteData<ScopePage>,
    ReturnType<typeof scopePagesKey>,
    string | null
  >({
    queryKey: scopePagesKey(projectId, session),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    staleTime: 5_000,
    retry: shouldRetryRead,
    queryFn: async ({ pageParam, signal }) => {
      try {
        const page = await getScopes(projectId, pageParam, signal);
        const current = getIdentitySnapshot();
        if (
          current.identityGeneration !== captured.identityGeneration
          || current.projectGeneration !== captured.projectGeneration
          || current.session?.user_id !== session.user_id
          || current.session.permissions_version !== session.permissions_version
          || current.activeProject?.id !== projectId
        ) {
          throw new StaleContextError();
        }
        return page;
      } catch (error) {
        return handleReadError(error, {
          identityGeneration: captured.identityGeneration,
          projectGeneration: captured.projectGeneration,
          userId: session.user_id,
          permissionsVersion: session.permissions_version,
          projectId,
        });
      }
    },
  });
}

export async function resetScopePages(session: Session, projectId: string) {
  await queryClient.resetQueries({
    queryKey: scopePagesKey(projectId, session),
    exact: true,
  });
}

export async function projectRequest<T>(
  session: Session,
  projectId: string,
  request: () => Promise<T>,
): Promise<T> {
  const captured = getIdentitySnapshot();
  try {
    const result = await request();
    const current = getIdentitySnapshot();
    if (
      current.identityGeneration !== captured.identityGeneration
      || current.projectGeneration !== captured.projectGeneration
      || current.session?.user_id !== session.user_id
      || current.session.permissions_version !== session.permissions_version
      || current.activeProject?.id !== projectId
    ) {
      throw new StaleContextError();
    }
    return result;
  } catch (error) {
    return handleReadError(error, {
      identityGeneration: captured.identityGeneration,
      projectGeneration: captured.projectGeneration,
      userId: session.user_id,
      permissionsVersion: session.permissions_version,
      projectId,
    });
  }
}

export function taskPageQueryOptions(session: Session, projectId: string, cursor: string | null) {
  return queryOptions<TaskPage, Error>({
    queryKey: taskPageKey(projectId, cursor, session),
    staleTime: 5_000,
    refetchOnWindowFocus: 'always',
    retry: shouldRetryRead,
    queryFn: ({ signal }) => projectRequest(
      session,
      projectId,
      () => getTasks(projectId, cursor, signal),
    ),
  });
}

export async function readTaskSnapshot(
  session: Session,
  projectId: string,
  taskId: string,
  signal: AbortSignal,
): Promise<TaskSnapshot> {
  const result = await projectRequest(session, projectId, () => getTask(projectId, taskId, signal));
  if (result.task.project_id !== projectId || result.task.id !== taskId) {
    throw new ApiRequestError({
      status: 200,
      code: 'INTERNAL_ERROR',
      message: '平台响应与当前任务不一致',
      contractFailure: true,
    });
  }
  return result;
}

export function readTaskEvents(
  session: Session,
  projectId: string,
  taskId: string,
  after: string | null,
  signal: AbortSignal,
): Promise<EventPage> {
  return projectRequest(session, projectId, () => getTaskEvents(projectId, taskId, after, signal));
}

export function findCommand(
  session: Session,
  projectId: string,
  idempotencyKey: string,
  signal: AbortSignal,
): Promise<CommandReceipt> {
  return projectRequest(
    session,
    projectId,
    () => getCommandByKey(projectId, idempotencyKey, signal),
  );
}

export function submitCreateTask(
  session: Session,
  projectId: string,
  request: CreateTask | NewCreateTaskRequest,
  idempotencyKey: string,
  signal: AbortSignal,
): Promise<CommandReceipt> {
  return projectRequest(
    session,
    projectId,
    () => postCreateTask(projectId, request, session.csrf_token, idempotencyKey, signal),
  );
}

export function submitTaskControl(
  session: Session,
  projectId: string,
  taskId: string,
  request: TaskControl,
  idempotencyKey: string,
  signal: AbortSignal,
): Promise<CommandReceipt> {
  return projectRequest(
    session,
    projectId,
    () => postTaskControl(
      projectId, taskId, request, session.csrf_token, idempotencyKey, signal,
    ),
  );
}

export async function refreshTaskLists(projectId: string) {
  await queryClient.invalidateQueries({
    predicate: (query) => query.queryKey[0] === 'private'
      && query.queryKey[1] === 'tasks'
      && query.queryKey.at(-2) === projectId,
  });
}

export async function previewTask(
  session: Session,
  projectId: string,
  draft: TaskDraft,
  signal: AbortSignal,
): Promise<TaskPreview> {
  const captured = getIdentitySnapshot();
  try {
    const preview = await postTaskPreview(projectId, draft, session.csrf_token, signal);
    const current = getIdentitySnapshot();
    if (
      current.identityGeneration !== captured.identityGeneration
      || current.projectGeneration !== captured.projectGeneration
      || current.session?.user_id !== session.user_id
      || current.session.permissions_version !== session.permissions_version
      || current.activeProject?.id !== projectId
    ) {
      throw new StaleContextError();
    }
    if (preview.project_id !== projectId) {
      throw new ApiRequestError({
        status: 200,
        code: 'INTERNAL_ERROR',
        message: '平台响应与当前项目不一致',
        contractFailure: true,
      });
    }
    return preview;
  } catch (error) {
    return handleReadError(error, {
      identityGeneration: captured.identityGeneration,
      projectGeneration: captured.projectGeneration,
      userId: session.user_id,
      permissionsVersion: session.permissions_version,
      projectId,
    });
  }
}

export async function loadCurrentSession(): Promise<Session> {
  return queryClient.fetchQuery({ ...sessionQueryOptions(), staleTime: 0 });
}

async function selectRouteProject(projectId: string | null) {
  const before = getIdentitySnapshot().projectGeneration;
  const generation = selectProject(projectId);
  if (generation !== before) {
    await queryClient.cancelQueries({
      predicate: (query) => query.queryKey[0] === 'private'
        && (query.queryKey[1] === 'project' || query.queryKey[1] === 'scopes' || query.queryKey[1] === 'tasks'),
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
      predicate: (query) => query.queryKey[0] === 'private'
        && (query.queryKey[1] === 'project' || query.queryKey[1] === 'scopes' || query.queryKey[1] === 'tasks'),
    });
  }
}

export function leaveUnavailableProject(projectId: string) {
  const generation = getIdentitySnapshot().projectGeneration;
  if (!clearProject(generation, projectId)) return;
  queryClient.removeQueries({
    predicate: (query) => query.queryKey[0] === 'private'
      && (query.queryKey[1] === 'project' || query.queryKey[1] === 'scopes' || query.queryKey[1] === 'tasks')
      && query.queryKey.includes(projectId),
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

export async function identityRequest<T>(session: Session, request: () => Promise<T>): Promise<T> {
  const captured = getIdentitySnapshot();
  try {
    const result = await request();
    const current = getIdentitySnapshot();
    if (current.identityGeneration !== captured.identityGeneration || current.session?.user_id !== session.user_id || current.session.permissions_version !== session.permissions_version) throw new StaleContextError();
    return result;
  } catch (error) {
    return handleReadError(error, {identityGeneration: captured.identityGeneration, userId: session.user_id, permissionsVersion: session.permissions_version});
  }
}

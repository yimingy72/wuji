import {
  createBrowserRouter,
  redirect,
  type LoaderFunctionArgs,
} from 'react-router-dom';
import { ApiRequestError, isApiError } from './api';
import { AppearanceProvider } from './Appearance';
import {
  LoginPage,
  HydrateFallbackPage,
  NotFoundPage,
  ProjectPage,
  ProjectsRoute,
  RootLayout,
  RouteErrorPage,
} from './pages';
import { ModelsPage } from './features/model-config/ModelsPage';
import { CreationPage, DraftsPage, NewCreationPage } from './features/task-creation/CreationPage';
import { TaskDetailPage, TasksPage } from './tasks';
import {
  enterProject,
  enterProjects,
  leaveUnavailableProject,
  loadCurrentSession,
  prepareProjectRoute,
  prepareProjectsRoute,
} from './queries';
import { isProjectId, loginPath, returnToFromRequest } from './routing';
import { getIdentitySnapshot } from './state';

async function requireSession(request: Request) {
  try {
    return await loadCurrentSession();
  } catch (error) {
    if (!request.signal.aborted && getIdentitySnapshot().status === 'signed-out') {
      throw redirect(loginPath(returnToFromRequest(request)));
    }
    throw error;
  }
}

async function projectsLoader({ request }: LoaderFunctionArgs) {
  await prepareProjectsRoute();
  const session = await requireSession(request);
  await enterProjects(session);
  return null;
}

async function projectLoader({ params, request }: LoaderFunctionArgs) {
  const projectId = params.projectId;
  if (!isProjectId(projectId)) {
    throw new ApiRequestError({
      status: 404,
      code: 'NOT_FOUND',
      message: '项目路径无效',
    });
  }
  await prepareProjectRoute(projectId);
  let session = await requireSession(request);
  for (;;) {
    try {
      await enterProject(session, projectId);
      return null;
    } catch (error) {
      if (request.signal.aborted) throw error;
      if (isApiError(error, 404)) {
        leaveUnavailableProject(projectId);
        throw redirect('/projects?notice=project-unavailable');
      }

      const current = getIdentitySnapshot();
      const replacement = current.status === 'authenticated'
        && current.activeProject?.id === projectId
        && current.session
        && (current.session.user_id !== session.user_id
          || current.session.permissions_version !== session.permissions_version)
        ? current.session
        : null;
      if (!replacement) throw error;
      session = replacement;
    }
  }
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppearanceProvider><RootLayout /></AppearanceProvider>,
    hydrateFallbackElement: <HydrateFallbackPage />,
    errorElement: <AppearanceProvider><RouteErrorPage /></AppearanceProvider>,
    children: [
      { index: true, loader: () => redirect('/projects') },
      { path: 'login', element: <LoginPage /> },
      {
        path: 'projects',
        loader: projectsLoader,
        element: <ProjectsRoute />,
        errorElement: <RouteErrorPage />,
      },
      {
        path: 'projects/:projectId',
        loader: projectLoader,
        element: <ProjectPage />,
        errorElement: <RouteErrorPage />,
      },
      {
        path: 'projects/:projectId/tasks',
        loader: projectLoader,
        element: <TasksPage />,
        errorElement: <RouteErrorPage />,
      },
      {
        path: 'projects/:projectId/tasks/new',
        loader: projectLoader,
        element: <NewCreationPage />,
        errorElement: <RouteErrorPage />,
      },
      {
        path: 'projects/:projectId/tasks/:taskId',
        loader: projectLoader,
        element: <TaskDetailPage />,
        errorElement: <RouteErrorPage />,
      },
      { path: 'projects/:projectId/drafts', loader: projectLoader, element: <DraftsPage />, errorElement: <RouteErrorPage /> },
      { path: 'projects/:projectId/drafts/:draftId', loader: projectLoader, element: <CreationPage />, errorElement: <RouteErrorPage /> },
      { path: 'settings/tenants/:tenantId/models', loader: async ({request}) => { await prepareProjectsRoute(); await requireSession(request); return null; }, element: <ModelsPage />, errorElement: <RouteErrorPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

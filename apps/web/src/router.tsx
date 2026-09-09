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
import {
  enterProject,
  enterProjects,
  leaveUnavailableProject,
  loadCurrentSession,
  prepareProjectRoute,
  prepareProjectsRoute,
} from './queries';
import { isProjectId, loginPath, returnToFromRequest } from './routing';

async function requireSession(request: Request) {
  try {
    return await loadCurrentSession();
  } catch (error) {
    if (isApiError(error, 401)) throw redirect(loginPath(returnToFromRequest(request)));
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
  const session = await requireSession(request);
  try {
    await enterProject(session, projectId);
  } catch (error) {
    if (isApiError(error, 404)) {
      leaveUnavailableProject(projectId);
      throw redirect('/projects?notice=project-unavailable');
    }
    throw error;
  }
  return null;
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
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

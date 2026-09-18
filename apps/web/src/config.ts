export interface WebRuntimeConfig {
  readonly apiBaseUrl: string;
  readonly authEntrypoint: string;
  readonly mode: string;
  readonly tenantId: string;
  readonly projectId: string;
  readonly taskId: string;
}

declare global {
  interface Window {
    __WUJI_CONFIG__?: Partial<WebRuntimeConfig>;
  }
}

const buildConfig: Partial<WebRuntimeConfig> = {
  apiBaseUrl: import.meta.env.VITE_WUJI_API_BASE_URL,
  authEntrypoint: import.meta.env.VITE_WUJI_AUTH_ENTRYPOINT,
  mode: import.meta.env.VITE_WUJI_MODE,
  tenantId: import.meta.env.VITE_WUJI_TENANT_ID,
  projectId: import.meta.env.VITE_WUJI_PROJECT_ID,
  taskId: import.meta.env.VITE_WUJI_TASK_ID,
};

function value(name: keyof WebRuntimeConfig): string {
  const runtimeValue = typeof window === 'undefined' ? undefined : window.__WUJI_CONFIG__?.[name];
  const buildValue = buildConfig[name];
  return (runtimeValue ?? buildValue ?? '').trim();
}

export const webConfig: WebRuntimeConfig = {
  apiBaseUrl: value('apiBaseUrl'),
  authEntrypoint: value('authEntrypoint'),
  mode: value('mode'),
  tenantId: value('tenantId'),
  projectId: value('projectId'),
  taskId: value('taskId'),
};

export const hasApiConfiguration = webConfig.apiBaseUrl.length > 0;
export const hasAuthConfiguration = webConfig.authEntrypoint.length > 0;
export const isVNextReadonlyConfigured = webConfig.mode === 'vnext-readonly'
  && hasAuthConfiguration;
export const isWebIntegrationConfigured = !isVNextReadonlyConfigured
  && hasApiConfiguration
  && hasAuthConfiguration;

export function apiUrl(path: string): string {
  if (!webConfig.apiBaseUrl) return path;
  const base = new URL(webConfig.apiBaseUrl, window.location.origin);
  if (base.pathname !== '/' && path.startsWith(`${base.pathname.replace(/\/$/, '')}/`)) {
    return new URL(path, base.origin).toString();
  }
  return new URL(path, base.origin).toString();
}

export function authUrl(returnTo: string): string {
  const url = new URL(webConfig.authEntrypoint, window.location.origin);
  url.searchParams.set('return_to', returnTo);
  return url.toString();
}

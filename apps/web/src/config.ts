export interface WebRuntimeConfig {
  readonly apiBaseUrl: string;
  readonly authEntrypoint: string;
}

declare global {
  interface Window {
    __WUJI_CONFIG__?: Partial<WebRuntimeConfig>;
  }
}

const buildConfig: Partial<WebRuntimeConfig> = {
  apiBaseUrl: import.meta.env.VITE_WUJI_API_BASE_URL,
  authEntrypoint: import.meta.env.VITE_WUJI_AUTH_ENTRYPOINT,
};

function value(name: keyof WebRuntimeConfig): string {
  const runtimeValue = window.__WUJI_CONFIG__?.[name];
  const buildValue = buildConfig[name];
  return (runtimeValue ?? buildValue ?? '').trim();
}

export const webConfig: WebRuntimeConfig = {
  apiBaseUrl: value('apiBaseUrl'),
  authEntrypoint: value('authEntrypoint'),
};

export const hasApiConfiguration = webConfig.apiBaseUrl.length > 0;
export const hasAuthConfiguration = webConfig.authEntrypoint.length > 0;
export const isWebIntegrationConfigured = hasApiConfiguration && hasAuthConfiguration;

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

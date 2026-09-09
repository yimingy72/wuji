const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const projectPathPattern = /^\/projects(?:\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(\/tasks\/new)?)?\/?$/i;

export function isProjectId(value: unknown): value is string {
  return typeof value === 'string' && uuidPattern.test(value);
}

export function normalizeReturnTo(value: unknown): string {
  if (typeof value !== 'string') return '/projects';
  const match = projectPathPattern.exec(value);
  if (!match) return '/projects';
  if (!match[1]) return '/projects';
  return match[2] ? `/projects/${match[1]}/tasks/new` : `/projects/${match[1]}`;
}

export function returnToFromRequest(request: Request): string {
  return normalizeReturnTo(new URL(request.url).pathname);
}

export function loginPath(returnTo: string): string {
  const search = new URLSearchParams({ return_to: normalizeReturnTo(returnTo) });
  return `/login?${search.toString()}`;
}

export function beginLoginPath(returnTo: string): string {
  const search = new URLSearchParams({ return_to: normalizeReturnTo(returnTo) });
  return `/api/v1/auth/login?${search.toString()}`;
}

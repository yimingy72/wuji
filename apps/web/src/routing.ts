const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const projectPathPattern = /^\/projects(?:\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:\/tasks(?:\/(new|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}))?)?)?\/?$/i;

export function isProjectId(value: unknown): value is string {
  return typeof value === 'string' && uuidPattern.test(value);
}

export const isTaskId = isProjectId;

export function normalizeReturnTo(value: unknown): string {
  if (typeof value !== 'string') return '/projects';
  const [pathname, query = ''] = value.split('?', 2);
  const draftMatch = /^\/projects\/([0-9a-f-]{36})\/drafts(?:\/([0-9a-f-]{36}))?\/?$/i.exec(pathname ?? '');
  if (draftMatch && isProjectId(draftMatch[1]) && (!draftMatch[2] || isProjectId(draftMatch[2]))) {
    const base = `/projects/${draftMatch[1]}/drafts${draftMatch[2] ? `/${draftMatch[2]}` : ''}`;
    const step = new URLSearchParams(query).get('step');
    return draftMatch[2] && step && /^[0-3]$/.test(step) ? `${base}?step=${step}` : base;
  }
  const tenantMatch = /^\/settings\/tenants\/([0-9a-f-]{36})\/models\/?$/i.exec(pathname ?? '');
  if (tenantMatch && isProjectId(tenantMatch[1])) return `/settings/tenants/${tenantMatch[1]}/models`;
  const match = projectPathPattern.exec(pathname ?? '');
  if (!match) return '/projects';
  if (!match[1]) return '/projects';
  if (!pathname?.includes('/tasks')) return `/projects/${match[1]}`;
  const normalized = match[2]
    ? `/projects/${match[1]}/tasks/${match[2]}`
    : `/projects/${match[1]}/tasks`;
  const search = new URLSearchParams(query);
  const cursorName = match[2] && match[2] !== 'new' ? 'list_cursor' : match[2] ? null : 'cursor';
  const cursor = cursorName ? search.get(cursorName) : null;
  return cursor && cursor.length <= 4096
    ? `${normalized}?${new URLSearchParams({ [cursorName!]: cursor }).toString()}`
    : normalized;
}

export function returnToFromRequest(request: Request): string {
  const url = new URL(request.url);
  return normalizeReturnTo(`${url.pathname}${url.search}`);
}

export function loginPath(returnTo: string): string {
  const search = new URLSearchParams({ return_to: normalizeReturnTo(returnTo) });
  return `/login?${search.toString()}`;
}

export function beginLoginPath(returnTo: string): string {
  const search = new URLSearchParams({ return_to: normalizeReturnTo(returnTo) });
  return `/api/v1/auth/login?${search.toString()}`;
}

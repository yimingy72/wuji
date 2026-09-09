import {
  validateError,
  validateProject,
  validateProjectPage,
  validateSession,
} from '@wuji/contracts/validators';

const session = {
  user_id: '00000000-0000-4000-8000-000000000103',
  display_name: 'Browser validator probe',
  csrf_token: 'fixture-only-not-a-real-token',
  expires_at: '2026-09-09T12:00:00Z',
  permissions_version: 1,
};
const project = {
  id: '00000000-0000-4000-8000-000000000102',
  tenant_id: '00000000-0000-4000-8000-000000000101',
  name: 'Browser project',
  permissions: ['project.read'],
};
const projectPage = { items: [project], next_cursor: null };
const error = {
  code: 'SERVICE_UNAVAILABLE',
  message: 'Dependency unavailable',
  trace_id: '00000000-0000-4000-8000-000000000111',
};

globalThis.__wujiContractProbe = {
  positive: [
    validateSession(session),
    validateProject(project),
    validateProjectPage(projectPage),
    validateError(error),
  ],
  negative: [
    validateSession({ ...session, user_id: 'invalid-uuid' }),
    validateSession({ ...session, expires_at: 'invalid-date' }),
    validateProjectPage({ items: [{ ...project, leaked: true }], next_cursor: null }),
    validateError({ ...error, trace_id: 'invalid-uuid' }),
  ],
};
document.body.dataset.ready = 'true';

declare global {
  var __wujiContractProbe: {
    positive: boolean[];
    negative: boolean[];
  };
}

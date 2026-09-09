import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { parse } from 'yaml';

const api = parse(readFileSync(new URL('../packages/contracts/openapi.yaml', import.meta.url), 'utf8'));
const fixture = JSON.parse(readFileSync(new URL('../packages/contracts/fixtures/phase1.json', import.meta.url), 'utf8'));
const phase1a = JSON.parse(readFileSync(new URL('../packages/contracts/fixtures/phase1a.json', import.meta.url), 'utf8'));
const lintIgnore = parse(readFileSync(new URL('../.redocly.lint-ignore.yaml', import.meta.url), 'utf8'));
const standaloneSource = readFileSync(new URL('../packages/contracts/generated/validators.js', import.meta.url), 'utf8');
const { validateError, validateProject, validateProjectPage, validateSession } = await import('../packages/contracts/generated/validators.js');
const schemaId = 'urn:wuji:phase1';
const schemas = JSON.parse(JSON.stringify(api.components.schemas).replaceAll('#/components/schemas/', `${schemaId}#/$defs/`));
const ajv = new Ajv2020({ allErrors: true, strict: true, strictRequired: false });
addFormats(ajv);
ajv.addSchema({ $id: schemaId, $defs: schemas });
const validate = (name, value) => {
  const check = ajv.getSchema(`${schemaId}#/$defs/${name}`);
  if (!check) throw new Error(`Missing schema ${name}`);
  return { valid: check(value), errors: check.errors };
};

describe('contract fixtures', () => {
  const cases = { session: 'Session', project: 'Project', draft: 'TaskDraft', scope: 'ApprovedScope', preview: 'TaskPreview', snapshot: 'TaskSnapshot', receipt: 'CommandReceipt', event: 'TaskEvent', artifact: 'Artifact', artifact_preview: 'ArtifactPreview', error: 'Error' };
  for (const [key, schema] of Object.entries(cases)) {
    it(`${key} follows ${schema}`, () => {
      const result = validate(schema, fixture[key]);
      expect(result.valid, JSON.stringify(result.errors)).toBe(true);
    });
  }
  it('compiles every published schema, including unused response pages', () => {
    for (const name of Object.keys(schemas)) expect(ajv.getSchema(`${schemaId}#/$defs/${name}`)).toBeTypeOf('function');
  });
});

describe('execution claims and strict inputs', () => {
  for (const state of ['completed', 'cancelled', 'failed']) {
    it(`${state} cannot hide active, unknown or authorized execution`, () => {
      const task = structuredClone(fixture.snapshot.task);
      task.state = state;
      task.allowed_actions = [];
      expect(validate('Task', task).valid).toBe(false);
      task.execution = { active_calls: 0, unknown_calls: 0, egress_state: 'revoked' };
      expect(validate('Task', task).valid).toBe(true);
      task.execution.unknown_calls = 1;
      expect(validate('Task', task).valid).toBe(false);
      task.execution.unknown_calls = 0;
      task.allowed_actions = ['resume'];
      expect(validate('Task', task).valid).toBe(false);
    });
  }
  it('paused requires drained calls and frozen egress', () => {
    const task = { ...structuredClone(fixture.snapshot.task), state: 'paused' };
    expect(validate('Task', task).valid).toBe(false);
    task.execution = { active_calls: 0, unknown_calls: 0, egress_state: 'frozen' };
    expect(validate('Task', task).valid).toBe(true);
  });
  it('rejects arbitrary tools, extra authority fields and missing limits', () => {
    expect(validate('TaskDraft', { ...fixture.draft, tool: 'bash' }).valid).toBe(false);
    expect(validate('TaskDraft', { ...fixture.draft, tenant_id: fixture.project.tenant_id }).valid).toBe(false);
    const draft = structuredClone(fixture.draft);
    delete draft.limits.max_total_requests;
    expect(validate('TaskDraft', draft).valid).toBe(false);
  });
  it('a blocked preview cannot advertise itself as creatable', () => {
    const preview = structuredClone(fixture.preview);
    preview.blockers = [{ code: 'MISSING_ADAPTER', message: 'HTTP Adapter is unavailable' }];
    expect(validate('TaskPreview', preview).valid).toBe(false);
    preview.can_create = false;
    expect(validate('TaskPreview', preview).valid).toBe(true);
  });
  it('rejects future event versions and unbounded evidence previews', () => {
    expect(validate('TaskEvent', { ...fixture.event, schema_version: '2.0' }).valid).toBe(false);
    expect(validate('ArtifactPreview', { ...fixture.artifact_preview, text: 'x'.repeat(65537) }).valid).toBe(false);
  });
  it('does not turn command acceptance into an execution success receipt', () => {
    expect(validate('CommandReceipt', { ...fixture.receipt, disposition: 'completed' }).valid).toBe(false);
  });
  it('requires session + CSRF for every exposed write operation', () => {
    for (const methods of Object.values(api.paths)) {
      for (const [method, operation] of Object.entries(methods)) {
        if (['post', 'put', 'patch', 'delete'].includes(method)) {
          expect(operation.security).toEqual([{ SessionCookie: [], CsrfToken: [] }]);
        }
      }
    }
  });
});

describe('Phase 1A contract increment', () => {
  it('preserves the original fixture while adding project.read', () => {
    expect(fixture.project.permissions).toEqual(['task.read', 'task.create', 'task.control', 'artifact.read']);
    expect(validate('Project', fixture.project).valid).toBe(true);
    expect(validate('Project', phase1a.project).valid).toBe(true);
  });

  it('publishes the four browser response validators as standalone ESM', () => {
    expect(Object.keys({ validateSession, validateProject, validateProjectPage, validateError }).sort()).toEqual([
      'validateError',
      'validateProject',
      'validateProjectPage',
      'validateSession',
    ]);
    expect(standaloneSource).not.toMatch(/require\s*\(|new Ajv|new\s+Function\s*\(|\.compile\(/);
    expect(validateSession(phase1a.session), JSON.stringify(validateSession.errors)).toBe(true);
    expect(validateProject(phase1a.project), JSON.stringify(validateProject.errors)).toBe(true);
    expect(validateProjectPage(phase1a.project_page), JSON.stringify(validateProjectPage.errors)).toBe(true);
    expect(validateError(phase1a.error), JSON.stringify(validateError.errors)).toBe(true);

    const extra = { ...phase1a.project, leaked: true };
    expect(validateProject(extra)).toBe(false);
    expect(validateProject.errors?.some(error => error.keyword === 'additionalProperties')).toBe(true);
  });

  it('defines the public auth flow and root health operations exactly', () => {
    expect(api.paths['/auth/login'].get.security).toEqual([]);
    expect(Object.keys(api.paths['/auth/login'].get.responses)).toContain('302');
    expect(api.paths['/auth/callback'].get.security).toEqual([]);
    expect(Object.keys(api.paths['/auth/callback'].get.responses)).toEqual(['303']);
    expect(api.paths['/auth/logout'].post.security).toEqual([{ SessionCookie: [], CsrfToken: [] }]);
    expect(Object.keys(api.paths['/auth/logout'].post.responses)).toContain('204');
    for (const path of ['/health/live', '/health/ready']) {
      expect(api.paths[path].get.security).toEqual([]);
      expect(api.paths[path].get.servers).toEqual([{ url: '/' }]);
    }
    expect(Object.keys(api.paths['/health/ready'].get.responses)).toContain('503');
    expect(lintIgnore).toEqual({
      'packages/contracts/openapi.yaml': {
        'operation-4xx-response': [
          '#/paths/~1auth~1callback/get/responses',
          '#/paths/~1health~1live/get/responses',
          '#/paths/~1health~1ready/get/responses',
        ],
      },
    });
  });

  it('keeps business routes and pagination names compatible', () => {
    expect(api.servers).toEqual([{ url: '/api/v1', description: 'Same-origin platform API' }]);
    expect(api.components.parameters.PageSize.name).toBe('limit');
    expect(api.components.parameters.PageCursor.name).toBe('cursor');
    expect(Object.keys(api.paths['/projects'].get.responses)).toContain('500');
    expect(api.paths['/projects'].get.description).toContain('(created_at, id) descending');
    expect(api.paths['/projects'].get.description).toContain('permissions version');
    expect(api.paths['/projects/{project_id}'].get.responses['200'].content['application/json'].schema.$ref).toBe('#/components/schemas/Project');
    expect(api.paths['/projects/{project_id}'].get.responses['403']).toBeUndefined();
    expect(validate('HealthStatus', phase1a.live).valid).toBe(true);
    expect(validate('HealthStatus', phase1a.ready).valid).toBe(true);
  });

  it('limits declared return paths to project routes with UUID-shaped identifiers', () => {
    const returnTo = api.paths['/auth/login'].get.parameters.find(parameter => parameter.name === 'return_to');
    const allowed = new RegExp(returnTo.schema.pattern);
    expect(allowed.test('/projects')).toBe(true);
    expect(allowed.test('/projects/')).toBe(true);
    expect(allowed.test('/projects/00000000-0000-0000-0000-000000000102')).toBe(true);
    for (const rejected of ['/projects/arbitrary', '/projects/../login', '/projects\\login', '//projects']) {
      expect(allowed.test(rejected)).toBe(false);
    }
  });
});

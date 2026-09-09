import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { parse } from 'yaml';

const api = parse(readFileSync(new URL('../packages/contracts/openapi.yaml', import.meta.url), 'utf8'));
const fixture = JSON.parse(readFileSync(new URL('../packages/contracts/fixtures/phase1.json', import.meta.url), 'utf8'));
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

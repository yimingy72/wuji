import { mkdir, readFile, writeFile } from 'node:fs/promises';
import Ajv2020 from 'ajv/dist/2020.js';
import standaloneCode from 'ajv/dist/standalone/index.js';
import addFormats from 'ajv-formats';
import openapiTS, { astToString } from 'openapi-typescript';
import { parse } from 'yaml';

const source = new URL('../packages/contracts/openapi.yaml', import.meta.url);
const generatedDirectory = new URL('../packages/contracts/generated/', import.meta.url);
const typeDestination = new URL('api.d.ts', generatedDirectory);
const validatorDestination = new URL('validators.js', generatedDirectory);
const validatorTypeDestination = new URL('validators.d.ts', generatedDirectory);
const schemaId = 'urn:wuji:contracts:0.5';
const validatorSchemas = {
  validateSession: 'Session',
  validateProject: 'Project',
  validateProjectPage: 'ProjectPage',
  validateApprovedScope: 'ApprovedScope',
  validateScopePage: 'ScopePage',
  validateTaskPreview: 'TaskPreview',
  validateTask: 'Task',
  validateTaskPage: 'TaskPage',
  validateTaskSnapshot: 'TaskSnapshot',
  validateCommandReceipt: 'CommandReceipt',
  validateEventPage: 'EventPage',
  validateSavedTaskDraft: 'SavedTaskDraft',
  validateSavedTaskDraftPage: 'SavedTaskDraftPage',
  validateTenantPage: 'TenantPage',
  validateModelDefinitionPage: 'ModelDefinitionPage',
  validateModelVersion: 'ModelVersion',
  validateModelVersionPage: 'ModelVersionPage',
  validateModelOperation: 'ModelOperation',
  validateScenarioProfilePage: 'ScenarioProfilePage',
  validateTaskCreationPreview: 'TaskCreationPreview',
  validateAgentRunPage: 'AgentRunPage',
  validateToolCallPage: 'ToolCallPage',
  validateArtifactPage: 'ArtifactPage',
  validateBlackBoardSnapshot: 'BlackBoardSnapshot',
  validateTaskResult: 'TaskResult',
  validateError: 'Error',
};

const sourceText = await readFile(source, 'utf8');
const api = parse(sourceText);
const schemas = JSON.parse(
  JSON.stringify(api.components.schemas).replaceAll('#/components/schemas/', `${schemaId}#/$defs/`),
);

const typeOutput = astToString(await openapiTS(source));
const ajv = new Ajv2020({
  allErrors: true,
  strict: true,
  strictRequired: false,
  code: { esm: true, lines: true, source: true },
});
addFormats(ajv);
ajv.addSchema({ $id: schemaId, $defs: schemas });

const standaloneExports = Object.fromEntries(
  Object.entries(validatorSchemas).map(([exportName, schemaName]) => {
    const reference = `${schemaId}#/$defs/${schemaName}`;
    if (!ajv.getSchema(reference)) throw new Error(`OpenAPI does not define ${schemaName}.`);
    return [exportName, reference];
  }),
);
const validatorOutput = convertRuntimeHelpersToEsm(standaloneCode(ajv, standaloneExports));
const validatorTypeOutput = `import type { components } from './api.js';

export interface ContractValidationError {
  readonly instancePath: string;
  readonly schemaPath: string;
  readonly keyword: string;
  readonly params: Record<string, unknown>;
  readonly message?: string;
}

export interface ContractValidator<T> {
  (value: unknown): value is T;
  errors: readonly ContractValidationError[] | null;
}

export declare const validateSession: ContractValidator<components['schemas']['Session']>;
export declare const validateProject: ContractValidator<components['schemas']['Project']>;
export declare const validateProjectPage: ContractValidator<components['schemas']['ProjectPage']>;
export declare const validateApprovedScope: ContractValidator<components['schemas']['ApprovedScope']>;
export declare const validateScopePage: ContractValidator<components['schemas']['ScopePage']>;
export declare const validateTaskPreview: ContractValidator<components['schemas']['TaskPreview']>;
export declare const validateTask: ContractValidator<components['schemas']['Task']>;
export declare const validateTaskPage: ContractValidator<components['schemas']['TaskPage']>;
export declare const validateTaskSnapshot: ContractValidator<components['schemas']['TaskSnapshot']>;
export declare const validateCommandReceipt: ContractValidator<components['schemas']['CommandReceipt']>;
export declare const validateEventPage: ContractValidator<components['schemas']['EventPage']>;
export declare const validateSavedTaskDraft: ContractValidator<components['schemas']['SavedTaskDraft']>;
export declare const validateSavedTaskDraftPage: ContractValidator<components['schemas']['SavedTaskDraftPage']>;
export declare const validateTenantPage: ContractValidator<components['schemas']['TenantPage']>;
export declare const validateModelDefinitionPage: ContractValidator<components['schemas']['ModelDefinitionPage']>;
export declare const validateModelVersion: ContractValidator<components['schemas']['ModelVersion']>;
export declare const validateModelVersionPage: ContractValidator<components['schemas']['ModelVersionPage']>;
export declare const validateModelOperation: ContractValidator<components['schemas']['ModelOperation']>;
export declare const validateScenarioProfilePage: ContractValidator<components['schemas']['ScenarioProfilePage']>;
export declare const validateTaskCreationPreview: ContractValidator<components['schemas']['TaskCreationPreview']>;
export declare const validateAgentRunPage: ContractValidator<components['schemas']['AgentRunPage']>;
export declare const validateToolCallPage: ContractValidator<components['schemas']['ToolCallPage']>;
export declare const validateArtifactPage: ContractValidator<components['schemas']['ArtifactPage']>;
export declare const validateBlackBoardSnapshot: ContractValidator<components['schemas']['BlackBoardSnapshot']>;
export declare const validateTaskResult: ContractValidator<components['schemas']['TaskResult']>;
export declare const validateError: ContractValidator<components['schemas']['Error']>;
`;

const outputs = [
  [typeDestination, typeOutput],
  [validatorDestination, validatorOutput],
  [validatorTypeDestination, validatorTypeOutput],
];

function convertRuntimeHelpersToEsm(output) {
  const imports = [];
  let converted = output;
  const helpers = [
    {
      pattern: /require\(["']ajv-formats\/dist\/formats["']\)/g,
      replacement: 'wujiAjvFormats',
      declaration: `import * as wujiAjvFormatsModule from 'ajv-formats/dist/formats.js';
const wujiAjvFormats = 'fullFormats' in wujiAjvFormatsModule
  ? wujiAjvFormatsModule
  : wujiAjvFormatsModule.default;`,
    },
    {
      pattern: /require\(["']ajv\/dist\/runtime\/ucs2length["']\)\.default/g,
      replacement: 'wujiAjvUcs2Length',
      declaration: `import * as wujiAjvUcs2LengthModule from 'ajv/dist/runtime/ucs2length.js';
const wujiAjvUcs2Length = typeof wujiAjvUcs2LengthModule.default === 'function'
  ? wujiAjvUcs2LengthModule.default
  : wujiAjvUcs2LengthModule.default.default;`,
    },
  ];

  for (const helper of helpers) {
    if (helper.pattern.test(converted)) {
      helper.pattern.lastIndex = 0;
      converted = converted.replace(helper.pattern, helper.replacement);
      imports.push(helper.declaration);
    }
  }
  if (/\brequire\s*\(/.test(converted)) {
    throw new Error('Standalone validator emitted an unapproved CommonJS runtime helper.');
  }
  if (/\bnew\s+Function\s*\(|\beval\s*\(/.test(converted)) {
    throw new Error('Standalone validator emitted runtime code generation.');
  }
  return `${imports.join('\n')}\n${converted.trimEnd()}\n`;
}

if (process.argv.includes('--check')) {
  const stale = [];
  for (const [destination, expected] of outputs) {
    const existing = await readFile(destination, 'utf8').catch(() => '');
    if (existing !== expected) stale.push(destination.pathname.split('/').at(-1));
  }
  if (stale.length > 0) {
    throw new Error(`Generated contracts are stale: ${stale.join(', ')}. Run pnpm contracts:generate and include the output.`);
  }
  console.log('Generated TypeScript types and standalone validators match OpenAPI.');
} else {
  await mkdir(generatedDirectory, { recursive: true });
  for (const [destination, output] of outputs) await writeFile(destination, output);
  console.log('Generated contract types and standalone validators.');
}

import type { components } from './api.js';

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
export declare const validateError: ContractValidator<components['schemas']['Error']>;

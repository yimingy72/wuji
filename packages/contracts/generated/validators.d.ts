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
export declare const validateError: ContractValidator<components['schemas']['Error']>;

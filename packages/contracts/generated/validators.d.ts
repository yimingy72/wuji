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
export declare const validateAssessmentView: ContractValidator<components['schemas']['AssessmentView']>;
export declare const validateObservationPage: ContractValidator<components['schemas']['ObservationPage']>;
export declare const validateVerificationPage: ContractValidator<components['schemas']['VerificationPage']>;
export declare const validateVerificationDetail: ContractValidator<components['schemas']['VerificationDetail']>;
export declare const validateError: ContractValidator<components['schemas']['Error']>;

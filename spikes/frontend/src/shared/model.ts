import { QueryClient } from '@tanstack/react-query';
import type { components } from '@wuji/contracts/types';
import rawFixture from '@wuji/contracts/fixtures';

export type Task = components['schemas']['Task'];
export type TaskState = components['schemas']['TaskState'];
export type Draft = components['schemas']['TaskDraft'];
// JSON fixtures are validated against OpenAPI by the contract test suite.
export const initialTask = rawFixture.snapshot.task as Task;
export const initialDraft = rawFixture.draft as Draft;
export const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity }, mutations: { retry: false } } });
let demoTask = structuredClone(initialTask);
let demoEvidenceAvailable = true;
export const taskKey = ['prototype', initialTask.tenant_id, initialTask.project_id, 'task', initialTask.id] as const;
export const taskQuery = { queryKey: taskKey, queryFn: async () => structuredClone(demoTask) };
export const taskPath = `/tasks/${initialTask.id}`;
export const artifactPath = `/evidence/${rawFixture.artifact.id}`;
export const stateLabel: Record<TaskState, string> = {
  queued: '等待启动', provisioning: '准备环境', running: '运行中', completing: '完成中', completed: '已完成',
  pausing: '暂停中', paused: '已暂停', cancelling: '取消中', cancelled: '已取消', reconciling: '结果核对中', failed: '已失败',
};
export function hasDemoEvidence() { return demoEvidenceAvailable; }
export async function createDemoTask(draft: Draft) {
  demoEvidenceAvailable = false;
  demoTask = { ...structuredClone(initialTask), name: draft.name.trim(), state: 'queued', version: 1, allowed_actions: ['cancel'], execution: { active_calls: 0, unknown_calls: 0, egress_state: 'pending' } };
  await queryClient.invalidateQueries({ queryKey: taskKey });
}
export async function cancelDemoTask(task: Task) {
  demoTask = { ...structuredClone(task), state: 'cancelling', allowed_actions: [], version: task.version + 1 };
  await queryClient.invalidateQueries({ queryKey: taskKey });
}
export async function stopDemoTask(task: Task) {
  demoTask = { ...structuredClone(task), state: 'cancelled', cleanup_state: 'cleaned', stop_reason: 'user_cancelled', allowed_actions: [], execution: { active_calls: 0, unknown_calls: 0, egress_state: 'revoked' }, version: task.version + 1 };
  await queryClient.invalidateQueries({ queryKey: taskKey });
}
export { rawFixture };

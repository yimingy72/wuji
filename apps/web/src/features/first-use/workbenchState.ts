import type { LaunchView, TaskView } from '../../v2WorkbenchApi';

export function taskStatusLabel(
  task: Pick<TaskView, 'desired_state' | 'observed_state' | 'result_outcome'> | null,
  launch: Pick<LaunchView, 'phase' | 'phase_status'> | null,
): string {
  if (!task) return '等待选择 Task';
  if (launch?.phase_status === 'reconciling' || task.observed_state === 'reconciling') return '待核对';
  if (task.desired_state === 'cancel' && task.observed_state === 'quiescing') return '已停止';
  if (launch?.phase_status === 'pending' || launch?.phase_status === 'running') return `启动${launch.phase}中`;
  if (launch?.phase_status === 'blocked' || launch?.phase_status === 'failed') return '启动阻断';
  if (launch?.phase_status === 'cancelled') return '取消受理';
  if (task.observed_state === 'ready') return '已创建未启动';
  if (task.observed_state === 'running') return '运行中';
  if (task.observed_state === 'paused') return '已暂停';
  if (task.observed_state === 'quiescing') return '停止收敛中';
  if (task.observed_state === 'closed' && task.result_outcome === 'partial') return '部分结果';
  if (task.observed_state === 'closed') return '已停止';
  return task.observed_state;
}

export function commandStatusMessage(command: string, label: string, fallback: string): string {
  return command === 'cancel' && label === '已停止' ? '取消已确认；实际 Task 已停止。' : fallback;
}

export function selectAuthorizedTaskId(
  taskIds: readonly string[],
  requestedTaskId: string | null,
  sessionTaskId: string | null | undefined,
  compatibleTaskId: string,
): string | null {
  const authorized = new Set(taskIds);
  if (requestedTaskId && authorized.has(requestedTaskId)) return requestedTaskId;
  if (sessionTaskId && authorized.has(sessionTaskId)) return sessionTaskId;
  if (compatibleTaskId && authorized.has(compatibleTaskId)) return compatibleTaskId;
  return taskIds[0] ?? null;
}

export function includeRequestedTask<T extends { readonly task_id: string }>(
  items: readonly T[],
  requested: T | null,
): T[] {
  if (!requested || items.some((item) => item.task_id === requested.task_id)) return [...items];
  return [requested, ...items];
}

export function isCurrentRequest(generation: number, currentGeneration: number, taskId: string, currentTaskId: string): boolean {
  return generation === currentGeneration && taskId === currentTaskId;
}

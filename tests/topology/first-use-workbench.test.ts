import { describe, expect, test, vi } from 'vitest';
import { artifactContentPath, beginLocalWorkbenchSession, materialPath } from '../../apps/web/src/v2WorkbenchApi';
import { resolveTaskSelection } from '../../apps/web/src/features/first-use/FirstUseWorkbench';
import { includeRequestedTask, isCurrentRequest, selectAuthorizedTaskId, taskStatusLabel } from '../../apps/web/src/features/first-use/workbenchState';

describe('first-use workbench state', () => {
  test('keeps an unstarted task visibly separate from running and stopped states', () => {
    expect(taskStatusLabel({ observed_state: 'ready', result_outcome: null }, { phase: 'not_requested', phase_status: 'not_requested' })).toBe('已创建未启动');
    expect(taskStatusLabel({ observed_state: 'running', result_outcome: null }, { phase: 'prepare', phase_status: 'running' })).toBe('启动prepare中');
    expect(taskStatusLabel({ observed_state: 'reconciling', result_outcome: 'inconclusive' }, { phase: 'wire', phase_status: 'reconciling' })).toBe('待核对');
    expect(taskStatusLabel({ observed_state: 'closed', result_outcome: 'partial' }, { phase: 'ready', phase_status: 'succeeded' })).toBe('部分结果');
  });

  test('never selects a URL task or session task that is absent from the authorized list', () => {
    expect(selectAuthorizedTaskId(['task-b', 'task-c'], 'task-a', 'task-a', 'task-a')).toBe('task-b');
    expect(selectAuthorizedTaskId(['task-b', 'task-c'], null, 'task-c', 'task-a')).toBe('task-c');
  });

  test('keeps an explicit created task ahead of a stale directory and initial session hint', () => {
    expect(resolveTaskSelection(['task-old'], null, 'task-old', 'task-old', 'task-new')).toBe('task-new');
    expect(resolveTaskSelection(['task-new', 'task-old'], null, 'task-old', 'task-old', 'task-new')).toBe('task-new');
    expect(resolveTaskSelection(['task-old'], null, 'task-old', 'task-old', null)).toBe('task-old');
  });

  test('includes an authorized URL task that is outside the first directory page', () => {
    const requested = { task_id: 'task-new', name: 'new' };
    expect(includeRequestedTask([{ task_id: 'task-old', name: 'old' }], requested)).toEqual([
      requested,
      { task_id: 'task-old', name: 'old' },
    ]);
    expect(includeRequestedTask([requested], requested)).toEqual([requested]);
  });

  test('rejects a late response after a task generation switch', () => {
    expect(isCurrentRequest(4, 5, 'task-a', 'task-b')).toBe(false);
    expect(isCurrentRequest(5, 5, 'task-b', 'task-b')).toBe(true);
  });

  test('uses the public material preview and separate immutable download paths', () => {
    expect(materialPath('task/a', 'artifact/1', '7')).toBe('/api/v2/tasks/task%2Fa/artifacts/artifact%2F1/material?version=7');
    expect(artifactContentPath('artifact/1', '7')).toBe('/api/v2/artifacts/artifact%2F1/content?version=7');
  });

  test('sends only the in-memory local access code to login and normalizes the server mode', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ authenticated: true, mode: 'local_single_operator', project_id: 'project-first-use', display_name: 'operator', initial_task_id: null }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const session = await beginLocalWorkbenchSession('/auth/login', 'one-time-access-code', new AbortController().signal);
    expect(session.identity_mode).toBe('local_single_operator');
    expect(fetchMock).toHaveBeenCalledWith('/auth/login', expect.objectContaining({ method: 'POST', credentials: 'include', headers: expect.objectContaining({ 'X-Wuji-Local-Access': 'one-time-access-code' }) }));
    expect(fetchMock.mock.calls[0]?.[1]?.body).toBeUndefined();
    vi.unstubAllGlobals();
  });
});

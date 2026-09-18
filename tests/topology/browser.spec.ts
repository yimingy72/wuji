import { expect, test } from '@playwright/test';

const themes = ['silver', 'glacier', 'celadon', 'slate', 'graphite'] as const;

test('fixed snapshot remains keyboard-readable and cannot issue graph mutations', async ({ page }) => {
  await page.goto('/?theme=silver');
  await expect(page.getByRole('region', { name: '任务拓扑图' })).toBeVisible();
  await expect(page.locator('.react-flow__node')).toHaveCount(13);
  await expect(page.locator('.react-flow__handle.connectable')).toHaveCount(0);
  await expect(page.locator('.react-flow__edgeupdater')).toHaveCount(0);

  const oldClaim = page.locator('.react-flow__node[data-id="claim:claim-1@1"]');
  await oldClaim.getByRole('button', { name: /Fact.*服务返回固定版本/ }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('selection')).toContainText('"revision":"1"');
  await page.keyboard.press('Delete');
  await expect(page.locator('.react-flow__node')).toHaveCount(13);
  await expect(page.getByTestId('command-events')).toHaveText('0');

  await page.getByText('列表', { exact: true }).click();
  const currentClaim = page.getByRole('button', { name: /claim.*服务可能返回新版本/i });
  await currentClaim.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('selection')).toContainText('"revision":"2"');
  await expect(page.getByText('支持旧修订', { exact: true })).toBeVisible();

  await page.getByText('画布', { exact: true }).click();
  const viewport = page.locator('.react-flow__viewport');
  const beforeIncrement = await viewport.getAttribute('style');
  await page.getByRole('button', { name: '新增修订' }).click();
  await expect(page.locator('.react-flow__node')).toHaveCount(14);
  await expect(viewport).toHaveAttribute('style', beforeIncrement ?? '');

  const pinnedClaim = page.locator('.react-flow__node[data-id="claim:claim-1@2"]');
  await expect(pinnedClaim).not.toHaveClass(/draggable/);

  const intentNode = page.locator('.react-flow__node[data-id="intent:intent-1@4"]');
  const intentBox = await intentNode.boundingBox();
  expect(intentBox).not.toBeNull();
  if (intentBox) {
    await page.mouse.move(intentBox.x + 12, intentBox.y + 12);
    await page.mouse.down();
    await page.mouse.move(intentBox.x + 72, intentBox.y + 52, { steps: 4 });
    await page.mouse.up();
  }
  await expect.poll(async () => Number(await page.getByTestId('layout-events').textContent())).toBeGreaterThan(0);
  await expect(page.getByTestId('layout-revision')).toHaveText('17');
});

test('request dimensions isolate an old snapshot and ignore its late completion', async ({ page }) => {
  await page.goto('/?theme=silver&case=request-isolation');
  await expect(page.getByRole('button', { name: '执行 重新核对' })).toBeVisible();
  await expect(page.getByText('任务 A 授权入口', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '更换读取器' }).click();
  await expect(page.getByText('任务 A 授权入口', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '执行 重新核对' })).toHaveCount(0);
  await expect(page.getByText('正在读取拓扑', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '切换任务 B' }).click();
  await page.getByRole('button', { name: '完成旧任务 A 请求' }).click();
  await expect(page.getByText('任务 A 授权入口', { exact: true })).toHaveCount(0);
  await expect(page.getByText('正在读取拓扑', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '完成任务 B 请求' }).click();
  await expect(page.getByText('任务 B 授权入口', { exact: true })).toBeVisible();
  await expect(page.getByText('任务 A 授权入口', { exact: true })).toHaveCount(0);
});

test('live actions invoke callbacks while history exposes no action or callback path', async ({ page }) => {
  await page.goto('/?theme=graphite');
  const command = page.getByRole('button', { name: '执行 重新核对' });
  await expect(command).toBeVisible();
  await command.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('command-events')).toHaveText('1');
  await expect(page.getByRole('button', { name: '展开关联' })).toBeVisible();
  await page.getByRole('button', { name: '展开关联' }).click();
  await expect(page.getByTestId('expand-events')).toHaveText('1');

  await page.goto('/?theme=graphite&mode=history');
  await expect(page.getByRole('region', { name: '任务拓扑图' })).toBeVisible();
  await expect(page.getByRole('button', { name: '执行 重新核对' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '展开关联' })).toHaveCount(0);
  await page.getByRole('button', { name: /Fact.*服务返回固定版本/ }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('command-events')).toHaveText('0');
  await expect(page.getByTestId('expand-events')).toHaveText('0');
});

test('the same formal component renders in all five shared themes', async ({ page }) => {
  for (const theme of themes) {
    await page.goto(`/?theme=${theme}`);
    await expect(page.locator('html')).toHaveAttribute('data-palette', theme);
    await expect(page.getByRole('region', { name: '任务拓扑图' })).toBeVisible();
    await page.screenshot({
      path: `tests/topology/screenshots/${theme}.png`,
      fullPage: true,
    });
  }
});

async function dragNodeBy(page: import('@playwright/test').Page, selector: string, dx: number, dy: number) {
  const node = page.locator(selector);
  await node.waitFor({ state: 'visible' });
  const box = await node.boundingBox();
  expect(box).not.toBeNull();
  if (!box) return;
  await page.mouse.move(box.x + 12, box.y + 12);
  await page.mouse.down();
  for (let step = 1; step <= 8; step += 1) {
    await page.mouse.move(box.x + 12 + (dx * step) / 8, box.y + 12 + (dy * step) / 8, { steps: 1 });
  }
  await page.mouse.up();
}

test('a failed conflict reload keeps the write queue frozen until a read succeeds', async ({ page }) => {
  await page.goto('/?theme=silver&case=layout-reload-failure');
  await expect(page.getByRole('region', { name: '任务拓扑图' })).toBeVisible();
  await expect(page.getByTestId('fault-server-revision')).toHaveText('4');
  await expect(page.getByTestId('fault-write-attempts')).toHaveText('0');

  // Another tab moves the server revision ahead of this page.
  await page.getByRole('button', { name: '其他标签页保存' }).click();
  await expect(page.getByTestId('fault-server-revision')).toHaveText('5');
  const otherTabLayout = await page.getByTestId('fault-server-layout').textContent();

  // The stale PUT is refused and the read-only recovery fails as well.
  await dragNodeBy(page, '.react-flow__node[data-id="intent:intent-1@4"]', 60, 40);
  await expect(page.getByTestId('fault-write-status')).toContainText('409');
  await expect(page.getByTestId('fault-write-attempts')).toHaveText('1');
  await expect(page.getByTestId('fault-read-status')).toContainText('503');

  // The rejected edit is never requeued, and a new gesture is refused too.
  await page.waitForTimeout(600);
  await expect(page.getByTestId('fault-write-attempts')).toHaveText('1');
  await dragNodeBy(page, '.react-flow__node[data-id="intent:intent-1@4"]', -40, -30);
  await expect(page.getByTestId('fault-write-attempts')).toHaveText('1');
  await expect(page.getByTestId('fault-server-layout')).toHaveText(otherTabLayout ?? '');

  // An explicit read that still fails stays read-only.
  const reload = page.getByRole('button', { name: '重新读取' });
  await expect(reload).toHaveCount(1);
  const failedReads = Number(await page.getByTestId('fault-read-attempts').textContent());
  await reload.click();
  await expect.poll(async () => Number(await page.getByTestId('fault-read-attempts').textContent())).toBeGreaterThan(failedReads);
  await expect(page.getByTestId('fault-write-attempts')).toHaveText('1');

  // Once the read succeeds the conflict clears and a new edit saves normally.
  await page.getByRole('button', { name: '允许读取' }).click();
  await reload.click();
  await expect(page.getByTestId('fault-read-status')).toContainText('200');
  await dragNodeBy(page, '.react-flow__node[data-id="intent:intent-1@4"]', 40, 30);
  await expect(page.getByTestId('fault-write-status')).toContainText('200');
  await expect(page.getByTestId('fault-write-attempts')).toHaveText('2');
  await expect(page.getByTestId('fault-server-revision')).toHaveText('6');
});

test('a task switch while the layout conflict is unresolved writes nothing', async ({ page }) => {
  await page.goto('/?theme=silver&case=layout-reload-failure');
  await expect(page.getByRole('region', { name: '任务拓扑图' })).toBeVisible();
  await page.getByRole('button', { name: '其他标签页保存' }).click();
  await expect(page.getByTestId('fault-server-revision')).toHaveText('5');

  await dragNodeBy(page, '.react-flow__node[data-id="intent:intent-1@4"]', 60, 40);
  await expect(page.getByTestId('fault-write-attempts')).toHaveText('1');
  await expect(page.getByTestId('fault-read-status')).toContainText('task-A');

  await page.getByRole('button', { name: '切换任务' }).click();
  await expect(page.getByTestId('fault-read-status')).toContainText('task-B');
  await page.waitForTimeout(600);
  await expect(page.getByTestId('fault-write-attempts')).toHaveText('1');
});

test('first-use workbench creates a ready task and starts only after an explicit command', async ({ page }) => {
  let started = false;
  const startKeys: string[] = [];
  const task = (running: boolean) => ({
    task_id: 'task-first-use',
    tenant_id: 'tenant-first-use',
    project_id: 'project-first-use',
    version: running ? '2' : '1',
    name: '首用安全入口',
    scenario: 'web_single',
    desired_state: running ? 'run' : 'pause',
    observed_state: running ? 'running' : 'ready',
    goal_revision: '1',
    execution_epoch: running ? '1' : '0',
    activated_at: running ? '2099-01-01T00:00:00.000Z' : null,
    close_trigger: null,
    result_outcome: null,
    allowed_actions: running ? ['pause', 'cancel'] : ['start', 'cancel'],
  });
  const readiness = {
    task_id: 'task-first-use',
    definition_digest: 'sha256:definition-first-use',
    observed_at: '2099-01-01T00:00:00.000Z',
    can_request_start: true,
    checks: [
      { id: 'identity', layer: 'identity', status: 'pass', reason_code: 'identity_valid', observed_at: '2099-01-01T00:00:00.000Z', evidence_ref: null, remediation_owner: 'application', message: 'local_single_operator 已核验' },
      { id: 'target', layer: 'target', status: 'unknown', reason_code: 'not_measured', observed_at: '2099-01-01T00:00:00.000Z', evidence_ref: null, remediation_owner: 'application', message: '尚未进行网络实测' },
    ],
  };
  const launch = () => ({
    operation_id: started ? 'operation-first-use' : null,
    command_id: started ? 'command-start-first-use' : null,
    task_id: 'task-first-use',
    definition_digest: 'sha256:definition-first-use',
    profile_digest: started ? 'sha256:profile-first-use' : null,
    runtime_attempt: started ? '1' : null,
    execution_epoch: started ? '1' : null,
    phase: started ? 'ready' : 'not_requested',
    phase_status: started ? 'succeeded' : 'not_requested',
    reason_code: null,
    allowed_actions: started ? ['pause', 'cancel'] : ['start', 'cancel'],
    observed_at: '2099-01-01T00:00:00.000Z',
  });
  await page.route('**/api/v2/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === 'GET' && url.pathname === '/api/v2/tasks' && url.searchParams.get('project_id') === 'project-first-use') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: started ? [task(true)] : [], next_cursor: null }) });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/v2/projects/project-first-use/task-options') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ project_id: 'project-first-use', model_profiles: [{ ref: 'profile/deepseek', name: 'DeepSeek observe', revision: '7', digest: 'sha256:model', capabilities: ['chat_completions', 'non_thinking', 'max_calls:12'], real_model_allowed: true }], runtime_profiles: [{ ref: 'runtime/fixture', name: 'Fixture first-use', revision: '4', digest: 'sha256:runtime', capabilities: ['http_target', 'max_calls:12'], real_model_allowed: true }], missing: [] }) });
      return;
    }
    if (request.method() === 'POST' && url.pathname === '/api/v2/tasks') {
      expect(request.headers()['idempotency-key']).toBeTruthy();
      console.log(`[A4-HTTP] POST /api/v2/tasks Idempotency-Key=${request.headers()['idempotency-key']}`);
      const body = JSON.parse(request.postData() ?? '{}') as { entry_points?: string[]; budget?: { amount?: string } };
      expect(body.entry_points).toEqual(['https://approved.example.test/safe?view=summary']);
      expect(body.budget?.amount).toBe('1');
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(task(false)) });
      return;
    }
    if (request.method() === 'POST' && url.pathname === '/api/v2/tasks/task-first-use/commands') {
      startKeys.push(request.headers()['idempotency-key'] ?? '');
      console.log(`[A4-HTTP] POST /api/v2/tasks/task-first-use/commands Idempotency-Key=${request.headers()['idempotency-key']}`);
      expect(JSON.parse(request.postData() ?? '{}')).toMatchObject({ command: 'start', expected_version: '1' });
      started = true;
      await route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ command_id: 'command-start-first-use', disposition: 'accepted', resource_ref: { entity_type: 'task', id: 'task-first-use', revision: '2' }, resource_version: '2', request_id: 'request-start-first-use', code: null }) });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/v2/tasks/task-first-use') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(task(started)) });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/v2/tasks/task-first-use/readiness') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(readiness) });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/v2/tasks/task-first-use/launch') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(launch()) });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/v2/tasks/task-first-use/topology') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ view_id: 'view-first-use', snapshot_id: 'snapshot-first-use', view_revision: '1', query_digest: 'sha256:query', access_scope_digest: 'sha256:scope', projection_version: 'v1', nodes: [{ id: 'origin:origin-first@1', ref: { entity_type: 'origin', id: 'origin-first', revision: '1' }, display_kind: 'origin', label: '已授权入口', state: 'ready', allowed_actions: [] }], edges: [], opaque_cursor: 'cursor-first-use', truncated: false, continuation: null, allowed_actions: [] }) });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/v2/tasks/task-first-use/layouts/knowledge-live') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ schema_version: 'wuji.api.v2', view_name: 'knowledge-live', layout_revision: '1', selection_mode: 'follow_latest', entries: [], viewport: { x: 0, y: 0, zoom: 1 } }) });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/v2/tasks/task-first-use/snapshots') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], opaque_cursor: null }) });
      return;
    }
    if (request.method() === 'GET' && url.pathname === '/api/v2/tasks/task-first-use/completion') {
      await route.fulfill({ status: 404, body: '' });
      return;
    }
    await route.fallback();
  });

  await page.goto('/?case=first-use&theme=silver');
  await expect(page.getByTestId('task-list')).toBeVisible();
  await page.getByTestId('new-task').click();
  await expect(page.getByTestId('task-create-form')).toBeVisible();
  await page.getByLabel('任务名称').fill('首用安全入口');
  await page.getByLabel('完整入口 URL').fill('https://approved.example.test/safe?view=summary');
  await page.getByLabel('任务目标').fill('仅验证获准入口并保留正文证据');
  await page.getByLabel('完成条件').fill('保存实际 HTTP 状态\n保留未执行原因');
  await page.getByLabel('授权截止时间').fill('2099-01-01T00:00');
  await page.getByLabel('Task 金额预算').fill('1');
  await page.getByLabel(/拥有目标访问授权/).check();
  await page.getByLabel(/允许本 Task/).check();
  await page.getByTestId('task-create-submit').click();
  await expect(page.getByTestId('task-status')).toContainText('已创建未启动');
  await expect(page.getByTestId('task-start')).toBeVisible();
  await expect.poll(() => startKeys.length).toBe(0);
  await page.getByTestId('task-start').click();
  await expect.poll(() => startKeys.length).toBe(1);
  await expect(page.getByTestId('task-status')).toContainText('运行中');
  await expect(page.getByTestId('launch-status')).toContainText('ready');
  await page.screenshot({ path: 'tests/topology/screenshots/first-use-workbench.png', fullPage: true });
});

test('a stale personal layout save reports the conflict and never rewrites the newer layout', async ({ page }) => {
  await page.goto('/?theme=silver&case=layout-conflict');
  await expect(page.getByRole('region', { name: '任务拓扑图' })).toBeVisible();
  await expect(page.getByTestId('server-revision')).toHaveText('4');
  await expect(page.getByTestId('write-attempts')).toHaveText('0');

  await page.getByRole('button', { name: '其他标签页保存' }).click();
  await expect(page.getByTestId('server-revision')).toHaveText('5');
  const otherTabLayout = await page.getByTestId('server-layout').textContent();

  await dragNodeBy(page, '.react-flow__node[data-id="intent:intent-1@4"]', 60, 40);

  await expect(page.getByTestId('write-status')).toContainText('409');
  await expect(page.getByRole('alert').filter({ hasText: '服务器布局已更新' })).toBeVisible();
  await expect(page.getByTestId('write-attempts')).toHaveText('1');
  await expect(page.getByTestId('server-layout')).toHaveText(otherTabLayout ?? '');
  await expect(page.getByTestId('server-revision')).toHaveText('5');

  // The user can keep working: a new edit after the conflict saves normally.
  await dragNodeBy(page, '.react-flow__node[data-id="intent:intent-1@4"]', 40, 30);
  await expect(page.getByTestId('write-status')).toContainText('200 6');
  await expect(page.getByTestId('write-attempts')).toHaveText('2');
  await expect(page.getByTestId('server-revision')).toHaveText('6');
});

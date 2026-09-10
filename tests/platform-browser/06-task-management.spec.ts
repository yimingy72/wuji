import { test, expect } from '@playwright/test';
import {
  validateCommandReceipt,
  validateScopePage,
  validateTaskPage,
  validateTaskPreview,
  validateTaskSnapshot,
} from '../../packages/contracts/generated/validators.js';
import { keycloakLogin, manifest } from './support';


test('lost create response recovers by original key, lists the task, and cancels it', async ({ page }) => {
  const run = await manifest();
  const user = run.seed_users.single_a;
  const projectId = user.project_ids[0]!;
  await keycloakLogin(page, user, `/projects/${projectId}/tasks/new`);

  const scopeResponse = await page.request.get(`/api/v1/projects/${projectId}/scopes`);
  expect(scopeResponse.status()).toBe(200);
  const scopePage: unknown = await scopeResponse.json();
  if (!validateScopePage(scopePage)) throw new Error('Scope response violates the public contract');
  const scope = scopePage.items[0];
  expect(scope).toBeTruthy();
  const target = new URL(scope!.origins[0]!);
  const allowedPrefix = scope!.allowed_path_prefixes[0]!;
  target.pathname = allowedPrefix === '/'
    ? '/browser-recovery'
    : `${allowedPrefix.replace(/\/$/, '')}/browser-recovery`;

  await page.getByLabel('批准范围', { exact: true }).focus();
  await page.getByLabel('批准范围', { exact: true }).press('ArrowDown');
  await page.getByLabel('批准范围', { exact: true }).press('Enter');
  await page.getByLabel('任务名称', { exact: true }).fill('Chrome 丢响应恢复');
  await page.getByLabel('目标 URL', { exact: true }).fill(target.href);
  const previewResponse = page.waitForResponse(response =>
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === `/api/v1/projects/${projectId}/task-previews`,
  );
  await page.getByRole('button', { name: '生成任务预览', exact: true }).click();
  const preview = await previewResponse;
  expect(preview.status()).toBe(200);
  const previewBody: unknown = await preview.json();
  if (!validateTaskPreview(previewBody)) throw new Error('Preview response violates the public contract');
  expect(previewBody.can_create).toBe(true);
  expect(previewBody.blockers).toEqual([]);

  let createKey: string | undefined;
  let committedTaskId: string | undefined;
  let resolveCreateCommit!: () => void;
  const createCommit = new Promise<void>(resolve => { resolveCreateCommit = resolve; });
  await page.route(`**/api/v1/projects/${projectId}/tasks`, async route => {
    createKey = route.request().headers()['idempotency-key'];
    const committed = await route.fetch();
    expect(committed.status()).toBe(202);
    const committedBody: unknown = await committed.json();
    if (!validateCommandReceipt(committedBody)) {
      throw new Error('Create response violates the public command receipt contract');
    }
    expect(committedBody.kind).toBe('create');
    expect(committedBody.project_id).toBe(projectId);
    committedTaskId = committedBody.task_id;
    await route.abort('failed');
    resolveCreateCommit();
  }, { times: 1 });
  await page.getByRole('button', { name: /创建任务|提交创建|执行任务/ }).click();
  await createCommit;
  await expect.poll(() => createKey).toMatch(/^[0-9a-f-]{36}$/i);
  await expect.poll(() => committedTaskId).toMatch(/^[0-9a-f-]{36}$/i);
  await expect(page.getByText('提交结果待确认', { exact: true })).toBeVisible();

  let lookupKey: string | undefined;
  let recoveredTaskId: string | undefined;
  page.on('request', request => {
    const path = new URL(request.url()).pathname;
    const marker = `/api/v1/projects/${projectId}/command-keys/`;
    if (path.startsWith(marker)) lookupKey = decodeURIComponent(path.slice(marker.length));
  });
  page.on('response', async response => {
    const path = new URL(response.url()).pathname;
    if (!path.startsWith(`/api/v1/projects/${projectId}/command-keys/`) || response.status() !== 200) return;
    const body: unknown = await response.json();
    if (!validateCommandReceipt(body)) {
      throw new Error('Reconciliation response violates the public command receipt contract');
    }
    expect(body.kind).toBe('create');
    expect(body.project_id).toBe(projectId);
    recoveredTaskId = body.task_id;
  });

  await page.reload();
  await expect(page.getByText('提交结果待确认', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '核对提交结果', exact: true }).click();
  await expect.poll(() => lookupKey).toBe(createKey);
  await expect.poll(() => recoveredTaskId).toMatch(/^[0-9a-f-]{36}$/i);
  expect(recoveredTaskId).toBe(committedTaskId);

  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/tasks/${committedTaskId}$`));
  await expect(page.getByRole('link', { name: '返回任务列表', exact: true })).toBeVisible();
  let listedMatchingIds: string[] | undefined;
  page.on('response', async response => {
    const parsed = new URL(response.url());
    if (response.request().method() !== 'GET'
      || parsed.pathname !== `/api/v1/projects/${projectId}/tasks`
      || response.status() !== 200) return;
    const body: unknown = await response.json();
    if (!validateTaskPage(body)) throw new Error('Task list violates the public contract');
    listedMatchingIds = body.items
      .filter(item => item.name === 'Chrome 丢响应恢复')
      .map(item => item.id);
  });
  await page.getByRole('link', { name: '返回任务列表', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/tasks$`));
  await expect.poll(() => listedMatchingIds).toEqual([committedTaskId]);
  await expect(page.getByText('Chrome 丢响应恢复', { exact: true })).toBeVisible();
  await page.goto(`/projects/${projectId}/tasks/${recoveredTaskId}`);
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/tasks/${recoveredTaskId}$`));
  await expect(page.getByText('Chrome 丢响应恢复', { exact: true })).toBeVisible();

  const cancelResponse = page.waitForResponse(response =>
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === `/api/v1/projects/${projectId}/tasks/${recoveredTaskId}/commands`
    && response.status() === 202,
  );
  const dialog = page.getByRole('dialog');
  await page.getByRole('button', { name: '取消任务', exact: true }).click();
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('确认取消任务');
  await dialog.getByRole('button', { name: '确认取消', exact: true }).click();
  await cancelResponse;
  const cancelledSnapshotResponse = await page.request.get(
    `/api/v1/projects/${projectId}/tasks/${recoveredTaskId}`,
  );
  expect(cancelledSnapshotResponse.status()).toBe(200);
  const cancelledSnapshot: unknown = await cancelledSnapshotResponse.json();
  if (!validateTaskSnapshot(cancelledSnapshot)) {
    throw new Error('Cancelled snapshot violates the public task snapshot contract');
  }
  expect(cancelledSnapshot.task.id).toBe(committedTaskId);
  expect(cancelledSnapshot.task.state).toBe('cancelled');
  expect(cancelledSnapshot.task.version).toBe(2);
  await expect(page.getByText('已取消', { exact: true })).toBeVisible();
  await page.screenshot({ path: `${run.artifacts_dir}/b23-task-management.png`, fullPage: true });
});

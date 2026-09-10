import { test, expect } from '@playwright/test';
import { validateScopePage, validateTaskPreview } from '../../packages/contracts/generated/validators.js';
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
  await page.route(`**/api/v1/projects/${projectId}/tasks`, async route => {
    createKey = route.request().headers()['idempotency-key'];
    const committed = await route.fetch();
    expect(committed.status()).toBe(202);
    await route.abort('failed');
  }, { times: 1 });
  await page.getByRole('button', { name: /创建任务|提交创建|执行任务/ }).click();
  await expect.poll(() => createKey).toMatch(/^[0-9a-f-]{36}$/i);

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
    const body = await response.json() as { task_id?: string };
    recoveredTaskId = body.task_id;
  });

  await page.reload();
  await expect(page.getByText('提交结果待确认', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '核对提交结果', exact: true }).click();
  await expect.poll(() => lookupKey).toBe(createKey);
  await expect.poll(() => recoveredTaskId).toMatch(/^[0-9a-f-]{36}$/i);

  await expect(page.getByRole('button', { name: '查看任务列表', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '查看任务列表', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/tasks$`));
  await expect(page.getByText('Chrome 丢响应恢复', { exact: true })).toBeVisible();
  await page.goto(`/projects/${projectId}/tasks/${recoveredTaskId}`);
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/tasks/${recoveredTaskId}$`));
  await expect(page.getByText('Chrome 丢响应恢复', { exact: true })).toBeVisible();

  const cancelResponse = page.waitForResponse(response =>
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === `/api/v1/projects/${projectId}/tasks/${recoveredTaskId}/commands`
    && response.status() === 202,
  );
  await page.getByRole('button', { name: /取消任务|取消/ }).click();
  const dialog = page.getByRole('dialog');
  if (await dialog.count()) {
    await dialog.getByRole('button', { name: /确认|确定|取消任务/ }).click();
  }
  await cancelResponse;
  await expect(page.getByText(/已取消|cancelled/i)).toBeVisible();
});

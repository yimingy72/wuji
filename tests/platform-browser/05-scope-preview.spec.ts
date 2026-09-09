import { test, expect } from '@playwright/test';
import { validateScopePage, validateTaskPreview } from '../../packages/contracts/generated/validators.js';
import { keycloakLogin, manifest } from './support';

// Independently authored by Luna; pinned to the delivered public API and labels during integration.
test('operator can preview an approved scope and creation remains unavailable', async ({ page }) => {
  const run = await manifest();
  const user = run.seed_users.single_a;
  const projectId = user.project_ids[0]!;
  await keycloakLogin(page, user, `/projects/${projectId}/tasks/new`);
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/tasks/new$`));
  await expect(page.getByRole('heading', { name: '任务草稿', exact: true })).toBeVisible();

  const scopeResponse = await page.request.get(`/api/v1/projects/${projectId}/scopes`);
  expect(scopeResponse.status()).toBe(200);
  const scopePage: unknown = await scopeResponse.json();
  if (!validateScopePage(scopePage)) throw new Error('Scope response violates the public contract');
  const scope = scopePage.items[0];
  expect(scope).toBeTruthy();
  const target = new URL(scope!.origins[0]!);
  target.pathname = scope!.allowed_path_prefixes[0]!.replace(/\/$/, '') + '/a';

  const picker = page.getByLabel('批准范围', { exact: true });
  await picker.focus();
  await picker.press('ArrowDown');
  await picker.press('Enter');
  await page.getByLabel('任务名称', { exact: true }).fill('B1 页面最小预览');
  await page.getByLabel('目标 URL', { exact: true }).fill(target.href);
  const responsePromise = page.waitForResponse(response =>
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === `/api/v1/projects/${projectId}/task-previews`);
  await page.getByRole('button', { name: '生成任务预览', exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const preview: unknown = await response.json();
  if (!validateTaskPreview(preview)) throw new Error('Preview response violates the public contract');
  expect(preview.draft.scope).toEqual(scope!.binding);
  expect(preview.draft.target_url).toBe(target.href);
  expect(preview.can_create).toBe(false);
  expect(preview.blockers.map(blocker => blocker.code)).toEqual(['CREATION_UNAVAILABLE']);
  const limits = Object.fromEntries(Object.entries(scope!.limits).map(([key, maximum]) =>
    [key, Math.min(maximum, preview.draft.limits[key as keyof typeof preview.draft.limits])],
  ));
  expect(preview.effective_scope.limits).toEqual(limits);

  const result = page.getByTestId('task-preview-result');
  await expect(result).toContainText('范围计算通过');
  await expect(result).toContainText('任务创建尚未开放');
  await expect(result).toContainText(target.href);
  await expect(page.getByRole('button', { name: /创建任务|提交创建|执行任务/ })).toHaveCount(0);
  await page.screenshot({ path: `${run.artifacts_dir}/b1-scope-preview.png`, fullPage: true });
});

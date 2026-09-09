import { test, expect } from '@playwright/test';
import { keycloakLogin, manifest } from './support';


test('operator can preview an approved scope and creation remains unavailable', async ({ page }) => {
  const run = await manifest();
  const user = run.seed_users.single_a;
  const projectId = user.project_ids[0]!;

  await keycloakLogin(page, user, `/projects/${projectId}/tasks/new`);
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/tasks/new$`));
  await expect(page.getByRole('heading', { name: /任务预览/ })).toBeVisible();

  const scope = page.getByLabel(/批准范围|Scope/).first();
  await scope.click();
  await page.getByRole('option').first().click();
  await page.getByLabel('任务名称', { exact: true }).fill('B1 页面最小预览');
  await page.getByLabel(/目标 URL|目标地址/).fill('https://training.example/public/a');
  await page.getByRole('button', { name: /预览有效范围/ }).click();

  await expect(page.getByText(/任务创建尚未开放|CREATION_UNAVAILABLE/)).toBeVisible();
  await expect(page.getByRole('button', { name: /创建任务|提交创建|执行任务/ })).toHaveCount(0);
  await page.screenshot({ path: `${run.artifacts_dir}/b1-scope-preview.png`, fullPage: true });
});

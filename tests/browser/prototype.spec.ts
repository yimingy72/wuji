import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

const task = '/tasks/00000000-0000-4000-8000-000000000005';
const artifact = '/evidence/00000000-0000-4000-8000-000000000009';

test.beforeAll(async () => { await mkdir('artifacts/workbench-current', { recursive: true }); });

test('list and preview flow invalidate changed inputs and show a queued task honestly', async ({ page }) => {
  await page.goto('/tasks');
  await expect(page.getByRole('heading', { name: '任务工作台', exact: true })).toBeVisible();
  await page.screenshot({ path: 'artifacts/workbench-current/tasks.png', fullPage: true, animations: 'disabled' });
  await page.getByRole('button', { name: '创建任务', exact: true }).click();
  await page.getByLabel('任务名称', { exact: true }).fill('');
  await page.getByRole('button', { name: '预览有效范围' }).click();
  await expect(page.getByRole('alert')).toHaveText('请填写任务名称');
  await page.getByLabel('任务名称', { exact: true }).fill('首个受控观察任务');
  await page.getByRole('button', { name: '预览有效范围' }).click();
  await expect(page.getByRole('button', { name: '创建任务' })).toBeVisible();
  await page.getByLabel('观察方法').click();
  await page.getByRole('option', { name: 'HEAD', exact: true }).click();
  await expect(page.getByRole('button', { name: '创建任务' })).toHaveCount(0);
  await page.getByRole('button', { name: '预览有效范围' }).click();
  await expect(page.getByRole('listbox')).toHaveCount(0);
  await page.screenshot({ path: 'artifacts/workbench-current/create.png', fullPage: true, animations: 'disabled' });
  await page.getByRole('button', { name: '创建任务' }).click();
  await expect(page.getByRole('heading', { name: '首个受控观察任务' })).toBeVisible();
  await expect(page.getByRole('region', { name: '任务执行' }).getByText('等待启动', { exact: true })).toBeVisible();
  await expect(page.getByText('执行环境就绪', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('link', { name: '查看完整证据' })).toHaveCount(0);
  await page.getByRole('button', { name: '取消任务', exact: true }).click();
  await expect(page.getByText('未产生观察记录', { exact: true })).toBeVisible();
  await expect(page.getByText('观察记录已保存', { exact: true })).toHaveCount(0);
});

test('cancel stays pending until a separate simulated execution receipt', async ({ page }) => {
  await page.goto(task);
  await page.getByRole('button', { name: '取消任务', exact: true }).click();
  await expect(page.getByRole('region', { name: '任务执行' }).getByText('取消中', { exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: '任务执行' }).getByText('已取消', { exact: true })).toHaveCount(0);
  await expect(page.getByText('取消请求已接受，等待停止回执')).toBeVisible();
  await page.screenshot({ path: 'artifacts/workbench-current/task-detail.png', fullPage: true, animations: 'disabled' });
  await page.getByRole('button', { name: '演示设置', exact: true }).click();
  await page.getByRole('button', { name: '模拟停止与清理回执' }).click();
  await expect(page.getByRole('region', { name: '任务执行' }).getByText('已取消', { exact: true })).toBeVisible();
  await expect(page.getByText('已清理', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: '取消任务', exact: true })).toHaveCount(0);
});

test('evidence remains inert text and the prototype never contacts external hosts', async ({ page }) => {
  const external: string[] = [];
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== 'http://127.0.0.1:4175') { external.push(url.origin); await route.abort(); }
    else await route.continue();
  });
  await page.goto(artifact);
  await expect(page.getByRole('heading', { name: 'HTTP 响应证据' })).toBeVisible();
  await expect(page.locator('pre')).toContainText('<script>window.__evidenceExecuted');
  await expect(page.locator('img[src*="external.example"]')).toHaveCount(0);
  expect(await page.evaluate(() => Object.hasOwn(window, '__evidenceExecuted'))).toBe(false);
  await page.screenshot({ path: 'artifacts/workbench-current/evidence.png', fullPage: true, animations: 'disabled' });
  expect(external).toEqual([]);
});

test('unknown execution, pending cleanup and denied data are distinct', async ({ page }) => {
  await page.goto(`${task}?scene=unknown`);
  await expect(page.getByRole('region', { name: '任务执行' }).getByText('结果核对中', { exact: true })).toBeVisible();
  await expect(page.getByText('有 1 个调用结果不明')).toBeVisible();
  await page.getByRole('button', { name: '演示设置', exact: true }).click();
  await page.getByLabel('演示场景').selectOption('cleanup');
  await expect(page.getByText('执行已停止，资源清理仍待完成')).toBeVisible();
  await page.getByRole('button', { name: '演示设置', exact: true }).click();
  await page.getByLabel('演示场景').selectOption('denied');
  await expect(page.getByRole('heading', { name: '当前项目不可访问' })).toBeVisible();
  await expect(page.getByText('https://training.example/public/', { exact: true })).toHaveCount(0);
});

test('deep links, keyboard navigation and narrow window remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/tasks');
  await expect(page.getByRole('heading', { name: '任务工作台', exact: true })).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: '跳到主要内容' })).toBeFocused();
  await page.screenshot({ path: 'artifacts/workbench-current/narrow.png', fullPage: true, animations: 'disabled' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.goto(artifact);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'HTTP 响应证据' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});


test('workbench keeps queue, execution and evidence connected', async ({ page }) => {
  await page.goto('/tasks');
  const execution = page.getByRole('region', { name: '任务执行' });
  const inspector = page.getByRole('complementary', { name: '证据检查器' });
  await execution.getByRole('tab', { name: '范围与限额' }).click();
  await expect(execution.getByText('/public/admin', { exact: true })).toBeVisible();
  await inspector.getByRole('tab', { name: '元数据' }).click();
  await expect(inspector.getByText('SHA-256', { exact: true })).toBeVisible();
  await page.getByRole('textbox', { name: '任务名称', exact: true }).fill('不存在的任务');
  await expect(execution).toHaveCount(0);
  await expect(page.getByRole('heading', { name: '没有匹配任务' })).toBeVisible();
  await page.getByRole('button', { name: '重置筛选' }).click();
  await expect(execution).toBeVisible();
  await page.getByRole('link', { name: '查看完整证据' }).click();
  await expect(page.getByRole('heading', { name: 'HTTP 响应证据' })).toBeVisible();
});

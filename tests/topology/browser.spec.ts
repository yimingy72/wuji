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

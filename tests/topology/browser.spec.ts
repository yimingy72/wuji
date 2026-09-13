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

test('history mode suppresses every projected action', async ({ page }) => {
  await page.goto('/?theme=graphite&mode=history');
  await expect(page.getByRole('region', { name: '任务拓扑图' })).toBeVisible();
  await expect(page.getByRole('button', { name: /执行 expand/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /执行 inspect/ })).toHaveCount(0);
  await expect(page.getByTestId('command-events')).toHaveText('0');
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

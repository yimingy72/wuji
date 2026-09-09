import { expect, test } from '@playwright/test';

test('standalone validators execute in a browser bundle', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('body')).toHaveAttribute('data-ready', 'true');
  const result = await page.evaluate(() => globalThis.__wujiContractProbe);
  expect(result.positive).toEqual([true, true, true, true]);
  expect(result.negative).toEqual([false, false, false, false]);
});

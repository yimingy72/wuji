import { test, expect, type Page } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';

const variants = ['silver', 'glacier', 'celadon', 'slate', 'graphite'] as const;
const artifact = '/evidence/00000000-0000-4000-8000-000000000009';

// Measure rendered text against the composited surface, including placeholders.
// This targets the palette regressions; it is not a full accessibility audit.
async function textContrast(page: Page) {
  return page.evaluate(() => {
    const context = document.createElement('canvas').getContext('2d')!;
    function rgba(color: string) {
      context.clearRect(0, 0, 1, 1);
      context.fillStyle = color;
      context.fillRect(0, 0, 1, 1);
      return Array.from(context.getImageData(0, 0, 1, 1).data).map((value, i) => i === 3 ? value / 255 : value);
    }
    function background(element: Element): number[] {
      const color = rgba(getComputedStyle(element).backgroundColor);
      if (color[3] === 1) return color;
      const parent = element.parentElement ? background(element.parentElement) : [255, 255, 255, 1];
      return color.map((value, i) => i === 3 ? 1 : value * color[3]! + parent[i]! * (1 - color[3]!));
    }
    function luminance(color: number[]) {
      return color.slice(0, 3).map(value => value / 255)
        .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
        .reduce((sum, value, i) => sum + value * [.2126, .7152, .0722][i]!, 0);
    }
    const samples: { text: string; ratio: number }[] = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const elements = new Set<Element>();
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.textContent?.trim() && node.parentElement) elements.add(node.parentElement);
    }
    document.querySelectorAll('input').forEach(element => elements.add(element));
    for (const element of elements) {
      if (element.closest('script, style, [aria-hidden="true"]') || !element.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
      const rect = element.getBoundingClientRect();
      if (!rect.width || !rect.height) continue;
      const placeholder = element instanceof HTMLInputElement && !element.value && element.placeholder;
      const text = placeholder || (element instanceof HTMLInputElement ? element.value : element.textContent?.trim());
      if (!text) continue;
      const foreground = rgba(getComputedStyle(element, placeholder ? '::placeholder' : null).color);
      const surface = background(element);
      const actual = foreground.map((value, i) => i === 3 ? 1 : value * foreground[3]! + surface[i]! * (1 - foreground[3]!));
      const high = Math.max(luminance(actual), luminance(surface));
      const low = Math.min(luminance(actual), luminance(surface));
      samples.push({ text: text.slice(0, 75), ratio: Number(((high + .05) / (low + .05)).toFixed(2)) });
    }
    return { minimum: Math.min(...samples.map(sample => sample.ratio)), failures: samples.filter(sample => sample.ratio < 4.5), samples };
  });
}

test.beforeAll(async () => { await mkdir('artifacts/palettes', { recursive: true }); });

for (const variant of variants) {
  test(`${variant}: text stays readable across workbench, forms, evidence and warnings`, async ({ page }) => {
    await page.goto(`/tasks?theme=${variant}`);
    await expect(page.getByRole('heading', { name: '任务工作台', exact: true })).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute('data-palette', variant);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: `artifacts/palettes/${variant}.png`, fullPage: true, animations: 'disabled' });
    const samples = { workbench: await textContrast(page) } as Record<string, Awaited<ReturnType<typeof textContrast>>>;
    await page.getByRole('button', { name: '创建任务', exact: true }).hover();
    samples.hover = await textContrast(page);
    await page.getByRole('button', { name: '创建任务', exact: true }).click();
    await page.getByRole('button', { name: '预览有效范围' }).click();
    samples.form = await textContrast(page);
    await page.screenshot({ path: `artifacts/palettes/${variant}-create.png`, fullPage: true, animations: 'disabled' });
    await page.getByLabel('任务名称', { exact: true }).fill('');
    await page.getByRole('button', { name: '预览有效范围' }).click();
    await expect(page.getByRole('alert')).toBeVisible();
    samples.error = await textContrast(page);
    await page.goto(`${artifact}?theme=${variant}`);
    await expect(page.getByRole('heading', { name: 'HTTP 响应证据' })).toBeVisible();
    samples.evidence = await textContrast(page);
    await page.goto(`/tasks?theme=${variant}&scene=unknown`);
    await expect(page.getByText('有 1 个调用结果不明')).toBeVisible();
    samples.warning = await textContrast(page);
    await page.getByRole('button', { name: '演示设置', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    samples.drawer = await textContrast(page);
    await writeFile(`artifacts/palettes/${variant}-contrast.json`, JSON.stringify(samples, null, 2));
    for (const [state, result] of Object.entries(samples)) expect(result.failures, `${variant} / ${state}`).toEqual([]);
  });
}

test('palette survives navigation and refresh while comparison tabs remain independent', async ({ page, context }) => {
  await page.goto('/tasks?theme=silver');
  const execution = page.getByRole('region', { name: '任务执行' });
  await page.getByRole('button', { name: '取消任务', exact: true }).click();
  await page.getByRole('combobox', { name: '工作台配色' }).click();
  await page.getByRole('option', { name: '冰蓝', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'glacier');
  await expect(execution.getByText('取消中', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: '查看完整证据' }).click();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'glacier');
  const comparison = await context.newPage();
  await comparison.goto('/tasks?theme=celadon');
  await expect(comparison.locator('html')).toHaveAttribute('data-palette', 'celadon');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'glacier');
  await page.goto('/tasks?theme=slate');
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'slate');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('combobox', { name: '工作台配色' }).click();
  await page.getByRole('option', { name: '雾银', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'silver');
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: 'artifacts/palettes/narrow.png', fullPage: true, animations: 'disabled' });
});

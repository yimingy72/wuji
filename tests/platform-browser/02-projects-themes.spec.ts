import { test, expect, type Page } from '@playwright/test';
import { keycloakLogin, manifest } from './support';


const themes = [
  ['silver', '雾银'],
  ['glacier', '冰蓝'],
  ['celadon', '青瓷'],
  ['slate', '亮石墨'],
  ['graphite', '原石墨'],
] as const;

async function chooseTheme(page: Page, label: string): Promise<void> {
  await page.getByRole('combobox', { name: '工作台配色' }).click();
  await page.getByRole('option', { name: label, exact: true }).click();
}

test('all five themes cover project pages and popup, persist, and remain keyboard operable', async ({ page }) => {
  const run = await manifest();
  await keycloakLogin(page, run.seed_users.single_a);
  for (const [id, label] of themes) {
    await chooseTheme(page, label);
    await expect(page.locator('html')).toHaveAttribute('data-palette', id);
    await page.getByRole('combobox', { name: '工作台配色' }).click();
    await expect(page.getByRole('option', { name: label, exact: true })).toBeVisible();
    await expect(page.locator('.ant-select-dropdown:visible')).toHaveCount(1);
    await page.keyboard.press('Escape');
    expect(await page.evaluate(() => localStorage.getItem('wuji.workbench.palette'))).toBe(id);
  }
  const selector = page.getByRole('combobox', { name: '工作台配色' });
  await selector.focus();
  await page.keyboard.press('Enter');
  for (let index = 1; index < themes.length; index += 1) {
    await page.keyboard.press('ArrowUp');
  }
  await page.keyboard.press('Enter');
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'silver');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'silver');
});

test('URL theme only overrides the tab and does not rewrite device preference', async ({ page, context }) => {
  const run = await manifest();
  await page.addInitScript(() => localStorage.setItem('wuji.workbench.palette', 'glacier'));
  await keycloakLogin(page, run.seed_users.single_a, '/projects');
  await page.goto('/projects?theme=celadon');
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'celadon');
  expect(await page.evaluate(() => localStorage.getItem('wuji.workbench.palette'))).toBe('glacier');
  const comparison = await context.newPage();
  await comparison.goto('/projects?theme=graphite');
  await expect(comparison.locator('html')).toHaveAttribute('data-palette', 'graphite');
  expect(await comparison.evaluate(() => localStorage.getItem('wuji.workbench.palette'))).toBe('glacier');
  await page.goto('/projects');
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'glacier');
});

test('unavailable storage and invalid preference still render the default theme', async ({ browser }) => {
  const run = await manifest();
  const context = await browser.newContext({ baseURL: run.urls.web });
  await context.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get() { throw new DOMException('blocked', 'SecurityError'); },
    });
  });
  const page = await context.newPage();
  try {
    await keycloakLogin(page, run.seed_users.single_a);
    await expect(page.locator('html')).toHaveAttribute('data-palette', 'silver');
    await chooseTheme(page, '冰蓝');
    await expect(page.locator('html')).toHaveAttribute('data-palette', 'glacier');
    await expect(page.getByRole('navigation', { name: '项目列表' })).toBeVisible();
  } finally {
    await context.close();
  }
  const invalidContext = await browser.newContext({ baseURL: run.urls.web });
  await invalidContext.addInitScript(() => localStorage.setItem('wuji.workbench.palette', 'not-a-theme'));
  try {
    const invalidPage = await invalidContext.newPage();
    await keycloakLogin(invalidPage, run.seed_users.single_a);
    await expect(invalidPage.locator('html')).toHaveAttribute('data-palette', 'silver');
  } finally {
    await invalidContext.close();
  }
});

test('theme changes preserve current project and cursor page', async ({ page }) => {
  const run = await manifest();
  await keycloakLogin(page, run.seed_users.dual_ab);
  const projectLinks = page.getByRole('navigation', { name: '项目列表' }).getByRole('link');
  const firstPage = await projectLinks.evaluateAll(links => links.map(link => link.getAttribute('href')));
  await page.getByRole('button', { name: '下一页' }).click();
  const secondPage = await projectLinks.evaluateAll(links => links.map(link => link.getAttribute('href')));
  expect(secondPage).not.toEqual(firstPage);
  await chooseTheme(page, '青瓷');
  expect(await projectLinks.evaluateAll(links => links.map(link => link.getAttribute('href')))).toEqual(secondPage);
  await page.getByRole('button', { name: '上一页' }).click();
  expect(await projectLinks.evaluateAll(links => links.map(link => link.getAttribute('href')))).toEqual(firstPage);

  const projectId = run.seed_users.dual_ab.project_ids[0]!;
  await page.goto(`/projects/${projectId}`);
  await expect(page.getByTestId('project-canary')).toBeVisible();
  await chooseTheme(page, '原石墨');
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}$`));
  await expect(page.getByTestId('project-canary')).toBeVisible();
});

test('no-project identity sees a real empty state', async ({ page }) => {
  const run = await manifest();
  await keycloakLogin(page, run.seed_users.no_projects);
  await expect(page.getByRole('status')).toContainText(/暂无|没有.*项目/);
  await expect(page.getByRole('navigation', { name: '项目列表' }).getByRole('link')).toHaveCount(0);
});

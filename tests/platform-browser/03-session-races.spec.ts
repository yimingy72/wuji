import { test, expect } from '@playwright/test';
import { control, keycloakLogin, manifest, permissionArgs } from './support';


test('logout masks private state immediately; 503 remains retryable without automatic SSO', async ({ page }) => {
  const run = await manifest();
  const user = run.seed_users.single_a;
  const projectId = user.project_ids[0]!;
  await keycloakLogin(page, user, `/projects/${projectId}`);
  await expect(page.getByTestId('project-canary')).toBeVisible();
  await control('db-forward', 'pause');
  try {
    await page.getByRole('button', { name: '退出登录' }).click();
    await expect(page.getByTestId('project-canary')).toHaveCount(0);
    await expect(page.getByRole('alert')).toContainText(/退出.*未完成|无法.*退出/);
    await expect(page.getByRole('button', { name: '重试退出' })).toBeVisible();
    await page.waitForTimeout(1_000);
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator('#username')).toHaveCount(0);
  } finally {
    await control('db-forward', 'resume');
    await control('api', 'wait-ready');
  }
  await page.getByRole('button', { name: '重试退出' }).click();
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/);
  expect((await page.request.get('/api/v1/session')).status()).toBe(401);
});

test('authoritative 401 clears identity and all private project content', async ({ page }) => {
  const run = await manifest();
  const user = run.seed_users.single_a;
  const projectId = user.project_ids[0]!;
  await keycloakLogin(page, user, `/projects/${projectId}`);
  await expect(page.getByTestId('project-canary')).toBeVisible();
  await control('user', 'disable', '--user', 'single_a');
  try {
    await page.reload();
    await expect(page).toHaveURL(/\/login(?:\?.*)?$/);
    await expect(page.getByTestId('project-canary')).toHaveCount(0);
    const project = Object.values(run.seed_entities.projects).find(item => item.id === projectId)!;
    await expect(page.getByText(project.name)).toHaveCount(0);
  } finally {
    await control('user', 'enable', '--user', 'single_a');
  }
});

test('late project error cannot replace the newly selected project', async ({ page }) => {
  const run = await manifest();
  await keycloakLogin(page, run.seed_users.dual_ab);
  const visibleProjectLinks = page.locator('a[href^="/projects/"]');
  await expect(visibleProjectLinks.first()).toBeVisible();
  const visibleHrefs = await visibleProjectLinks.evaluateAll(links =>
    [...new Set(links.map(link => link.getAttribute('href')).filter((href): href is string => Boolean(href)))],
  );
  expect(visibleHrefs.length).toBeGreaterThanOrEqual(2);
  const [oldHref, newHref] = visibleHrefs;
  const oldId = oldHref!.split('/').at(-1)!;
  const newId = newHref!.split('/').at(-1)!;
  let started!: () => void;
  let release!: () => void;
  const wasStarted = new Promise<void>(resolve => { started = resolve; });
  const canRelease = new Promise<void>(resolve => { release = resolve; });
  await page.route(`**/api/v1/projects/${oldId}`, async route => {
    started();
    await canRelease;
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      headers: { 'cache-control': 'no-store' },
      body: JSON.stringify({ code: 'SERVICE_UNAVAILABLE', message: 'delayed', trace_id: crypto.randomUUID() }),
    }).catch(() => undefined);
  }, { times: 1 });
  const oldNavigation = page.locator(`a[href="${oldHref}"]`).click();
  await wasStarted;
  await page.locator(`a[href="${newHref}"]`).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${newId}$`));
  await expect(page.getByTestId('project-canary')).toContainText(newId!);
  release();
  await oldNavigation;
  await page.waitForTimeout(250);
  await expect(page).toHaveURL(new RegExp(`/projects/${newId}$`));
  await expect(page.getByTestId('project-canary')).toContainText(newId!);
  await expect(page.locator('body')).not.toContainText('delayed');
});

test('revocation wins over an already-authorized delayed 200 response', async ({ page }) => {
  const run = await manifest();
  const user = run.seed_users.single_a;
  const projectId = user.project_ids[0]!;
  let captured!: () => void;
  let release!: () => void;
  const oldResponseCaptured = new Promise<void>(resolve => { captured = resolve; });
  const canRelease = new Promise<void>(resolve => { release = resolve; });
  await keycloakLogin(page, user);
  const initialSession = await page.request.get('/api/v1/session');
  expect(initialSession.status()).toBe(200);
  const initialPermissionsVersion = Number((await initialSession.json()).permissions_version);
  const projectLink = page.locator(`a[href="/projects/${projectId}"]`);
  await expect(projectLink).toBeVisible();
  await page.route(`**/api/v1/projects/${projectId}`, async route => {
    const oldAuthorizedResponse = await route.fetch();
    expect(oldAuthorizedResponse.status()).toBe(200);
    captured();
    await canRelease;
    await route.fulfill({ response: oldAuthorizedResponse }).catch(() => undefined);
  }, { times: 1 });
  const oldNavigation = projectLink.click();
  await oldResponseCaptured;
  await control('permissions', 'revoke', ...permissionArgs(run, 'single_a', projectId, 'operator'));
  try {
    const refreshedSession = page.waitForResponse(response =>
      response.url().endsWith('/api/v1/session') && response.status() === 200,
    );
    const revokedDetail = page.waitForResponse(response =>
      response.url().endsWith(`/api/v1/projects/${projectId}`) && response.status() === 404,
    );
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    const refreshedSessionResponse = await refreshedSession;
    expect(Number((await refreshedSessionResponse.json()).permissions_version))
      .toBeGreaterThan(initialPermissionsVersion);
    await revokedDetail;
    await expect(page).toHaveURL(/\/projects(?:\?.*)?$/);
    await expect(page.getByTestId('project-canary')).toHaveCount(0);
    release();
    await oldNavigation;
    await page.waitForTimeout(250);
    await expect(page.getByTestId('project-canary')).toHaveCount(0);
    await expect(page).toHaveURL(/\/projects(?:\?.*)?$/);
    await expect(page.getByTestId('project-canary')).toHaveCount(0);
  } finally {
    release();
    await control('permissions', 'grant', ...permissionArgs(run, 'single_a', projectId, 'operator'));
  }
});

test('served production application contains no seed credentials or prototype controls', async ({ page }) => {
  const run = await manifest();
  const scripts: string[] = [];
  page.on('response', async response => {
    if (response.request().resourceType() === 'script' && response.ok()) {
      scripts.push(await response.text());
    }
  });
  await page.goto('/login');
  await expect(page.getByRole('link', { name: '使用组织账号登录' })).toBeVisible();
  const bundle = scripts.join('\n');
  for (const user of Object.values(run.seed_users)) {
    expect(bundle).not.toContain(user.password);
  }
  expect(bundle).not.toContain('seed_users');
  expect(bundle).not.toContain('tests/fixtures');
  await expect(page.getByText('演示设置', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /创建任务|执行任务|运行任务/ })).toHaveCount(0);
});

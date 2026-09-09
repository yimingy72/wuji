import { test, expect } from '@playwright/test';
import {
  assertSafeCallbackFailure,
  beginLogin,
  captureKeycloakCallback,
  keycloakLogin,
  manifest,
} from './support';


test.beforeAll(async () => {
  const { control } = await import('./support');
  await control('api', 'restart', '--profile', 'keycloak');
  await control('api', 'wait-ready');
});

test('real Keycloak Code+PKCE login, deep-link return and logout', async ({ page }) => {
  const run = await manifest();
  const user = run.seed_users.single_a;
  const projectId = user.project_ids[0]!;
  const project = Object.values(run.seed_entities.projects).find(item => item.id === projectId)!;
  await keycloakLogin(page, user, `/projects/${projectId}`);
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}$`));
  await expect(page.getByRole('heading', { name: project.name })).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}$`));
  await page.getByRole('button', { name: '退出登录' }).click();
  await expect(page).toHaveURL(/\/login(?:\?.*)?$/);
  const session = await page.request.get('/api/v1/session');
  expect(session.status()).toBe(401);
});

test('wrong browser cannot consume valid state; owning browser can still finish', async ({ browser }) => {
  const run = await manifest();
  const owner = await browser.newContext({ baseURL: run.urls.web });
  const other = await browser.newContext({ baseURL: run.urls.web });
  try {
    const ownerPage = await owner.newPage();
    const callback = await captureKeycloakCallback(
      ownerPage,
      await beginLogin(owner),
      run.seed_users.single_a,
    );
    await assertSafeCallbackFailure(await other.request.get(callback, { maxRedirects: 0 }));
    const success = await owner.request.get(callback, { maxRedirects: 0 });
    expect(success.status()).toBe(303);
    expect(success.headers().location).toBe('/projects');
    expect((await owner.request.get('/api/v1/session')).status()).toBe(200);
  } finally {
    await owner.close();
    await other.close();
  }
});

test('new browser binding replaces old pending callback', async ({ browser }) => {
  const run = await manifest();
  const context = await browser.newContext({ baseURL: run.urls.web });
  try {
    const page = await context.newPage();
    const first = await beginLogin(context);
    const second = await beginLogin(context);
    const oldCallback = await captureKeycloakCallback(page, first, run.seed_users.single_a);
    const newCallback = await captureKeycloakCallback(page, second, run.seed_users.single_a);
    await assertSafeCallbackFailure(await context.request.get(oldCallback, { maxRedirects: 0 }));
    const success = await context.request.get(newCallback, { maxRedirects: 0 });
    expect(success.status()).toBe(303);
    expect(success.headers().location).toBe('/projects');
  } finally {
    await context.close();
  }
});

test('same Keycloak callback is consumed once under concurrency and replay fails', async ({ browser }) => {
  const run = await manifest();
  const context = await browser.newContext({ baseURL: run.urls.web });
  try {
    const callback = await captureKeycloakCallback(
      await context.newPage(),
      await beginLogin(context),
      run.seed_users.single_a,
    );
    const responses = await Promise.all([
      context.request.get(callback, { maxRedirects: 0 }),
      context.request.get(callback, { maxRedirects: 0 }),
    ]);
    expect(responses.filter(response => response.headers().location === '/projects')).toHaveLength(1);
    await assertSafeCallbackFailure(await context.request.get(callback, { maxRedirects: 0 }));
  } finally {
    await context.close();
  }
});

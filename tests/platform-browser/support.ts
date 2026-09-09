import { expect, type APIResponse, type BrowserContext, type Page } from '@playwright/test';
import { execFile } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export type SeedUser = {
  id: string;
  sub: string;
  fixture_sub: string;
  username: string;
  email: string;
  password: string;
  tenant_ids: string[];
  project_ids: string[];
};

export type RunManifest = {
  schema_version: 1;
  run_id: string;
  source_sha: string;
  artifacts_dir: string;
  namespace: string;
  urls: Record<'web' | 'api' | 'idp' | 'issuer_fixture' | 'unmigrated_api' | 'database', string>;
  seed_users: Record<string, SeedUser>;
  seed_entities: {
    tenants: Record<string, { id: string }>;
    projects: Record<string, { id: string; tenant_id: string; name: string }>;
  };
};

export async function manifest(): Promise<RunManifest> {
  const path = process.env.WUJI_TEST_RUN_FILE;
  if (!path) throw new Error('WUJI_TEST_RUN_FILE is required');
  return JSON.parse(await readFile(path, 'utf8'));
}

export async function control(...args: string[]): Promise<Record<string, unknown>> {
  const runFile = process.env.WUJI_TEST_RUN_FILE;
  if (!runFile) throw new Error('WUJI_TEST_RUN_FILE is required');
  const { stdout } = await execFileAsync(
    './scripts/platform/control.sh',
    ['--run-file', runFile, ...args],
    { timeout: 120_000, maxBuffer: 2_000_000 },
  );
  const payload = JSON.parse(stdout);
  return payload.result && typeof payload.result === 'object' ? payload.result : payload;
}

export function permissionArgs(run: RunManifest, user: string, projectId: string, role = 'viewer'): string[] {
  const [projectSymbol, project] = Object.entries(run.seed_entities.projects)
    .find(([, value]) => value.id === projectId)!;
  const tenantSymbol = Object.entries(run.seed_entities.tenants)
    .find(([, value]) => value.id === project.tenant_id)![0];
  return ['--scope', 'project', '--user', user, '--tenant', tenantSymbol, '--project', projectSymbol, '--role', role];
}

export async function beginLogin(context: BrowserContext, returnTo = '/projects'): Promise<string> {
  const response = await context.request.get(
    `/api/v1/auth/login?return_to=${encodeURIComponent(returnTo)}`,
    { maxRedirects: 0 },
  );
  expect(response.status()).toBe(302);
  return response.headers().location;
}

export async function captureKeycloakCallback(page: Page, authorizationUrl: string, user: SeedUser): Promise<string> {
  let resolveCallback!: (value: string) => void;
  const callback = new Promise<string>(resolve => { resolveCallback = resolve; });
  await page.route('**/api/v1/auth/callback?**', async route => {
    const url = route.request().url();
    await route.fulfill({
      status: 204,
      headers: { 'cache-control': 'no-store' },
    });
    resolveCallback(url);
  }, { times: 1 });
  const navigation = page.goto(authorizationUrl).catch(() => null);
  const username = page.locator('#username');
  const outcome = await Promise.race([
    callback.then(() => 'callback' as const),
    username.waitFor({ state: 'visible', timeout: 8_000 }).then(() => 'form' as const).catch(() => 'pending' as const),
  ]);
  if (outcome === 'form') {
    await username.fill(user.username);
    await page.locator('#password').fill(user.password);
    await page.locator('#kc-form-login').evaluate((form: HTMLFormElement) => form.requestSubmit());
  }
  const value = await callback;
  void navigation;
  return value;
}

export async function keycloakLogin(page: Page, user: SeedUser, returnTo = '/projects'): Promise<void> {
  const navigation = page.goto(`/api/v1/auth/login?return_to=${encodeURIComponent(returnTo)}`);
  const username = page.locator('#username');
  const atReturn = page.waitForURL(new RegExp(`${returnTo.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?:\\?.*)?$`));
  const outcome = await Promise.race([
    atReturn.then(() => 'returned' as const),
    username.waitFor({ state: 'visible', timeout: 8_000 }).then(() => 'form' as const),
  ]);
  if (outcome === 'form') {
    await username.fill(user.username);
    await page.locator('#password').fill(user.password);
    await page.locator('#kc-login').click();
  }
  await navigation.catch(() => null);
  await expect(page).toHaveURL(new RegExp(`${returnTo.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?:\\?.*)?$`));
}

export async function assertSafeCallbackFailure(response: APIResponse): Promise<void> {
  expect(response.status()).toBe(303);
  const location = response.headers().location;
  expect(location).toMatch(/^\/login\?error=(?:UNAUTHENTICATED|FORBIDDEN|SERVICE_UNAVAILABLE|INTERNAL_ERROR)&trace_id=[0-9a-fA-F-]{36}$/);
  expect(location).not.toContain('code=');
  expect(location).not.toContain('state=');
  expect(location).not.toContain('token=');
}

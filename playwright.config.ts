import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  timeout: 30_000,
  retries: 0,
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:4175',
    browserName: 'chromium',
    channel: process.env.WUJI_BROWSER_CHANNEL === 'chrome' ? 'chrome' : undefined,
    viewport: { width: 1440, height: 960 },
    trace: 'retain-on-failure',
  },
  webServer: { command: 'pnpm --filter @wuji/frontend-spike exec vite preview --host 127.0.0.1 --port 4175 --strictPort', url: 'http://127.0.0.1:4175', reuseExistingServer: false, timeout: 30_000 },
});

import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/contracts-browser',
  timeout: 20_000,
  retries: 0,
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:4176',
    browserName: 'chromium',
    channel: process.env.WUJI_BROWSER_CHANNEL === 'chrome' ? 'chrome' : undefined,
    viewport: { width: 800, height: 600 },
  },
  webServer: {
    command: 'pnpm --filter @wuji/web exec vite ../../tests/contracts-browser --host 127.0.0.1 --port 4176 --strictPort',
    url: 'http://127.0.0.1:4176',
    reuseExistingServer: false,
    timeout: 30_000,
  },
});

import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/topology',
  testMatch: 'browser.spec.ts',
  fullyParallel: false,
  workers: 1,
  reporter: [['line']],
  outputDir: 'work/topology-playwright-results',
  use: {
    baseURL: 'http://127.0.0.1:4194',
    browserName: 'chromium',
    viewport: { width: 1440, height: 1000 },
    reducedMotion: 'reduce',
  },
  webServer: {
    command: 'pnpm --dir apps/web exec vite ../../tests/topology/browser --config ../../tests/topology/browser/vite.config.ts --host 127.0.0.1 --port 4194 --strictPort',
    url: 'http://127.0.0.1:4194',
    reuseExistingServer: false,
    timeout: 30_000,
  },
});

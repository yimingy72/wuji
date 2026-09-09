import { defineConfig } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const runFile = process.env.WUJI_TEST_RUN_FILE;
if (!runFile || !path.isAbsolute(runFile)) {
  throw new Error('WUJI_TEST_RUN_FILE must be an absolute path');
}
const manifest = JSON.parse(readFileSync(runFile, 'utf8'));
if (manifest.schema_version !== 1) throw new Error('unsupported run manifest schema');

export default defineConfig({
  testDir: './tests/platform-browser',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  retries: 0,
  workers: 1,
  fullyParallel: false,
  forbidOnly: true,
  outputDir: path.join(manifest.artifacts_dir, 'playwright-results'),
  reporter: [['line'], ['json', { outputFile: path.join(manifest.artifacts_dir, 'playwright-report.json') }]],
  use: {
    baseURL: manifest.urls.web,
    browserName: 'chromium',
    channel: process.env.WUJI_BROWSER_CHANNEL === 'chrome' ? 'chrome' : undefined,
    viewport: { width: 1440, height: 960 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});

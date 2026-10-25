import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: 'workspace.spec.mjs', workers: 1, retries: 0,
  timeout: 180_000, globalTimeout: 10 * 60_000,
  expect: { timeout: 30_000 }, reporter: 'list',
  use: {
    browserName: 'chromium', headless: true, baseURL: 'http://127.0.0.1:8765',
    launchOptions: { chromiumSandbox: true },
    trace: 'off', video: 'off', screenshot: 'off', acceptDownloads: true,
  },
  webServer: {
    command: 'python3 -m http.server 8765 --bind 127.0.0.1 --directory ../web',
    url: 'http://127.0.0.1:8765/workspace/', reuseExistingServer: false,
    timeout: 30_000,
  },
});

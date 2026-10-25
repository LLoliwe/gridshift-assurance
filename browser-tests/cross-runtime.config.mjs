// Lane B private development config. Same sandboxed Chromium settings as the incumbent config.
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: 'cross-runtime.spec.mjs', workers: 1, retries: 0,
  timeout: 300_000, globalTimeout: 10 * 60_000, expect: { timeout: 30_000 }, reporter: 'list',
  use: {
    browserName: 'chromium', headless: true, baseURL: 'http://127.0.0.1:8767',
    launchOptions: { chromiumSandbox: true },
    trace: 'off', video: 'off', screenshot: 'off', acceptDownloads: true,
  },
  webServer: {
    command: 'python3 -m http.server 8767 --bind 127.0.0.1 --directory ../web',
    url: 'http://127.0.0.1:8767/workspace/', reuseExistingServer: false, timeout: 30_000,
  },
});

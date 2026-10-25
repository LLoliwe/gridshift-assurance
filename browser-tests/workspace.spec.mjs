// Public synthetic development test. No sealed evaluator material or native-Python substitute.
import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const flagship = new URL('../web/reconcile/flagship.json', import.meta.url);
async function download(page, selector) {
  const pending = page.waitForEvent('download');
  await page.locator(selector).click();
  const result = await pending;
  expect(await result.failure()).toBeNull();
  return readFile(await result.path());
}
test('real worker/Pyodide synthetic correction, acceptance, export and distrust on reopen', async ({page, browser}) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto('/workspace/');
  await expect(page.locator('#runtime')).toHaveText('Python runtime ready', {timeout: 120_000});
  expect(page.workers().some(w => w.url().endsWith('/workspace/workspace-worker.js'))).toBe(true);
  console.log(`Real browser=${browser.version()} sandbox_requested=true; actual worker ready; no runtime mocks`);
  const raw = await readFile(flagship);
  await page.locator('#case-file').setInputFiles({name:'synthetic-public-flagship.json', mimeType:'application/json', buffer:raw});
  await expect(page.locator('#case-workspace')).toBeVisible();
  await page.locator('#reviewer').fill('SYNTHETIC CI reviewer — not authenticated');
  await page.locator('#run').click();
  await expect(page.locator('#decision-title')).toHaveText('Correction proposed');
  await expect(page.locator('#result')).toContainText('96 tCO₂e');
  await expect(page.locator('#proposal-hash')).toHaveText(/^[a-f0-9]{64}$/);
  await expect(page.locator('#accept')).toBeDisabled();
  // Keyboard-only confirmation of the exact proposal; not a screen-reader audit.
  await page.locator('#confirm').focus();
  await page.keyboard.press('Space');
  await expect(page.locator('#confirm')).toBeChecked();
  await page.keyboard.press('Tab');
  await expect(page.locator('#accept')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#decision-title')).toHaveText('Exact correction accepted');
  const exported = await download(page, '#export-case');
  const envelope = JSON.parse(exported.toString('utf8'));
  expect(Buffer.from(envelope.original.raw_base64, 'base64').equals(raw)).toBe(true);
  const summary = await download(page, '#export-summary');
  expect(summary.length).toBeGreaterThan(0);
  await page.locator('#case-file').setInputFiles({name:'synthetic-reopened.case.json', mimeType:'application/json', buffer:exported});
  await expect(page.locator('#decision-title')).toHaveText('Not reviewed');
  await expect(page.locator('#accept')).toBeDisabled();
  await page.locator('#run').click();
  await expect(page.locator('#decision-title')).toHaveText('Correction proposed');
  // Viewport geometry only. Owner visual/aesthetic and assistive-tech gates stay pending.
  for (const width of [1440, 390]) {
    await page.setViewportSize({width, height:900});
    await expect(page.locator('#run')).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow, `unexpected document overflow at ${width}px`).toBe(false);
  }
  expect(errors).toEqual([]);
  console.log('Synthetic correction/accept/export/reopen and viewport geometry passed; owner visual and assistive-tech acceptance NOT established.');
});

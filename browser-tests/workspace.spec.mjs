// Public synthetic development test. No sealed evaluator material or native-Python substitute.
import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
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
  // Runtime chip: plain status, open actions disabled until Ready (checked only while not yet ready).
  const early = await page.evaluate(() => ({ chip: document.getElementById('runtime').textContent,
    disabled: ['case-file', 'new-case', 'example', 'load-example'].map(id => document.getElementById(id).disabled),
    notice: document.getElementById('notice').textContent,
    look: ['new-case', 'example', 'load-example'].map(id => { const s = getComputedStyle(document.getElementById(id)); return [s.opacity, s.cursor]; })
      .concat([(s => [s.opacity, s.cursor])(getComputedStyle(document.querySelector('.file-label')))]) }));
  if (early.chip !== 'Ready') { expect(early.chip).toBe('Loading calculator…'); expect(early.disabled).toEqual([true, true, true, true]);
    expect(early.notice).toBe('Getting the calculator ready. Opening a case unlocks in a moment.');
    expect(early.look).toEqual(Array(4).fill(['0.55', 'not-allowed'])); }
  console.log(`Early runtime chip: ${early.chip}; open actions disabled: ${early.disabled.join(',')}; look: ${JSON.stringify(early.look)}`);
  await expect(page.locator('#runtime')).toHaveText('Ready', {timeout: 120_000});
  for (const id of ['#case-file', '#new-case', '#example', '#load-example']) await expect(page.locator(id)).toBeEnabled();
  await expect(page.locator('#notice')).toHaveText('Open a declared case, or enter the original report and evidence using guided fields.');
  const chipStyle = await page.locator('#runtime').evaluate(e => { const s = getComputedStyle(e); return { border: s.borderTopWidth, background: s.backgroundColor }; });
  expect(chipStyle).toEqual({ border: '0px', background: 'rgba(0, 0, 0, 0)' });
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

// Regression (round 2): intake refusals show only the user-facing message; the Python traceback is
// kept in a collapsed "Technical details" disclosure. Mirrors adversarial C12 and C14.
test('refusal notice never shows a Python traceback (C12 float year, C14 big integer)', async ({ page }) => {
  const flag = readFileSync(new URL('../web/reconcile/flagship.json', import.meta.url), 'utf8');
  const c12 = flag.replace('"data_year": 2024', '"data_year": 2024.0');
  const p = JSON.parse(flag); p.report.unreviewed_extension = '__BIG__';
  const c14 = JSON.stringify(p, null, 2).replace('"__BIG__"', '18446744073709551617');
  expect(c12).not.toBe(flag);
  const cases = [
    ['C12_float_year', c12, /data_year at \$\.report\.data_year .*JSON integer 2024/],
    ['C14_big_int_unknown_field', c14, /JavaScript transport limit/],
  ];
  for (const [id, body, expected] of cases) {
    await page.goto('/workspace/');
    await expect(page.locator('#runtime')).toHaveText('Ready', { timeout: 120_000 });
    await page.locator('#case-file').setInputFiles({ name: `${id}.json`, mimeType: 'application/json', buffer: Buffer.from(body) });
    const notice = page.locator('#notice');
    await expect(notice).toContainText('Case was not opened', { timeout: 60_000 });
    const text = await notice.textContent();
    expect(text, `${id} notice`).not.toContain('Traceback');
    expect(text, `${id} notice`).not.toContain('File "');
    expect(text).toMatch(expected);
    const details = page.locator('#notice-details');
    await expect(details).toBeVisible();
    expect(await details.evaluate(d => d.open)).toBe(false);
    await expect(page.locator('#notice-trace')).toBeHidden();
    await details.locator('summary').click();
    await expect(page.locator('#notice-trace')).toContainText('Traceback (most recent call last):');
    await expect(page.locator('#case-workspace')).toBeHidden();
    console.log(`${id} real-Chromium notice: ${text}`);
  }
});

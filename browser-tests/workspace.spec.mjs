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

// Regression (rounds 2-3): C12/C14 are quarantined at intake. The user sees the quarantine panel with
// reasons and no Python traceback; calculation controls are disabled; export is a diagnostic only.
test('intake quarantine never shows a Python traceback (C12 float year, C14 big integer)', async ({ page }) => {
  const flag = readFileSync(new URL('../web/reconcile/flagship.json', import.meta.url), 'utf8');
  const c12 = flag.replace('"data_year": 2024', '"data_year": 2024.0');
  const p = JSON.parse(flag); p.report.unreviewed_extension = '__BIG__';
  const c14 = JSON.stringify(p, null, 2).replace('"__BIG__"', '18446744073709551617');
  expect(c12).not.toBe(flag);
  const cases = [
    ['C12_float_year', c12, /FLOAT_OR_EXPONENT_NUMBER at \$\.report\.data_year/],
    ['C14_big_int_unknown_field', c14, /INTEGER_OUTSIDE_PORTABLE_RANGE|JavaScript transport limit/],
  ];
  for (const [id, body, expected] of cases) {
    await page.goto('/workspace/');
    await expect(page.locator('#runtime')).toHaveText('Ready', { timeout: 120_000 });
    await page.locator('#case-file').setInputFiles({ name: `${id}.json`, mimeType: 'application/json', buffer: Buffer.from(body) });
    const panel = page.locator('#quarantine');
    await expect(panel).toBeVisible({ timeout: 60_000 });
    await expect(page.locator('#quarantine-title')).toHaveText('File quarantined: not opened');
    const all = `${await panel.textContent()} ${await page.locator('#notice').textContent()}`;
    expect(all, id).not.toContain('Traceback');
    expect(all, id).not.toContain('File "');
    for (const c of ['#quarantine-title', '#quarantine-status', '#quarantine-facts', '#quarantine-reasons', '#notice'])
      expect(await page.locator(c).textContent(), `${id} ${c}`).not.toMatch(/WITHHOLD|Withheld|More evidence required/);
    await expect(page.locator('#notice')).toHaveText('Not opened: the file was rejected at intake and is quarantined for inspection only. No case is open.');
    expect(all).toMatch(expected);
    for (const c of ['#run', '#save-draft', '#accept', '#export-case', '#export-summary']) await expect(page.locator(c)).toBeDisabled();
    await expect(page.locator('#case-workspace')).toBeHidden();
    await page.locator('#quarantine-view').click();
    await expect(page.locator('#quarantine-text')).toHaveText(body);
    const dl = page.waitForEvent('download');
    await page.locator('#quarantine-export').click();
    const download = await dl;
    expect(download.suggestedFilename()).toMatch(/^gridshift-quarantine-[0-9a-f]{12}\.json$/);
    const diag = JSON.parse(readFileSync(await download.path(), 'utf8'));
    expect(JSON.stringify(diag)).toContain('NO CALCULATION, NO PROPOSAL AND NO ACCEPTANCE OCCURRED');
    await page.locator('#quarantine-close').click();
    await expect(panel).toBeHidden();
    console.log(`${id} real-Chromium quarantine: ${(await page.locator('#notice').textContent())}`);
  }
});

test('C30 schema failure is presented as a schema rejection; E1-W10 names engine-stated releasing evidence', async ({ page }) => {
  const flag = readFileSync(new URL('../web/reconcile/flagship.json', import.meta.url), 'utf8');
  const c30 = flag.replace('"record_id"', '"__proto__": "x", "record_id"');
  const w10 = readFileSync(new URL('../lane-b/e1-frozen/cases/E1-W10.json', import.meta.url));
  await page.goto('/workspace/');
  await expect(page.locator('#runtime')).toHaveText('Ready', { timeout: 120_000 });
  const label = await page.locator('.private-label').first().evaluate(e => getComputedStyle(e).borderTopWidth);
  expect(label, 'private label is plain text, not a button').toBe('0px');
  await page.locator('#case-file').setInputFiles({ name: 'C30.json', mimeType: 'application/json', buffer: Buffer.from(c30) });
  await expect(page.locator('#run')).toBeEnabled({ timeout: 60_000 });
  await page.locator('#run').click();
  await expect(page.locator('#decision-title')).toHaveText('Schema rejection: not calculated', { timeout: 60_000 });
  await expect(page.locator('#decision-status')).toHaveText('Schema rejected');
  await expect(page.locator('#result')).toContainText('Why the schema was rejected');
  await page.locator('#case-file').setInputFiles({ name: 'E1-W10.json', mimeType: 'application/json', buffer: w10 });
  await expect(page.locator('#case-title')).toContainText('E1-W10', { timeout: 60_000 });
  await page.locator('#run').click();
  await expect(page.locator('#decision-title')).toHaveText('More evidence required', { timeout: 60_000 });
  await expect(page.locator('#release')).toContainText('Engine requirement: activity unit must be kWh or MWh');
  await expect(page.locator('#release')).toContainText('Record A: meter M1, 2024-01-01 to 2025-01-01 (end exclusive), currently declared in ZAR');
});

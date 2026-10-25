// Lane B: drive the frozen adversarial cases through the REAL workspace worker
// (Chromium + Pyodide + case_adapter.py), using the same step semantics as
// lane-b/adversarial/native_runner.py. Synthetic public-fixture-derived data only.
import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
const INPUT = process.env.LANEB_CASES, OUTPUT = process.env.LANEB_OUT;
const READY = 'Ready';

test('frozen adversarial cases through the real browser worker', async ({ page, browser }) => {
  const cases = JSON.parse(await readFile(INPUT, 'utf8'));
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  await page.goto('/workspace/');
  await expect(page.locator('#runtime')).toHaveText(READY, { timeout: 120_000 });
  const results = await page.evaluate(async (cases) => {
    const worker = new Worker('/workspace/workspace-worker.js', { type: 'module' });
    let seq = 0; const waiting = new Map();
    worker.addEventListener('message', ev => { const w = waiting.get(ev.data.id); if (w) { waiting.delete(ev.data.id); w(ev.data); } });
    const call = (msg) => new Promise(res => { const id = ++seq; waiting.set(id, res); worker.postMessage({ id, ...msg }); });
    const ready = await call({ type: 'init' });
    if (ready.type !== 'ready') return { fatal: ready };
    const hex = async s => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)))].map(x => x.toString(16).padStart(2, '0')).join('');
    const pyError = m => { const lines = String(m).trim().split('\n'); for (let i = lines.length - 1; i >= 0; i--) { const x = lines[i].match(/^([A-Za-z_.]*(?:Error|Exception)): (.*)$/); if (x) return `${x[1].split('.').pop()}: ${x[2]}`; } return `JSWorkerError: ${m}`; };
    const out = {};
    for (const c of cases) {
      const raw = Uint8Array.from(atob(c.raw_base64), ch => ch.charCodeAt(0));
      const steps = []; let caseObj = null, last = null;
      for (const step of c.steps) {
        let activities;
        if (step === 'open') activities = { operation: 'open', raw };
        else if (step === 'reopen_export') activities = { operation: 'open', raw: new TextEncoder().encode(last.export_json) };
        else if (step === 'review') activities = { operation: 'review', case: structuredClone(caseObj) };
        else if (step === 'accept_current') activities = { operation: 'accept', case: structuredClone(caseObj), proposal_sha256: last.result.proposal_sha256, reviewer_id: c.reviewer };
        else activities = { operation: 'accept', case: structuredClone(caseObj), proposal_sha256: step.split(':')[1], reviewer_id: c.reviewer };
        const m = await call({ type: 'review', activities });
        if (m.type !== 'result') { steps.push({ step, ok: false, error: m.exception ? `${m.exception}: ${m.message}` : pyError(m.message), kind: m.kind ?? null, raw_error: String(m.detail || m.message).slice(-600) }); break; }
        const o = { step, ok: true, raw_sha256: m.case.original.raw_sha256, revision: m.case.revision, history_len: m.case.history.length,
          cached_review_null: m.case.cached_review === null };
        const res = m.case.working && m.case.working.resolutions; o.active_resolutions = Array.isArray(res) ? res.length : null;
        const r = m.result; o.decision = r ? r.decision : null;
        if (r) { const rep = r.accepted_report || r.proposed_report; o.emissions = rep ? rep.emissions_tco2e : null; o.proposal_sha256 = r.proposal_sha256; o.resolution_accepted = r.resolution_accepted; o.finding_codes = (r.findings || []).map(f => f.code); }
        if ('export_json' in m) { o.export_sha256 = await hex(m.export_json); o.export_json = m.export_json; }
        steps.push(o); caseObj = m.case; if ('export_json' in m || m.result) last = m;
      }
      out[c.id] = steps;
    }
    worker.terminate();
    return { cases: out };
  }, cases);
  expect(results.fatal).toBeUndefined();
  // Cross-runtime assertion (C17): the browser's size refusal must be byte-identical to native
  // open_case's `ValueError: <message>`, with the same structured kind.
  const LIMITS = JSON.parse(await readFile(new URL('../web/workspace/intake-limits.json', import.meta.url), 'utf8'));
  if (results.cases.C17_empty) {
    expect(results.cases.C17_empty[0].error).toBe(`ValueError: ${LIMITS.open_size_message}`);
    expect(results.cases.C17_empty[0].kind).toBe('intake_refusal');
  }
  // Pyodide interpreter version, from a separate runtime load (informational).
  const pyVersion = await page.evaluate(async () => {
    const { loadPyodide } = await import('https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs');
    const py = await loadPyodide({ indexURL: 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/' });
    return py.runPython('import sys; sys.version');
  });
  // Real UI checks: XSS-like strings stay inert text; float-year case through the actual buttons.
  const ui = {};
  for (const id of ['C28_xss_strings', 'C12_float_year', 'C14_big_int_unknown_field']) {
    const c = cases.find(x => x.id === id);
    // Harness fix (round 2): reset all UI state between cases. In run 2 the C12/C14 UI entries
    // inherited C28's open case (opened:true, C28 title); those entries are not evidence.
    await page.goto('/workspace/');
    await expect(page.locator('#runtime')).toHaveText(READY, { timeout: 120_000 });
    await page.locator('#case-file').setInputFiles({ name: `${id}.json`, mimeType: 'application/json', buffer: Buffer.from(c.raw_base64, 'base64') });
    await page.waitForTimeout(1500);
    const opened = await page.locator('#case-workspace').isVisible();
    let decision = null;
    if (opened && await page.locator('#run').isEnabled()) { await page.locator('#run').click(); await page.waitForTimeout(2500); decision = await page.locator('#decision-title').textContent(); }
    ui[id] = { ui_reset: 'fresh page load before this case', opened, decision, quarantined: await page.locator('#quarantine').isVisible(), notice: await page.locator('#notice').textContent(), case_title: await page.locator('#case-title').textContent(),
      xss_flag: await page.evaluate(() => window.__xss ?? null), injected_nodes: await page.locator('#xss-pkg, img[src="x"]').count() };
  }
  await writeFile(OUTPUT, JSON.stringify({ runtime: 'chromium-pyodide-worker', browser: browser.version(), pyodide_python: pyVersion,
    pyodide_runtime: '314.0.7', ui, page_errors: pageErrors, cases: results.cases }, null, 1));
  console.log(`browser run complete: ${Object.keys(results.cases).length} cases; browser ${browser.version()}; ${pyVersion.split(' ')[0]}`);
});

"""Human-readable, offline report from recomputed GRIDSHIFT evidence, no remote assets."""
from html import escape
from emissions import calculate_batch, CURATED_FACTOR, verify_receipt


def render_report(report):
    if not isinstance(report, dict) or not isinstance(report.get('receipts'), list) or not report['receipts']:
        raise ValueError('nonempty calculation report required')
    if not all(isinstance(r, dict) and isinstance(r.get('activity'), dict) for r in report['receipts']):
        raise ValueError('receipt activity schema is invalid')
    if not all(verify_receipt(r) for r in report['receipts']):
        raise ValueError('receipt integrity check failed')
    fresh = calculate_batch([r['activity'] for r in report['receipts']], CURATED_FACTOR)
    if fresh != report:
        raise ValueError('report differs from deterministic recalculation')
    e = lambda x: escape(str(x), quote=True)
    rows = []
    for r in report['receipts']:
        a = r['activity']
        rows.append(f'''<section class="receipt"><div class="eyebrow">ACTIVITY / {e(a['activity_id'])}</div>
<h2>{e(a['site_id'])} <span class="status">{e(a['source_status'])}</span></h2>
<div class="equation"><strong>{e(r['energy_mwh'])}</strong> MWh <span>×</span> <strong>0.960</strong> tCO2e/MWh <span>=</span> <strong>{e(r['emissions_tco2e'])}</strong> tCO2e</div>
<p>Meter: {e(a['meter_id'])} · {e(a['period_start'])} to {e(a['period_end'])} (end exclusive)</p>
<p class="muted">Input: {e(a['quantity'])} {e(a['unit'])}.</p><p class="muted"><strong>Input note (unverified assertion):</strong> {e(a['source_note'])}</p>
<details><summary>Inspect reproducible integrity receipt</summary><code>{e(r['receipt_sha256'])}</code><p>A SHA-256 checksum detects accidental changes to these recorded contents. It is not a signature, blockchain record, proof of measurement or proof of authenticity. Anyone can recompute a hash.</p></details></section>''')
    f = CURATED_FACTOR
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GRIDSHIFT | Electricity emissions evidence</title><style>
:root{{--ink:#122c36;--muted:#49636c;--accent:#087c72;--paper:#f2f6f5;--line:#cbdcd8}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1040px;margin:auto;padding:48px 28px}}header{{border-top:6px solid var(--accent);padding-top:24px}}.eyebrow{{font-size:12px;letter-spacing:.13em;font-weight:800;color:var(--accent)}}h1{{font-size:clamp(32px,5vw,54px);line-height:1.1;margin:14px 0}}h2{{font-size:22px;line-height:1.3}}.lead{{font-size:20px;max-width:740px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin:28px 0}}.card,.receipt,.source{{padding:24px;background:#fff;border:1px solid var(--line);border-radius:12px}}.big{{font-size:48px;line-height:1.1;font-weight:800}}.muted{{color:var(--muted)}}.alert{{background:#fff2d5;border-left:5px solid #c47e08;padding:16px 22px}}.receipt{{margin:20px 0}}.status{{display:inline-block;font-size:11px;background:#fff0c5;padding:5px 8px;border-radius:4px;vertical-align:middle}}.equation{{background:#e6f3ee;padding:18px;font-size:18px;border-radius:6px}}.equation span{{padding:0 8px;color:var(--muted)}}details{{margin-top:18px}}summary{{cursor:pointer;font-weight:700}}code{{display:block;overflow-wrap:anywhere;font-size:12px;padding:12px;background:var(--paper)}}a{{color:#00645d;overflow-wrap:anywhere}}li{{margin:6px 0}}footer{{margin-top:28px;border-top:1px solid var(--line);padding-top:18px;font-size:12px}}@media print{{body{{background:white}}main{{padding:15px}}details{{display:block}}.receipt,.source{{break-inside:avoid}}}} </style></head><body><main>
<header><div class="eyebrow">GRIDSHIFT ASSURANCE / CLIMATE EVIDENCE PROTOTYPE</div><h1>Show the calculation.<br>Keep the caveats.</h1><p class="lead">An electricity-only location-based estimate using the published national grid factor. Every activity keeps its source status, factor year and calculation receipt.</p></header>
<div class="alert"><strong>Demonstration, not a verified inventory.</strong> These results are estimates, not measured savings, avoided emissions, carbon credits or carbon-neutrality claims. Activity statuses: {e(', '.join(report['activity_statuses']))}.</div>
<div class="alert"><strong>Published factor; unresolved source reconciliation.</strong> We retain the official 2024 NGGEF of 0.960 tCO2e/MWh. A separate arithmetic audit could not reconcile the published input tables and auxiliary-consumption footnotes. This factor has not been independently re-derived. Market-based emissions are not computed; organizational boundaries are not reviewed. This is not a full Scope 2 compliance assessment.</div>
<div class="cards"><section class="card"><div class="eyebrow">ESTIMATED EMISSIONS</div><div class="big">{e(report['total_emissions_tco2e'])}</div><div>tCO2e · {e(report['count'])} activity record(s)</div></section><section class="card"><div class="eyebrow">MATCHED FACTOR YEAR</div><div class="big">2024</div><div>South Africa · annual grid average</div></section><section class="card"><div class="eyebrow">SOURCE UNCERTAINTY</div><h2>Not quantified</h2><div>No invented confidence interval.</div></section></div>
{''.join(rows)}
<section class="source"><div class="eyebrow">PROVENANCE / CURATED MANUAL TRANSCRIPTION</div><h2>0.960 tCO2e/MWh · South Africa NGGEF</h2><p>{e(f['source_title'])}. Data year 2024, published {e(f['published_on'])}. {e(f['source_locator'])}. GWP basis: {e(f['gwp_basis'])}.</p><p><a href="{e(f['source_url'])}">Official DFFE report in Government Gazette 55353, Notice 7891</a></p><ul><li>Purchased electricity, Scope 2 location-based. Excludes transmission and distribution losses assigned to Scope 3.</li><li>Annual average, not an hourly, marginal, supplier-specific or renewable-energy factor.</li><li>This prototype conservatively requires matching factor and activity years and refuses 2026 usage with the 2024 factor. This is a prototype policy, not a universal accounting requirement.</li><li>Source uncertainty is not quantified. Measurement error and transcription risk are not removed by exact arithmetic.</li><li>All estimates are calculated from explicit energy quantities, never currency amounts.</li></ul></section>
<footer>Offline GRIDSHIFT proof of concept. No network calls, customer verification, smart contracts, blockchain, device control or external assurance. Source facts are attributed; no licence to redistribute the government PDF is asserted.</footer></main></body></html>'''

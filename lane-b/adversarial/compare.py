"""Check frozen policy expectations in each runtime, then diff runtimes step by step.
Exit 0 only when every expectation holds in every runtime and runtimes agree on all
policy-relevant fields. Error-message wording differences are reported separately."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
POLICY_FIELDS = ['step', 'ok', 'raw_sha256', 'revision', 'history_len', 'cached_review_null', 'active_resolutions',
                 'decision', 'emissions', 'proposal_sha256', 'resolution_accepted', 'finding_codes', 'export_sha256']


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def check(expect, steps):
    fails = []
    first = steps[0]
    if expect['open'] == 'REFUSED':
        if first['ok']:
            fails.append('open should be refused but succeeded')
        return fails
    if not first['ok']:
        return [f"open should succeed but failed: {first.get('error')}"]
    reviews = [s for s in steps[1:] if s['step'] in ('review', 'accept_current', 'reopen_export') or s['step'].startswith('accept_hash')]
    if 'decisions' in expect:
        got = [s.get('decision') if s['ok'] else 'ERROR' for s in reviews][:len(expect['decisions'])]
        if got != expect['decisions']:
            fails.append(f"decisions expected {expect['decisions']} got {got}")
    if 'emissions' in expect:
        e = [s.get('emissions') for s in reviews if s['ok'] and s.get('decision')]
        if not e or any(x != expect['emissions'] for x in e):
            fails.append(f"emissions expected {expect['emissions']} got {e}")
    if expect.get('cached_review_null') and not first.get('cached_review_null'):
        fails.append('imported cached_review survived reopen')
    if 'active_resolutions' in expect and first.get('active_resolutions') != expect['active_resolutions']:
        fails.append(f"active resolutions after open: {first.get('active_resolutions')}")
    if expect.get('no_total') and any(s.get('emissions') for s in reviews if s['ok']):
        fails.append('a total was produced where none is allowed')
    if 'final' in expect and steps[-1]['ok']:
        fails.append('final step should have been refused')
    if expect.get('working_equals_original_after_open'):
        exp = next((s for s in steps if s.get('export_json')), None)
        if exp is None:
            fails.append('working/original equality not evaluable: no export was produced')
        else:
            env = json.loads(exp['export_json'])
            w = dict(env['working']); o = dict(env['original']['parsed']); w.pop('resolutions', None); o.pop('resolutions', None)
            if canonical(w) != canonical(o):
                fails.append('working copy differs from preserved original after open (silent evidence mutation)')
    return fails


def main(native_path, browser_path, out_path):
    manifest = json.loads((HERE / 'FROZEN_MANIFEST.json').read_text())
    runs = {'native': json.loads(Path(native_path).read_text()), 'browser': json.loads(Path(browser_path).read_text())}
    report = {'manifest_cases': len(manifest['cases']), 'runtimes': {k: {x: v.get(x) for x in ('runtime', 'python', 'browser', 'pyodide_python', 'pyodide_runtime')} for k, v in runs.items()},
              'cases': [], 'ui': runs['browser'].get('ui'), 'page_errors': runs['browser'].get('page_errors')}
    totals = {'expectation_failures': 0, 'policy_divergences': 0, 'message_only_divergences': 0}
    for case in manifest['cases']:
        cid = case['id']; row = {'id': cid, 'attack': case['attack']}
        for name, run in runs.items():
            f = check(case['expect'], run['cases'][cid]); row[f'{name}_expectation_failures'] = f; totals['expectation_failures'] += len(f)
        a, b = runs['native']['cases'][cid], runs['browser']['cases'][cid]
        pol = []; msg = []
        for i in range(max(len(a), len(b))):
            sa = a[i] if i < len(a) else None; sb = b[i] if i < len(b) else None
            if sa is None or sb is None:
                pol.append({'index': i, 'native': sa and {k: sa.get(k) for k in POLICY_FIELDS + ['error']}, 'browser': sb and {k: sb.get(k) for k in POLICY_FIELDS + ['error']}}); continue
            da = {k: sa.get(k) for k in POLICY_FIELDS}; db = {k: sb.get(k) for k in POLICY_FIELDS}
            if da != db:
                pol.append({'index': i, 'step': sa['step'], 'fields': {k: [da[k], db[k]] for k in POLICY_FIELDS if da[k] != db[k]},
                            'native_error': sa.get('error'), 'browser_error': sb.get('error')})
            elif sa.get('error') != sb.get('error'):
                msg.append({'index': i, 'step': sa['step'], 'native': sa.get('error'), 'browser': sb.get('error')})
        row['policy_divergences'] = pol; row['message_divergences'] = msg
        totals['policy_divergences'] += len(pol); totals['message_only_divergences'] += len(msg)
        report['cases'].append(row)
    ui = runs['browser'].get('ui', {}).get('C28_xss_strings', {})
    report['xss_ui_inert'] = ui.get('xss_flag') is None and ui.get('injected_nodes') == 0
    report['totals'] = totals
    Path(out_path).write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(totals), 'xss_ui_inert=', report['xss_ui_inert'])
    for row in report['cases']:
        flags = [k for k in ('native_expectation_failures', 'browser_expectation_failures', 'policy_divergences', 'message_divergences') if row[k]]
        if flags:
            print(row['id'], {k: row[k] for k in flags})
    return 0 if totals['expectation_failures'] == 0 and totals['policy_divergences'] == 0 and report['xss_ui_inert'] else 1


if __name__ == '__main__':
    raise SystemExit(main(*sys.argv[1:4]))

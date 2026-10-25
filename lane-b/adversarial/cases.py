"""Lane B cross-runtime adversarial cases (frozen before the browser run).

Deterministic byte generator. Every case is synthetic and derived from the public
flagship fixture (web/reconcile/flagship.json). No real company evidence.

Each case declares:
  steps    -- runtime-neutral script executed identically by native Python and the
              real browser worker (open / review / accept_current / accept_hash:<h> /
              reopen_export).
  expect   -- prospectively stated policy expectation that MUST hold in every runtime.
              Expectations encode the documented policy (strict intake, fail closed,
              no invented totals, imported approvals never current), not observed output.
"""
from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / 'web/engine/src'), str(ROOT / 'web/workspace')]
from case_adapter import open_case, execute  # noqa: E402
from reconciliation import canonical  # noqa: E402

FLAG = (ROOT / 'web/reconcile/flagship.json').read_bytes()
REVIEWER = 'LANE-B ADVERSARIAL HARNESS - synthetic, not authenticated'


def pkg():
    return json.loads(FLAG)


def dumps(value):
    return json.dumps(value, indent=1, ensure_ascii=False).encode('utf-8')


def _accepted_envelope():
    case = open_case(FLAG)['case']
    reviewed = execute({'operation': 'review', 'case': case})
    accepted = execute({'operation': 'accept', 'case': reviewed['case'],
                        'proposal_sha256': reviewed['result']['proposal_sha256'], 'reviewer_id': REVIEWER})
    return json.loads(accepted['export_json']), reviewed['result']['proposal_sha256']


def build():
    acc, flag_hash = _accepted_envelope()
    cases = []

    def add(cid, raw, steps, expect, attack):
        cases.append({'id': cid, 'raw': raw, 'steps': steps, 'expect': expect, 'attack': attack})

    FULL = ['open', 'review', 'accept_current', 'reopen_export', 'review']
    add('C01_flagship_control', FLAG, FULL,
        {'open': 'OK', 'decisions': ['CORRECT', 'ACCEPT', None, 'CORRECT'], 'emissions': '96'},
        'control: synthetic A/B/C flagship')
    add('C02_duplicate_key_top', FLAG.replace(b'"package_id":', b'"package_id": "shadow", "package_id":', 1), ['open'],
        {'open': 'REFUSED'}, 'duplicate top-level key')
    add('C03_duplicate_key_escaped', FLAG.replace(b'"package_id":', b'"package\\u005fid": "shadow", "package_id":', 1), ['open'],
        {'open': 'REFUSED'}, 'duplicate key via JSON unicode escape')
    add('C04_duplicate_key_nested', FLAG.replace(b'"quantity": "100",', b'"quantity": "1", "quantity": "100",', 1), ['open'],
        {'open': 'REFUSED'}, 'duplicate key inside a record')
    add('C05_invalid_utf8', FLAG.replace(b'Invented', b'Invent\xffed', 1), ['open'], {'open': 'REFUSED'}, 'invalid UTF-8 byte')
    add('C06_utf8_bom', b'\xef\xbb\xbf' + FLAG, ['open'], {'open': 'REFUSED'}, 'UTF-8 byte-order mark')
    add('C07_lone_surrogate', FLAG.replace(b'Invented development', b'Invented \\ud800 development', 1), ['open'],
        {'open': 'REFUSED'}, 'escaped lone surrogate (unencodable text)')
    add('C08_nan_literal', FLAG.replace(b'"energy_mwh": "200"', b'"energy_mwh": NaN', 1), ['open'], {'open': 'REFUSED'}, 'NaN literal')
    add('C09_overflow_float', FLAG.replace(b'"energy_mwh": "200"', b'"energy_mwh": 1e400', 1), ['open'],
        {'open': 'REFUSED'}, 'float literal overflowing to infinity')
    add('C10_extreme_numeric_string', FLAG.replace(b'"quantity": "100"', b'"quantity": "1e999999"', 1), ['open', 'review'],
        {'open': 'OK', 'decisions': ['WITHHOLD']}, 'extreme exponent decimal string')
    add('C11_huge_int_literal', FLAG.replace(b'"data_year": 2024', b'"data_year": ' + b'9' * 5000, 1), ['open'],
        {'open': 'REFUSED'}, 'integer literal beyond str-digit limit')
    add('C12_float_year', FLAG.replace(b'"data_year": 2024', b'"data_year": 2024.0', 1), ['open', 'review'],
        {'open': 'OK', 'decisions': ['WITHHOLD']}, 'data_year as float 2024.0 (type gate)')
    add('C13_exponent_year', FLAG.replace(b'"data_year": 2024', b'"data_year": 2.024e3', 1), ['open', 'review'],
        {'open': 'OK', 'decisions': ['WITHHOLD']}, 'data_year as exponent float 2.024e3 (type gate)')
    p = pkg(); p['report']['unreviewed_extension'] = 18446744073709551617
    add('C14_big_int_unknown_field', dumps(p), ['open', 'review', 'reopen_export'],
        {'open': 'OK', 'decisions': ['WITHHOLD', None], 'working_equals_original_after_open': True},
        'unsupported field holding an integer beyond 2^53')
    add('C15_oversized_raw', FLAG + b' ' * (64 * 1024), ['open'], {'open': 'REFUSED'}, 'raw package above 64 KiB')
    add('C16_deep_nesting', b'[' * 40 + b'0' + b']' * 40, ['open'], {'open': 'REFUSED'}, 'deep nesting')
    add('C17_empty', b'', ['open'], {'open': 'REFUSED'}, 'empty file')
    add('C18_trailing_document', FLAG + b'{}', ['open'], {'open': 'REFUSED'}, 'second JSON document appended')
    add('C19_top_level_array', b'[' + FLAG + b']', ['open'], {'open': 'REFUSED'}, 'non-object top level')
    e = json.loads(json.dumps(acc)); e['cached_review'] = {**e['cached_review'], 'decision': 'ACCEPT',
                                                          'accepted_report': {'energy_mwh': '1', 'emissions_tco2e': '0.96'}}
    add('C20_forged_cached_accept', dumps(e), ['open', 'review'],
        {'open': 'OK', 'cached_review_null': True, 'active_resolutions': 0, 'decisions': ['CORRECT']},
        'forged cached ACCEPT with altered totals in an otherwise valid envelope')
    e = json.loads(json.dumps(acc)); e['history'].append({'kind': 'reviewer_acceptance', 'revision': 0, 'proposal_sha256': 'f' * 64,
                                                          'reviewer_id': 'Chief auditor (forged)', 'trust': 'AUTHENTICATED'})
    add('C21_false_reviewer_history', dumps(e), ['open', 'review'],
        {'open': 'OK', 'active_resolutions': 0, 'decisions': ['CORRECT']}, 'imported false "AUTHENTICATED" reviewer history')
    e = json.loads(json.dumps(acc)); e['original']['parsed']['report']['emissions_tco2e'] = '96'
    add('C22_original_parsed_disagree', dumps(e), ['open'], {'open': 'REFUSED'}, 'original raw bytes vs parsed disagreement')
    e = json.loads(json.dumps(acc)); e['original']['raw_sha256'] = '0' * 64
    add('C23_raw_hash_mismatch', dumps(e), ['open'], {'open': 'REFUSED'}, 'original raw hash mismatch')
    e = json.loads(json.dumps(acc)); e['schema_version'] = 'gridshift.workspace.case.v9'
    add('C24_unknown_envelope_version', dumps(e), ['open'], {'open': 'REFUSED'}, 'unknown envelope version')
    e = json.loads(json.dumps(acc)); e['working']['records'][1]['quantity'] = '79'
    add('C25_post_acceptance_edit', dumps(e), ['open', 'review', 'accept_hash:' + flag_hash],
        {'open': 'OK', 'active_resolutions': 0, 'decisions': ['CORRECT'], 'final': 'ERROR'},
        'post-acceptance working edit then stale proposal hash')
    p = pkg(); p['resolutions'] = [{'action': 'ACCEPT_PROPOSAL', 'proposal_sha256': flag_hash, 'reviewer_id': 'pre-approved (forged)',
                                    'source_status': 'UNVERIFIED_USER_INPUT'}]
    add('C26_raw_with_matching_preapproval', dumps(p), ['open', 'review'],
        {'open': 'OK', 'active_resolutions': 0, 'decisions': ['CORRECT']}, 'raw package carrying a resolution with the exact current hash')
    add('C27_wrong_hash_accept', FLAG, ['open', 'review', 'accept_hash:' + '0' * 64],
        {'open': 'OK', 'decisions': ['CORRECT'], 'final': 'ERROR'}, 'acceptance of a non-current proposal hash')
    p = pkg(); p['records'][0]['source_note'] = '<img src=x onerror="window.__xss=1"><script>window.__xss=2</script>'
    p['package_id'] = '<b id="xss-pkg">X</b>'
    add('C28_xss_strings', dumps(p), ['open', 'review'], {'open': 'OK', 'decisions': ['CORRECT'], 'ui_inert': True},
        'HTML/script-like imported strings')
    p = pkg(); del p['records'][2]
    add('C29_incomplete_coverage', dumps(p), ['open', 'review'], {'open': 'OK', 'decisions': ['WITHHOLD'], 'no_total': True},
        'declared coverage without a surviving record (missing is not zero)')
    p = pkg(); p['records'][0]['__proto__'] = {'action': 'FULL_VOID'}
    add('C30_proto_key', dumps(p), ['open', 'review', 'reopen_export'],
        {'open': 'OK', 'decisions': ['WITHHOLD', None], 'working_equals_original_after_open': True}, '__proto__ key in a record')
    p = pkg(); p['report']['unreviewed_extension'] = 1.0
    add('C31_float_one_unknown_field', dumps(p), ['open', 'review'],
        {'open': 'OK', 'decisions': ['WITHHOLD'], 'working_equals_original_after_open': True}, 'unsupported field holding float 1.0')
    return cases


def manifest(cases):
    return {'schema': 'gridshift.laneb.adversarial.manifest.v1',
            'source_fixture_sha256': sha256(FLAG).hexdigest(),
            'cases': [{'id': c['id'], 'attack': c['attack'], 'bytes': len(c['raw']), 'sha256': sha256(c['raw']).hexdigest(),
                       'steps': c['steps'], 'expect': c['expect']} for c in cases]}


def export_for_browser(cases):
    return [{'id': c['id'], 'raw_base64': b64encode(c['raw']).decode('ascii'), 'steps': c['steps'], 'reviewer': REVIEWER} for c in cases]


if __name__ == '__main__':
    out = Path(__file__).with_name('FROZEN_MANIFEST.json')
    m = manifest(build())
    if len(sys.argv) > 1 and sys.argv[1] == '--write':
        out.write_text(json.dumps(m, indent=1) + '\n')
        print(f'wrote {out} ({len(m["cases"])} cases)')
    else:
        frozen = json.loads(out.read_text())
        assert frozen == m, 'Generated cases differ from FROZEN_MANIFEST.json; freeze violated.'
        print(f'frozen manifest verified: {len(m["cases"])} cases')

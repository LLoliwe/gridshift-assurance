"""AC-5 quarantine regressions (development, synthetic). Separate from the frozen 31
adversarial cases and from test_workspace_portability.py; frozen files are only read."""
from base64 import b64decode
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'web/engine/src'), str(ROOT / 'web/workspace')]
from case_adapter import ENVELOPE_LIMIT, INTAKE_PATH, RAW_LIMIT, execute, open_case  # noqa: E402
import quarantine as q  # noqa: E402
from quarantine_state import (QUARANTINED, SCHEMA_REJECTION, STATE_LABELS, WITHHOLD,  # noqa: E402
                              QuarantineRefusal)

FLAG = (ROOT / 'web/reconcile/flagship.json').read_bytes()
MISSING_EDGE = (ROOT / 'web/reconcile/missing-edge.json').read_bytes()
MANIFEST = json.loads((ROOT / 'lane-b/adversarial/FROZEN_MANIFEST.json').read_text())
FROZEN_SHA = {c['id']: c['sha256'] for c in MANIFEST['cases']}
NOW = datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc)


def _dumps(value):
    return json.dumps(value, indent=1, ensure_ascii=False).encode('utf-8')


def _with_extension(value):
    p = json.loads(FLAG)
    p['report']['unreviewed_extension'] = value
    return _dumps(p)


# Same constructions as the frozen C12/C13/C14/C31 inputs; equality is asserted against the manifest.
STYLE = {
    'C12_float_year': (FLAG.replace(b'"data_year": 2024', b'"data_year": 2024.0', 1),
                       'FLOAT_OR_EXPONENT_NUMBER', '$.report.data_year', '2024.0'),
    'C13_exponent_year': (FLAG.replace(b'"data_year": 2024', b'"data_year": 2.024e3', 1),
                          'FLOAT_OR_EXPONENT_NUMBER', '$.report.data_year', '2.024e3'),
    'C14_big_int_unknown_field': (_with_extension(18446744073709551617), 'INTEGER_OUTSIDE_PORTABLE_RANGE',
                                  '$.report.unreviewed_extension', '18446744073709551617'),
    'C31_float_one_unknown_field': (_with_extension(1.0), 'FLOAT_OR_EXPONENT_NUMBER',
                                    '$.report.unreviewed_extension', '1.0'),
}


def _quarantine(raw):
    out = q.intake(raw, now=NOW, commit='0' * 40)
    assert out['state'] == QUARANTINED, out
    return out['quarantine']


class QuarantineIntakeTests(unittest.TestCase):
    def test_style_inputs_match_frozen_bytes(self):
        for cid, (raw, *_rest) in STYLE.items():
            with self.subTest(cid):
                self.assertEqual(sha256(raw).hexdigest(), FROZEN_SHA[cid])

    def test_c12_c13_c14_c31_style_inputs_are_quarantined_with_field_reasons(self):
        for cid, (raw, code, path, token) in STYLE.items():
            with self.subTest(cid):
                out = q.intake(raw, now=NOW)
                self.assertEqual((out['state'], out['intake_result']), (QUARANTINED, SCHEMA_REJECTION))
                self.assertIsNone(out['case'])
                self.assertIsNone(out['result'])
                record = out['quarantine']
                self.assertIsNone(record['engine_decision'])
                self.assertIs(record['admitted_to_calculation'], False)
                self.assertIs(record['acceptance_possible'], False)
                self.assertEqual(b64decode(record['original']['raw_base64']), raw)
                self.assertEqual(record['original']['raw_sha256'], sha256(raw).hexdigest())
                self.assertIn({'code': code, 'path': path, 'token': token},
                              [{k: r.get(k) for k in ('code', 'path', 'token')} for r in record['rejection']['reasons']])
                self.assertEqual(record['quarantined_at_utc'], '2026-10-25T20:00:00.000000Z')

    def test_all_numeric_findings_are_listed_not_only_the_first(self):
        raw = FLAG.replace(b'"data_year": 2024', b'"data_year": 2.024e3, "a": 1e400, "b": -9007199254740992', 1)
        codes = [(r['code'], r['path']) for r in _quarantine(raw)['rejection']['reasons']]
        self.assertEqual(codes, [('FLOAT_OR_EXPONENT_NUMBER', '$.report.data_year'),
                                 ('FLOAT_OR_EXPONENT_NUMBER', '$.report.a'),
                                 ('INTEGER_OUTSIDE_PORTABLE_RANGE', '$.report.b')])

    def test_parse_level_rejections_are_quarantined_with_reason(self):
        cases = {b'\xff\xfe{}': 'INVALID_UTF8', b'{"a":1,"a":2}': 'DUPLICATE_KEY', b'{"a": NaN}': 'NON_FINITE_CONSTANT',
                 b'{"a": [1,}': 'JSON_SYNTAX', b'[' * 200 + b']' * 200: 'PARSE_REJECTION'}
        for raw, code in cases.items():
            with self.subTest(code):
                record = _quarantine(raw)
                self.assertEqual(record['rejection']['reasons'][-1]['code'], code)
                self.assertEqual(q.original_bytes(record), raw)

    def test_supported_inputs_open_exactly_as_before(self):
        out = q.intake(FLAG)
        self.assertEqual((out['state'], out['intake_result'], out['quarantine']), ('OPEN', 'ADMITTED', None))
        self.assertEqual(out['case'], open_case(FLAG)['case'])
        self.assertEqual(execute({'operation': 'review', 'case': out['case']})['result']['decision'], 'CORRECT')

    def test_valid_input_without_established_total_is_withhold_not_quarantine(self):
        out = q.intake(MISSING_EDGE)
        self.assertEqual(out['state'], 'OPEN')
        self.assertEqual(execute({'operation': 'review', 'case': out['case']})['result']['decision'], WITHHOLD)


class QuarantineBoundTests(unittest.TestCase):
    def setUp(self):
        INTAKE_PATH.unlink(missing_ok=True)

    def _refused(self, raw):
        with self.assertRaises(q.IntakeRefused) as ctx:
            q.intake(raw)
        self.assertIn('nothing', str(ctx.exception).lower())
        self.assertFalse(INTAKE_PATH.exists())

    def test_empty_input_refused_and_not_stored(self):
        self._refused(b'')

    def test_oversized_input_refused_and_not_stored(self):
        self._refused(b'{' + b' ' * ENVELOPE_LIMIT)
        self._refused(FLAG + b' ' * ENVELOPE_LIMIT)

    def test_non_bytes_refused(self):
        for value in ['{}', None, {'a': 1}]:
            with self.subTest(value=value):
                self._refused(value)

    def test_upper_bound_is_inclusive_and_large_raw_package_is_quarantined_exactly(self):
        raw = FLAG + b' ' * (ENVELOPE_LIMIT - len(FLAG))
        self.assertEqual(len(raw), ENVELOPE_LIMIT)
        record = _quarantine(raw)  # raw packages above 64 KiB are a schema rejection, kept exactly
        self.assertEqual(q.original_bytes(record), raw)
        self.assertIn('64 KiB', record['rejection']['adapter_message'])
        self.assertGreater(len(raw), RAW_LIMIT)
        self.assertFalse(INTAKE_PATH.exists())


class QuarantineExportTests(unittest.TestCase):
    def test_byte_exact_export_round_trip(self):
        for cid, (raw, *_rest) in STYLE.items():
            with self.subTest(cid):
                record = _quarantine(raw)
                exported = q.export_diagnostic(record, now=NOW)
                text = exported['text']
                self.assertEqual(sha256(text.encode('utf-8')).hexdigest(), exported['export_sha256'])
                diagnostic = json.loads(text)
                self.assertEqual(q.export_original_bytes(diagnostic), raw)
                self.assertEqual(diagnostic['original']['raw_sha256'], sha256(raw).hexdigest())
                self.assertEqual(diagnostic['rejection'], record['rejection'])
                self.assertEqual(diagnostic['quarantined_at_utc'], '2026-10-25T20:00:00.000000Z')
                self.assertEqual(diagnostic['exported_at_utc'], '2026-10-25T20:00:00.000000Z')
                self.assertEqual(diagnostic['tool_at_quarantine']['commit'], '0' * 40)
                self.assertTrue(diagnostic['tool_at_export']['quarantine_py_sha256'])
                self.assertIn('NO CALCULATION, NO PROPOSAL AND NO ACCEPTANCE OCCURRED', diagnostic['statement'])
                self.assertEqual((diagnostic['calculation_performed'], diagnostic['proposal_created'],
                                  diagnostic['acceptance_performed'], diagnostic['engine_decision']),
                                 (False, False, False, None))
                self.assertEqual(diagnostic['export_recheck'],
                                 {'raw_sha256_verified': True, 'still_rejected_by_current_intake': True,
                                  'current_adapter_message': record['rejection']['adapter_message'],
                                  'reasons_match_record': True})

    def test_non_utf8_bytes_round_trip_exactly(self):
        raw = b'\x00\xff\xfe binary \x80'
        diagnostic = json.loads(q.export_diagnostic(_quarantine(raw))['text'])
        self.assertEqual(q.export_original_bytes(diagnostic), raw)
        self.assertFalse(q.view(_quarantine(raw))['display_is_exact_utf8'])

    def test_view_is_display_only(self):
        raw = STYLE['C13_exponent_year'][0]
        shown = q.view(_quarantine(raw))
        self.assertEqual(shown['display_text'].encode('utf-8'), raw)
        self.assertEqual(shown['state'], QUARANTINED)

    def test_tampered_records_are_rejected(self):
        record = _quarantine(STYLE['C12_float_year'][0])
        for mutate in [lambda r: r['original'].update(raw_sha256='0' * 64),
                       lambda r: r['original'].update(raw_base64=r['original']['raw_base64'][:-4]),
                       lambda r: r['original'].update(byte_length=1),
                       lambda r: r.update(state='OPEN'),
                       lambda r: r.update(admitted_to_calculation=True),
                       lambda r: r.update(engine_decision=WITHHOLD),
                       lambda r: r.update(extra=1)]:
            tampered = json.loads(json.dumps(record))
            mutate(tampered)
            with self.subTest(tampered=str(tampered)[:80]), self.assertRaises(ValueError):
                q.export_diagnostic(tampered)


class QuarantineRefusalTests(unittest.TestCase):
    def setUp(self):
        self.record = _quarantine(STYLE['C14_big_int_unknown_field'][0])
        self.diagnostic = q.export_diagnostic(self.record)['diagnostic']
        self.proposal = execute({'operation': 'review', 'case': open_case(FLAG)['case']})['result']['proposal_sha256']

    def test_calculate_propose_accept_save_export_refuse_quarantined_material(self):
        for material in (self.record, self.diagnostic):
            for request in [{'operation': 'review', 'case': material},
                            {'operation': 'accept', 'case': material, 'proposal_sha256': self.proposal,
                             'reviewer_id': 'synthetic reviewer'},
                            {'operation': 'save', 'case': material}, {'operation': 'export', 'case': material},
                            {'operation': 'review', 'quarantine': material}, material]:
                with self.subTest(op=request.get('operation'), kind=material['schema_version']), \
                        self.assertRaisesRegex(QuarantineRefusal, '^QUARANTINED: .*refused'):
                    execute(request)

    def test_quarantine_record_and_diagnostic_cannot_be_reopened_as_a_case(self):
        for material in (self.record, self.diagnostic):
            raw = json.dumps(material).encode('utf-8')
            with self.assertRaises(QuarantineRefusal):
                open_case(raw)
            again = q.intake(raw)
            self.assertEqual(again['state'], QUARANTINED)
            self.assertIn('QUARANTINE_DIAGNOSTIC_NOT_ADMISSIBLE',
                          [r['code'] for r in again['quarantine']['rejection']['reasons']])

    def test_quarantine_execute_offers_only_view_and_export(self):
        for op in ('review', 'accept', 'open', 'save'):
            with self.subTest(op=op), self.assertRaises(QuarantineRefusal):
                q.quarantine_execute({'operation': op, 'quarantine': self.record})
        self.assertEqual(q.quarantine_execute({'operation': 'quarantine_view', 'quarantine': self.record})['state'], QUARANTINED)


class StateLabelTests(unittest.TestCase):
    def test_three_labels_are_distinct(self):
        self.assertEqual(len(set(STATE_LABELS.values())), 3)
        self.assertEqual(STATE_LABELS, {'storage_state': 'QUARANTINED', 'intake_result': 'SCHEMA_REJECTION',
                                        'engine_policy_result': 'WITHHOLD'})

    def test_schema_rejection_is_never_labelled_withhold(self):
        for cid, (raw, *_rest) in STYLE.items():
            with self.subTest(cid):
                out = q.intake(raw)
                exported = q.export_diagnostic(out['quarantine'])['text']
                self.assertNotIn(WITHHOLD, json.dumps(out))
                self.assertNotIn(WITHHOLD, exported)
                self.assertNotEqual(out['intake_result'], WITHHOLD)

    def test_documented_number_policy_is_carried_in_record(self):
        policy = _quarantine(STYLE['C12_float_year'][0])['rejection']['number_policy']
        self.assertIn('conservatively', policy)
        self.assertIn('transport limit', policy)
        self.assertIn('not an accounting limit', policy)


if __name__ == '__main__':
    unittest.main()

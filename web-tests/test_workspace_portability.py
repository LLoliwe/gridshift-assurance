"""Lane B regression cases (development, synthetic). Exposed by the run-1 cross-runtime
comparison in lane-b/adversarial/results/run1_pre_fix; not independent holdout evidence."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'web/engine/src'), str(ROOT / 'web/workspace')]
from case_adapter import open_case, execute
RAW = (ROOT / 'web/reconcile/flagship.json').read_bytes()


class PortabilityIntakeTests(unittest.TestCase):
    def test_float_and_exponent_numbers_refused_at_open_with_path(self):
        for value in [b'2024.0', b'2.024e3', b'2024e0']:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, r'\$\.report\.data_year.*JSON integer 2024'):
                open_case(RAW.replace(b'"data_year": 2024', b'"data_year": ' + value, 1))

    def test_unsafe_integers_refused_at_open(self):
        for value in [b'9007199254740992', b'-9007199254740992', b'18446744073709551617']:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'portable range'):
                open_case(RAW.replace(b'"data_year": 2024', b'"data_year": 2024, "laneb_extra": ' + value, 1))

    def test_boundary_safe_integer_still_opens_and_is_reviewed(self):
        case = open_case(RAW.replace(b'"data_year": 2024', b'"data_year": 2024, "laneb_extra": 9007199254740991', 1))['case']
        self.assertEqual(execute({'operation': 'review', 'case': case})['result']['decision'], 'WITHHOLD')

    def test_nested_float_in_history_of_envelope_refused(self):
        exported = execute({'operation': 'export', 'case': open_case(RAW)['case']})['export_json']
        tampered = exported.replace('"history":[]', '"history":[{"note":1.0}]', 1)
        self.assertNotEqual(tampered, exported)
        with self.assertRaisesRegex(ValueError, r'\$\.history\[0\]\.note'):
            open_case(tampered.encode())

    def test_data_year_advice_is_integer_not_decimal_string(self):
        # Round-2 regression: the R1 message told users to write data_year as a decimal string,
        # which then withholds as REPORT_FACTOR_MISMATCH. The advice must point to integer 2024.
        for value in [b'2024.0', b'2.024e3', b'9007199254740993']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as ctx:
                    open_case(RAW.replace(b'"data_year": 2024', b'"data_year": ' + value, 1))
                message = str(ctx.exception)
                self.assertIn('JSON integer 2024', message)
                self.assertNotIn('decimal string', message)
        quoted = execute({'operation': 'review', 'case': open_case(RAW.replace(b'"data_year": 2024', b'"data_year": "2024"', 1))['case']})
        self.assertEqual(quoted['result']['decision'], 'WITHHOLD')
        fixed = execute({'operation': 'review', 'case': open_case(RAW)['case']})['result']
        self.assertEqual(fixed['decision'], 'CORRECT')

    def test_quantity_and_unknown_field_advice_is_field_specific(self):
        with self.assertRaisesRegex(ValueError, r'\$\.report\.energy_mwh.*quoted decimal strings'):
            open_case(RAW.replace(b'"energy_mwh": "200"', b'"energy_mwh": 200.0', 1))
        with self.assertRaises(ValueError) as ctx:
            open_case(RAW.replace(b'"data_year": 2024', b'"data_year": 2024, "laneb_extra": 1.0', 1))
        self.assertIn('$.report.laneb_extra', str(ctx.exception))
        self.assertNotIn('decimal string', str(ctx.exception))

    def test_flagship_unaffected(self):
        r = execute({'operation': 'review', 'case': open_case(RAW)['case']})['result']
        self.assertEqual((r['decision'], r['proposed_report']['emissions_tco2e']), ('CORRECT', '96'))


if __name__ == '__main__':
    unittest.main()

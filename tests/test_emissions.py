"""Behavior tests: wrong conversion, hidden provenance, unsafe period/factor selection."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
try:
    from emissions import calculate
except ImportError:
    calculate = None

FACTOR = {
    'factor_id': 'ZA_NGGEF_2024_DFFE_2026', 'value': '0.960',
    'unit': 'tCO2e/MWh', 'country': 'ZA', 'data_year': 2024,
    'boundary': 'SCOPE2_LOCATION_BASED_PURCHASED_ELECTRICITY',
    'source_url': 'https://www.gov.za/sites/default/files/gcis_document/202609/55353gon7891.pdf',
    'source_title': 'South Africa 2024 Grid Emission Factors Report',
    'source_locator': 'Table 1, printed page 3; Appendix A, printed page 19',
    'published_on': '2026-09-11', 'gwp_basis': 'IPCC Second Assessment Report',
    'uncertainty': 'NOT_QUANTIFIED_IN_SOURCE',
    'transcription_status': 'MANUALLY_TRANSCRIBED_OFFICIAL_SOURCE',
}
ACTIVITY = {
    'activity_id': 'synthetic-2024-001', 'site_id': 'DEMO-SITE', 'meter_id': 'DEMO-METER',
    'country': 'ZA', 'period_start': '2024-01-01', 'period_end': '2025-01-01',
    'quantity': '500', 'unit': 'MWh', 'source_status': 'SYNTHETIC',
    'source_note': 'Invented activity matching official report worked example; not a real customer.',
}

class EmissionsTests(unittest.TestCase):
    def test_official_worked_example_500_mwh_is_480_tonnes(self):
        self.assertTrue(callable(calculate), 'emissions calculator is not implemented')
        result = calculate(ACTIVITY, FACTOR)
        self.assertEqual(result['emissions_tco2e'], '480')
        self.assertEqual(result['activity_status'], 'SYNTHETIC')
        self.assertEqual(result['factor'], FACTOR)
        self.assertEqual(result['uncertainty'], 'NOT_QUANTIFIED_IN_SOURCE')

    def test_kwh_conversion(self):
        for qty, expected in [('500000', '480'), ('1', '0.00096'), ('0', '0')]:
            a = dict(ACTIVITY, quantity=qty, unit='kWh')
            self.assertEqual(calculate(a, FACTOR)['emissions_tco2e'], expected)

    def test_reject_invalid_quantities(self):
        for qty in ['-1', 'NaN', 'Infinity', True, None, '', '1e99999']:
            with self.subTest(quantity=qty), self.assertRaises(ValueError):
                calculate(dict(ACTIVITY, quantity=qty), FACTOR)

    def test_reject_unknown_units(self):
        for unit in ['ZAR', 'kW', 'mwh', '', None]:
            with self.subTest(unit=unit), self.assertRaises(ValueError):
                calculate(dict(ACTIVITY, unit=unit), FACTOR)

    def test_country_mismatch(self):
        with self.assertRaises(ValueError):
            calculate(dict(ACTIVITY, country='KE'), FACTOR)

    def test_period_year_mismatch_or_cross_year(self):
        for start, end in [('2026-01-01', '2026-02-01'), ('2023-12-31', '2024-02-01'),
                           ('2024-12-01', '2025-01-02'), ('2024-01-01', '2024-01-01'),
                           ('2024-02-01', '2024-01-01'), ('not-a-date', '2025-01-01')]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                calculate(dict(ACTIVITY, period_start=start, period_end=end), FACTOR)

    def test_reject_non_scope2_factors(self):
        for field, val in [('boundary', 'DOMESTIC_GENERATION'), ('unit', 'kgCO2e/kWh'),
                           ('value', '-1'), ('value', 'NaN'), ('data_year', True),
                           ('data_year', '2024'), ('published_on', 'invalid')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                calculate(ACTIVITY, dict(FACTOR, **{field:val}))

    def test_missing_or_blank_provenance_fails(self):
        for field in FACTOR:
            for val in [None, '']:
                with self.subTest(field=field, val=val), self.assertRaises(ValueError):
                    calculate(ACTIVITY, dict(FACTOR, **{field: val}))

    def test_missing_or_blank_activity_fields_fail(self):
        for field in ACTIVITY:
            a = dict(ACTIVITY); del a[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                calculate(a, FACTOR)

    def test_no_false_verified_status_or_invented_uncertainty(self):
        with self.assertRaises(ValueError):
            calculate(dict(ACTIVITY, source_status='VERIFIED'), FACTOR)
        with self.assertRaises(ValueError):
            calculate(ACTIVITY, dict(FACTOR, uncertainty='+/- 5%'))

    def test_inputs_not_mutated(self):
        a, f = copy.deepcopy(ACTIVITY), copy.deepcopy(FACTOR)
        r = calculate(a, f); r['factor']['value'] = '99'
        self.assertEqual(a, ACTIVITY); self.assertEqual(f, FACTOR)

    def test_receipt_stable_and_sensitive_to_activity_changes(self):
        r = calculate(ACTIVITY, FACTOR)
        self.assertIn('receipt_sha256', r)
        self.assertEqual(len(r['receipt_sha256']), 64)
        self.assertEqual(r, calculate(dict(reversed(list(ACTIVITY.items()))), FACTOR))
        altered = calculate(dict(ACTIVITY, quantity='501'), FACTOR)
        self.assertNotEqual(r['receipt_sha256'], altered['receipt_sha256'])
        self.assertEqual(r['activity'], ACTIVITY)
        self.assertEqual(r['energy_mwh'], '500')
        self.assertEqual(r['method'], 'ENERGY_MWH_TIMES_GRID_FACTOR')
        self.assertIn('NOT_AN_INDEPENDENT_VERIFICATION', r['limitations'])

    def test_receipt_verification_detects_tampering(self):
        import emissions
        self.assertTrue(callable(getattr(emissions, 'verify_receipt', None)), 'receipt verifier missing')
        r = calculate(ACTIVITY, FACTOR)
        self.assertTrue(emissions.verify_receipt(r))
        r['emissions_tco2e'] = '0'
        self.assertFalse(emissions.verify_receipt(r))

    def test_batch_totals_and_duplicate_meter_intervals(self):
        import emissions
        self.assertTrue(callable(getattr(emissions, 'calculate_batch', None)), 'batch calculator missing')
        a = dict(ACTIVITY, activity_id='a', period_end='2024-02-01', quantity='10')
        b = dict(ACTIVITY, activity_id='b', period_start='2024-02-01', period_end='2024-03-01', quantity='20')
        result = emissions.calculate_batch([a, b], FACTOR)
        self.assertEqual(result['total_emissions_tco2e'], '28.8')
        self.assertEqual(result['count'], 2)
        for bad in [dict(b, activity_id='a'), dict(b, period_start='2024-01-31')]:
            with self.assertRaises(ValueError):
                emissions.calculate_batch([a, bad], FACTOR)
        with self.assertRaises(ValueError):
            emissions.calculate_batch([], FACTOR)

    def test_signed_zero_results_normalize_without_rewriting_source_input(self):
        for quantity in ['-0', '-0.000']:
            r=calculate(dict(ACTIVITY,quantity=quantity),FACTOR)
            self.assertEqual(r['emissions_tco2e'],'0')
            self.assertEqual(r['energy_mwh'],'0')
            self.assertEqual(r['activity']['quantity'],quantity)

if __name__ == '__main__': unittest.main()

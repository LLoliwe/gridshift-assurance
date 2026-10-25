import copy
import unittest
from test_emissions import ACTIVITY, FACTOR
import emissions

class PreflightTests(unittest.TestCase):
    def check(self, activities):
        self.assertTrue(callable(getattr(emissions, 'preflight', None)), 'batch preflight missing')
        return emissions.preflight(activities, FACTOR)

    def test_reports_every_invalid_row_without_partial_emissions_total(self):
        wrong_year = dict(ACTIVITY, activity_id='year', period_start='2026-01-01', period_end='2027-01-01')
        bad_unit = dict(ACTIVITY, activity_id='money', unit='ZAR')
        result = self.check([ACTIVITY, wrong_year, bad_unit])
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['input_count'], 3)
        self.assertEqual(result['blocked_count'], 2)
        self.assertEqual(result['rows'][0]['status'], 'READY')
        self.assertEqual(result['rows'][1]['activity_id'], 'year')
        self.assertEqual(result['rows'][1]['index'], 1)
        self.assertIn('FACTOR_YEAR_MISMATCH', result['rows'][1]['issues'][0]['message'])
        self.assertTrue(result['rows'][1]['issues'][0]['action'])
        self.assertNotIn('total_emissions_tco2e', result)
        self.assertNotIn('emissions_tco2e', result['rows'][0])

    def test_both_sides_of_overlap_are_flagged(self):
        b = dict(ACTIVITY, activity_id='second')
        result = self.check([ACTIVITY, b])
        self.assertEqual(result['blocked_count'], 2)
        for row in result['rows']:
            self.assertIn('OVERLAPPING_PERIOD', [i['code'] for i in row['issues']])

    def test_duplicate_ids_across_sites_are_flagged_on_both_rows(self):
        b = dict(ACTIVITY, site_id='OTHER')
        result = self.check([ACTIVITY, b])
        self.assertEqual(result['blocked_count'], 2)
        for row in result['rows']:
            self.assertIn('DUPLICATE_ID', [i['code'] for i in row['issues']])

    def test_valid_batch_ready_but_does_not_claim_input_verification(self):
        result = self.check([ACTIVITY])
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['blocked_count'], 0)
        self.assertEqual(result['rows'][0]['activity_status'], 'SYNTHETIC')
        self.assertFalse(result['input_authenticity_verified'])

    def test_malformed_row_is_reported_not_dropped(self):
        result = self.check([None, ACTIVITY])
        self.assertEqual(result['input_count'], 2)
        self.assertEqual(result['rows'][0]['status'], 'BLOCKED')
        self.assertIsNone(result['rows'][0]['activity_id'])

if __name__ == '__main__': unittest.main()

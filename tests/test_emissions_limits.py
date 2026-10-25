"""Resource ceilings are explicit protocol limits, not performance claims."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_emissions import ACTIVITY, FACTOR
from emissions import calculate, calculate_batch, preflight
ROOT=Path(__file__).resolve().parents[1]

class ResourceLimitTests(unittest.TestCase):
    def test_batches_above_1000_records_are_rejected(self):
        values=[dict(ACTIVITY, activity_id=str(i), meter_id=str(i)) for i in range(1001)]
        for fn in [calculate_batch,preflight]:
            with self.subTest(function=fn.__name__), self.assertRaises(ValueError):fn(values,FACTOR)

    def test_overlong_numeric_token_rejected_before_decimal_conversion(self):
        # Small numeric value, excessive representation length: not an overflow test.
        with self.assertRaises(ValueError):calculate(dict(ACTIVITY,quantity='0'*10000+'1'),FACTOR)

    def test_large_conflict_graph_has_explicit_bounded_diagnostics(self):
        values=[dict(ACTIVITY,activity_id=str(i)) for i in range(25)]
        r=preflight(values,FACTOR)
        self.assertEqual(r['blocked_count'],25)
        for row in r['rows']:
            self.assertIn('issue_count',row,'diagnostic count required before bounded excerpts')
            self.assertEqual(row['issue_count'],24)
            self.assertEqual(len(row['issues']),16)
            self.assertEqual(row['omitted_issue_count'],8)

    def test_cli_refuses_input_above_2_mib(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'large.json';p.write_text(' '*2097153)
            r=subprocess.run([sys.executable,str(ROOT/'src/emissions.py'),'--activities',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2)
            self.assertIn('INPUT_SIZE_LIMIT',r.stderr)
            self.assertFalse(r.stdout)

    def test_nesting_limit_is_explicit_before_json_parser(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'deep.json';p.write_text('['*2000+'0'+']'*2000)
            r=subprocess.run([sys.executable,str(ROOT/'src/emissions.py'),'--activities',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2)
            self.assertIn('JSON_NESTING_LIMIT',r.stderr)
            self.assertNotIn('Traceback',r.stderr)

    def test_brackets_and_escaped_quotes_inside_strings_do_not_count_as_nesting(self):
        a=dict(ACTIVITY,source_note='[\"quoted\"]'*100)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'literal.json';p.write_text(json.dumps({'activities':[a]}))
            r=subprocess.run([sys.executable,str(ROOT/'src/emissions.py'),'--activities',str(p)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(json.loads(r.stdout)['total_emissions_tco2e'],'480')

if __name__=='__main__':unittest.main()

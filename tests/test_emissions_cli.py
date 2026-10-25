"""CLI contract: actual executable behavior, no mocked process or source greps."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class EmissionsCliTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run([sys.executable, str(ROOT/'src/emissions.py'), *args],
                              cwd=ROOT, text=True, capture_output=True)

    def test_cli_outputs_traceable_example(self):
        r = self.invoke('--activities', 'fixtures/demo_energy_2024.json')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.strip(), 'CLI must produce actual JSON, not silently exit')
        report = json.loads(r.stdout)
        self.assertEqual(report['total_emissions_tco2e'], '480')
        self.assertEqual(report['activity_statuses'], ['SYNTHETIC'])

    def test_cli_refuses_wrong_year_without_output_file(self):
        with tempfile.TemporaryDirectory() as d:
            source = json.loads((ROOT/'fixtures/demo_energy_2024.json').read_text())
            source['activities'][0]['period_start'] = '2026-01-01'
            source['activities'][0]['period_end'] = '2027-01-01'
            inp, out = Path(d)/'input.json', Path(d)/'output.json'
            inp.write_text(json.dumps(source))
            r = self.invoke('--activities', str(inp), '--output', str(out))
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(out.exists(), 'blocked estimate must not generate a valid-looking result')
            self.assertIn('FACTOR_YEAR_MISMATCH', r.stderr)

    def test_cli_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as d:
            inp = Path(d)/'input.json'
            inp.write_text('{"activities": [], "activities": []}')
            r = self.invoke('--activities', str(inp))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('duplicate JSON key', r.stderr)

    def test_cli_does_not_clobber_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'existing.json'; out.write_text('keep this evidence')
            r = self.invoke('--activities', 'fixtures/demo_energy_2024.json', '--output', str(out))
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(out.read_text(), 'keep this evidence')

    def test_cli_writes_readable_html_when_requested(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'report.html'
            r = self.invoke('--activities', 'fixtures/demo_energy_2024.json', '--format', 'html', '--output', str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            page = out.read_text()
            self.assertIn('<!doctype html>', page)
            self.assertIn('480', page)
            self.assertIn('SYNTHETIC', page)
            self.assertIn('not measured savings', page)

    def test_changed_curated_factor_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            local = Path(d); (local/'src').mkdir(); (local/'fixtures').mkdir()
            (local/'src/emissions.py').write_bytes((ROOT/'src/emissions.py').read_bytes())
            factor = json.loads((ROOT/'fixtures/za_grid_factor_2024.json').read_text())
            factor['value'] = '0.994'
            (local/'fixtures/za_grid_factor_2024.json').write_text(json.dumps(factor))
            r = subprocess.run([sys.executable, str(local/'src/emissions.py'), '--activities', str(ROOT/'fixtures/demo_energy_2024.json')], text=True, capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('CURATED_FACTOR_INTEGRITY', r.stderr)

    def test_preflight_cli_returns_all_rows_and_blocked_exit(self):
        with tempfile.TemporaryDirectory() as d:
            data = json.loads((ROOT/'fixtures/demo_energy_2024.json').read_text())
            a = data['activities'][0]
            data['activities'] += [dict(a, activity_id='wrong-year', period_start='2026-01-01', period_end='2027-01-01'), dict(a, activity_id='wrong-unit', unit='ZAR')]
            inp = Path(d)/'mixed.json'; inp.write_text(json.dumps(data))
            r = self.invoke('--activities', str(inp), '--preflight')
            self.assertEqual(r.returncode, 2)
            self.assertTrue(r.stdout.strip(), 'preflight diagnostic JSON must be returned')
            check = json.loads(r.stdout)
            self.assertEqual(check['status'], 'BLOCKED')
            self.assertEqual(check['input_count'], 3)
            self.assertEqual(check['blocked_count'], 2)
            self.assertNotIn('total_emissions_tco2e', check)

if __name__ == '__main__': unittest.main()

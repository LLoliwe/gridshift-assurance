"""Independent behavior regression tests for fail-closed emissions provenance.

These tests intentionally begin red where current validation is incomplete.
Expected numerical values are independent hand calculations, not implementation helpers.
"""
import unittest
from decimal import Decimal, localcontext
from test_emissions import ACTIVITY, FACTOR
from emissions import calculate


class AdversarialEmissionsTests(unittest.TestCase):
    def test_same_official_factor_identity_cannot_carry_different_value(self):
        # A changed factor under the same official provenance must not produce a result.
        for value in ['0', '0.994', '0.906', '9.60']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                calculate(ACTIVITY, dict(FACTOR, value=value))

    def test_factor_source_cannot_be_relabelled_as_official(self):
        for url in ['https://example.com/fake.pdf', 'https://www.gov.za.evil.example/f.pdf',
                    'https://www.gov.za@evil.example/f.pdf']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                calculate(ACTIVITY, dict(FACTOR, source_url=url))

    def test_metadata_fields_require_meaningful_strings(self):
        for field in ['factor_id', 'source_title', 'source_locator', 'gwp_basis']:
            for value in ['   ', [], {}, True, 123]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    calculate(ACTIVITY, dict(FACTOR, **{field: value}))

    def test_activity_identifiers_and_notes_require_meaningful_strings(self):
        for field in ['activity_id', 'site_id', 'meter_id', 'source_note']:
            for value in ['   ', [], {}, True, 123]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    calculate(dict(ACTIVITY, **{field: value}), FACTOR)

    def test_malformed_source_url_yields_validation_error_not_crash(self):
        for value in [[], {}, True, 123, 'https://[invalid']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                calculate(ACTIVITY, dict(FACTOR, source_url=value))

    def test_factor_identity_cannot_be_relabelled_to_another_year(self):
        a = dict(ACTIVITY, period_start='2026-01-01', period_end='2027-01-01')
        with self.assertRaises(ValueError):
            calculate(a, dict(FACTOR, data_year=2026))

    def test_decimal_fraction_has_no_binary_float_rounding(self):
        r = calculate(dict(ACTIVITY, quantity='0.1', unit='kWh'), FACTOR)
        self.assertEqual(r['emissions_tco2e'], '0.000096')

    def test_valid_leap_day_and_exclusive_year_end(self):
        r = calculate(dict(ACTIVITY, period_start='2024-02-29',
                           period_end='2024-03-01', quantity='1'), FACTOR)
        self.assertEqual(r['emissions_tco2e'], '0.96')

    def test_input_float_is_rejected_instead_of_silently_rounded(self):
        with self.assertRaises(ValueError):
            calculate(dict(ACTIVITY, quantity=0.1), FACTOR)

    def test_external_decimal_precision_does_not_change_result(self):
        with localcontext() as context:
            context.prec = 2
            r = calculate(dict(ACTIVITY, quantity='123456789.123456789', unit='kWh'), FACTOR)
        self.assertEqual(r['emissions_tco2e'], '118518.51755851851744')

    def test_unknown_factor_cannot_claim_curated_official_provenance(self):
        with self.assertRaises(ValueError):
            calculate(ACTIVITY, dict(FACTOR, factor_id='invented-official-factor'))

    def test_energy_and_emissions_stay_consistent_under_external_decimal_context(self):
        with localcontext() as context:
            context.prec = 2
            r = calculate(dict(ACTIVITY, quantity='123456789.123456789', unit='kWh'), FACTOR)
        self.assertEqual(r['energy_mwh'], '123456.789123456789')
        self.assertEqual(r['emissions_tco2e'], '118518.51755851851744')

    def test_decimal_object_is_either_explicitly_rejected_or_serializable(self):
        # The public API must not accept a numeric type then crash hashing it.
        try:
            r = calculate(dict(ACTIVITY, quantity=Decimal('1.5')), FACTOR)
        except ValueError:
            return
        self.assertEqual(r['emissions_tco2e'], '1.44')

    def test_nested_receipt_tamper_is_detected(self):
        from emissions import verify_receipt
        r = calculate(ACTIVITY, FACTOR)
        self.assertTrue(verify_receipt(r))
        r['activity']['quantity'] = '499'
        self.assertFalse(verify_receipt(r))

    def test_duplicate_meter_interval_rejected_even_with_new_activity_id(self):
        from emissions import calculate_batch
        with self.assertRaises(ValueError):
            calculate_batch([ACTIVITY, dict(ACTIVITY, activity_id='another')], FACTOR)

    def test_adjacent_intervals_are_valid_not_overlaps(self):
        from emissions import calculate_batch
        a = dict(ACTIVITY, period_end='2024-02-01', quantity='1')
        b = dict(ACTIVITY, activity_id='next', period_start='2024-02-01', quantity='2')
        r = calculate_batch([a, b], FACTOR)
        self.assertEqual(r['total_emissions_tco2e'], '2.88')

    def test_containing_interval_rejected_regardless_of_input_order(self):
        from emissions import calculate_batch
        short = dict(ACTIVITY, activity_id='short', period_start='2024-03-01', period_end='2024-04-01')
        for activities in [[ACTIVITY, short], [short, ACTIVITY]]:
            with self.subTest(activities=activities), self.assertRaises(ValueError):
                calculate_batch(activities, FACTOR)

    def test_external_decimal_exponent_limits_do_not_break_valid_input(self):
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            r = calculate(dict(ACTIVITY, quantity='10000', unit='MWh'), FACTOR)
        self.assertEqual(r['emissions_tco2e'], '9600')

    def test_unrecognized_activity_fields_cannot_smuggle_verified_or_savings_claims(self):
        for extra in [{'verified': True}, {'savings_tco2e': '99'}, {'source_status_override': 'VERIFIED'}]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                calculate(dict(ACTIVITY, **extra), FACTOR)

    def test_randomized_decimal_arithmetic_matches_fraction_oracle(self):
        from fractions import Fraction
        from random import Random
        random = Random(20241025)
        for _ in range(100):
            whole = random.randrange(0, 10**12)
            fraction = random.randrange(0, 10**6)
            qty = f'{whole}.{fraction:06d}'
            unit = random.choice(['kWh', 'MWh'])
            actual = calculate(dict(ACTIVITY, quantity=qty, unit=unit), FACTOR)
            expected = Fraction(qty) * Fraction(24, 25)
            if unit == 'kWh':
                expected /= 1000
            self.assertEqual(Fraction(actual['emissions_tco2e']), expected)

    def test_minimum_and_maximum_supported_magnitudes_are_exact(self):
        for qty, expected in [('1e-24', '0.00000000000000000000000096'),
                              ('1e24', '960000000000000000000000')]:
            with self.subTest(qty=qty):
                self.assertEqual(calculate(dict(ACTIVITY, quantity=qty), FACTOR)['emissions_tco2e'], expected)

    def test_batch_mixed_synthetic_unverified_status_is_preserved(self):
        from emissions import calculate_batch
        a = dict(ACTIVITY, quantity='1')
        b = dict(ACTIVITY, activity_id='u', meter_id='second', quantity='2', source_status='UNVERIFIED_USER_INPUT')
        result = calculate_batch([a, b], FACTOR)
        self.assertEqual(result['total_emissions_tco2e'], '2.88')
        self.assertEqual(result['activity_statuses'], ['SYNTHETIC', 'UNVERIFIED_USER_INPUT'])

    def test_duplicate_id_blocked_across_distinct_sites(self):
        from emissions import calculate_batch
        with self.assertRaises(ValueError):
            calculate_batch([ACTIVITY, dict(ACTIVITY, site_id='OTHER')], FACTOR)

    def test_identifier_whitespace_cannot_bypass_overlap_detection(self):
        from emissions import calculate_batch
        # Same identifier with accidental outer spaces must not count as a second meter.
        for field in ['activity_id', 'site_id', 'meter_id']:
            with self.subTest(field=field), self.assertRaises(ValueError):
                calculate_batch([ACTIVITY, dict(ACTIVITY, activity_id='second',
                                              **{field: ACTIVITY[field] + ' '})]
                                if field != 'activity_id' else
                                [ACTIVITY, dict(ACTIVITY, activity_id=ACTIVITY['activity_id'] + ' ')], FACTOR)

    def test_unpaired_unicode_surrogate_is_rejected_as_invalid_input(self):
        for field in ['activity_id', 'source_note']:
            with self.subTest(field=field), self.assertRaises(ValueError):
                calculate(dict(ACTIVITY, **{field: '\ud800'}), FACTOR)

    def test_cli_cannot_overwrite_its_provenance_input(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'activity.json'
            original = json.dumps({'activities': [ACTIVITY]})
            source.write_text(original)
            run = subprocess.run([sys.executable, str(root/'src/emissions.py'),
                                  '--activities', str(source), '--output', str(source)],
                                 text=True, capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(source.read_text(), original)

    def test_cli_invalid_input_does_not_destroy_previous_output(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/'bad.json', Path(directory)/'out.json'
            source.write_text(json.dumps({'activities': [dict(ACTIVITY, unit='ZAR')]}))
            output.write_text('previous-evidence')
            run = subprocess.run([sys.executable, str(root/'src/emissions.py'),
                                  '--activities', str(source), '--output', str(output)],
                                 text=True, capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(output.read_text(), 'previous-evidence')

    def test_cli_cannot_overwrite_input_through_file_alias(self):
        import json
        import os
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        for alias_kind in ['symlink', 'hardlink']:
            with self.subTest(alias_kind=alias_kind), tempfile.TemporaryDirectory() as directory:
                source, alias = Path(directory)/'activity.json', Path(directory)/'alias.json'
                original = json.dumps({'activities': [ACTIVITY]})
                source.write_text(original)
                if alias_kind == 'symlink':
                    alias.symlink_to(source)
                else:
                    os.link(source, alias)
                run = subprocess.run([sys.executable, str(root/'src/emissions.py'),
                                      '--activities', str(source), '--output', str(alias)],
                                     text=True, capture_output=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(source.read_text(), original)

    def test_render_rejects_forged_but_self_consistent_checksum(self):
        import hashlib
        import json
        from emissions import calculate_batch
        from emissions_report import render_report
        report = calculate_batch([ACTIVITY], FACTOR)
        receipt = report['receipts'][0]
        receipt['emissions_tco2e'] = '0'
        del receipt['receipt_sha256']
        receipt['receipt_sha256'] = hashlib.sha256(json.dumps(receipt, sort_keys=True,
            separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        with self.assertRaises(ValueError):
            render_report(report)

    def test_render_malformed_hash_valid_receipt_is_validation_error(self):
        import hashlib
        from emissions_report import render_report
        r = {'receipt_sha256': hashlib.sha256(b'{}').hexdigest()}
        with self.assertRaises(ValueError):
            render_report({'receipts': [r]})

    def test_preflight_ready_iff_batch_calculates_for_adversarial_corpus(self):
        from emissions import calculate_batch, preflight
        variants = [ACTIVITY, None, {}, [], 'not an object',
                    dict(ACTIVITY, quantity='NaN'), dict(ACTIVITY, quantity='-1'),
                    dict(ACTIVITY, unit='ZAR'), dict(ACTIVITY, country='KE'),
                    dict(ACTIVITY, period_start='2026-01-01', period_end='2027-01-01'),
                    dict(ACTIVITY, activity_id='other'),
                    dict(ACTIVITY, activity_id='other', meter_id='OTHER-METER'),
                    dict(ACTIVITY, activity_id='month', period_end='2024-02-01'),
                    dict(ACTIVITY, activity_id='later', period_start='2024-02-01')]
        from itertools import product
        for first, second in product(variants, repeat=2):
            items = [first, second]
            with self.subTest(items=items):
                try:
                    calculate_batch(items, FACTOR)
                    success = True
                except ValueError:
                    success = False
                report = preflight(items, FACTOR)
                self.assertEqual(report['status'] == 'READY', success)
                self.assertEqual(report['input_count'], 2)
                self.assertEqual([r['index'] for r in report['rows']], [0, 1])
                self.assertFalse(report['input_authenticity_verified'])

    def test_preflight_reordering_preserves_conflicts_and_record_identity(self):
        from emissions import preflight
        a = dict(ACTIVITY, activity_id='a', period_end='2024-03-01')
        b = dict(ACTIVITY, activity_id='b', period_start='2024-02-01', period_end='2024-04-01')
        c = dict(ACTIVITY, activity_id='c', meter_id='independent', source_status='UNVERIFIED_USER_INPUT')
        for items in [[a, b, c], [c, b, a], [b, a, c]]:
            r = preflight(items, FACTOR)
            self.assertEqual(r['blocked_count'], 2)
            by_id = {row['activity_id']: row for row in r['rows']}
            self.assertEqual(by_id['c']['status'], 'READY')
            self.assertEqual(by_id['c']['activity_status'], 'UNVERIFIED_USER_INPUT')
            for identity, related in [('a', 'b'), ('b', 'a')]:
                row = by_id[identity]
                self.assertEqual(row['status'], 'BLOCKED')
                issue = next(i for i in row['issues'] if i['code'] == 'OVERLAPPING_PERIOD')
                self.assertEqual(items[issue['related_index']]['activity_id'], related)

    def test_preflight_does_not_mutate_inputs_or_factor(self):
        import copy
        from emissions import preflight
        items, factor = copy.deepcopy([ACTIVITY, None]), copy.deepcopy(FACTOR)
        before_items, before_factor = copy.deepcopy(items), copy.deepcopy(factor)
        preflight(items, factor)
        self.assertEqual(items, before_items)
        self.assertEqual(factor, before_factor)

    def test_preflight_invalid_factor_never_marks_rows_ready(self):
        from emissions import preflight
        for factor in [None, {}, dict(FACTOR, value='0.994'), dict(FACTOR, data_year=2026)]:
            r = preflight([ACTIVITY, dict(ACTIVITY, activity_id='other', meter_id='other')], factor)
            self.assertEqual(r['status'], 'BLOCKED')
            self.assertEqual(r['blocked_count'], 2)
            self.assertTrue(all(row['issues'] for row in r['rows']))
            self.assertNotIn('total_emissions_tco2e', r)

    def test_numeric_token_exact_length_boundary(self):
        self.assertEqual(calculate(dict(ACTIVITY, quantity='0'*127+'1'), FACTOR)['emissions_tco2e'], '0.96')
        with self.assertRaises(ValueError):
            calculate(dict(ACTIVITY, quantity='0'*128+'1'), FACTOR)

    def test_batch_exact_1000_row_boundary_is_allowed(self):
        from emissions import calculate_batch, preflight
        rows = [dict(ACTIVITY, activity_id=f'a{i}', meter_id=f'm{i}', quantity='1') for i in range(1000)]
        self.assertEqual(calculate_batch(rows, FACTOR)['total_emissions_tco2e'], '960')
        result = preflight(rows, FACTOR)
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['input_count'], 1000)
        self.assertTrue(all(r['issue_count'] == r['omitted_issue_count'] == 0 for r in result['rows']))

    def test_dense_conflicts_count_every_issue_even_when_examples_truncated(self):
        from emissions import preflight
        result = preflight([dict(ACTIVITY) for _ in range(40)], FACTOR)
        self.assertEqual(result['blocked_count'], 40)
        for row in result['rows']:
            # Each of39other rows conflicts by both ID and period:78issues.
            self.assertEqual(row['issue_count'], 78)
            self.assertEqual(len(row['issues']), 16)
            self.assertEqual(row['omitted_issue_count'], 62)
            self.assertEqual(row['issue_count'], len(row['issues']) + row['omitted_issue_count'])
            self.assertEqual({x['code'] for x in row['issues']}, {'DUPLICATE_ID', 'OVERLAPPING_PERIOD'})

    def test_cli_exact_2_mib_valid_json_boundary_is_allowed(self):
        import json, subprocess, sys, tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'exact.json'
            raw = json.dumps({'activities': [ACTIVITY]}).encode()
            path.write_bytes(raw + b' ' * (2097152-len(raw)))
            run = subprocess.run([sys.executable,str(root/'src/emissions.py'),'--activities',str(path)],capture_output=True,text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)['total_emissions_tco2e'], '480')

    def test_cli_deeply_nested_json_fails_cleanly_without_traceback(self):
        import subprocess, sys, tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'deep.json'
            path.write_text('['*10000+'0'+']'*10000)
            code = 'import sys,runpy;sys.setrecursionlimit(1000);p=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(p,run_name="__main__")'
            run = subprocess.run([sys.executable,'-c',code,str(root/'src/emissions.py'),'--activities',str(path)],capture_output=True,text=True)
            self.assertEqual(run.returncode, 2)
            self.assertNotIn('Traceback', run.stderr)
            self.assertFalse(run.stdout)

    def test_cli_partial_write_failure_leaves_no_final_or_temporary_report(self):
        """Inject a disk-write error after real bytes reach a real temporary filesystem.

        Only the nondeterministic filesystem error is mocked; observable filesystem
        state and CLI exit status, not mock calls, are the assertions.
        """
        import contextlib, errno, io, json, tempfile, os
        from pathlib import Path
        from unittest.mock import patch
        from emissions import main
        real_fdopen = os.fdopen

        class PartialFailure:
            def __init__(self, handle): self.handle = handle
            def __enter__(self): return self
            def __exit__(self, *args): self.handle.close()
            def write(self, contents):
                self.handle.write(contents[:64])
                self.handle.flush()
                raise OSError(errno.ENOSPC, 'injected disk full after partial write')
            def __getattr__(self, name): return getattr(self.handle, name)

        def open_with_failure(fd, mode='r', *args, **kwargs):
            handle = real_fdopen(fd, mode, *args, **kwargs)
            return PartialFailure(handle) if any(m in mode for m in 'wax') else handle

        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/'input.json', Path(directory)/'result.json'
            source.write_text(json.dumps({'activities': [ACTIVITY]}))
            before = {p.name for p in Path(directory).iterdir()}
            with patch.object(os, 'fdopen', open_with_failure), contextlib.redirect_stderr(io.StringIO()):
                status = main(['--activities', str(source), '--output', str(output)])
            self.assertEqual(status, 2)
            self.assertFalse(output.exists(), 'failed write exposed a partial report at its final path')
            self.assertEqual({p.name for p in Path(directory).iterdir()}, before,
                             'failed write must not leave temporary report residue')

    def test_cli_sync_or_publish_failure_cleans_unpublished_file(self):
        import contextlib, errno, io, json, os, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from emissions import main
        for stage in ['fsync', 'link']:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                source, output = Path(directory)/'input.json', Path(directory)/'result.json'
                source.write_text(json.dumps({'activities': [ACTIVITY]}))
                before = {p.name for p in Path(directory).iterdir()}
                with patch.object(os, stage, side_effect=OSError(errno.EIO, 'injected filesystem failure')), contextlib.redirect_stderr(io.StringIO()):
                    status = main(['--activities', str(source), '--output', str(output)])
                self.assertEqual(status, 2)
                self.assertFalse(output.exists())
                self.assertEqual({p.name for p in Path(directory).iterdir()}, before)

    def test_cli_existing_destination_survives_staged_publication(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from emissions import main
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/'input.json', Path(directory)/'result.json'
            source.write_text(json.dumps({'activities': [ACTIVITY]}))
            output.write_text('prior-evidence-must-survive')
            before = {p.name for p in Path(directory).iterdir()}
            with contextlib.redirect_stderr(io.StringIO()):
                status = main(['--activities', str(source), '--output', str(output)])
            self.assertEqual(status, 2)
            self.assertEqual(output.read_text(), 'prior-evidence-must-survive')
            self.assertEqual({p.name for p in Path(directory).iterdir()}, before)

    def test_published_factor_retained_despite_unresolved_reconciliation(self):
        r = calculate(dict(ACTIVITY, quantity='1', unit='MWh'), FACTOR)
        self.assertEqual(r['factor']['value'], '0.960')
        self.assertEqual(r['emissions_tco2e'], '0.96')
        self.assertIn('PUBLISHED_FACTOR_INPUT_RECONCILIATION_UNRESOLVED', r['limitations'])
        for alternative in ['0.9555', '0.8576']:
            with self.subTest(alternative=alternative), self.assertRaises(ValueError):
                calculate(ACTIVITY, dict(FACTOR, value=alternative))

    def test_renderer_rejects_rehashed_removal_of_material_limitations(self):
        import hashlib, json
        from emissions import calculate_batch, verify_receipt
        from emissions_report import render_report
        required = ['PUBLISHED_FACTOR_INPUT_RECONCILIATION_UNRESOLVED',
                    'MARKET_BASED_NOT_COMPUTED', 'ORGANIZATIONAL_BOUNDARY_NOT_REVIEWED',
                    'NOT_FULL_SCOPE2_COMPLIANCE']
        for removed in required:
            with self.subTest(removed=removed):
                report = calculate_batch([ACTIVITY], FACTOR)
                receipt = report['receipts'][0]
                self.assertIn(removed, receipt['limitations'])
                receipt['limitations'].remove(removed)
                del receipt['receipt_sha256']
                receipt['receipt_sha256'] = hashlib.sha256(json.dumps(receipt,sort_keys=True,
                    separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
                self.assertTrue(verify_receipt(receipt)) # Integrity alone is insufficient.
                with self.assertRaises(ValueError):
                    render_report(report)

    def test_rendered_warning_and_user_note_preserve_narrow_scope(self):
        from emissions import calculate_batch
        from emissions_report import render_report
        from html.parser import HTMLParser
        class VisibleText(HTMLParser):
            def __init__(self): super().__init__(); self.parts=[]
            def handle_data(self,data): self.parts.append(data)
        p = VisibleText()
        p.feed(render_report(calculate_batch([dict(ACTIVITY, source_note='My unsupported assertion')], FACTOR)))
        text = ' '.join(p.parts)
        for caveat in ['unresolved source reconciliation', 'not been independently re-derived',
                       'Market-based emissions are not computed', 'organizational boundaries are not reviewed',
                       'not a full Scope 2 compliance assessment', 'Input note (unverified assertion):']:
            self.assertIn(caveat, text)

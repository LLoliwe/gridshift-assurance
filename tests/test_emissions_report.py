import sys
from pathlib import Path
import unittest
from test_emissions import ACTIVITY, FACTOR
from emissions import calculate_batch
try:
    from emissions_report import render_report
except ImportError:
    render_report = None

class ReportTests(unittest.TestCase):
    def test_report_shows_actual_results_and_limitations(self):
        self.assertTrue(callable(render_report), 'human-readable report not implemented')
        page = render_report(calculate_batch([ACTIVITY], FACTOR))
        from html.parser import HTMLParser
        class TextParser(HTMLParser):
            def __init__(self): super().__init__(); self.text = []
            def handle_data(self, data): self.text.append(data)
        parser = TextParser(); parser.feed(page); text = ' '.join(parser.text)
        for required in ['480', 'SYNTHETIC', '2024', '0.960', 'not measured savings', 'not quantified', 'Scope 2', '500']:
            self.assertIn(required, text)

    def test_activity_markup_is_escaped(self):
        self.assertTrue(callable(render_report), 'human-readable report not implemented')
        a = dict(ACTIVITY, source_note='<script>alert(1)</script>')
        page = render_report(calculate_batch([a], FACTOR))
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)

    def test_tampered_result_is_not_presented_as_valid_report(self):
        self.assertTrue(callable(render_report), 'human-readable report not implemented')
        report = calculate_batch([ACTIVITY], FACTOR)
        report['receipts'][0]['emissions_tco2e'] = '0'
        with self.assertRaises(ValueError): render_report(report)

    def test_free_text_assurance_claim_is_explicitly_labelled_unverified(self):
        a=dict(ACTIVITY,source_note='Verified carbon neutral according to the sender')
        page=render_report(calculate_batch([a],FACTOR))
        self.assertIn('Input note (unverified assertion):',page)
        self.assertIn('ACTIVITY_NOT_VERIFIED',str(calculate_batch([a],FACTOR)))

if __name__ == '__main__': unittest.main()

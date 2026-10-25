"""Lane B (KF-3): the protected engine reports a schema failure as decision WITHHOLD with finding
INVALID_SCHEMA. The adapter and UI must present it as a schema rejection, never as WITHHOLD.
The engine output itself is passed through unchanged (protected file). Synthetic development data."""
from pathlib import Path
import json, re, sys, unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'web/engine/src'), str(ROOT / 'web/workspace')]
from case_adapter import open_case, execute, is_schema_rejection

FLAGSHIP = (ROOT / 'web/reconcile/flagship.json').read_text(encoding='utf-8')


def review(raw):
    opened = open_case(raw.encode('utf-8'))
    return execute({'operation': 'review', 'case': opened['case']})


class SchemaRejectionPresentationTests(unittest.TestCase):
    def test_c30_style_proto_key_is_schema_rejection_not_withhold(self):
        raw = FLAGSHIP.replace('"record_id"', '"__proto__": "x", "record_id"', 1)
        self.assertNotEqual(raw, FLAGSHIP)
        out = review(raw)
        # Protected engine label, unchanged and documented in KNOWN_FAILURES (KF-3).
        self.assertEqual(out['result']['decision'], 'WITHHOLD')
        self.assertEqual([f['code'] for f in out['result']['findings']], ['INVALID_SCHEMA'])
        self.assertTrue(is_schema_rejection(out['result']))
        self.assertEqual(out['presentation']['outcome'], 'SCHEMA_REJECTION')
        self.assertIs(out['presentation']['calculation_performed'], False)
        current = out['summary'].split('CURRENT REVIEW', 1)[1].split('FINDINGS', 1)[0]
        self.assertIn('SCHEMA REJECTION', current)
        self.assertNotIn('MORE EVIDENCE REQUIRED', out['summary'])
        self.assertNotRegex(current, r'WITHHOLD|Withheld')

    def test_policy_withhold_stays_withhold(self):
        raw = (ROOT / 'web/reconcile/missing-edge.json').read_text(encoding='utf-8')
        out = review(raw)
        self.assertEqual(out['result']['decision'], 'WITHHOLD')
        self.assertFalse(is_schema_rejection(out['result']))
        self.assertEqual(out['presentation']['outcome'], 'WITHHOLD')
        self.assertIn('MORE EVIDENCE REQUIRED', out['summary'])

    def test_ui_has_distinct_schema_rejection_path(self):
        js = (ROOT / 'web/workspace/workspace.js').read_text(encoding='utf-8')
        self.assertIn("presentation?.outcome==='SCHEMA_REJECTION'||isSchemaRejection(r)", js)
        self.assertIn("'Schema rejection: not calculated'", js)


if __name__ == '__main__':
    unittest.main()

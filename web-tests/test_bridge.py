"""Disclosed bridge tests run fixed Python code natively, not in WASM."""
import json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from reconciliation import reconcile_package,accept_proposal,export_package
from test_reconciliation_development import flagship
BRIDGE=re.search(r'export const REVIEW_PYTHON=`\n(.*?)`;',(ROOT/'web/reconciliation-worker.js').read_text(),re.S).group(1)
def invoke(request):
 scope=dict(json=json,reconcile_package=reconcile_package,accept_proposal=accept_proposal,export_package=export_package,_reconciliation_request_json=json.dumps(request))
 code=BRIDGE.rsplit('\n',1)[0] if BRIDGE.endswith('\n') else BRIDGE
 lines=code.splitlines();exec('\n'.join(lines[:-1]),scope);return json.loads(eval(lines[-1],scope))
class Bridge(unittest.TestCase):
 def test_review_accept_export_preserves_original(self):
  p=flagship();r=invoke(dict(operation='review',package=p));self.assertEqual(r['result']['decision'],'CORRECT')
  a=invoke(dict(operation='accept',package=p,proposal_sha256=r['result']['proposal_sha256'],reviewer_id='synthetic-reviewer'))
  self.assertEqual(a['result']['decision'],'ACCEPT');self.assertEqual(a['package']['records'],p['records']);self.assertEqual(a['package']['report'],p['report']);self.assertEqual(json.loads(a['export_json'])['result'],a['result'])
 def test_bad_proposal_not_accepted(self):
  with self.assertRaises(ValueError):invoke(dict(operation='accept',package=flagship(),proposal_sha256='0'*64,reviewer_id='synthetic-reviewer'))

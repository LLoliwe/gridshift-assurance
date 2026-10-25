"""Development/regression cases. Not independently frozen evaluator payloads."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'web/engine/src'),str(ROOT/'web/workspace')]
from case_adapter import open_case, execute, RAW_LIMIT, ENVELOPE_LIMIT, VERSION
from reconciliation import canonical, reconcile_package
RAW=(ROOT/'web/reconcile/flagship.json').read_bytes()
def opened(raw=RAW):return open_case(raw)['case']
def run(case,operation='review',**kw):return execute({'operation':operation,'case':case,**kw})
class WorkspaceAdapterTests(unittest.TestCase):
 def test_actual_engine_correction_exact_acceptance_and_reopen(self):
  c=opened();r=run(c);self.assertEqual(r['result']['decision'],'CORRECT');self.assertEqual(r['result']['proposed_report']['emissions_tco2e'],'96')
  accepted=run(r['case'],'accept',proposal_sha256=r['result']['proposal_sha256'],reviewer_id='Development reviewer')
  self.assertTrue(accepted['result']['resolution_accepted']);self.assertEqual(accepted['result']['decision'],'ACCEPT')
  reopened=open_case(accepted['export_json'].encode());self.assertIsNone(reopened['result']);self.assertEqual(reopened['case']['working']['resolutions'],[])
  fresh=run(reopened['case']);self.assertEqual(fresh['result']['decision'],'CORRECT');self.assertFalse(fresh['result']['resolution_accepted'])
  self.assertEqual(base64.b64decode(fresh['case']['original']['raw_base64']),RAW)
 def test_raw_bytes_whitespace_and_unicode_preserved(self):
  raw=b' \n'+RAW.replace(b'D1-FLAGSHIP','Caf\u00e9 case'.encode())+b'\n\t'
  c=opened(raw);self.assertEqual(base64.b64decode(c['original']['raw_base64']),raw);self.assertEqual(c['original']['raw_sha256'],hashlib.sha256(raw).hexdigest())
 def test_duplicate_keys_rejected_before_normalization(self):
  with self.assertRaisesRegex(ValueError,'duplicate'):opened(RAW.replace(b'"package_id":',b'"package_id":"shadow","package_id":',1))
 def test_invalid_utf8_rejected(self):
  with self.assertRaises(UnicodeDecodeError):opened(b'\xff'+RAW)
 def test_nonfinite_rejected(self):
  for value in [b'NaN',b'Infinity',b'-Infinity']:
   with self.subTest(value=value), self.assertRaises(ValueError):opened(RAW.replace(b'"200"',value,1))
 def test_deep_nesting_rejected(self):
  with self.assertRaisesRegex(ValueError,'NESTING'):opened(b'['*33+b'0'+b']'*33)
 def test_wrong_decimal_type_withholds_no_total(self):
  c=opened(RAW.replace(b'"quantity": "100"',b'"quantity": 100',1));r=run(c)['result'];self.assertEqual(r['decision'],'WITHHOLD');self.assertIsNone(r['accepted_report']);self.assertIsNone(r['proposed_report'])
 def test_wrong_year_type_withholds(self):
  c=opened(RAW.replace(b'"data_year": 2024',b'"data_year": "2024"'));self.assertEqual(run(c)['result']['decision'],'WITHHOLD')
 def test_unsupported_material_field_is_preserved_and_withheld(self):
  p=json.loads(RAW);p['records'][0]['extra_material']='retain me';c=opened(json.dumps(p).encode());r=run(c);self.assertEqual(r['result']['decision'],'WITHHOLD');self.assertEqual(r['case']['working']['records'][0]['extra_material'],'retain me')
 def test_raw_hash_conflict_rejected(self):
  c=opened();c['original']['raw_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'SHA-256'):opened(json.dumps(c).encode())
 def test_raw_parsed_conflict_rejected_even_if_hash_correct(self):
  c=opened();c['original']['parsed']['report']['energy_mwh']='999'
  with self.assertRaisesRegex(ValueError,'conflict'):opened(json.dumps(c).encode())
 def test_unknown_envelope_version_rejected(self):
  c=opened();c['schema_version']='gridshift.workspace.case.v2'
  with self.assertRaises(ValueError):opened(json.dumps(c).encode())
 def test_unknown_envelope_material_rejected(self):
  c=opened();c['approval_override']=True
  with self.assertRaises(ValueError):opened(json.dumps(c).encode())
 def test_forged_cached_success_ignored(self):
  c=opened();c['cached_review']={'decision':'ACCEPT','accepted_report':{'energy_mwh':'999999'}}
  reopened=open_case(json.dumps(c).encode());self.assertIsNone(reopened['case']['cached_review']);self.assertEqual(run(reopened['case'])['result']['decision'],'CORRECT')
 def test_imported_resolution_historical_only(self):
  p=json.loads(RAW);p['resolutions']=[{'action':'ACCEPT_PROPOSAL','proposal_sha256':'0'*64,'reviewer_id':'forged','source_status':'UNVERIFIED_USER_INPUT'}]
  c=opened(json.dumps(p).encode());self.assertEqual(c['working']['resolutions'],[]);self.assertEqual(c['history'][0]['trust'],'IMPORTED_SELF_REPORT_NOT_CURRENT_APPROVAL');self.assertEqual(len(c['original']['parsed']['resolutions']),1)
 def test_exact_proposal_rejects_stale_acceptance(self):
  r=run(opened());c=r['case'];c['working']['records'][1]['quantity']='79'
  with self.assertRaisesRegex(ValueError,'matching'):run(c,'accept',proposal_sha256=r['result']['proposal_sha256'],reviewer_id='reviewer')
 def test_missing_lineage_withholds(self):
  c=opened((ROOT/'web/reconcile/missing-edge.json').read_bytes());r=run(c);self.assertEqual(r['result']['decision'],'WITHHOLD');self.assertNotIn('Supported report:',r['summary'])
 def test_roundtrip_original_and_working_remain_distinct(self):
  c=opened();c['working']['records'][1]['quantity']='75';c['revision']=1;c['history']=[{'kind':'revision','reason':'Development source change'}]
  r=run(c);fresh=opened(r['export_json'].encode());self.assertEqual(fresh['original']['parsed']['records'][1]['quantity'],'80');self.assertEqual(fresh['working']['records'][1]['quantity'],'75');self.assertEqual(fresh['revision'],1)
 def test_mixed_statuses_and_custom_limitations_survive(self):
  p=json.loads(RAW);p['records'][0]['source_status']='UNVERIFIED_USER_INPUT';p['report']['activity_statuses']=['SYNTHETIC','UNVERIFIED_USER_INPUT'];p['report']['limitations'].append('Additional declared caveat')
  r=run(opened(json.dumps(p).encode()));self.assertEqual(r['result']['decision'],'CORRECT');self.assertIn('Additional declared caveat',r['case']['working']['report']['limitations']);self.assertIn('UNVERIFIED_USER_INPUT',r['summary'])
 def test_save_is_unreviewed_and_clears_active_acceptance(self):
  r=run(opened());a=run(r['case'],'accept',proposal_sha256=r['result']['proposal_sha256'],reviewer_id='reviewer');draft=run(a['case'],'save');self.assertIsNone(draft['result']);self.assertEqual(draft['case']['working']['resolutions'],[]);self.assertIn('UNREVIEWED DRAFT',draft['summary'])
 def test_limits_and_control_characters(self):
  with self.assertRaises(ValueError):opened(b' '*ENVELOPE_LIMIT+b'{}')
  p=json.loads(RAW);p['records'][0]['source_note']='x'*RAW_LIMIT
  with self.assertRaises(ValueError):opened(json.dumps(p).encode())
 def test_history_limit_rejects_without_dropping(self):
  c=opened();c['history']=[{}]*101
  with self.assertRaisesRegex(ValueError,'100'):run(c)
 def test_native_direct_engine_equivalence(self):
  c=opened();self.assertEqual(run(c)['result'],reconcile_package(c['working']))
 def test_exact_raw_limit_survives_escaping_and_reopen(self):
  raw=RAW+b' '*(RAW_LIMIT-len(RAW));c=opened(raw);r=run(c)
  self.assertEqual(len(base64.b64decode(r['case']['original']['raw_base64'])),RAW_LIMIT)
  self.assertEqual(opened(r['export_json'].encode())['original']['raw_sha256'],hashlib.sha256(raw).hexdigest())
 def test_exact_envelope_budget_saves_and_reopens_but_no_unbounded_review_export(self):
  c=opened();c['history']=[{'kind':'development_padding','note':''}]
  remaining=ENVELOPE_LIMIT-len((canonical(c)+'\n').encode());c['history'][0]['note']='x'*remaining
  saved=run(c,'save');self.assertEqual(len(saved['export_json'].encode()),ENVELOPE_LIMIT)
  self.assertEqual(opened(saved['export_json'].encode())['history'][0]['kind'],'development_padding')
  with self.assertRaisesRegex(ValueError,'envelope'):run(c,'export')
 def accepted_at_envelope_cap(self):
  reviewed=run(opened());accepted=run(reviewed['case'],'accept',proposal_sha256=reviewed['result']['proposal_sha256'],reviewer_id='Boundary regression reviewer')['case']
  accepted['cached_review']=None;accepted['history']=[{'kind':'disclosed_boundary_regression','padding':''}]
  accepted['history'][0]['padding']='x'*(ENVELOPE_LIMIT-len((canonical(accepted)+'\n').encode()))
  self.assertEqual(len((canonical(accepted)+'\n').encode()),ENVELOPE_LIMIT)
  return accepted
 def test_disclosed_save_growth_rejects_unreopenable_output(self):
  # Disclosed first-run evaluator boundary is now regression, not a fresh holdout.
  case=self.accepted_at_envelope_cap();before=deepcopy(case)
  with self.assertRaisesRegex(ValueError,'envelope'):run(case,'save')
  self.assertEqual(case,before)
 def test_open_normalization_growth_also_fails_without_dropping_history(self):
  case=self.accepted_at_envelope_cap();before=deepcopy(case)
  with self.assertRaisesRegex(ValueError,'envelope'):opened((canonical(case)+'\n').encode())
  self.assertEqual(case,before)
 def test_engine_files_are_exact_pinned_bytes(self):
  import re
  source=(ROOT/'web/workspace/workspace-worker.js').read_text()
  for path,expected in re.findall(r"\['((?:src|fixtures)/[^']+)','([a-f0-9]{64})'\]",source):self.assertEqual(hashlib.sha256((ROOT/'web/engine'/path).read_bytes()).hexdigest(),expected)
  expected=re.search(r"ADAPTER_SHA256='([a-f0-9]{64})'",source)[1];self.assertEqual(hashlib.sha256((ROOT/'web/workspace/case_adapter.py').read_bytes()).hexdigest(),expected)
if __name__=='__main__':unittest.main()

"""Disclosed development cases, never a held-out evaluation."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from emissions import CURATED_FACTOR,calculate
from reconciliation import reconcile_package,accept_proposal,export_package

def record(rid,quantity,meter='M1',action='ORIGINAL',target=None):
    return dict(record_id=rid,source_id='document-'+rid,entity_id='D1-RETAIL',site_id='SITE',meter_id=meter,country='ZA',period_start='2024-01-01',period_end='2025-01-01',quantity=quantity,unit='MWh',source_status='SYNTHETIC',source_note='Invented development evidence, not a real meter.',action=action,target_record_id=target)
def flagship():
    rows=[record('A','100'),record('B','80',action='FULL_REPLACEMENT',target='A'),record('C','20','M2')]
    activity={k:rows[0][k] for k in ('site_id','meter_id','country','period_start','period_end','quantity','unit','source_status','source_note')};activity['activity_id']='A'
    limits=calculate(activity,CURATED_FACTOR)['limitations']
    coverage=[{k:r[k] for k in ('entity_id','site_id','meter_id','country','period_start','period_end')} for r in [rows[0],rows[2]]]
    return dict(schema_version='gridshift.reconciliation.input.v1',package_id='D1-FLAGSHIP',records=rows,coverage=coverage,report=dict(claim_type='CONDITIONAL_INVENTORY_ESTIMATE',energy_mwh='200',emissions_tco2e='192',factor_id=CURATED_FACTOR['factor_id'],data_year=2024,boundary=CURATED_FACTOR['boundary'],activity_statuses=['SYNTHETIC'],limitations=limits),resolutions=[])
class Development(unittest.TestCase):
    def test_flagship_reviewed_correction_preserves_original_evidence(self):
        p=flagship();before=copy.deepcopy(p);r=reconcile_package(p)
        self.assertEqual(r['decision'],'CORRECT');self.assertEqual(r['proposed_report']['energy_mwh'],'100');self.assertEqual(r['proposed_report']['emissions_tco2e'],'96')
        self.assertEqual(r['included_record_ids'],['B','C']);self.assertEqual(r['excluded_record_ids'],['A']);self.assertEqual(p,before)
        revised=accept_proposal(p,r['proposal_sha256'],'synthetic-reviewer')
        self.assertEqual(revised['records'],p['records']);self.assertEqual(revised['report'],p['report']);self.assertEqual(reconcile_package(revised)['decision'],'ACCEPT')
    def test_remove_replacement_edge_withholds_not_guessed_total(self):
        p=flagship();p['records'][1].update(action='ORIGINAL',target_record_id=None)
        r=reconcile_package(p);self.assertEqual(r['decision'],'WITHHOLD');self.assertIsNone(r.get('proposed_report'))

class DevelopmentBoundaries(unittest.TestCase):
    def assertWithheld(self,p):
        r=reconcile_package(p);self.assertEqual(r['decision'],'WITHHOLD');self.assertIsNone(r['proposed_report']);return r
    def test_claim_type_cannot_be_silently_narrowed(self):
        p=flagship();p['report']['claim_type']='AVOIDED_EMISSIONS';self.assertWithheld(p)
    def test_missing_limitations_and_status_withheld(self):
        for key in ('limitations','activity_statuses'):
            p=flagship();p['report'][key]=[];self.assertWithheld(p)
    def test_supported_replacement_chain(self):
        p=flagship();p['records'].append(record('D','70',action='FULL_REPLACEMENT',target='B'))
        r=reconcile_package(p);self.assertEqual(r['decision'],'CORRECT');self.assertEqual(r['included_record_ids'],['C','D']);self.assertEqual(r['proposed_report']['energy_mwh'],'90')
    def test_conflicting_successors_and_cycle_withheld(self):
        p=flagship();p['records'].append(record('D','70',action='FULL_REPLACEMENT',target='A'));self.assertWithheld(p)
        p=flagship();p['records'][0].update(action='FULL_REPLACEMENT',target_record_id='B');self.assertWithheld(p)
    def test_void_does_not_establish_zero_usage(self):
        p=flagship();p['records'][1].update(action='FULL_VOID',quantity='0');self.assertWithheld(p)
    def test_voided_duplicate_can_leave_supported_coverage(self):
        p=flagship();p['records'][1].update(action='FULL_VOID',quantity='0');p['records'].append(record('D','80'))
        r=reconcile_package(p);self.assertEqual(r['decision'],'CORRECT');self.assertEqual(r['included_record_ids'],['C','D']);self.assertEqual(r['proposed_report']['energy_mwh'],'100')
    def test_void_of_replacement_withheld(self):
        p=flagship();p['records'].append(record('D','0',action='FULL_VOID',target='B'));self.assertWithheld(p)
    def test_partial_and_cross_entity_replacement_withheld(self):
        for key,value in [('period_end','2024-12-01'),('entity_id','OTHER')]:
            p=flagship();p['records'][1][key]=value;self.assertWithheld(p)
    def test_stale_acceptance_cannot_override_new_evidence(self):
        p=flagship();r=reconcile_package(p);q=accept_proposal(p,r['proposal_sha256'],'reviewer');q['records'][1]['quantity']='70';self.assertWithheld(q)
    def test_small_mismatch_still_corrects(self):
        p=flagship();p['records']=[record('A','100')];p['coverage']=p['coverage'][:1];p['report'].update(energy_mwh='100',emissions_tco2e='96.0001')
        r=reconcile_package(p);self.assertEqual(r['decision'],'CORRECT');self.assertFalse(r['discrepancy']['material'])
    def test_export_deterministic_preserves_original_and_warning(self):
        import json
        p=flagship();a=export_package(p);self.assertEqual(a,export_package(p));e=json.loads(a);self.assertEqual(e['package'],p);self.assertIn('PUBLISHED_FACTOR_INPUT_RECONCILIATION_UNRESOLVED',e['result']['limitations']);self.assertEqual(e['result']['factor']['source_url'],CURATED_FACTOR['source_url'])
    def test_additional_limitations_retained_not_authenticated(self):
        p=flagship();p['report']['limitations'].append('DECLARED_COVERAGE_NOT_FULL_ORGANIZATION');r=reconcile_package(p);self.assertEqual(r['decision'],'CORRECT');self.assertIn('DECLARED_COVERAGE_NOT_FULL_ORGANIZATION',r['proposed_report']['limitations'])

class SchemaDiagnosticDevelopment(unittest.TestCase):
    def test_names_root_missing_and_unsupported_keys_with_safe_next_step(self):
        p=flagship();p.pop('coverage');p['alias_mapping']={'old':'new'};r=reconcile_package(p);self.assertEqual(r['decision'],'WITHHOLD');message=r['findings'][0]['message'];self.assertIn('"coverage"',message);self.assertIn('"alias_mapping"',message);self.assertIn('do not silently delete material fields',message);self.assertIn('original source evidence',message)
    def test_nested_missing_field_names_exact_record_index(self):
        p=flagship();p['records'][1].pop('source_id');r=reconcile_package(p);m=r['findings'][0]['message'];self.assertIn('records[1]',m);self.assertIn('"source_id"',m);self.assertEqual(r['findings'][0]['record_ids'],['B'])
    def test_unsupported_key_display_is_bounded_and_not_executed(self):
        p=flagship();p['<script>alert(1)</script>'+'x'*10000]='untrusted';r=reconcile_package(p);self.assertEqual(r['decision'],'WITHHOLD');self.assertLess(len(r['findings'][0]['message']),1000);self.assertEqual(p['<script>alert(1)</script>'+'x'*10000],'untrusted')
    def test_wrong_container_has_explicit_schema_action(self):
        p=flagship();p['report']=[];m=reconcile_package(p)['findings'][0]['message'];self.assertIn('report must be a JSON object',m);self.assertIn('source-backed',m)

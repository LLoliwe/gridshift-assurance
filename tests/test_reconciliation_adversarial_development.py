"""Disclosed engineering regressions only; no held-out fixtures accessed or used."""
import copy, hashlib, json, sys, unittest
from decimal import localcontext
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from reconciliation import reconcile_package,accept_proposal,export_package
from test_reconciliation_development import flagship,record

def clean(quantity='100'):
    p=flagship();p['records']=[record('A',quantity)];p['coverage']=p['coverage'][:1]
    p['report'].update(energy_mwh='100',emissions_tco2e='96');return p

class ReconciliationAdversarialDevelopment(unittest.TestCase):
    def assert_withheld(self,p):
        r=reconcile_package(p);self.assertEqual(r['decision'],'WITHHOLD',r)
        self.assertIsNone(r['proposed_report']);self.assertIsNone(r['accepted_report']);self.assertIsNone(r['proposal_sha256']);return r
    def test_claim_factor_status_and_limitation_laundering(self):
        for key,value in [('claim_type','AVOIDED_EMISSIONS'),('factor_id','other'),('data_year',2026),('data_year',True),('boundary','SCOPE3'),('activity_statuses',['VERIFIED']),('limitations',[])]:
            p=clean();p['report'][key]=value
            with self.subTest(key=key,value=value):self.assert_withheld(p)
        p=flagship();p['records'][0]['source_status']='UNVERIFIED_USER_INPUT';self.assert_withheld(p)
        p['report']['activity_statuses']=['SYNTHETIC','UNVERIFIED_USER_INPUT'];self.assertEqual(reconcile_package(p)['decision'],'CORRECT')
    def test_cycles_branches_missing_edges_and_partial_corrections(self):
        cases=[]
        p=flagship();p['records'][0].update(action='FULL_REPLACEMENT',target_record_id='B');cases.append(p)
        p=flagship();p['records'].append(record('D','70',action='FULL_REPLACEMENT',target='A'));cases.append(p)
        p=flagship();p['records'][1]['target_record_id']='missing';cases.append(p)
        p=flagship();p['records'][1]['period_start']='2024-02-01';cases.append(p)
        for p in cases:self.assert_withheld(p)
    def test_void_cannot_create_coverage_or_revive(self):
        p=clean();p['records'].append(record('V','0',action='FULL_VOID',target='A'));self.assert_withheld(p)
        p['records'].append(record('R','100',action='FULL_REPLACEMENT',target='V'));self.assert_withheld(p)
        p=flagship();p['records'].append(record('V','0',action='FULL_VOID',target='B'));self.assert_withheld(p)
        p=clean();p['records'].append(record('V','1',action='FULL_VOID',target='A'));self.assert_withheld(p)
    def test_coverage_gaps_overlaps_and_unscoped_records(self):
        for field,value in [('period_start','2024-01-02'),('period_end','2024-12-31'),('meter_id','different')]:
            p=clean();p['coverage'][0][field]=value;self.assert_withheld(p)
        p=clean();p['coverage'].append(copy.deepcopy(p['coverage'][0]));self.assert_withheld(p)
        p=clean();p['records'].append(record('EXTRA','100','M2'));self.assert_withheld(p)
        p=clean();p['records'][0].update(quantity='40',period_end='2024-07-01');p['records'].append(record('B','60'));p['records'][1]['period_start']='2024-07-01';self.assertEqual(reconcile_package(p)['decision'],'ACCEPT')
    def test_stale_acceptance_and_original_evidence_immutability(self):
        p=flagship();before=copy.deepcopy(p);r=reconcile_package(p);accepted=accept_proposal(p,r['proposal_sha256'],'reviewer')
        self.assertEqual(p,before);self.assertEqual(accepted['records'],before['records']);self.assertEqual(accepted['report'],before['report']);self.assertEqual(reconcile_package(accepted)['decision'],'ACCEPT')
        for section,key,value in [('report','energy_mwh','201'),('records','source_note','changed source assertion'),('coverage','period_start','2024-02-01')]:
            altered=copy.deepcopy(accepted)
            if section=='report':altered[section][key]=value
            else:altered[section][0][key]=value
            self.assert_withheld(altered)
        with self.assertRaises(ValueError):accept_proposal(p,'0'*64,'reviewer')
    def test_any_delta_requires_correction_not_only_material(self):
        for energy,emissions,material in [('100','96.0001',False),('100.01','96',False),('100','97',True)]:
            p=clean();p['report'].update(energy_mwh=energy,emissions_tco2e=emissions);r=reconcile_package(p)
            self.assertEqual(r['decision'],'CORRECT');self.assertEqual(r['discrepancy']['material'],material)
        p=clean('0');p['report'].update(energy_mwh='0',emissions_tco2e='0');r=reconcile_package(p);self.assertEqual(r['decision'],'ACCEPT');self.assertIsNone(r['discrepancy']['relative_emissions_fraction']);self.assertEqual(r['discrepancy']['materiality_threshold_tco2e'],'1')
    def test_external_decimal_context_does_not_change_decisions(self):
        p=flagship();normal=reconcile_package(p)
        with localcontext() as c:
            c.prec=2;c.Emax=2;c.Emin=-2
            altered=reconcile_package(p)
        self.assertEqual(altered,normal)
    def test_order_changes_no_totals_but_exact_proposal_identity_changes(self):
        p=flagship();a=reconcile_package(p);p['records'].reverse();p['coverage'].reverse();b=reconcile_package(p)
        self.assertEqual(a['proposed_report'],b['proposed_report']);self.assertEqual(a['included_record_ids'],b['included_record_ids']);self.assertNotEqual(a['proposal_sha256'],b['proposal_sha256'])
    def test_export_recomputes_and_preserves_package(self):
        p=flagship();before=copy.deepcopy(p);result=json.loads(export_package(p));self.assertEqual(p,before);self.assertEqual(result['package'],p);self.assertEqual(result['result'],reconcile_package(p))
        checksum=result.pop('receipt_sha256');body=json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode();self.assertEqual(hashlib.sha256(body).hexdigest(),checksum)
        p['report']['claim_type']='VERIFIED_SAVINGS';self.assertEqual(json.loads(export_package(p))['result']['decision'],'WITHHOLD')
    def test_resource_and_unknown_schema_fail_closed(self):
        p=clean();p['records']=[record(str(i),'1',str(i)) for i in range(1001)];self.assert_withheld(p)
        p=clean();p['records'][0]['quantity']='0'*129;self.assert_withheld(p)
        p=clean();p['override']={'accept':True};self.assert_withheld(p)
        p=clean();p['records'][0]['source_status']='VERIFIED';self.assert_withheld(p)
    def test_malformed_json_value_sweep_never_raises_or_invents_acceptance(self):
        for section in ['record','coverage','report']:
            template=clean();node=template['records'][0] if section=='record' else template['coverage'][0] if section=='coverage' else template['report']
            for key in node:
                for value in [None,{},[],True,False]:
                    if section=='record' and key=='target_record_id' and value is None:continue
                    p=clean();target=p['records'][0] if section=='record' else p['coverage'][0] if section=='coverage' else p['report'];target[key]=value
                    with self.subTest(section=section,key=key,value=value):self.assert_withheld(p)
    def test_literal_void_requires_new_source_to_establish_coverage(self):
        p=clean();p['records'] += [record('V','0',action='FULL_VOID',target='A'),record('NEW','100')]
        result=reconcile_package(p);self.assertEqual(result['decision'],'CORRECT');self.assertEqual(result['included_record_ids'],['NEW']);self.assertEqual(result['proposed_report']['emissions_tco2e'],'96')
        for value in ['0.0','-0','0e0']:
            altered=copy.deepcopy(p);altered['records'][1]['quantity']=value
            with self.subTest(value=value):self.assert_withheld(altered)
    def test_extra_limitations_remain_unverified_and_never_replace_core_warnings(self):
        p=clean();p['report']['limitations'].append('CALLER_SAYS_VERIFIED')
        result=reconcile_package(p);self.assertEqual(result['decision'],'ACCEPT');self.assertEqual(result['additional_report_limitations'],'UNVERIFIED_USER_ASSERTIONS_NOT_SCOPE_OVERRIDES');self.assertIn('ACTIVITY_NOT_VERIFIED',result['limitations']);self.assertEqual(result['factor']['value'],'0.960');self.assertEqual(result['factor']['uncertainty'],'NOT_QUANTIFIED_IN_SOURCE')
        p['report']['limitations'].remove('PUBLISHED_FACTOR_INPUT_RECONCILIATION_UNRESOLVED');result=self.assert_withheld(p);self.assertEqual(result['factor']['value'],'0.960')

import unittest,json,copy,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'src'))
from assurance import *
ROOT=Path(__file__).resolve().parents[1]
T=json.loads((ROOT/'fixtures/demo_tariffs.json').read_text())['tariffs']
I=json.loads((ROOT/'fixtures/demo_invoices.json').read_text())['invoices']
def t(i=0):return copy.deepcopy(T[i])
def inv(i=0):return copy.deepcopy(I[i])
class AssuranceTests(unittest.TestCase):
 def test_01_baseline_nine(self): self.assertEqual(audit_portfolio(T,I)['processed'],9)
 def test_02_two_variances(self):self.assertEqual(audit_portfolio(T,I)['review_required'],2)
 def test_03_seven_match(self):self.assertEqual(audit_portfolio(T,I)['model_matched'],7)
 def test_04_no_blocked_baseline(self):self.assertEqual(audit_portfolio(T,I)['blocked'],0)
 def test_05_demo_only(self):self.assertEqual(audit_invoice(inv(),t())['source_status'],'SYNTHETIC')
 def test_06_prohibits_false_verification(self):
  x=t(); x['source_status']='OFFICIAL_VERIFIED'
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_07_missing_provenance(self):
  x=t(); del x['source_url']
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_08_negative_rate(self):
  x=t();x['components'][0]['rate']=-1
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_09_nan_rate(self):
  x=t();x['components'][0]['rate']='NaN'
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_10_infinite_rate(self):
  x=t();x['components'][0]['rate']='Infinity'
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_11_unknown_unit(self):
  x=t(); x['components'][0]['unit']='x'
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_12_duplicate_tariff_component(self):
  x=t();x['components'].append(x['components'][0])
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_13_bad_currency(self):
  x=t();x['currency']='RAND'
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_14_bad_source_scheme(self):
  x=t();x['source_url']='file://internal'
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_15_invalid_effective_dates(self):
  x=t();x['effective_to']=x['effective_from']
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_16_missing_quantity(self):
  x=inv();del x['quantities']['kwh_peak']
  with self.assertRaises(ValueError):audit_invoice(x,t())
 def test_17_bad_usage_conservation(self):
  x=inv();x['quantities']['kwh_total']+=1
  with self.assertRaises(ValueError):audit_invoice(x,t())
 def test_18_cross_currency_rejected(self):
  x=inv();x['currency']='USD'
  with self.assertRaises(ValueError):audit_invoice(x,t())
 def test_19_cross_country_rejected(self):
  x=inv();x['country']='NG'
  with self.assertRaises(ValueError):audit_invoice(x,t())
 def test_20_unknown_line(self):
  x=inv();x['billed_lines'].append({'code':'nonsense','amount':'9'});x['billed_total']=str(Decimal(x['billed_total'])+9)
  a=audit_invoice(x,t());self.assertIn('nonsense',a['unknown_billed_lines']);self.assertTrue(any(f['severity']=='UNMODELED' for f in a['flags']))
 def test_21_missing_line(self):
  x=inv();x['billed_lines']=[z for z in x['billed_lines'] if z['code']!='tax']
  self.assertTrue(any(f['code']=='EXPECTED_LINE_MISSING' for f in audit_invoice(x,t())['flags']))
 def test_22_duplicate_line(self):
  x=inv();x['billed_lines'].append(x['billed_lines'][0])
  self.assertTrue(any(f['code']=='DUPLICATE_LINE_CODE' for f in audit_invoice(x,t())['flags']))
 def test_23_stated_total_variance(self):
  x=inv();x['billed_total']='3.00'
  self.assertTrue(any(f['code']=='STATED_TOTAL_MISMATCH' for f in audit_invoice(x,t())['flags']))
 def test_24_missing_tariff_version(self):
  x=inv();x['tariff_id']='OTHER'
  self.assertEqual(audit_portfolio(T,[x])['blocked'],1)
 def test_25_outside_tariff_effective(self):
  x=inv();x['period_end']='2028-02-01'
  self.assertEqual(audit_portfolio(T,[x])['blocked'],1)
 def test_26_duplicate_invoice(self):
  a=audit_portfolio(T,[inv(),inv()]);self.assertEqual(a['review_required'],1)
  self.assertTrue(any(f['code']=='DUPLICATE_INVOICE_NUMBER' for f in a['reports'][1]['flags']))
 def test_27_overlap(self):
  a=audit_portfolio(T,[inv(0),inv(0)]);self.assertTrue(any(f['code'].startswith('OVERLAPPING') for f in a['reports'][1]['flags']))
 def test_28_not_overlap_adjacent(self):
  a=audit_portfolio(T,[inv(0),inv(1)]);self.assertFalse(any(f['code'].startswith('OVERLAPPING') for f in a['reports'][1]['flags']))
 def test_29_zero_amount(self):self.assertEqual(money(dec('0')),'0.00')
 def test_30_round_half_up(self):self.assertEqual(money(Decimal('0.005')),'0.01')
 def test_31_negative_billed(self):
  x=inv();x['billed_lines'][0]['amount']='-9'
  with self.assertRaises(ValueError):audit_invoice(x,t())
 def test_32_zero_days(self):
  with self.assertRaises(ValueError):days_between('2026-07-01','2026-07-01')
 def test_33_noniso_date(self):
  with self.assertRaises(ValueError):parse_date('07/01/2026')
 def test_34_ke_separate(self):self.assertEqual(audit_invoice(inv(6),t(1))['currency'],'KES')
 def test_35_inconsistent_service_days(self):
  x=inv();x['quantities']['service_days']=30
  with self.assertRaises(ValueError):audit_invoice(x,t())
 def test_36_tax_out_of_bounds(self):
  x=t();x['tax_rate']='1.25'
  with self.assertRaises(ValueError):validate_tariff(x)
 def test_37_invoice_number_missing(self):
  x=inv();del x['invoice_number']
  with self.assertRaises(ValueError):audit_invoice(x,t())
 def test_38_bad_bill_currency_portfolio(self):
  x=inv();x['currency']='USD';self.assertEqual(audit_portfolio(T,[x])['blocked'],1)
 def test_39_invalid_quantity_bool(self):
  x=inv();x['quantities']['kwh_peak']=True
  with self.assertRaises(ValueError):audit_invoice(x,t())
 def test_40_multiple_versions_ambiguous(self):
  self.assertEqual(audit_portfolio([t(),t()],[inv()])['blocked'],1)
 def test_41_explicit_warning(self): self.assertIn('NOT proof',audit_invoice(inv(),t())['evidence_statement'])
 def test_42_multi_currency_no_aggregate(self):self.assertIn('never sum',audit_portfolio(T,I)['currency_scope'])
 def test_43_cross_tariff_end(self):
  x=inv();x['period_start']='2026-03-31'; self.assertEqual(audit_portfolio(T,[x])['blocked'],1)
 def test_44_no_tax_allowed(self):
  x=t();del x['tax_rate'];y=inv();y['billed_lines']=[z for z in y['billed_lines'] if z['code']!='tax'];y['billed_total']=str(sum(Decimal(z['amount']) for z in y['billed_lines'])); self.assertEqual(audit_invoice(y,x)['outcome'],'MODEL_MATCH')
if __name__=='__main__':unittest.main(verbosity=2)

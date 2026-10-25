"""Author challenge manifest before importing or running target implementation."""
import copy,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
A=json.loads((R/'fixtures/demo_energy_2024.json').read_text())['activities'][0]
F=json.loads((R/'fixtures/za_grid_factor_2024.json').read_text())
cases=[]
def case(cid,activities=None,factor=None,accept=True,total=None,why=''):
 cases.append(dict(id=cid,activities=activities or [copy.deepcopy(A)],factor=factor or copy.deepcopy(F),expected_accept=accept,expected_total_tco2e=total,reason=why))
def activity(**kw):a=copy.deepcopy(A);a.update(kw);return a
def factor(**kw):f=copy.deepcopy(F);f.update(kw);return f
case('valid_fractional_mwh',[activity(quantity='12.345')],total='11.85120',why='Positive same-year purchased electricity, synthetic input')
case('valid_equivalent_kwh',[activity(quantity='12345',unit='kWh')],total='11.85120',why='Unit conversion before multiplication')
case('valid_zero',[activity(quantity='0')],total='0',why='Zero consumption is valid, not missing data')
case('valid_small_kwh',[activity(quantity='0.125',unit='kWh')],total='0.000120',why='Small nonnegative energy remains valid')
case('valid_large_mwh',[activity(quantity='125000')],total='120000',why='Magnitude alone does not establish invalidity')
case('valid_adjacent_periods',[activity(activity_id='h1',quantity='20',period_end='2024-07-01'),activity(activity_id='h2',quantity='30',period_start='2024-07-01')],total='48',why='Adjacent end-exclusive periods do not overlap')
case('valid_distinct_meters',[activity(activity_id='h3',meter_id='METER-A',quantity='2'),activity(activity_id='h4',meter_id='METER-B',quantity='3')],total='4.8',why='Concurrent records on distinct meters are not duplicates')
case('valid_distinct_sites',[activity(activity_id='h5',site_id='SITE-A',quantity='2'),activity(activity_id='h6',site_id='SITE-B',quantity='3')],total='4.8',why='Same local meter label on different sites must not collide')
case('invalid_activity_country',[activity(country='KE')],accept=False,why='ZA factor cannot estimate Kenya consumption')
case('invalid_activity_year',[activity(period_start='2026-01-01',period_end='2027-01-01')],accept=False,why='Publication year is not factor data year')
case('invalid_cross_year',[activity(period_start='2023-12-15',period_end='2024-02-01')],accept=False,why='Single annual factor does not cover prior-year portion')
case('invalid_currency_as_energy',[activity(unit='ZAR')],accept=False,why='Money is not electricity activity')
case('invalid_power_as_energy',[activity(unit='kW')],accept=False,why='Power is not energy without duration')
case('invalid_negative_energy',[activity(quantity='-1')],accept=False,why='Negative grid consumption unsupported in this accounting boundary')
case('invalid_nonfinite_energy',[activity(quantity='NaN')],accept=False,why='Nonfinite inputs cannot produce estimate')
case('invalid_factor_country',factor=factor(country='KE'),accept=False,why='Country mismatch')
case('invalid_factor_data_year',factor=factor(data_year=2026),accept=False,why='Official factor identity/value cited for2024 cannot relabel2026')
case('invalid_factor_unit',factor=factor(unit='tCO2e/kWh'),accept=False,why='Dimension changed while numeric value retained')
case('invalid_factor_generation_boundary',factor=factor(boundary='GENERATION'),accept=False,why='Generation boundary is not purchased Scope2')
case('invalid_factor_value',factor=factor(value='0.096'),accept=False,why='Tenfold transcription error against fixed cited source')
case('invalid_factor_unproven_source',factor=factor(source_url='https://example.org/not-an-official-factor.pdf'),accept=False,why='Unsupported source cannot inherit official provenance')
case('invalid_claimed_verified_activity',[activity(source_status='VERIFIED')],accept=False,why='No independent activity-verification mechanism in this synthetic pilot')
case('invalid_duplicate_activity_id',[activity(activity_id='dup',meter_id='A',quantity='2'),activity(activity_id='dup',meter_id='B',quantity='3')],accept=False,why='Duplicate activity identifier cannot be treated as distinct input')
case('invalid_same_meter_overlap',[activity(activity_id='o1',quantity='20',period_end='2024-08-01'),activity(activity_id='o2',quantity='30',period_start='2024-07-01')],accept=False,why='Overlapping meter intervals risk double counting')
obj={'name':'GRIDSHIFT independent authored synthetic challenge v1','design':'Not random, field data, representative accuracy or competitive product comparison. Author has not read emissions implementation or test internals. Fixtures, function signatures and public review only used.','baseline':'Simple numeric multiplication baseline: normalizes recognized kWh/MWh, rejects negative/nonfinite quantities or factors, but ignores country/year/factor provenance/boundary/dedup/overlap. Not a claim about all spreadsheets or products.','expected_semantics':'Accept only same-year ZA purchased-electricity synthetic activities with cited fixed factor, nonnegative finite quantities and unique nonoverlapping records per site/meter. Exact arithmetic with Decimal.','cases':cases}
p=R/'benchmarks/holdout_manifest.json';p.write_text(json.dumps(obj,indent=2)+'\n');h=hashlib.sha256(p.read_bytes()).hexdigest();(R/'benchmarks/holdout_manifest.sha256').write_text(h+'  holdout_manifest.json\n');print(h,len(cases))

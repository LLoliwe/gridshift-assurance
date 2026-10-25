import sys,json,hashlib,datetime
from decimal import Decimal
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from emissions import calculate,calculate_batch
M=R/'benchmarks/holdout_manifest.json';expected_hash=(R/'benchmarks/holdout_manifest.sha256').read_text().split()[0];assert hashlib.sha256(M.read_bytes()).hexdigest()==expected_hash
manifest=json.loads(M.read_text())
def naive(acts,f):
 rate=Decimal(str(f['value']))
 if not rate.is_finite() or rate<0:raise ValueError('invalid numeric factor')
 total=Decimal(0)
 for a in acts:
  q=Decimal(str(a['quantity']))
  if not q.is_finite() or q<0:raise ValueError('invalid numeric activity')
  if a['unit']=='kWh':q/=1000
  elif a['unit']!='MWh':raise ValueError('unsupported energy unit')
  total+=q*rate
 return str(total)
def target(acts,f):
 if len(acts)==1:return calculate(acts[0],f)['emissions_tco2e']
 return calculate_batch(acts,f)['total_emissions_tco2e']
rows=[]
for c in manifest['cases']:
 row={k:c[k] for k in ['id','expected_accept','expected_total_tco2e','reason']}
 for name,fn in [('simple_arithmetic_baseline',naive),('gridshift',target)]:
  try:value=fn(c['activities'],c['factor']);r={'accepted':True,'value':value}
  except Exception as e:r={'accepted':False,'error_type':type(e).__name__,'error':str(e)}
  r['decision_correct']=r['accepted']==c['expected_accept']
  r['arithmetic_correct']=bool(r['accepted'] and c['expected_accept'] and Decimal(r['value'])==Decimal(c['expected_total_tco2e'])) if c['expected_accept'] else None
  row[name]=r
 rows.append(row)
summary={}
for n in ['simple_arithmetic_baseline','gridshift']:
 summary[n]={'valid_cases':sum(c['expected_accept'] for c in rows),'valid_arithmetic_correct':sum(bool(c[n]['arithmetic_correct']) for c in rows),'false_rejects':sum(c['expected_accept'] and not c[n]['accepted'] for c in rows),'invalid_cases':sum(not c['expected_accept'] for c in rows),'unsafe_acceptances':sum(not c['expected_accept'] and c[n]['accepted'] for c in rows),'correct_rejections':sum(not c['expected_accept'] and not c[n]['accepted'] for c in rows)}
out={'run_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':expected_hash,'implementation_sha256':hashlib.sha256((R/'src/emissions.py').read_bytes()).hexdigest(),'summary':summary,'rows':rows,'limitations':manifest['design']+' '+manifest['baseline']}
p=R/'benchmarks/holdout_results.json';p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(summary,indent=2));print('TARGET FAILURES');print(json.dumps([x for x in rows if not x['gridshift']['decision_correct'] or x['gridshift']['arithmetic_correct'] is False],indent=2))

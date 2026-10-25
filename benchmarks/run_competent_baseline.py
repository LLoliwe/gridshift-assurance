import json,hashlib,datetime
from decimal import Decimal
from pathlib import Path
from competent_rules_baseline import calculate_rows
R=Path(__file__).resolve().parents[1]
m=R/'benchmarks/holdout_manifest.json';assert hashlib.sha256(m.read_bytes()).hexdigest()==(R/'benchmarks/holdout_manifest.sha256').read_text().split()[0]
f=json.loads((R/'fixtures/za_grid_factor_2024.json').read_text());manifest=json.loads(m.read_text());rows=[]
for c in manifest['cases']:
 try:v=calculate_rows(c['activities'],c['factor'],f);r={'accepted':True,'value':v}
 except Exception as e:r={'accepted':False,'error_type':type(e).__name__,'error':str(e)}
 r.update(id=c['id'],expected_accept=c['expected_accept']);r['decision_correct']=r['accepted']==c['expected_accept'];r['arithmetic_correct']=(r['accepted'] and Decimal(r['value'])==Decimal(c['expected_total_tco2e'])) if c['expected_accept'] else None;rows.append(r)
summary={'valid_cases':8,'valid_arithmetic_correct':sum(bool(r['arithmetic_correct']) for r in rows),'false_rejects':sum(r['expected_accept'] and not r['accepted'] for r in rows),'invalid_cases':16,'unsafe_acceptances':sum(not r['expected_accept'] and r['accepted'] for r in rows),'correct_rejections':sum(not r['expected_accept'] and not r['accepted'] for r in rows)}
out={'run_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':hashlib.sha256(m.read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((R/'benchmarks/competent_baseline_protocol.json').read_bytes()).hexdigest(),'baseline_source_sha256':hashlib.sha256((R/'benchmarks/competent_rules_baseline.py').read_bytes()).hexdigest(),'summary':summary,'rows':rows}
(R/'benchmarks/competent_baseline_results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(summary,indent=2))

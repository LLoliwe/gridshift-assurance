"""Exact replay of curated known cell facts; not automatic source discovery."""
from fractions import Fraction
from decimal import Decimal,localcontext
import re,json
FORMATS={'#,##0':0,'#,##0.00':2,'#,##0.000':3}
COMPAT='COMPATIBLE_UNDER_DECLARED_DISPLAY_ROUNDING_CONVENTION'
QUESTION='SOURCE_RECONCILIATION_QUESTION_UNDER_DECLARED_CONVENTION'
UNAVAILABLE='UNRESOLVED_MISSING_OR_NONCOMPARABLE_INPUT'
def packed(v):
 with localcontext() as c:c.prec=30;s=format(Decimal(v.numerator)/Decimal(v.denominator),'.12g')
 return {'numerator':v.numerator,'denominator':v.denominator,'decimal_approx':s}
def literal(s):
 if not isinstance(s,str) or len(s)>100 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',s):raise ValueError('Unsupported literal decimal')
 return Fraction(s),len(s.split('.')[1]) if '.' in s else 0
def round_positive(v,places):
 scale=10**places;x=v*scale;n=(2*x.numerator+x.denominator)//(2*x.denominator);return Fraction(n,scale)
def amount(cell):
 if not isinstance(cell,dict) or cell.get('formula') is not None:raise ValueError('Missing/unsupported source amount')
 text=cell.get('source_text_or_numeric_token');value,places=literal(text)
 if cell.get('xml_type')=='n':
  fmt=cell.get('number_format')
  if fmt not in FORMATS:raise ValueError('Unsupported numeric display format')
  places=FORMATS[fmt];display=round_positive(value,places);interpretation='NUMERIC_CELL_FORMAT_ROUNDING'
 elif cell.get('xml_type') in ('s','inlineStr','str'):
  display=value;interpretation='LITERAL_TEXT_PRECISION_NOT_NUMERIC_CELL_FORMAT'
 else:raise ValueError('Unsupported source cell type')
 half=Fraction(1,2*10**places)
 return value,display,(max(Fraction(0),display-half),display+half),interpretation
def reported(cell):
 if not isinstance(cell,dict) or cell.get('formula') is not None:raise ValueError('Unsupported percentage source')
 s=cell.get('source_text_or_numeric_token')
 if not isinstance(s,str):raise ValueError('Missing percentage text')
 m=re.fullmatch(r'([▲▼►])([+\-−]?)([0-9]+(?:\.[0-9]+)?)',s)
 if not m:raise ValueError('Unsupported percentage label')
 arrow,sign,magnitude=m.groups();v,places=literal(magnitude);direction={'▲':1,'▼':-1,'►':0}[arrow]
 if direction==0 and v!=0:raise ValueError('Nonzero horizontal-arrow label')
 signed=(-v if sign in ('-','−') else v) if sign else direction*v
 conflict=bool(v and sign and ((signed>0)!=(direction>0)))
 half=Fraction(1,2*10**places)
 return signed,places,(signed-half,signed+half),arrow,sign,conflict
def replay(row):
 out={'source':row,'status':UNAVAILABLE,'method':'100 * (current / prior - 1); exact rational arithmetic; declared display sensitivity, not metering uncertainty'}
 try:
  cur,dc,cb,ci=amount(row.get('current_source'));old,do,ob,oi=amount(row.get('prior_source'));pct,places,pb,arrow,sign,conflict=reported(row.get('percentage_source'))
  if old<=0 or ob[0]<=0:raise ValueError('Prior value or conservative lower bound is not positive')
  exact=100*(cur/old-1);display=100*(dc/do-1);bounds=(100*(cb[0]/ob[1]-1),100*(cb[1]/ob[0]-1))
  overlap=max(bounds[0],pb[0])<=min(bounds[1],pb[1]);trunc=Fraction(int(exact*10**places),10**places)
  out.update(status=COMPAT if overlap and not conflict else QUESTION,exact_value_percentage=packed(exact),display_value_percentage=packed(display),ordinary_percentage_bounds=[packed(x) for x in bounds],reported_percentage_bounds=[packed(x) for x in pb],amount_interpretations=[ci,oi],reported_arrow=arrow,reported_explicit_sign=sign,explicit_sign_arrow_conflict=conflict,exact_value_truncation_matches_report=trunc==pct,displayed_current=packed(dc),displayed_prior=packed(do))
 except (ValueError,TypeError,ZeroDivisionError) as e:out['unavailable_reason']=str(e)
 return out
def replay_all(rows):
 if not isinstance(rows,list) or len(rows)>1000:raise ValueError('Expected bounded curated comparison list')
 results=[replay(x) for x in rows];counts={k:sum(r['status']==k for r in results) for k in (COMPAT,QUESTION,UNAVAILABLE)}
 return {'schema_version':'gridshift.known_source_comparison.v1','mode':'RETROSPECTIVE_REPLAY_OF_MANUALLY_CURATED_KNOWN_SOURCE_FACTS','comparison_count':len(results),'status_counts':counts,'rows':results,'limitations':['Not discovery by the inventory engine, general workbook ingestion, unseen validation or independent human expert certification.','Compatible does not establish correctness; questions are not proven errors or authoritative corrections.','Declared ordinary prior-year formula may differ from an intended source baseline/restatement; ask the publisher rather than overwrite.','Display-rounding bounds are not measurement uncertainty.','No emissions factor, savings, financial materiality or physical impact calculation.','Competent same-information spreadsheet/rules comparison can tie; no superiority claim.','Original corporate workbooks remain privately retained; official links and limited attributed factual extracts do not imply an open-data/MIT licence.']}
if __name__=='__main__':
 import sys
 from pathlib import Path
 rows=json.loads(Path(sys.argv[1]).read_text())['rows'];Path(sys.argv[2]).write_text(json.dumps(replay_all(rows),sort_keys=True,ensure_ascii=False,indent=2)+'\n')

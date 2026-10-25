"""Independent fixed-factor reference, not copied from target code."""
from decimal import Decimal
from datetime import date

def calculate_rows(rows, supplied_factor, authorized_factor):
 if supplied_factor != authorized_factor:raise ValueError('factor differs from protected reviewed fixture')
 if not rows:raise ValueError('no activity rows')
 ids=set();periods={};total=Decimal(0)
 year=int(authorized_factor['data_year']);first=date(year,1,1);after=date(year+1,1,1)
 for row in rows:
  for key in ['activity_id','site_id','meter_id']:
   if not isinstance(row.get(key),str) or not row[key].strip():raise ValueError('missing identifier')
  if row['activity_id'] in ids:raise ValueError('duplicate activity identifier')
  ids.add(row['activity_id'])
  if row.get('source_status')!='SYNTHETIC':raise ValueError('unsupported activity assurance status')
  if row.get('country')!=authorized_factor['country']:raise ValueError('country mismatch')
  start=date.fromisoformat(row['period_start']);end=date.fromisoformat(row['period_end'])
  if not first<=start<end<=after:raise ValueError('invalid interval for factor data year')
  key=(row['site_id'],row['meter_id'])
  for old_start,old_end in periods.get(key,[]):
   if start<old_end and old_start<end:raise ValueError('overlapping meter intervals')
  periods.setdefault(key,[]).append((start,end))
  if isinstance(row['quantity'],bool):raise ValueError('boolean not an energy quantity')
  q=Decimal(str(row['quantity']))
  if not q.is_finite() or q<0:raise ValueError('invalid numeric energy')
  if row['unit']=='kWh':q/=1000
  elif row['unit']!='MWh':raise ValueError('unsupported energy unit')
  total+=q*Decimal(authorized_factor['value'])
 return str(total)

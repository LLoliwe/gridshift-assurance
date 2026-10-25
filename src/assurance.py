"""GRIDSHIFT Assurance v0.2, an offline, evidence-oriented demonstration.
All packaged amounts and utilities are invented. NEVER claim verified tariff accuracy.
Uses Python stdlib only. No internet, integrations, secrets, or device control.
"""
from __future__ import annotations
import argparse, json, hashlib
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from pathlib import Path
from collections import defaultdict

Q = Decimal('0.01')
SUPPORTED_UNITS = {'kwh_peak', 'kwh_standard', 'kwh_offpeak', 'kwh_total', 'peak_kw', 'demand_kva', 'service_days', 'bill_count'}

def dec(value, field='number'):
    if isinstance(value, bool): raise ValueError(f'{field}: bool not numeric')
    try: d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError): raise ValueError(f'{field}: invalid decimal')
    if not d.is_finite() or d < 0: raise ValueError(f'{field}: negative/nonfinite not allowed')
    return d

def money(d):
    return str(d.quantize(Q, rounding=ROUND_HALF_UP))

def parse_date(s):
    try: return date.fromisoformat(s)
    except (ValueError, TypeError): raise ValueError(f'invalid ISO date: {s}')

def days_between(start, end):
    a, b = parse_date(start), parse_date(end)
    if b <= a: raise ValueError('invoice period end must be later than start (exclusive)')
    return (b-a).days

def validate_tariff(t):
    for f in ('tariff_id', 'utility', 'country', 'currency', 'effective_from', 'effective_to', 'source_url', 'source_status', 'components'):
        if f not in t: raise ValueError('tariff missing '+f)
    if t['source_status'] not in ('SYNTHETIC', 'UNVERIFIED_TRANSCRIPTION'):
        raise ValueError('Only synthetic or explicitly unverified sources allowed in this pilot')
    if len(t['country']) != 2 or len(t['currency']) != 3: raise ValueError('ISO country/currency needed')
    if not str(t['source_url']).startswith(('https://','http://')): raise ValueError('source URL required')
    if parse_date(t['effective_to']) <= parse_date(t['effective_from']): raise ValueError('invalid effective interval')
    seen = set()
    for c in t['components']:
        code = c.get('code');unit=c.get('unit')
        if not code or code in seen: raise ValueError('duplicate/empty component code')
        seen.add(code)
        if unit not in SUPPORTED_UNITS: raise ValueError(f'unsupported component unit {unit}')
        dec(c.get('rate'), f'rate for {code}')
    if 'tax_rate' in t:
        if dec(t['tax_rate']) > 1: raise ValueError('tax_rate must be 0 through 1')
    return True

def expected_lines(invoice,t):
    validate_tariff(t)
    for k in ('invoice_number','site_id','meter_id','country','currency','utility','tariff_id','period_start','period_end','quantities','billed_lines','billed_total'):
        if k not in invoice: raise ValueError(f'invoice missing {k}')
    days = days_between(invoice['period_start'], invoice['period_end'])
    if invoice['period_start'] < t['effective_from'] or invoice['period_end'] > t['effective_to']:
        raise ValueError('RATE_VERSION_SPLIT_REQUIRED: invoice outside tariff validity')
    for key in ('country','currency','utility','tariff_id'):
        if invoice[key] != t[key]: raise ValueError('tariff/invoice mismatch: '+key)
    qmap = {k:dec(v,k) for k,v in invoice['quantities'].items()}
    if 'service_days' in qmap and qmap['service_days']!=days: raise ValueError('service_days inconsistent')
    qmap['service_days']=Decimal(days)
    qmap['bill_count']=Decimal(1)
    if {'kwh_peak','kwh_standard','kwh_offpeak','kwh_total'}.issubset(qmap):
        if abs(qmap['kwh_peak']+qmap['kwh_standard']+qmap['kwh_offpeak']-qmap['kwh_total']) > Decimal('0.001'):
            raise ValueError('TOU quantities do not equal total kWh')
    result={}
    for c in t['components']:
        unit=c['unit']
        if unit not in qmap: raise ValueError(f'MISSING_QUANTITY: {unit}')
        result[c['code']]={'expected':money(dec(c['rate'])*qmap[unit]),'unit':unit,'quantity':str(qmap[unit]),'rate':str(c['rate'])}
    if t.get('tax_rate') is not None:
        taxable = sum((Decimal(v['expected']) for v in result.values()),Decimal(0))
        result['tax']={'expected':money(taxable*dec(t['tax_rate'])),'unit':'tax','quantity':'1','rate':str(t['tax_rate'])}
    return result

def audit_invoice(invoice, t, tolerance='0.02'):
    expected=expected_lines(invoice,t); threshold=dec(tolerance,'tolerance')
    billed={}; flags=[]; unknown=[]
    for line in invoice['billed_lines']:
        code=line['code']
        if code in billed: flags.append({'severity':'BLOCKED','code':'DUPLICATE_LINE_CODE','line_code':code})
        else: billed[code]=dec(line['amount'],code)
    total_actual=dec(invoice['billed_total'],'billed_total')
    sum_lines=sum(billed.values(),Decimal(0))
    if abs(total_actual-sum_lines)>threshold:
        flags.append({'severity':'REVIEW','code':'STATED_TOTAL_MISMATCH','difference':money(abs(total_actual-sum_lines))})
    lines=[]; diff=Decimal(0)
    for code, v in expected.items():
        x=billed.get(code)
        exp=Decimal(v['expected'])
        if x is None:
            flags.append({'severity':'REVIEW','code':'EXPECTED_LINE_MISSING','line_code':code})
            lines.append({'code':code,'expected':v['expected'],'billed':None,'delta':None,'status':'MISSING'})
        else:
            delta=x-exp;diff+=delta
            if abs(delta)>threshold: flags.append({'severity':'REVIEW','code':'LINE_VARIANCE','line_code':code,'difference':money(abs(delta))})
            lines.append({'code':code,'expected':v['expected'],'billed':money(x),'delta':str(delta.quantize(Q)),'status':'REVIEW' if abs(delta)>threshold else 'MATCH'})
    for code in billed:
        if code not in expected:
            unknown.append(code)
            flags.append({'severity':'UNMODELED','code':'UNKNOWN_BILLED_LINE','line_code':code})
    flags.sort(key=lambda a:(a['severity'],a['code'],a.get('line_code','')))
    return {'invoice_number':invoice['invoice_number'],'site_id':invoice['site_id'],'meter_id':invoice['meter_id'],
            'country':t['country'],'currency':t['currency'],'source_status':t['source_status'],
            'period_start':invoice['period_start'],'period_end_exclusive':invoice['period_end'],'billing_days':days_between(invoice['period_start'],invoice['period_end']),
            'billed_total':money(total_actual),'expected_modeled_total':money(sum(Decimal(v['expected']) for v in expected.values())),
            'known_line_variance':money(diff),'lines':lines,'flags':flags,'unknown_billed_lines':unknown,
            'outcome':'REVIEW_REQUIRED' if flags else 'MODEL_MATCH',
            'evidence_statement':'INTERNAL DEMONSTRATION ONLY. Synthetic or unverified rates; results NOT proof of overbilling, statutory compliance, recoverable savings, or customer liability.'}

def audit_portfolio(tariffs, invoices):
    lookup={}
    for t in tariffs:
        validate_tariff(t)
        key=(t['country'],t['utility'],t['tariff_id'])
        lookup.setdefault(key,[]).append(t)
    seen=set();grouped=defaultdict(list);results=[]
    for inv in invoices:
        inv_id=(inv.get('country'),inv.get('utility'),inv.get('invoice_number'))
        key=(inv.get('site_id'),inv.get('meter_id'),inv.get('utility'))
        issues=[]
        if inv_id in seen: issues.append('DUPLICATE_INVOICE_NUMBER')
        seen.add(inv_id)
        try:
            a=parse_date(inv['period_start']); b=parse_date(inv['period_end'])
            days_between(inv['period_start'],inv['period_end'])
            for pa,pb,pid in grouped[key]:
                if a < pb and pa < b: issues.append('OVERLAPPING_BILLING_PERIOD:'+str(pid))
            grouped[key].append((a,b,inv.get('invoice_number')))
            candidates=[t for t in lookup.get((inv['country'],inv['utility'],inv['tariff_id']),[])
                        if t['effective_from']<=inv['period_start'] and inv['period_end']<=t['effective_to']]
            if len(candidates)!=1: raise ValueError('TARIFF_VERSION_NOT_UNIQUE_OR_MISSING')
            result=audit_invoice(inv,candidates[0])
            for issue in issues: result['flags'].append({'severity':'BLOCKED','code':issue})
            if issues: result['outcome']='REVIEW_REQUIRED'
        except (ValueError, KeyError, TypeError) as exc:
            result={'invoice_number':inv.get('invoice_number'),'site_id':inv.get('site_id'),
                    'outcome':'BLOCKED','flags':[{'severity':'BLOCKED','code':str(exc)}],
                    'evidence_statement':'No modeled conclusion available'}
        results.append(result)
    return {'product':'GRIDSHIFT Assurance','version':'0.2.0','currency_scope':'per-invoice, never sum different currencies',
            'processed':len(results),'blocked':sum(x['outcome']=='BLOCKED' for x in results),
            'review_required':sum(x['outcome']=='REVIEW_REQUIRED' for x in results),
            'model_matched':sum(x['outcome']=='MODEL_MATCH' for x in results),
            'reports':results,
            'safety':'All packaged data synthetic. Findings are candidate billing exceptions, not proven savings or enforceable claims.'}

def main():
    p=argparse.ArgumentParser(description='GRIDSHIFT Assurance offline billing audit (demo data only)')
    p.add_argument('--tariffs',required=True);p.add_argument('--invoices',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    t=json.loads(Path(a.tariffs).read_text()); v=json.loads(Path(a.invoices).read_text())
    results=audit_portfolio(t['tariffs'],v['invoices']); raw=json.dumps(results,sort_keys=True,indent=2)
    Path(a.output).parent.mkdir(exist_ok=True,parents=True);Path(a.output).write_text(raw,encoding='utf8')
    print(json.dumps({'processed':results['processed'],'review_required':results['review_required'],'blocked':results['blocked'],'model_matched':results['model_matched'],'output':a.output,'sha256':hashlib.sha256(raw.encode()).hexdigest()},indent=2))
if __name__=='__main__':main()

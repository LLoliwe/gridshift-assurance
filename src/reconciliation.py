"""Evidence-bound report reconciliation. Declared lineage is not source authentication.
Additive restricted policy; the pinned emissions core remains unchanged.
"""
from copy import deepcopy
from decimal import Decimal, Context, localcontext
import hashlib
import json
from emissions import calculate, CURATED_FACTOR, _decimal, _date

SCHEMA='gridshift.reconciliation.input.v1'
POLICY='gridshift.reconciliation.policy.v1'
SCOPE=('entity_id','site_id','meter_id','country','period_start','period_end')
RECORD=set(SCOPE)|{'record_id','source_id','quantity','unit','source_status','source_note','action','target_record_id'}
REPORT={'claim_type','energy_mwh','emissions_tco2e','factor_id','data_year','boundary','activity_statuses','limitations'}
LIMITS=['NOT_AN_INDEPENDENT_VERIFICATION','NOT_BLOCKCHAIN','NOT_MEASURED_SAVINGS','EXCLUDES_SCOPE3_T_AND_D','ANNUAL_AVERAGE_NOT_TIME_OF_USE','ACTIVITY_NOT_VERIFIED','PUBLISHED_FACTOR_INPUT_RECONCILIATION_UNRESOLVED','MARKET_BASED_NOT_COMPUTED','ORGANIZATIONAL_BOUNDARY_NOT_REVIEWED','NOT_FULL_SCOPE2_COMPLIANCE']

class PolicyError(ValueError):
    def __init__(self,code,message,ids=()):self.code=code;self.ids=list(ids);super().__init__(message)
def fail(code,message,ids=()):raise PolicyError(code,message,ids)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def text(value,label):
    if not isinstance(value,str) or not value or value!=value.strip() or len(value)>2000:fail('INVALID_FIELD',f'{label} requires a bounded nonempty string.')
def fields(value,expected,label):
    if not isinstance(value,dict):fail('INVALID_SCHEMA',f'{label} must be a JSON object. Supply the source-backed object in the documented schema; do not invent missing evidence.')
    missing=sorted(set(expected)-set(value));extra=sorted(set(value)-set(expected),key=str)
    if missing or extra:
        def names(keys):
            shown=[json.dumps(str(key)[:96]+('…' if len(str(key))>96 else ''),ensure_ascii=True) for key in keys[:20]]
            return ', '.join(shown)+(f' (+{len(keys)-20} further keys)' if len(keys)>20 else '') or 'none'
        instruction=[]
        if missing:instruction.append('Supply these missing fields from the original source evidence, then rerun; do not invent values.')
        if extra:instruction.append('These keys have unsupported semantics under this policy. Preserve the original evidence; do not silently delete material fields to force acceptance. Obtain a supported source-backed representation or reconcile outside this prototype.')
        record_ids=[value['record_id']] if label.startswith('records[') and isinstance(value.get('record_id'),str) and 0<len(value['record_id'])<=2000 else []
        fail('INVALID_SCHEMA',f'{label}: missing keys [{names(missing)}]; unsupported keys [{names(extra)}]. '+' '.join(instruction),record_ids)
def number(value,label):
    if not isinstance(value,str):fail('INVALID_NUMBER',f'{label} must be an exact decimal string.')
    try:return _decimal(value)
    except ValueError as e:fail('INVALID_NUMBER',str(e))
def fmt(x):return format(x.normalize(),'f') if x else '0'
def source_digest(p):return digest({k:v for k,v in p.items() if k!='resolutions'})
def scope(r):return tuple(r[k] for k in SCOPE)
def meter(r):return tuple(r[k] for k in SCOPE[:4])
def activity(r):return {**{k:r[k] for k in ('site_id','meter_id','country','period_start','period_end','quantity','unit','source_status','source_note')},'activity_id':r['record_id']}
def intervals(rows,label):
    grouped={}
    for r in rows:grouped.setdefault(meter(r),[]).append((r['period_start'],r['period_end'],r.get('record_id',label)))
    result={}
    for key,values in grouped.items():
        values.sort();merged=[];previous_id=None
        for start,end,rid in values:
            if merged and start<merged[-1][1]:fail('AMBIGUOUS_OVERLAP',f'{label}: overlapping intervals in declared identity {key} require explicit supported lineage or nonoverlapping coverage evidence.',[x for x in (previous_id,rid) if x and x!=label])
            if merged and start==merged[-1][1]:merged[-1]=(merged[-1][0],end)
            else:merged.append((start,end))
            previous_id=rid
        result[key]=merged
    return result

def _run(p):
    fields(p,{'schema_version','package_id','records','coverage','report','resolutions'},'package')
    if p['schema_version']!=SCHEMA:fail('INVALID_SCHEMA','Unsupported reconciliation schema.')
    text(p['package_id'],'package_id')
    if not isinstance(p['records'],list) or not 1<=len(p['records'])<=1000:fail('RECORD_LIMIT','Provide 1–1000 source records.')
    if not isinstance(p['coverage'],list) or not 1<=len(p['coverage'])<=1000:fail('COVERAGE_REQUIRED','Declare the intended sites, meters and end-exclusive periods.')
    if not isinstance(p['resolutions'],list) or len(p['resolutions'])>1:fail('INVALID_RESOLUTION','At most one explicit current-proposal acceptance is supported.')
    byid={};receipts={};successors={}
    for record_index,r in enumerate(p['records']):
        fields(r,RECORD,f'records[{record_index}]')
        for k in RECORD-{'target_record_id'}:text(r[k],k)
        rid=r['record_id']
        if rid in byid:fail('DUPLICATE_RECORD_ID','Record IDs must uniquely identify evidence; no automatic document deduplication.',[rid])
        if r['action'] not in ('ORIGINAL','FULL_REPLACEMENT','FULL_VOID'):fail('UNSUPPORTED_LINEAGE','Only original, complete replacement or original-record void is supported.',[rid])
        if (r['action']=='ORIGINAL')!=(r['target_record_id'] is None):fail('INVALID_TARGET','Original records have no target; corrections require an explicit target.',[rid])
        if r['target_record_id'] is not None:text(r['target_record_id'],'target_record_id')
        number(r['quantity'],'quantity')
        if r['action']=='FULL_VOID' and r['quantity']!='0':fail('VOID_NOT_ENERGY','A void must carry zero, not signed or inferred consumption.',[rid])
        try:receipts[rid]=calculate(activity(r),CURATED_FACTOR)
        except ValueError as e:fail('SOURCE_NOT_SUPPORTED',str(e),[rid])
        byid[rid]=r
    for rid,r in byid.items():
        target=r['target_record_id']
        if target is None:continue
        if target not in byid:fail('MISSING_TARGET','Supply the original referenced source record.',[rid,target])
        t=byid[target]
        if scope(r)!=scope(t):fail('PARTIAL_OR_CROSS_SCOPE','Full correction must retain entity, site, meter, country and identical full interval.',[rid,target])
        if t['action']=='FULL_VOID' or (r['action']=='FULL_VOID' and t['action']!='ORIGINAL'):fail('UNSUPPORTED_REVIVAL','Void-of-replacement, void-of-void and revival are not supported.',[rid,target])
        successors.setdefault(target,[]).append(rid)
    for target,children in successors.items():
        if len(children)>1:fail('CONFLICTING_SUCCESSORS','Resolve competing replacement/void assertions with explicit source evidence.',[target]+sorted(children))
    for rid in byid:
        seen=set();cur=rid
        while cur is not None:
            if cur in seen:fail('LINEAGE_CYCLE','Source correction lineage must be acyclic.',sorted(seen))
            seen.add(cur);cur=byid[cur]['target_record_id']
    included=sorted(rid for rid,r in byid.items() if rid not in successors and r['action']!='FULL_VOID')
    excluded=sorted(set(byid)-set(included))
    coverage=[]
    for coverage_index,c in enumerate(p['coverage']):
        fields(c,SCOPE,f'coverage[{coverage_index}]')
        for k in SCOPE:text(c[k],k)
        try:
            start,end=_date(c['period_start']),_date(c['period_end'])
            if end<=start:raise ValueError('Coverage end must follow start.')
        except ValueError as e:fail('INVALID_COVERAGE',str(e))
        coverage.append(c)
    intended=intervals(coverage,'declared coverage');accepted=intervals([byid[x] for x in included],'accepted records')
    if accepted!=intended:fail('COVERAGE_UNRESOLVED','Surviving records must exactly cover the declared scope. A void or missing record is not zero usage; supply explicit supported records or a corrected coverage declaration.',included)
    report=p['report'];fields(report,REPORT,'report')
    if report['claim_type']!='CONDITIONAL_INVENTORY_ESTIMATE':fail('UNSUPPORTED_CLAIM','Only a conditional inventory estimate is supported. Supply an explicitly narrower report; avoided emissions or verified truth cannot be silently relabelled.')
    if report['factor_id']!=CURATED_FACTOR['factor_id'] or type(report['data_year']) is not int or report['data_year']!=2024 or report['boundary']!=CURATED_FACTOR['boundary']:fail('REPORT_FACTOR_MISMATCH','Report must declare the supported factor, data year and accounting boundary.')
    statuses=sorted(set(r['source_status'] for r in byid.values()))
    if not isinstance(report['activity_statuses'],list) or sorted(report['activity_statuses'])!=statuses:fail('SOURCE_STATUS_LOSS','Retain every original source status, including synthetic/unverified labels.')
    if not isinstance(report['limitations'],list) or len(report['limitations'])>100 or any(not isinstance(x,str) or not x.strip() or len(x)>2000 for x in report['limitations']) or not set(LIMITS).issubset(report['limitations']):fail('LIMITATIONS_LOSS','Retain every required limitation and unresolved factor reconciliation warning.')
    claimed_energy=number(report['energy_mwh'],'report energy_mwh');claimed_emissions=number(report['emissions_tco2e'],'report emissions_tco2e')
    with localcontext(Context(prec=80,Emin=-999999,Emax=999999)):
        energy=sum((Decimal(receipts[x]['energy_mwh']) for x in included),Decimal(0));emissions=sum((Decimal(receipts[x]['emissions_tco2e']) for x in included),Decimal(0))
        proposed={**deepcopy(report),'energy_mwh':fmt(energy),'emissions_tco2e':fmt(emissions)}
        delta=abs(claimed_emissions-emissions);threshold=max(Decimal(1),emissions*Decimal('.01'))
        discrepancy={'energy_mwh':fmt(claimed_energy-energy),'emissions_tco2e':fmt(claimed_emissions-emissions),'absolute_emissions_tco2e':fmt(delta),'relative_emissions_fraction':None if emissions==0 else fmt(delta/emissions),'materiality_threshold_tco2e':fmt(threshold),'material':delta>=threshold,'policy':'PROTOTYPE_TRIAGE_NOT_AUDIT_STANDARD'}
    trace=[{'record_id':rid,'source_id':byid[rid]['source_id'],'action':byid[rid]['action'],'target_record_id':byid[rid]['target_record_id'],'included':rid in included,'reason':'ACTIVE_SUPPORTED_RECORD' if rid in included else 'VOID_INSTRUCTION' if byid[rid]['action']=='FULL_VOID' else 'EXPLICITLY_SUPERSEDED_OR_VOIDED','source_status':byid[rid]['source_status']} for rid in sorted(byid)]
    correction=bool(excluded) or claimed_energy!=energy or claimed_emissions!=emissions
    proposal={'policy':POLICY,'source_package_sha256':source_digest(p),'included_record_ids':included,'excluded_record_ids':excluded,'proposed_report':proposed,'trace':trace}
    proposal_hash=digest(proposal) if correction else None
    resolution_accepted=False
    if p['resolutions']:
        r=p['resolutions'][0];fields(r,{'action','proposal_sha256','reviewer_id','source_status'},'resolutions[0]');text(r['reviewer_id'],'reviewer_id')
        if not correction or r['action']!='ACCEPT_PROPOSAL' or r['proposal_sha256']!=proposal_hash or r['source_status']!='UNVERIFIED_USER_INPUT':fail('STALE_OR_UNSUPPORTED_RESOLUTION','Only explicit acceptance of this exact current proposal is supported; no bare override or stale approval.')
        resolution_accepted=True
    decision='CORRECT' if correction and not resolution_accepted else 'ACCEPT'
    return {'schema_version':'gridshift.reconciliation.result.v1','policy':POLICY,'decision':decision,'decision_label':'Accepted within this calculation policy' if decision=='ACCEPT' else 'Correction proposed; reviewer acceptance required','source_package_sha256':source_digest(p),'included_record_ids':included,'excluded_record_ids':excluded,'proposed_report':proposed if correction else None,'accepted_report':proposed if decision=='ACCEPT' else None,'proposal_sha256':proposal_hash,'resolution_accepted':resolution_accepted,'trace':trace,'discrepancy':discrepancy,'findings':([{'code':'SUPPORTED_LINEAGE_CORRECTION','message':'Explicit supported lineage changes the accepted record set; original evidence retained.','record_ids':excluded}] if excluded else [])+([{'code':'REPORT_TOTAL_MISMATCH','message':'Reported energy or emissions differ from the uniquely supported record set.','record_ids':included}] if claimed_energy!=energy or claimed_emissions!=emissions else []),'required_evidence':[],'limitations':deepcopy(LIMITS),'activity_statuses':statuses,'coverage_scope':'DECLARED_PACKAGE_ONLY_NOT_ORGANIZATIONAL_COMPLETENESS','reviewer_identity':'SELF_REPORTED_NOT_AUTHENTICATED','factor':deepcopy(CURATED_FACTOR),'additional_report_limitations':'UNVERIFIED_USER_ASSERTIONS_NOT_SCOPE_OVERRIDES'}

def reconcile_package(package):
    """Fail closed, retain no invented totals, and never mutate caller evidence."""
    try:
        if len(canonical(package).encode())>2*1024*1024:fail('INPUT_LIMIT','Package exceeds 2 MiB.')
        return _run(package)
    except (PolicyError,ValueError,TypeError,RecursionError) as e:
        return {'schema_version':'gridshift.reconciliation.result.v1','policy':POLICY,'decision':'WITHHOLD','decision_label':'Withheld pending specific evidence','proposed_report':None,'accepted_report':None,'proposal_sha256':None,'findings':[{'code':getattr(e,'code','INVALID_INPUT'),'message':str(e),'record_ids':getattr(e,'ids',[])}],'required_evidence':[str(e)],'issue_completeness':'FIRST_BLOCKER_ONLY_ADDITIONAL_ISSUES_MAY_EMERGE_NOT_MINIMALITY_PROOF','limitations':deepcopy(LIMITS),'coverage_scope':'NOT_ESTABLISHED','reviewer_identity':'SELF_REPORTED_NOT_AUTHENTICATED','factor':deepcopy(CURATED_FACTOR),'additional_report_limitations':'UNVERIFIED_USER_ASSERTIONS_NOT_SCOPE_OVERRIDES'}

def accept_proposal(package,proposal_sha256,reviewer_id):
    result=reconcile_package(package)
    if result['decision']!='CORRECT' or result['proposal_sha256']!=proposal_sha256:raise ValueError('No matching current correction proposal to accept.')
    text(reviewer_id,'reviewer_id');revised=deepcopy(package)
    revised['resolutions']=[{'action':'ACCEPT_PROPOSAL','proposal_sha256':proposal_sha256,'reviewer_id':reviewer_id,'source_status':'UNVERIFIED_USER_INPUT'}]
    return revised

def export_package(package):
    """Recompute, then export immutable original evidence and computational resolution."""
    payload={'schema_version':'gridshift.reconciliation.export.v1','package':deepcopy(package),'result':reconcile_package(package),'receipt_semantics':'UNSIGNED_CONTENT_HASH_NOT_AUTHENTICITY_OR_BLOCKCHAIN'}
    payload['receipt_sha256']=digest(payload)
    return canonical(payload)+'\n'


def load_package(path):
    from pathlib import Path
    from emissions import _check_json_depth, _unique_object
    with Path(path).open('rb') as stream: raw=stream.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:raise ValueError('Package exceeds 2 MiB.')
    source=raw.decode('utf-8');_check_json_depth(source)
    return json.loads(source,object_pairs_hook=_unique_object,parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON constant rejected.')))

def main(argv=None):
    import argparse,sys
    from emissions import _write_exclusive_atomic
    parser=argparse.ArgumentParser(description='Restricted GRIDSHIFT report reconciliation; not source verification.')
    parser.add_argument('package');parser.add_argument('--output');parser.add_argument('--accept-proposal');parser.add_argument('--reviewer')
    args=parser.parse_args(argv)
    try:
        if bool(args.accept_proposal)!=bool(args.reviewer):raise ValueError('Acceptance requires both exact proposal hash and reviewer identifier.')
        package=load_package(args.package)
        if args.accept_proposal:package=accept_proposal(package,args.accept_proposal,args.reviewer)
        output=export_package(package)
        if args.output:_write_exclusive_atomic(args.output,output)
        else:sys.stdout.write(output)
        return {'ACCEPT':0,'CORRECT':3,'WITHHOLD':2}[reconcile_package(package)['decision']]
    except (ValueError,TypeError,OSError,RecursionError) as error:
        sys.stderr.write(str(error)+'\n');return 2

if __name__=='__main__':raise SystemExit(main())

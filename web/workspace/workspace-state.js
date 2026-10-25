/** UI state and evidence editing only. Never computes scientific values. */
export const copy=value=>structuredClone(value);
export const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export class WorkspaceState {
 constructor(){this.case=null;this.draft=null;this.result=null;this.last=null;this.generation=0;this.pending=null;this.reviewer='';this.confirmed=false;}
 invalidate(){this.generation++;this.pending=null;this.result=null;this.last=null;this.confirmed=false;if(this.case){this.case.cached_review=null;this.clearActiveResolution();}}
 clearActiveResolution(){
  const resolutions=this.case?.working?.resolutions;
  if(Array.isArray(resolutions)&&resolutions.length){
   this.case.history.push({kind:'invalidated_resolution',revision:this.case.revision,resolutions:copy(resolutions),trust:'HISTORICAL_NOT_CURRENT_APPROVAL'});
   this.case.working.resolutions=[];
  }
 }
 begin(operation){this.confirmed=false;const token={generation:this.generation,operation};this.pending=token;return token;}
 receive(token,message){
  if(!token||this.pending!==token||token.generation!==this.generation)return false;
  this.pending=null;this.case=copy(message.case);this.draft=null;this.result=message.result?copy(message.result):null;this.last=message.result?copy(message):null;this.confirmed=false;
  return true;
 }
 openStarted(){this.invalidate();this.draft=null;}
 reviewerChanged(value){if(value!==this.reviewer){this.reviewer=value;this.invalidate();}}
 beginDraft(){if(!this.case)return;this.invalidate();this.draft=copy(this.case.working);}
 cancelDraft(){this.draft=null;this.invalidate();}
 saveDraft(reason){
  if(!this.draft||typeof reason!=='string'||!reason.trim())throw Error('Explain the source-backed reason for this revision.');
  if(this.case.history.length>=100)throw Error('Case history is full. Prior history will not be removed.');
  if(reason.length>2000)throw Error('Keep the reason within 2000 characters.');
  if(same(this.case.working,this.draft))throw Error('No declaration has changed. Cancel to return to the case.');
  const before=copy(this.case.working),after=copy(this.draft);after.resolutions=[];
  this.case.revision++;
  this.case.history.push({kind:'revision',revision:this.case.revision,reason,changes:diff(before,after),trust:'DECLARED_SOURCE_NOT_AUTHENTICATED'});
  this.case.working=after;this.draft=null;this.invalidate();
 }
 restoreOriginal(reason){this.beginDraft();this.draft=copy(this.case.original.parsed);if(Array.isArray(this.draft.resolutions))this.draft.resolutions=[];this.saveDraft(reason);}
 canAccept(){return !this.draft&&this.result?.decision==='CORRECT'&&typeof this.result.proposal_sha256==='string'&&this.confirmed&&Boolean(this.reviewer.trim());}
}
export function diff(before,after,path=''){
 if(same(before,after))return [];
 if(before&&after&&typeof before==='object'&&typeof after==='object'&&Array.isArray(before)===Array.isArray(after)){
  return [...new Set([...Object.keys(before),...Object.keys(after)])].flatMap(key=>diff(before[key],after[key],`${path}/${key}`));
 }
 return [{path,before:before===undefined?{absent:true}:copy(before),after:after===undefined?{absent:true}:copy(after)}];
}
export const SCOPE_FIELDS=['entity_id','site_id','meter_id','country','period_start','period_end'];
export const RECORD_FIELDS=['record_id','source_id',...SCOPE_FIELDS,'quantity','unit','source_status','source_note','action','target_record_id'];
export const LIMITATIONS=['NOT_AN_INDEPENDENT_VERIFICATION','NOT_BLOCKCHAIN','NOT_MEASURED_SAVINGS','EXCLUDES_SCOPE3_T_AND_D','ANNUAL_AVERAGE_NOT_TIME_OF_USE','ACTIVITY_NOT_VERIFIED','PUBLISHED_FACTOR_INPUT_RECONCILIATION_UNRESOLVED','MARKET_BASED_NOT_COMPUTED','ORGANIZATIONAL_BOUNDARY_NOT_REVIEWED','NOT_FULL_SCOPE2_COMPLIANCE'];
export function blankPackage(){return {schema_version:'gridshift.reconciliation.input.v1',package_id:'',records:[],coverage:[],report:{claim_type:'CONDITIONAL_INVENTORY_ESTIMATE',energy_mwh:'',emissions_tco2e:'',factor_id:'ZA_NGGEF_2024_DFFE_2026',data_year:2024,boundary:'SCOPE2_LOCATION_BASED_PURCHASED_ELECTRICITY',activity_statuses:[],limitations:[...LIMITATIONS]},resolutions:[]};}
export function blankRecord(){return Object.fromEntries(RECORD_FIELDS.map(k=>[k,k==='target_record_id'?null:'']));}
export function blankCoverage(){return Object.fromEntries(SCOPE_FIELDS.map(k=>[k,'']));}
export function evidenceGuide(result){
 if(!result)return {title:'Start with the declared evidence',why:'Run the actual Python review before relying on a finding.',next:'Open a case or enter declarations. Inspect the report, records and explicit coverage. No evidence is inferred.',recordIds:[]};
 const first=result.findings?.[0];
 if(result.decision==='WITHHOLD')return {title:'More evidence is required',why:first?.message||'The policy could not support a result.',next:'Inspect the affected declared sources. Record a revision only when you have source-backed evidence, then rerun. This is the first blocker; further issues may remain.',recordIds:Array.isArray(first?.record_ids)?first.record_ids:[]};
 if(result.decision==='CORRECT')return {title:'Check the exact correction',why:first?.message||'The declared record set supports a correction to the report.',next:'Compare the original report, included/excluded records and proposal. Only you can confirm this exact proposal. The guide cannot edit or approve it.',recordIds:Array.isArray(first?.record_ids)?first.record_ids:[]};
 return {title:result.resolution_accepted?'Your exact confirmation was recorded':'Consistent with this calculation policy',why:result.resolution_accepted?'Python reran and accepted the matching proposal. Reviewer identity remains self-reported.':'No correction is required within the supported policy. This does not imply a human approval.',next:'Download the readable handoff and companion case. The next reviewer must reopen and recompute; imported acceptance is history only.',recordIds:[]};
}

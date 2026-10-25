import {EngineController} from './engine-controller.js';
import LIMITS from './intake-limits.json' with {type:'json'};
import {WorkspaceState,copy,diff,blankPackage,blankRecord,blankCoverage,RECORD_FIELDS,SCOPE_FIELDS,evidenceGuide} from './workspace-state.js';
const $=id=>document.getElementById(id);
const el=(tag,value,cls)=>{const node=document.createElement(tag);if(value!==undefined)node.textContent=String(value??'');if(cls)node.className=cls;return node;};
const state=new WorkspaceState();let engine,pendingToken=null,waitingOpen=null,openSequence=0,loadingFile=false,operationTimer=null,selectedRecord=0,downloadKind=null,creatingCase=false;
const display=value=>typeof value==='string'?value:JSON.stringify(value);
const metric=(label,report)=>{const node=el('div',undefined,'metric result-metric');node.append(el('span',label),el('strong',`${report.emissions_tco2e} tCO₂e`),el('p',`${report.energy_mwh} MWh · conditional inventory estimate`));return node;};
function notice(message,detail=null){$('notice').textContent=message;$('notice-details').hidden=!detail;$('notice-details').open=false;$('notice-trace').textContent=detail||'';}
function buttons(){
 const ready=engine?.state==='ready'&&!loadingFile&&!waitingOpen&&!state.pending;
 const existing=Boolean(state.case),draft=Boolean(state.draft);
 $('run').disabled=!(ready&&existing&&!draft);$('save-draft').disabled=!(ready&&existing&&!draft);
 $('accept').disabled=!(ready&&state.canAccept());
 $('export-case').disabled=$('export-summary').disabled=!(ready&&state.last&&!draft);
 $('revise').disabled=!existing||draft||loadingFile; // Editing can deliberately invalidate an in-flight review.
 $('download-original').disabled=!existing;
 $('retry').hidden=!['failed','suspended'].includes(engine?.state);
 $('confirm').disabled=!ready;
 $('save-revision').disabled=loadingFile;
 const runtimeUp=['ready','checking'].includes(engine?.state);
 for(const id of ['case-file','new-case','example','load-example'])$(id).disabled=!runtimeUp;
 $('case-file').closest?.('label')?.classList.toggle('disabled',!runtimeUp);
}
function clearResult(message='Declarations changed. Rerun before using a result or confirming a correction.'){
 state.result=null;state.last=null;state.confirmed=false;$('confirm').checked=false;$('acceptance').hidden=true;$('result').replaceChildren();$('decision-title').textContent='Not reviewed';$('decision-status').textContent='Rerun required';$('decision-status').dataset.state='stale';$('decision-label').textContent=message;$('proposal-hash').textContent='';renderGuide();if(state.case)renderEvidence();buttons();
}
function changed(message){engine?.invalidate();state.invalidate();clearResult(message);notice(message);renderHistory();}
function showRecord(index,focus=false){
 selectedRecord=index;const record=state.case?.working?.records?.[index];$('record-fields').replaceChildren();
 $('record-title').textContent=record&&typeof record==='object'?`Record ${display(record.record_id)}`:'Record declaration';
 if(record&&typeof record==='object')for(const [key,value] of Object.entries(record)){$('record-fields').append(el('dt',labels[key]||key),el('dd',display(value)));}
 else $('record-fields').append(el('dd',display(record)));
 const original=state.case?.original?.parsed?.records;
 const matches=Array.isArray(original)?original.filter(r=>r&&typeof r==='object'&&r.record_id===record?.record_id):[];
 $('record-original').textContent=matches.length?JSON.stringify(matches,null,2):'No preserved original with this record identifier. See full original package for the unchanged evidence.';
 document.querySelectorAll('#records button').forEach((node,i)=>node.setAttribute('aria-pressed',String(i===index)));
 if(focus)$('record-detail').focus({preventScroll:false});
}
function renderEvidence(){
 const c=state.case;if(!c)return;
 $('empty').hidden=true;$('case-workspace').hidden=false;
 const pkg=c.working,original=c.original.parsed;
 $('case-title').textContent=typeof pkg.package_id==='string'&&pkg.package_id?pkg.package_id:'Untitled declared package';
 const statuses=Array.isArray(pkg.records)?[...new Set(pkg.records.map(r=>r?.source_status).filter(x=>typeof x==='string'))]:[];
 $('case-kind').textContent=statuses.length&&statuses.every(x=>x==='SYNTHETIC')?'INVENTED / SYNTHETIC EVIDENCE':statuses.includes('SYNTHETIC')?'MIXED DECLARED SOURCE STATUSES':'DECLARED / UNVERIFIED EVIDENCE';
 $('revision-label').textContent=`Revision ${c.revision}${state.draft?' · unsaved draft':''}`;
 $('original-energy').textContent=`${display(original.report?.energy_mwh)??'Not supplied'} MWh`;
 $('original-emissions').textContent=`${display(original.report?.emissions_tco2e)??'Not supplied'} tCO₂e`;
 $('working-report').textContent=`Working report: ${display(pkg.report?.energy_mwh)??'not supplied'} MWh / ${display(pkg.report?.emissions_tco2e)??'not supplied'} tCO₂e. Source statuses: ${statuses.join(', ')||'not supplied'}.`;
 $('original-hash').textContent=c.original.raw_sha256;$('original-json').textContent=JSON.stringify(original,null,2);
 $('records').replaceChildren();
 if(Array.isArray(pkg.records))pkg.records.forEach((record,index)=>{
  const row=el('tr'),cell=el('td'),button=el('button',record?.record_id??`Record ${index+1}`,'record-button');button.type='button';button.addEventListener('click',()=>showRecord(index,true));cell.append(button);row.append(cell);
  const trace=state.result?.trace?.find(t=>t.record_id===record?.record_id);
  const use=trace?(trace.included?'Included':state.result.excluded_record_ids?.includes(trace.record_id)?'Excluded, retained':'Unresolved'):'Not established';
  const originalRecord=Array.isArray(original.records)?original.records.find(r=>r?.record_id===record?.record_id):null;
  row.append(el('td',originalRecord?`${display(originalRecord.quantity)} ${display(originalRecord.unit)}`:'No matching original ID'),el('td',`${display(record?.quantity)??'missing'} ${display(record?.unit)??''}`),el('td',`${display(record?.action)??'missing'}${record?.target_record_id!==null&&record?.target_record_id!==undefined?` → ${display(record.target_record_id)}`:''}`),el('td',use));$('records').append(row);
 });
 if(!Array.isArray(pkg.records)||!pkg.records.length){const tr=el('tr'),td=el('td','No source records supplied. Use “Record a revision” to add explicit source declarations.');td.colSpan=5;tr.append(td);$('records').append(tr);}
 showRecord(Math.min(selectedRecord,Math.max(0,(pkg.records?.length||1)-1)));
 $('coverage').replaceChildren();
 if(Array.isArray(pkg.coverage))for(const row of pkg.coverage){const dl=el('dl',undefined,'coverage-row');if(row&&typeof row==='object')for(const key of SCOPE_FIELDS)dl.append(el('dt',labels[key]),el('dd',display(row[key])??'Not supplied'));else dl.append(el('dd',display(row)));$('coverage').append(dl);}
 renderHistory();buttons();
}
function renderHistory(){
 const entries=state.case?.history||[];$('history-count').textContent=`(${entries.length})`;$('history-list').replaceChildren();
 for(const item of entries){const d=el('details',undefined,'history-entry');d.append(el('summary',`${item.kind||'Imported history'} · revision ${item.revision??'not stated'}`),el('pre',JSON.stringify(item,null,2)));$('history-list').append(d);}
}
function renderGuide(){
 const guide=evidenceGuide(state.result);$('guide-title').textContent=guide.title;$('guide-why').textContent=guide.why;$('guide-next').textContent=guide.next;$('guide-links').replaceChildren();
 for(const id of guide.recordIds){const index=Array.isArray(state.case?.working.records)?state.case.working.records.findIndex(r=>r?.record_id===id):-1;if(index<0)continue;const b=el('button',`Show source ${id}`,'quiet');b.type='button';b.addEventListener('click',()=>showRecord(index,true));$('guide-links').append(b);}
}
function renderResult(message){
 const r=message.result;if(!r){clearResult(message.notice||'Run a fresh Python review.');return;}
 $('result').replaceChildren();$('confirm').checked=false;state.confirmed=false;
 const accepted=r.resolution_accepted===true;
 $('decision-title').textContent=r.decision==='WITHHOLD'?'More evidence required':r.decision==='CORRECT'?'Correction proposed':accepted?'Exact correction accepted':'Consistent with the policy';
 $('decision-status').dataset.state=r.decision==='WITHHOLD'?'withheld':r.decision==='CORRECT'?'proposed':'accepted';
 $('decision-status').textContent=r.decision==='WITHHOLD'?'Withheld':r.decision==='CORRECT'?'Not yet accepted':accepted?'Reviewer confirmation recorded':'Not a human approval';
 $('decision-label').textContent=accepted?'Python reran and confirmed the matching proposal. Reviewer identity is self-reported, not authenticated.':r.decision==='ACCEPT'?'This package is consistent with the supported calculation policy. That is not independent assurance or an authenticated reviewer approval.':r.decision==='WITHHOLD'?'No accepted or proposed total. The engine reports its first blocker; other issues may remain.':'Check the supported record set and exact proposal before intentionally accepting a correction.';
 if(r.decision!=='WITHHOLD'){const report=r.accepted_report||r.proposed_report;if(report)$('result').append(metric(r.accepted_report?'SUPPORTED WITHIN CALCULATION POLICY':'PROPOSED — ACCEPTANCE REQUIRED',report));}
 if(r.discrepancy)$('result').append(el('p',`Absolute report difference: ${r.discrepancy.absolute_emissions_tco2e} tCO₂e. This is a report correction, not emissions saved. Prototype triage threshold: ${r.discrepancy.materiality_threshold_tco2e} tCO₂e; not an audit standard.`,'source-caption'));
 const findings=el('ul',undefined,'findings');for(const f of r.findings||[]){const li=el('li');li.append(el('strong',f.code),el('p',f.message));if(f.record_ids?.length)li.append(el('p',`Affected records: ${f.record_ids.join(', ')}`));findings.append(li);}if(findings.children.length){$('result').append(el('h3','What needs checking'),findings);}
 if(r.required_evidence?.length){$('result').append(el('h3','What evidence is missing?'));for(const evidence of r.required_evidence)$('result').append(el('p',typeof evidence==='string'?evidence:JSON.stringify(evidence)));}
 if(r.trace?.length){$('result').append(el('h3','Why each record is used'));for(const trace of r.trace){const row=el('div',undefined,'trace-row');row.append(el('strong',`${trace.record_id} · ${trace.included?'included':'excluded, retained'}`),el('span',`${trace.action}${trace.target_record_id?` → ${trace.target_record_id}`:''}`),el('span',trace.reason),el('small',`${trace.source_id} · ${trace.source_status}`));$('result').append(row);}}
 const details=el('details',undefined,'advanced');details.append(el('summary','Exact Python result and all limitations'),el('pre',JSON.stringify(r,null,2)));$('result').append(details);
 $('acceptance').hidden=r.decision!=='CORRECT';$('proposal-hash').textContent=r.proposal_sha256||'';
 const proposed=r.proposed_report;$('proposal-description').textContent=proposed?`Proposed report: ${proposed.energy_mwh} MWh / ${proposed.emissions_tco2e} tCO₂e. Included: ${(r.included_record_ids||[]).join(', ')}. Excluded, not deleted: ${(r.excluded_record_ids||[]).join(', ')||'none'}.`:'';
 renderEvidence();renderGuide();buttons();
}
function dispatch(request){
 if(engine.state!=='ready')return false;
 pendingToken=state.begin(request.operation);const started=engine.review(request);
 if(!started){state.pending=null;pendingToken=null;buttons();return false;}
 clearTimeout(operationTimer);operationTimer=setTimeout(()=>{if(engine.state==='checking'){state.generation++;state.pending=null;pendingToken=null;engine.suspend();clearResult('The worker did not respond in time. Retry the runtime and rerun.');notice('No result or acceptance was recorded for the interrupted request. Your case remains in memory.');buttons();}},90000);
 buttons();return true;
}
function flushOpen(){if(waitingOpen&&engine.state==='ready'){const raw=waitingOpen;waitingOpen=null;dispatch({operation:'open',raw});}}
async function openBytes(bytes,sequence){
 if(sequence!==openSequence)return;
 loadingFile=false;state.generation++;state.pending=null;pendingToken=null;engine.invalidate();state.confirmed=false;$('confirm').checked=false;
 waitingOpen=bytes;notice('Validating original raw bytes with the strict Python loader. The existing case stays intact if intake fails.');buttons();flushOpen();
}
function beginIntake(){
 waitingOpen=null;loadingFile=true;engine.invalidate();state.invalidate();pendingToken=null;clearResult('Opening another case. Previous evidence remains visible, but its review and approval are invalidated.');notice('Reading a new case. Earlier responses are ignored immediately; the preserved evidence remains until strict intake succeeds.');renderHistory();buttons();
}
async function readFile(file){
 const sequence=++openSequence;if(!file)return;beginIntake();if(file.size===0||file.size>LIMITS.envelope_limit_bytes){loadingFile=false;notice(LIMITS.open_size_message+' Raw input packages are limited to 64 KiB. Previous evidence is intact; rerun its review before use.');buttons();return;}
try{await openBytes(new Uint8Array(await file.arrayBuffer()),sequence);}catch(error){if(sequence===openSequence){loadingFile=false;notice(String(error.message));buttons();}}
}
function download(content,name,type){const url=URL.createObjectURL(new Blob([content],{type})),a=el('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function safeName(){return (state.case?.working.package_id||'case').replace(/[^a-zA-Z0-9_-]/g,'_').slice(0,80)||'case';}
function received(message){
 clearTimeout(operationTimer);const token=pendingToken;pendingToken=null;
 if(!state.receive(token,message))return;
 if(message.operation==='open'){
  selectedRecord=0;$('revision-editor').hidden=true;renderEvidence();clearResult(message.notice);notice(message.notice);
  if(message.case.working.package_id===''){creatingCase=true;startDraft();$('revision-title').textContent='Enter the original report and declarations';$('save-revision').textContent='Create original case';$('revision-reason').required=false;notice('Enter your original declarations. Nothing here is approved; the original is established only when you choose Create original case.');}else creatingCase=false;
 }else if(message.operation==='save'){
  clearResult('An unreviewed draft was saved. Rerun before relying on a decision.');download(message.export_json,`${safeName()}-draft.json`,'application/json');notice('Unreviewed draft downloaded. Reopen will validate the original and require a fresh review.');
 }else{
  renderResult(message);notice(message.operation==='accept'?'Exact proposal acceptance confirmed by the Python rerun. Originals are unchanged.':message.result.decision==='WITHHOLD'?'Review withheld. Supply the specific missing evidence; no total has been invented.':'Python review complete. Inspect the decision and declared evidence.');
  if(message.operation==='export'){
   if(downloadKind==='summary')download(message.summary,`${safeName()}-review.txt`,'text/plain;charset=utf-8');
   else download(message.export_json,`${safeName()}-review.case.json`,'application/json');
   notice('Current evidence recomputed and downloaded. For a complete handoff, download both the case and readable summary.');
  }
 }
 downloadKind=null;buttons();if(message.operation==='review'||message.operation==='accept')$('decision-title').focus({preventScroll:false});
}
const LOADING_NOTICE='Getting the calculator ready. Opening a case unlocks in a moment.',READY_NOTICE='Open a declared case, or enter the original report and evidence using guided fields.';
const RUNTIME_LABELS={loading:'Loading calculator…',ready:'Ready',checking:'Checking',failed:'Not available',suspended:'Paused'};
function runtime(next){
 // Plain status chip. Open actions stay disabled until the pinned runtime is ready.
 $('runtime').textContent=RUNTIME_LABELS[next]||next;$('runtime').dataset.state=next;
 if(next==='ready'&&$('notice').textContent===LOADING_NOTICE)notice(READY_NOTICE);
 if(next==='ready'){clearTimeout(operationTimer);queueMicrotask(flushOpen);}buttons();
}
function failure({phase,message,detail=null}){
 clearTimeout(operationTimer);const opening=pendingToken?.operation==='open';state.pending=null;pendingToken=null;downloadKind=null;
 if(!opening){state.invalidate();clearResult('No current result. Retry or rerun before relying on this case.');}
 notice(`${opening?'Case was not opened; the previous case is intact, but rerun is required. ':''}${message}`,detail);buttons();
}
const labels={package_id:'Case identifier',record_id:'Record identifier',source_id:'Source identifier',entity_id:'Entity identifier',site_id:'Site identifier',meter_id:'Meter identifier',country:'Country code',period_start:'Period starts (YYYY-MM-DD)',period_end:'Period ends, exclusive (YYYY-MM-DD)',quantity:'Exact quantity (decimal text)',unit:'Unit',source_status:'Declared source status',source_note:'Source note or document reference',action:'Declared relationship',target_record_id:'Explicit target record identifier',energy_mwh:'Reported energy (MWh, decimal text)',emissions_tco2e:'Reported emissions (tCO₂e, decimal text)',claim_type:'Report claim',factor_id:'Factor identifier',data_year:'Data year (integer)',boundary:'Accounting boundary',activity_statuses:'All declared activity statuses',limitations:'All report limitations'};
const choiceLabels={SYNTHETIC:'Invented / synthetic evidence',UNVERIFIED_USER_INPUT:'Unverified source declaration',ORIGINAL:'Original record (no target)',FULL_REPLACEMENT:'Fully replaces another record',FULL_VOID:'Fully voids an original record',ZA:'South Africa (ZA)',MWh:'Megawatt-hours (MWh)',kWh:'Kilowatt-hours (kWh)'};
const options={unit:['','MWh','kWh'],country:['','ZA'],source_status:['','SYNTHETIC','UNVERIFIED_USER_INPUT'],action:['','ORIGINAL','FULL_REPLACEMENT','FULL_VOID']};
function field(parent,obj,key,prefix,{readonly=false,kind='text'}={}){
 const wrapper=el('div',undefined,'field'),id=`${prefix}-${key}`;wrapper.append(el('label',labels[key]||key));wrapper.firstChild.htmlFor=id;
 const current=obj?.[key];let input;
 if(options[key]&&!readonly){input=el('select');for(const value of [...new Set([...options[key],...(typeof current==='string'&&!options[key].includes(current)?[current]:[])])]){const opt=el('option',choiceLabels[value]||value||'Choose explicitly');opt.value=value;input.append(opt);}}
 else input=el(key==='source_note'||kind==='lines'?'textarea':'input');
 input.id=id;input.name=id;if(input.tagName==='INPUT')input.type='text';if(input.tagName==='TEXTAREA')input.rows=3;
 input.value=kind==='lines'&&Array.isArray(current)?current.join('\n'):current===null?'':typeof current==='string'||typeof current==='number'?String(current):current===undefined?'':JSON.stringify(current);
 if(readonly)input.readOnly=true;else if(input.tagName!=='SELECT')input.maxLength=kind==='lines'?200000:2000;
 if(key==='quantity'||key==='energy_mwh'||key==='emissions_tco2e')input.inputMode='decimal';
 if(!readonly)input.addEventListener('input',()=>{obj[key]=kind==='lines'?input.value.split('\n'):key==='target_record_id'&&input.value===''?null:key==='data_year'&&/^\d+$/.test(input.value)?Number(input.value):input.value;renderDraftDiff();});
 wrapper.append(input);if(kind==='lines')wrapper.append(el('small','One exact value per line. Preserve all original statuses and limitations; do not remove material declarations.'));
 if(current!==undefined&&current!==null&&typeof current!=='string'&&key!=='data_year'&&kind!=='lines')wrapper.append(el('small','Original field has an unsupported type. It is preserved unless you explicitly edit it.'));
 if(key==='target_record_id')wrapper.append(el('small','Blank means no target (null). Only originals have no target; never guess a link.'));
 if(key==='source_status')wrapper.append(el('small','Unverified user input is not authenticated. Keep synthetic labels on invented evidence.'));
 parent.append(wrapper);
}
function renderDraft(){
 const p=state.draft;if(!p)return;
 $('package-fields').replaceChildren();field($('package-fields'),p,'package_id','package');
 $('report-fields').replaceChildren();if(p.report&&typeof p.report==='object'&&!Array.isArray(p.report)){
  for(const key of ['energy_mwh','emissions_tco2e'])field($('report-fields'),p.report,key,'report');
  const statuses=el('fieldset',undefined,'field');statuses.append(el('legend','Which kinds of evidence does the report declare?'));
  for(const status of ['SYNTHETIC','UNVERIFIED_USER_INPUT']){const label=el('label',undefined,'check-label'),check=el('input');check.type='checkbox';check.id=`report-status-${status}`;check.checked=Array.isArray(p.report.activity_statuses)&&p.report.activity_statuses.includes(status);check.addEventListener('change',()=>{if(!Array.isArray(p.report.activity_statuses))return;const other=p.report.activity_statuses.filter(x=>x!==status);p.report.activity_statuses=check.checked?[...other,status]:other;renderDraftDiff();});check.disabled=!Array.isArray(p.report.activity_statuses);label.append(check,el('span',choiceLabels[status]));statuses.append(label);}
  statuses.append(el('small','Select every status declared by the original and replacement records. This is explicit, not inferred. Unsupported imported statuses stay preserved.'));$('report-fields').append(statuses);
  const metadata=el('details',undefined,'advanced');metadata.append(el('summary','Supported policy metadata and retained report limitations'));const fields=el('div',undefined,'field-grid');
  for(const key of ['claim_type','factor_id','data_year','boundary'])field(fields,p.report,key,'report',{readonly:true});
  for(const key of ['activity_statuses','limitations'])field(fields,p.report,key,'report',{kind:'lines',readonly:true});metadata.append(fields,el('p','Imported metadata is preserved, including unsupported values. Do not relabel a different year, claim or boundary to obtain acceptance.'));$('report-fields').append(metadata);
 }else $('report-fields').append(el('p','Report is not a supported object. Original evidence is retained; obtain a supported source-backed representation.'));
 $('record-editors').replaceChildren();if(Array.isArray(p.records))p.records.forEach((record,index)=>{const group=el('fieldset',undefined,'revision-row');group.append(el('legend',`Record ${index+1}: ${record?.record_id||'new declaration'}`));const grid=el('div',undefined,'field-grid');if(record&&typeof record==='object'&&!Array.isArray(record))for(const key of RECORD_FIELDS)field(grid,record,key,`record-${index}`);else grid.append(el('p','Unsupported record type preserved. Obtain a supported source-backed input rather than deleting material evidence.'));group.append(grid);$('record-editors').append(group);});
 $('coverage-editors').replaceChildren();if(Array.isArray(p.coverage))p.coverage.forEach((row,index)=>{const group=el('fieldset',undefined,'revision-row');group.append(el('legend',`Coverage declaration ${index+1}`));const grid=el('div',undefined,'field-grid');if(row&&typeof row==='object'&&!Array.isArray(row))for(const key of SCOPE_FIELDS)field(grid,row,key,`coverage-${index}`);else grid.append(el('p','Unsupported coverage type preserved.'));group.append(grid);$('coverage-editors').append(group);});
 $('add-record').disabled=!Array.isArray(p.records)||p.records.length>=1000;$('add-coverage').disabled=!Array.isArray(p.coverage)||p.coverage.length>=1000;renderDraftDiff();
}
function renderDraftDiff(){
 if(!state.draft)return;$('working-json').textContent=JSON.stringify(state.draft,null,2);$('draft-diff').replaceChildren();
 const changes=diff(state.case.working,state.draft);if(!changes.length)$('draft-diff').append(el('p','No declaration changed yet.'));
 for(const change of changes){const row=el('div',undefined,'diff-row');row.append(el('strong',change.path),el('span',`Before: ${display(change.before)}`),el('span',`After: ${display(change.after)}`));$('draft-diff').append(row);}
}
function startDraft(){
 if(!state.case||state.draft)return;engine.invalidate();state.beginDraft();clearResult('Working draft open. Earlier result and approval eligibility have been cleared.');$('revision-editor').hidden=false;$('revision-title').textContent='Record what the evidence supports';$('save-revision').textContent='Save revision · rerun required';$('revision-reason').required=true;$('revision-reason').value='';renderDraft();renderEvidence();$('revision-title').focus({preventScroll:false});notice('Original evidence is preserved. Save a source-backed revision, then rerun.');buttons();
}
engine=new EngineController({workerFactory:()=>new Worker(new URL('./workspace-worker.js',import.meta.url),{type:'module'}),onState:runtime,onResult:received,onError:failure});
$('case-file').addEventListener('change',()=>{const file=$('case-file').files?.[0];if(file)readFile(file);$('case-file').value='';});
$('load-example').addEventListener('click',async()=>{const sequence=++openSequence;beginIntake();try{const name=$('example').value;if(!['missing-edge','flagship'].includes(name))throw Error('Unknown example.');const response=await fetch(`../reconcile/${name}.json`,{cache:'no-store'});if(!response.ok)throw Error('Invented example could not be loaded.');await openBytes(new Uint8Array(await response.arrayBuffer()),sequence);}catch(error){if(sequence===openSequence){loadingFile=false;notice(String(error.message));buttons();}}});
$('new-case').addEventListener('click',()=>{const sequence=++openSequence;beginIntake();openBytes(new TextEncoder().encode(JSON.stringify(blankPackage())),sequence);});
$('run').addEventListener('click',()=>{if($('run').disabled)return;const c=copy(state.case);clearResult('Waiting for the actual Python result.');dispatch({operation:'review',case:c});});
$('reviewer').addEventListener('input',()=>{state.reviewerChanged($('reviewer').value);engine.invalidate();clearResult('Reviewer identifier changed. Rerun before accepting this exact correction.');notice('Reviewer changed. Previous approval eligibility is cleared; rerun to obtain a current proposal.');renderHistory();});
$('confirm').addEventListener('change',()=>{state.confirmed=$('confirm').checked;buttons();});
$('accept').addEventListener('click',()=>{if($('accept').disabled)return;const request={operation:'accept',case:copy(state.case),proposal_sha256:state.result.proposal_sha256,reviewer_id:state.reviewer.trim()};clearResult('Recording your exact confirmation and rerunning Python. Nothing is accepted until its matching result returns.');dispatch(request);});
$('save-draft').addEventListener('click',()=>{if(!$('save-draft').disabled)dispatch({operation:'save',case:copy(state.case)});});
for(const [id,kind] of [['export-case','case'],['export-summary','summary']])$(id).addEventListener('click',()=>{if($(id).disabled)return;downloadKind=kind;dispatch({operation:'export',case:copy(state.case)});});
$('download-original').addEventListener('click',()=>{if(!state.case)return;const binary=atob(state.case.original.raw_base64),bytes=Uint8Array.from(binary,x=>x.charCodeAt(0));download(bytes,`${safeName()}-original.json`,'application/json');});
$('revise').addEventListener('click',startDraft);
$('cancel-revision').addEventListener('click',()=>{state.cancelDraft();$('revision-editor').hidden=true;clearResult('Draft cancelled. Working declarations retained; rerun before relying on a decision.');renderEvidence();notice('Draft discarded, original and saved revisions preserved. Rerun required.');$('revise').focus();});
$('add-record').addEventListener('click',()=>{if(!state.draft||$('add-record').disabled)return;state.draft.records.push(blankRecord());renderDraft();$(`record-${state.draft.records.length-1}-record_id`).focus();});
$('add-coverage').addEventListener('click',()=>{if(!state.draft||$('add-coverage').disabled)return;state.draft.coverage.push(blankCoverage());renderDraft();$(`coverage-${state.draft.coverage.length-1}-entity_id`).focus();});
$('restore-original').addEventListener('click',()=>{if(!state.draft)return;state.draft=copy(state.case.original.parsed);if(Array.isArray(state.draft.resolutions))state.draft.resolutions=[];renderDraft();notice('Draft now contains original declarations. Supply a reason and save to retain this return in history, or cancel.');});
$('revision-form').addEventListener('submit',event=>{event.preventDefault();try{if(creatingCase){if(!state.draft.package_id)throw Error('Supply a case identifier before creating the original.');const raw=new TextEncoder().encode(JSON.stringify(state.draft,null,2));if(raw.length>64*1024)throw Error('Original package exceeds 64 KiB; no original was created.');creatingCase=false;openBytes(raw,++openSequence);return;}state.saveDraft($('revision-reason').value);$('revision-editor').hidden=true;clearResult('Revision saved. Rerun required; no approval carries over.');renderEvidence();notice('Source-backed revision saved separately from the original. Review the new package.');$('run').focus();}catch(error){notice(String(error.message));}});
$('retry').addEventListener('click',()=>{state.invalidate();state.pending=null;pendingToken=null;clearResult('Retrying the runtime. Rerun required.');engine.start();});
window.addEventListener('pagehide',()=>{clearTimeout(operationTimer);state.invalidate();state.pending=null;pendingToken=null;engine.suspend();});
window.addEventListener('pageshow',event=>{if(event.persisted){clearResult('Returned to this tab. Rerun required; no prior approval is current.');engine.start();}});
renderGuide();engine.start();

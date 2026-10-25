/** Development DOM/event simulation backed by the real native Python adapter.
 * NOT a browser, Pyodide/WASM, visual, accessibility or independent-user test. */
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFile} from 'node:child_process';
const ids=new Map(),downloads=[],windowEvents=new Map();let focus=null;
const realSetTimeout=globalThis.setTimeout,realClearTimeout=globalThis.clearTimeout,longTimers=new Map();
globalThis.setTimeout=(fn,ms,...args)=>{const id=realSetTimeout(fn,ms,...args);if(ms===90000)longTimers.set(id,fn);return id;};
globalThis.clearTimeout=id=>{longTimers.delete(id);realClearTimeout(id);};
let holdNextReview=false,heldReview=null;
class Element {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.events=new Map();this.attributes={};this.dataset={};this.hidden=false;this.disabled=false;this.checked=false;this.value='';this._text='';this.parentNode=null;}
 set id(value){this._id=value;ids.set(value,this);}get id(){return this._id;}
 get firstChild(){return this.children[0];}get firstElementChild(){return this.children[0];}
 set textContent(value){this._text=String(value??'');this.children=[];}get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
 append(...nodes){for(let node of nodes){if(typeof node==='string'){const text=new Element('span');text.textContent=node;node=text;}node.parentNode=this;this.children.push(node);}}
 replaceChildren(...nodes){this.children=[];this._text='';this.append(...nodes);}
 setAttribute(key,value){this.attributes[key]=String(value);}getAttribute(key){return this.attributes[key];}
 addEventListener(type,fn){const list=this.events.get(type)||[];list.push(fn);this.events.set(type,list);}
 removeEventListener(type,fn){this.events.set(type,(this.events.get(type)||[]).filter(x=>x!==fn));}
 async emit(type,event={}){for(const fn of this.events.get(type)||[])await fn({target:this,preventDefault(){},...event});}
 click(){if(this.disabled)return;if(this.tagName==='A'){downloads.push({name:this.download,blob:blobs.get(this.href)});return;}return this.emit('click');}
 focus(){focus=this.id;}remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(x=>x!==this);}
}
const html=await readFile(new URL('../web/workspace/index.html',import.meta.url),'utf8');
for(const match of html.matchAll(/<([a-z][a-z0-9-]*)\b([^>]*?)\bid="([^"]+)"([^>]*?)>/g)){const node=new Element(match[1]);node.id=match[3];node.hidden=/\bhidden\b/.test(match[2]+match[4]);node.disabled=/\bdisabled\b/.test(match[2]+match[4]);}
const body=new Element('body');globalThis.document={body,getElementById:id=>ids.get(id),createElement:tag=>new Element(tag),querySelectorAll:query=>{assert.equal(query,'#records button');const result=[];const walk=node=>{if(node.tagName==='BUTTON')result.push(node);for(const child of node.children)walk(child);};walk(ids.get('records'));return result;}};
globalThis.window={addEventListener:(type,fn)=>windowEvents.set(type,fn)};
const blobs=new Map();let blobId=0;URL.createObjectURL=blob=>{const key=`blob:test-${++blobId}`;blobs.set(key,blob);return key;};URL.revokeObjectURL=()=>{};
import {publicError} from '../web/workspace/engine-controller.js';
// Native errors are wrapped the way Pyodide reports them, then structured by the real shared publicError.
const pyodideTrace=message=>`Traceback (most recent call last):\n  File "/lib/python314.zip/_pyodide/_base.py", line 597, in eval_code_async\n  File "/gridshift/src/case_adapter.py", line 24, in _require\n    raise ValueError(message)\nValueError: ${message}\n`;
let workerCount=0;
class NativeWorker {
 constructor(){this.events=new Map();this.terminated=false;workerCount++;}
 addEventListener(type,fn){this.events.set(type,fn);}removeEventListener(type){this.events.delete(type);}terminate(){this.terminated=true;}
 postMessage(message){
  if(message.type==='init'){queueMicrotask(()=>this.send({id:message.id,type:'ready'}));return;}
  if(holdNextReview){holdNextReview=false;heldReview={worker:this,message};return;}
  let request=message.activities;if(request.operation==='open')request={operation:'open',raw_base64:Buffer.from(request.raw).toString('base64')};
  const child=execFile('python',[new URL('./workspace-native-driver.py',import.meta.url).pathname],{maxBuffer:4*1024*1024},(error,stdout)=>{if(error){this.send({id:message.id,type:'error',message:String(error)});return;}const result=JSON.parse(stdout);this.send(result.ok?{id:message.id,type:'result',...result.value}:{id:message.id,type:'error',...publicError(pyodideTrace(result.message),request.operation)});});child.stdin.end(JSON.stringify(request));
 }
 send(data){if(!this.terminated)this.events.get('message')?.({data});}
}
globalThis.Worker=NativeWorker;
const $=id=>{const node=ids.get(id);assert.ok(node,`Missing element ${id}`);return node;};
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
async function until(fn,label){for(let i=0;i<500;i++){if(fn())return;await tick();}throw Error(`Timed out: ${label}; notice=${$('notice').textContent}`);}
async function input(id,value){$(id).value=value;await $(id).emit('input');}
async function open(raw){$('case-file').files=[{size:raw.length,arrayBuffer:async()=>Uint8Array.from(raw).buffer}];await $('case-file').emit('change');await until(()=>$('runtime').textContent==='Ready'&&!$('run').disabled,'open');}
for(const id of ['case-file','new-case','example','load-example'])assert.equal($(id).disabled,true,`${id} disabled in markup before runtime`);{const html=await readFile(new URL('../web/workspace/index.html',import.meta.url),'utf8');for(const id of ['notice','runtime'])$(id).textContent=html.match(new RegExp(`id="${id}"[^>]*>([^<]*)<`))[1];}assert.equal($('notice').textContent,'Getting the calculator ready. Opening a case unlocks in a moment.');assert.equal($('runtime').textContent,'Loading calculator…');
await import('../web/workspace/workspace.js');await until(()=>$('runtime').textContent==='Ready','init');for(const id of ['case-file','new-case','example','load-example'])assert.equal($(id).disabled,false,`${id} enabled once Ready`);assert.equal($('runtime').dataset.state,'ready');assert.equal($('notice').textContent,'Open a declared case, or enter the original report and evidence using guided fields.');
const p=JSON.parse(await readFile(new URL('../web/reconcile/flagship.json',import.meta.url),'utf8'));
p.package_id='DEVELOPMENT-UNFAMILIAR-IDS';p.records[0].record_id='invoice-z';p.records[0].source_id='statement-z';p.records[0].quantity='12.50';p.records[1].record_id='amendment-q';p.records[1].source_id='statement-q';p.records[1].quantity='11.75';p.records[1].action='ORIGINAL';p.records[1].target_record_id=null;p.records[2].record_id='meter-t';p.records[2].quantity='2.50';p.report.energy_mwh='27';p.report.emissions_tco2e='25.92';
const raw=Buffer.from(JSON.stringify(p,null,2));await open(raw);assert.equal($('case-title').textContent,p.package_id);assert.equal($('original-energy').textContent,'27 MWh');
await $('run').click();await until(()=>$('decision-title').textContent==='More evidence required','refusal');assert.equal($('result').textContent.includes('PROPOSED —'),false);
await $('revise').click();assert.equal(focus,'revision-title');assert.equal($('run').disabled,true);
await input('record-1-action','FULL_REPLACEMENT');await input('record-1-target_record_id','invoice-z');await input('revision-reason','Development document Q explicitly replaces invoice Z for its full period.');await $('revision-form').emit('submit');assert.equal($('original-energy').textContent,'27 MWh');
await input('reviewer','Development reviewer');await $('run').click();await until(()=>$('decision-title').textContent==='Correction proposed','proposed');assert.ok($('result').textContent.includes('13.68 tCO₂e'));assert.equal(focus,'decision-title');
$('confirm').checked=true;await $('confirm').emit('change');assert.equal($('accept').disabled,false);await $('accept').click();assert.equal($('export-case').disabled,true);await until(()=>$('decision-title').textContent==='Exact correction accepted','accept');
await $('export-case').click();await until(()=>downloads.some(x=>x.name.endsWith('.case.json')),'case export');const exported=downloads.find(x=>x.name.endsWith('.case.json'));const json=await exported.blob.text(),bundle=JSON.parse(json);assert.equal(Buffer.from(bundle.original.raw_base64,'base64').toString(),raw.toString());assert.equal(bundle.original.parsed.records[1].action,'ORIGINAL');assert.equal(bundle.working.records[1].action,'FULL_REPLACEMENT');assert.equal(bundle.cached_review.resolution_accepted,true);
await $('export-summary').click();await until(()=>downloads.some(x=>x.name.endsWith('.txt')),'summary export');assert.ok((await downloads.find(x=>x.name.endsWith('.txt')).blob.text()).includes('REVIEWER ACCEPTED THIS EXACT CORRECTION'));
await open(Buffer.from(json));assert.equal($('decision-title').textContent,'Not reviewed');await $('run').click();await until(()=>$('decision-title').textContent==='Correction proposed','reopen reconfirmation');assert.equal($('confirm').checked,false);
const before=$('case-title').textContent;await open(Buffer.from('{"x":1,"x":2}'));assert.equal($('case-title').textContent,before);assert.ok($('notice').textContent.includes('previous case is intact'));assert.equal($('records').textContent.includes('Included'),false,'Invalidated intake must clear the derived inclusion ledger');
// Regression: refusal notice is user-facing only; any traceback lives in the collapsed Technical details.
{const floatYear=JSON.stringify(p,null,2).replace(/"data_year": 2024\b/,'"data_year": 2024.0');assert.notEqual(floatYear,JSON.stringify(p,null,2),'fixture must contain data_year 2024');
const kept=$('case-title').textContent;await open(Buffer.from(floatYear));assert.equal($('case-title').textContent,kept);
assert.equal($('notice').textContent.includes('Traceback'),false,`notice leaked a traceback: ${$('notice').textContent}`);assert.equal($('notice').textContent.includes('File "'),false);
assert.match($('notice').textContent,/^Case was not opened; the previous case is intact, but rerun is required\. data_year at \$\.report\.data_year .*JSON integer 2024/);
assert.equal($('notice-details').hidden,false);assert.equal($('notice-details').open,false);assert.match($('notice-trace').textContent,/^Traceback \(most recent call last\):/);
}

await $('revise').click();await input('record-1-quantity','11.00');await $('cancel-revision').click();assert.equal($('decision-title').textContent,'Not reviewed');assert.equal($('revision-editor').hidden,true);
// An interrupted review must not leave the new revision permanently busy.
await $('run').click();await $('revise').click();await input('record-1-quantity','11.25');await input('revision-reason','Later development source statement');await $('revision-form').emit('submit');await until(()=>!$('run').disabled,'edit during pending review');assert.equal($('decision-title').textContent,'Not reviewed');
// Guided entry establishes user-entered declarations as the preserved original, not an empty template.
await $('new-case').click();await until(()=>!$('revision-editor').hidden&&$('save-revision').textContent==='Create original case','new case');
await input('package-package_id','GUIDED-ORIGINAL');await input('report-energy_mwh','5.00');await input('report-emissions_tco2e','4.80');
$('report-status-UNVERIFIED_USER_INPUT').checked=true;await $('report-status-UNVERIFIED_USER_INPUT').emit('change');await $('add-record').click();
for(const [key,value] of Object.entries({record_id:'new-record',source_id:'new-source',entity_id:'entity-new',site_id:'site-new',meter_id:'meter-new',country:'ZA',period_start:'2024-01-01',period_end:'2025-01-01',quantity:'5.00',unit:'MWh',source_status:'UNVERIFIED_USER_INPUT',source_note:'User-entered development declaration',action:'ORIGINAL'}))await input(`record-0-${key}`,value);
await $('add-coverage').click();for(const [key,value] of Object.entries({entity_id:'entity-new',site_id:'site-new',meter_id:'meter-new',country:'ZA',period_start:'2024-01-01',period_end:'2025-01-01'}))await input(`coverage-0-${key}`,value);
await $('revision-form').emit('submit');await until(()=>!$('run').disabled&&$('case-title').textContent==='GUIDED-ORIGINAL','original creation');assert.equal($('original-energy').textContent,'5.00 MWh');await $('run').click();await until(()=>$('decision-title').textContent==='Consistent with the policy','consistent original');assert.equal($('decision-status').textContent,'Not a human approval');
// Intake invalidates earlier response eligibility BEFORE an asynchronous file read.
await open(raw);await $('run').click();
let resolveRaw;const delayed=new Promise(resolve=>{resolveRaw=resolve;});
$('case-file').files=[{size:raw.length,arrayBuffer:()=>delayed}];const selection=$('case-file').emit('change');
await until(()=>$('runtime').textContent==='Ready','prior response during delayed read');
assert.equal($('decision-title').textContent,'Not reviewed','Earlier review must not render during a new file read');
assert.equal($('export-case').disabled,true);assert.equal($('accept').disabled,true);
resolveRaw(Uint8Array.from(raw).buffer);await selection;await until(()=>!$('run').disabled,'finish delayed intake');
// A request that is invalidated while hung must still time out and allow recovery.
holdNextReview=true;await $('run').click();await $('revise').click();assert.equal($('runtime').textContent,'Checking');
assert.ok(longTimers.size>0);for(const [id,fn] of [...longTimers]){longTimers.delete(id);realClearTimeout(id);fn();}
assert.equal($('runtime').textContent,'Paused');for(const id of ['case-file','new-case','example','load-example'])assert.equal($(id).disabled,true,`${id} must stay disabled until the runtime is ready`);assert.equal($('retry').hidden,false);assert.equal($('accept').disabled,true);
await $('cancel-revision').click();await $('retry').click();await until(()=>$('runtime').textContent==='Ready','recover timed-out invalidated operation');
heldReview.worker.send({id:heldReview.message.id,type:'result',case:bundle,result:{decision:'ACCEPT',resolution_accepted:true}});assert.equal($('decision-title').textContent,'Not reviewed');
await $('run').click();await until(()=>$('decision-title').textContent==='More evidence required','fresh review after recovery');
// A newer delayed selection must discard an older queued import, not briefly commit it.
holdNextReview=true;await $('run').click();const previousTitle=$('case-title').textContent;
const queuedPackage=structuredClone(p);queuedPackage.package_id='OBSOLETE-QUEUED-CASE';const queuedBytes=Buffer.from(JSON.stringify(queuedPackage));
$('case-file').files=[{size:queuedBytes.length,arrayBuffer:async()=>Uint8Array.from(queuedBytes).buffer}];await $('case-file').emit('change');await until(()=>$('notice').textContent.startsWith('Validating original raw bytes'),'older queued import');
let releaseLatest;const latestRead=new Promise(resolve=>{releaseLatest=resolve;});$('case-file').files=[{size:raw.length,arrayBuffer:()=>latestRead}];await $('case-file').emit('change');
heldReview.worker.send({id:heldReview.message.id,type:'error',message:'Obsolete development response'});await tick();await tick();await tick();await tick();
assert.equal($('case-title').textContent,previousTitle,'Obsolete queued case must not replace evidence during a newer read');
releaseLatest(Uint8Array.from(raw).buffer);await until(()=>!$('run').disabled,'latest selected case');
windowEvents.get('pagehide')();console.log('Native-backed DOM/event journey passed: raw intake → refusal → guided source revision → exact proposal acceptance → current export/readable summary → strict reopen/reconfirmation; malformed intake preserves open case; cancel draft invalidates. NOT real browser/Pyodide/visual proof.');

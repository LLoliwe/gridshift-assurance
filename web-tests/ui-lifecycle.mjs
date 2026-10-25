// Independent mocked UI transport only. Does not execute actual acceptance or external actions.
import vm from 'node:vm';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
const base=new URL('../',import.meta.url).pathname;
const fixture=JSON.parse(await readFile(base+'web/reconcile/flagship.json','utf8'));
const proposal=JSON.parse(await readFile(base+'web-tests/flagship-proposal.json','utf8'));
const controller=(await readFile(base+'web/engine-controller.js','utf8')).replace('export class EngineController','class EngineController').replace('export default EngineController;','');
const app=(await readFile(base+'web/reconcile/reconcile-ui.js','utf8')).replace(/^import .*?;\n/,'').replaceAll('import.meta.url',"'https://example.test/reconcile/index.html'");
function boot(){
 const nodes=new Map(),workers=[],blobs=[];let fetcher=async()=>({ok:true,json:async()=>structuredClone(fixture)});
 class E{constructor(){this.children=[];this.listeners={};this.value='';this.checked=false;this.hidden=false;this.readOnly=false;this.disabled=false;this.textContent=''}set innerHTML(_){throw Error('unsafe HTML sink')}addEventListener(k,f){this.listeners[k]=f}setAttribute(k,v){this[k]=v}append(...v){this.children.push(...v)}replaceChildren(...v){this.children=[...v]}focus(){}scrollIntoView(){}remove(){}fire(k){return this.listeners[k]?.()}click(){return this.fire('click')}}
 const get=id=>{if(!nodes.has(id))nodes.set(id,new E());return nodes.get(id)};get('case').value='flagship';get('reviewer').value='reviewer-demo';
 class Worker{constructor(){this.listeners={};this.sent=[];workers.push(this)}addEventListener(k,f){this.listeners[k]=f}removeEventListener(k,f){if(this.listeners[k]===f)delete this.listeners[k]}postMessage(m){this.sent.push(m)}terminate(){this.terminated=true}message(m){this.listeners.message?.({data:m})}error(message){this.listeners.error?.({message})}}
 class BlobStub{constructor(parts){this.parts=parts}}
 class URLStub extends URL{static createObjectURL(blob){blobs.push(blob);return 'blob:test'}static revokeObjectURL(){}}
 const c=vm.createContext({document:{getElementById:get,createElement:()=>new E(),querySelectorAll:()=>[],body:new E()},structuredClone,fetch:(...args)=>fetcher(...args),Worker,URL:URLStub,Blob:BlobStub,matchMedia:()=>({matches:true}),setTimeout:()=>1,clearTimeout(){},console});vm.runInContext(controller+'\n'+app,c);
 return {c,get,workers,blobs,setFetch:f=>fetcher=f,ready(){const w=workers.at(-1);w.message({id:w.sent[0].id,type:'ready'});return w},reply(w,p=fixture,r=proposal){w.message({id:w.sent.at(-1).id,type:'result',package:structuredClone(p),result:structuredClone(r),export_json:'synthetic-test-export'})}};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
{
 const h=boot();await flush();const w=h.ready();h.get('run').click();h.reply(w);assert.equal(h.get('accept').disabled,true);const count=w.sent.length;
 h.get('accept').click();assert.equal(w.sent.length,count);h.get('confirm').checked=true;h.get('reviewer').value=' ';h.get('confirm').fire('change');h.get('accept').click();assert.equal(w.sent.length,count);
 h.get('reviewer').value='reviewer-demo';h.get('confirm').fire('change');assert.equal(h.get('accept').disabled,false);h.get('accept').click();const request=w.sent.at(-1).activities;assert.equal(request.operation,'accept');assert.equal(request.proposal_sha256,proposal.proposal_sha256);assert.equal(request.reviewer_id,'reviewer-demo');assert.equal(request.package.report.emissions_tco2e,'192');assert.equal(h.get('export').disabled,true);
 const acceptedPkg=structuredClone(fixture);acceptedPkg.resolutions=[{action:'ACCEPT_PROPOSAL',proposal_sha256:proposal.proposal_sha256,reviewer_id:'reviewer-demo',source_status:'UNVERIFIED_USER_INPUT'}];const acceptedResult={...structuredClone(proposal),decision:'ACCEPT',resolution_accepted:true,accepted_report:proposal.proposed_report};h.reply(w,acceptedPkg,acceptedResult);assert.equal(h.get('reviewer').readOnly,true);assert.equal(h.get('original-emissions').textContent,'192');assert.equal(h.get('acceptance').hidden,true);h.get('export').click();assert.equal(h.blobs.length,1);
 h.get('reset').click();h.get('export').click();assert.equal(h.blobs.length,1);await flush();assert.equal(h.get('reviewer').readOnly,false);h.get('run').click();assert.equal(w.sent.at(-1).activities.package.resolutions.length,0);
}
{
 const h=boot();await flush();const w=h.ready();h.get('run').click();const stale=w.sent.at(-1).id;h.get('reviewer').value='different';h.get('reviewer').fire('input');assert.equal(h.get('acceptance').hidden,true);assert.equal(h.get('export').disabled,true);w.message({id:stale,type:'result',package:fixture,result:proposal,export_json:'stale'});assert.equal(h.get('decision-title').textContent,'Not reviewed');assert.equal(h.get('export').disabled,true);
 h.get('run').click();h.reply(w);h.get('confirm').checked=true;h.get('confirm').fire('change');h.get('case').value='missing-edge';h.get('case').fire('change');h.get('accept').click();assert.equal(w.sent.at(-1).activities.operation,'review');assert.equal(h.get('export').disabled,true);await flush();
 h.get('run').click();h.reply(w);w.error('runtime failed');h.get('export').click();assert.equal(h.blobs.length,0);assert.equal(h.get('acceptance').hidden,true);assert.equal(h.get('run').disabled,true);
}
{
 const h=boot();await flush();const w=h.ready();let firstResolve;h.setFetch(path=>path.includes('flagship')?new Promise(resolve=>firstResolve=resolve):Promise.resolve({ok:true,json:async()=>({...structuredClone(fixture),package_id:'NEW'})}));h.get('case').value='flagship';h.get('case').fire('change');h.get('case').value='missing-edge';await h.get('case').fire('change');firstResolve({ok:true,json:async()=>({...structuredClone(fixture),package_id:'OLD'})});await flush();h.get('run').click();assert.equal(w.sent.at(-1).activities.package.package_id,'NEW');
 const malicious=structuredClone(proposal);malicious.findings=[{code:'<img src=x onerror=alert(1)>',message:'<script>bad()</script>',record_ids:['<svg onload=bad()>']}];malicious.trace=[{record_id:'<script>bad()</script>',source_status:'SYNTHETIC',action:'ORIGINAL',reason:'<b>untrusted</b>'}];h.reply(w,fixture,malicious);assert.equal(h.get('decision-title').textContent,'CORRECT');assert.equal(h.get('original-emissions').textContent,'192');
}
console.log('Independent actual-controller/UI mocked lifecycle passes: explicit proposal gating, stale invalidation, reviewer lock/reset, original preservation, text-only sinks, async-case supersession and export clearing. No actual acceptance executed.');

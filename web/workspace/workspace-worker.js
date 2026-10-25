// Additive raw-intake workspace bridge. No JS accounting; no executable user interpolation.
import LIMITS from './intake-limits.json' with {type:'json'};
import {publicError,intakeRefusal} from './engine-controller.js';
export {LIMITS};
export const RUNTIME_VERSION='314.0.7';
export const ASSETS=Object.freeze([
 ['src/emissions.py','82f8e3e9a99f6fa354fa3be097d764e475159ff8bbd3c300733a1215e0a85655'],
 ['src/reconciliation.py','5f328d7f9acb4aa955ca2da64279a26dd6754a5ed93ee46c43a3ec97f87996cd'],
 ['fixtures/za_grid_factor_2024.json','13f30d6c4b20bcefee4bb26dae1ca30aa5ba32ea4fdb1717e718ce5389ca14d3']
]);
export async function verifyAsset(bytes,expected){const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');if(actual!==expected)throw Error('WORKSPACE_INTEGRITY: bundled source does not match reviewed bytes.');}
export const RAW_LIMIT=LIMITS.raw_limit_bytes;
export const ENVELOPE_LIMIT=LIMITS.envelope_limit_bytes;
export const REQUEST_LIMIT=2*1024*1024;
export const LIMITS_SHA256='3fd8c1d1f6992f9c7fdb78ca827d641c4f04e80b45658e0f4dac725ce70fb36a';
export const ADAPTER_SHA256='9f03b10bdb319f04675df48f241ff5984a03b93b0bcac8ce21c4e3f4729a519e';
// AC-5 quarantine modules (web/workspace), pinned like the adapter.
export const QUARANTINE_ASSETS=Object.freeze([
 ['quarantine_state.py','5eb2bd263b7591206dfe8a6b50ae964a39aed97ae3d0bdccbe578f394e00c619'],
 ['quarantine.py','e95b2bf10145420d4801559bc1e0c03a61dda69181784c2abb28d6b20ca1defe']
]);
export const QUARANTINE_OPERATIONS=Object.freeze(['quarantine_view','quarantine_export']);
export function looksQuarantined(value){return !!value&&typeof value==='object'&&(value.state==='QUARANTINED'||value.intake_result==='SCHEMA_REJECTION'||/^gridshift\.workspace\.quarantine/.test(String(value.schema_version||'')));}
const CDN=`https://cdn.jsdelivr.net/pyodide/v${RUNTIME_VERSION}/full/`;
export function validateMessage(message){
 if(!message||!Number.isSafeInteger(message.id)||message.id<1)throw Error('A positive safe request ID is required.');
 if(message.type==='init')return;
 if(message.type!=='review'||!message.activities||typeof message.activities!=='object')throw Error('Unsupported workspace message.');
 const r=message.activities;
 if(r.operation==='open'||r.operation==='intake'){
  if(Object.keys(r).sort().join('|')!=='operation|raw'||!(r.raw instanceof Uint8Array)||!r.raw.length||r.raw.byteLength>ENVELOPE_LIMIT)throw intakeRefusal(LIMITS.open_size_message); // Same kind and exception name as native open_case: ValueError.
 }else if(QUARANTINE_OPERATIONS.includes(r.operation)){
  if(Object.keys(r).sort().join('|')!=='operation|quarantine'||!looksQuarantined(r.quarantine))throw Error('Quarantine operations expect exactly one quarantine record.');
  if(new TextEncoder().encode(JSON.stringify(r)).byteLength>REQUEST_LIMIT)throw Error('Workspace request exceeds 2 MiB including escaped text and envelope overhead.');
 }else{
  if(looksQuarantined(r.case)||'quarantine' in r)throw Error('QUARANTINED: calculation, proposal and acceptance are refused for quarantined input.');
  const fields=r.operation==='accept'?['operation','case','proposal_sha256','reviewer_id']:['operation','case'];
  if(!['review','accept','save','export'].includes(r.operation)||Object.keys(r).sort().join('|')!==fields.sort().join('|'))throw Error('Unsupported workspace operation or fields.');
  if(r.operation==='accept'&&(!/^[a-f0-9]{64}$/.test(r.proposal_sha256)||typeof r.reviewer_id!=='string'||!r.reviewer_id.trim()||r.reviewer_id.length>2000))throw Error('Exact proposal and bounded self-reported reviewer ID required.');
  if(new TextEncoder().encode(JSON.stringify(r)).byteLength>REQUEST_LIMIT)throw Error('Workspace request exceeds 2 MiB including escaped text and envelope overhead.');
 }
}
let initialization;
async function initialize(){
 if(!initialization)initialization=(async()=>{
  const sources=[...ASSETS.map(([path,hash])=>[new URL(`../engine/${path}`,import.meta.url),`/gridshift/${path}`,hash]),[new URL('./case_adapter.py',import.meta.url),'/gridshift/src/case_adapter.py',ADAPTER_SHA256],[new URL('./intake-limits.json',import.meta.url),'/gridshift/src/intake-limits.json',LIMITS_SHA256],...QUARANTINE_ASSETS.map(([name,hash])=>[new URL(`./${name}`,import.meta.url),`/gridshift/src/${name}`,hash])];
  const assets=await Promise.all(sources.map(async([url,path,hash])=>{const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('Workspace source unavailable.');const bytes=new Uint8Array(await r.arrayBuffer());await verifyAsset(bytes,hash);return[path,bytes];}));
  const {loadPyodide}=await import(`${CDN}pyodide.mjs`);
  const runtime=await loadPyodide({indexURL:CDN});await runtime.loadPackagesFromImports('import hashlib');
  runtime.FS.mkdirTree('/gridshift/src');runtime.FS.mkdirTree('/gridshift/fixtures');
  for(const [path,bytes] of assets)runtime.FS.writeFile(path,bytes);
  await runtime.runPythonAsync("import sys, json\nsys.path.insert(0, '/gridshift/src')\nfrom pathlib import Path\nfrom case_adapter import open_case, execute\nfrom quarantine import intake, quarantine_execute\n");
  return runtime;
 })();
 return initialization;
}
export const OPEN_PYTHON="json.dumps(open_case(Path('/tmp/gridshift-workspace-raw.json').read_bytes()), ensure_ascii=False, allow_nan=False)";
export const INTAKE_PYTHON="json.dumps(intake(Path('/tmp/gridshift-workspace-raw.json').read_bytes()), ensure_ascii=False, allow_nan=False)";
export const QUARANTINE_PYTHON='json.dumps(quarantine_execute(json.loads(_workspace_request_json)), ensure_ascii=False, allow_nan=False)';
export const EXECUTE_PYTHON='json.dumps(execute(json.loads(_workspace_request_json)), ensure_ascii=False, allow_nan=False)';
export async function handleMessage(message,post,load=initialize){
 const id=message?.id;
 try{
  validateMessage(message);const runtime=await load();
  if(message.type==='init'){post({id,type:'ready'});return;}
  const request=message.activities;let output;
  if(request.operation==='open'||request.operation==='intake'){
   runtime.FS.writeFile('/tmp/gridshift-workspace-raw.json',request.raw);
   try{output=await runtime.runPythonAsync(request.operation==='open'?OPEN_PYTHON:INTAKE_PYTHON);}finally{runtime.FS.unlink('/tmp/gridshift-workspace-raw.json');}
  }else{
   runtime.globals.set('_workspace_request_json',JSON.stringify(request));
   output=await runtime.runPythonAsync(QUARANTINE_OPERATIONS.includes(request.operation)?QUARANTINE_PYTHON:EXECUTE_PYTHON);
  }
  // Only Python-validated output is parsed in JS. File bytes were never JSON.parsed.
  post({id,type:'result',...JSON.parse(output)});
 }catch(error){
  // Structured refusal: `message` is user-facing only; any Python traceback goes to `detail`.
  post({id,type:'error',...publicError(error,message?.activities?.operation)});
 }
}
if(typeof WorkerGlobalScope!=='undefined'&&self instanceof WorkerGlobalScope){
 let queue=Promise.resolve();self.addEventListener('message',event=>{queue=queue.then(()=>handleMessage(event.data,m=>self.postMessage(m)));});
}

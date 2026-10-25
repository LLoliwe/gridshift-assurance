// AC-5 worker bridge contract, mocked runtime only. NOT a browser/WASM/Pyodide run.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateMessage,handleMessage,verifyAsset,QUARANTINE_ASSETS,QUARANTINE_OPERATIONS,looksQuarantined,ENVELOPE_LIMIT,REQUEST_LIMIT,INTAKE_PYTHON,OPEN_PYTHON,QUARANTINE_PYTHON,EXECUTE_PYTHON} from '../web/workspace/workspace-worker.js';
const record={schema_version:'gridshift.workspace.quarantine.v1',state:'QUARANTINED',intake_result:'SCHEMA_REJECTION'};
const diagnostic={schema_version:'gridshift.workspace.quarantine-diagnostic.v1',state:'QUARANTINED'};
const raw=new TextEncoder().encode('{"data_year": 2.024e3}');
// Pinned quarantine sources match the bytes on disk; tampering fails closed.
for(const [name,hash] of QUARANTINE_ASSETS)await verifyAsset(await readFile(new URL(`../web/workspace/${name}`,import.meta.url)),hash);
await assert.rejects(verifyAsset(new Uint8Array([1]),QUARANTINE_ASSETS[1][1]),/INTEGRITY/);
// Intake uses the same byte bounds as open: empty and oversized never reach Python.
assert.doesNotThrow(()=>validateMessage({id:1,type:'review',activities:{operation:'intake',raw}}));
assert.doesNotThrow(()=>validateMessage({id:1,type:'review',activities:{operation:'intake',raw:new Uint8Array(ENVELOPE_LIMIT)}}));
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'intake',raw:new Uint8Array(0)}}));
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'intake',raw:new Uint8Array(ENVELOPE_LIMIT+1)}}));
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'intake',raw:'{}'}}));
// Calculation/proposal/acceptance/save/export of quarantined material is refused before Python.
for(const material of [record,diagnostic]){
 assert.equal(looksQuarantined(material),true);
 for(const activities of [{operation:'review',case:material},{operation:'save',case:material},{operation:'export',case:material},
  {operation:'accept',case:material,proposal_sha256:'a'.repeat(64),reviewer_id:'synthetic'},{operation:'review',case:{},quarantine:material}])
  assert.throws(()=>validateMessage({id:2,type:'review',activities}),/QUARANTINED/);
}
// Quarantine operations accept only a quarantine record, bounded.
for(const operation of QUARANTINE_OPERATIONS){
 assert.doesNotThrow(()=>validateMessage({id:3,type:'review',activities:{operation,quarantine:record}}));
 assert.throws(()=>validateMessage({id:3,type:'review',activities:{operation,quarantine:{schema_version:'gridshift.workspace.case.v1'}}}));
 assert.throws(()=>validateMessage({id:3,type:'review',activities:{operation,quarantine:record,case:{}}}));
 assert.throws(()=>validateMessage({id:3,type:'review',activities:{operation,quarantine:{...record,pad:'x'.repeat(REQUEST_LIMIT)}}}));
}
// Routing: intake bytes go to fixed intake Python unchanged; quarantine ops never reach execute().
let written,code,removed=false,globalJson;
const runtime={FS:{writeFile:(p,b)=>{assert.equal(p,'/tmp/gridshift-workspace-raw.json');written=b;},unlink:()=>{removed=true;}},
 globals:{set:(k,v)=>{assert.equal(k,'_workspace_request_json');globalJson=v;}},
 runPythonAsync:async c=>{code=c;return '{"operation":"intake","state":"QUARANTINED","intake_result":"SCHEMA_REJECTION","case":null,"result":null}';}};
let out;await handleMessage({id:4,type:'review',activities:{operation:'intake',raw}},m=>out=m,async()=>runtime);
assert.equal(written,raw);assert.equal(code,INTAKE_PYTHON);assert.notEqual(code,OPEN_PYTHON);assert.equal(removed,true);assert.equal(out.state,'QUARANTINED');
await handleMessage({id:5,type:'review',activities:{operation:'quarantine_export',quarantine:record}},m=>out=m,async()=>runtime);
assert.equal(code,QUARANTINE_PYTHON);assert.notEqual(code,EXECUTE_PYTHON);assert.deepEqual(JSON.parse(globalJson),{operation:'quarantine_export',quarantine:record});
code=null;await handleMessage({id:6,type:'review',activities:{operation:'review',case:record}},m=>out=m,async()=>runtime);
assert.equal(out.type,'error');assert.match(out.message,/QUARANTINED/);assert.equal(code,null);
// 'open' behaviour is unchanged.
await handleMessage({id:7,type:'review',activities:{operation:'open',raw}},m=>out=m,async()=>runtime);assert.equal(code,OPEN_PYTHON);
console.log('Workspace quarantine bridge: pinned sources, byte bounds, routing and pre-Python refusal passed with a MOCKED runtime. No browser/WASM/Pyodide claim.');

import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateMessage,handleMessage,verifyAsset,ASSETS,ADAPTER_SHA256,ENVELOPE_LIMIT,REQUEST_LIMIT,OPEN_PYTHON} from '../web/workspace/workspace-worker.js';
const raw=new TextEncoder().encode('{"quantity":"1.000","quantity":"2"}');
assert.doesNotThrow(()=>validateMessage({id:1,type:'review',activities:{operation:'open',raw}})); // Python, not JS, owns strict parsing.
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'open',raw:'{}'}}));
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'open',raw:new Uint8Array(ENVELOPE_LIMIT+1)}}));
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'review',case:{note:'\\'.repeat(REQUEST_LIMIT)}}}));
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'accept',case:{},proposal_sha256:'wrong',reviewer_id:'user'}}));
let written,code,removed=false;const runtime={FS:{writeFile:(path,bytes)=>{assert.equal(path,'/tmp/gridshift-workspace-raw.json');written=bytes;},unlink:()=>{removed=true;}},runPythonAsync:async value=>{code=value;return '{"operation":"open","case":{},"result":null}';}};
let result;await handleMessage({id:3,type:'review',activities:{operation:'open',raw}},m=>result=m,async()=>runtime);
assert.equal(written,raw);assert.equal(code,OPEN_PYTHON);assert.equal(removed,true);assert.equal(result.id,3);assert.equal(result.type,'result');
for(const [path,hash] of ASSETS)await verifyAsset(await readFile(new URL(`../web/engine/${path}`,import.meta.url)),hash);
await verifyAsset(await readFile(new URL('../web/workspace/case_adapter.py',import.meta.url)),ADAPTER_SHA256);
await assert.rejects(verifyAsset(new Uint8Array([0]),ADAPTER_SHA256),/INTEGRITY/);
const source=await readFile(new URL('../web/workspace/workspace.js',import.meta.url),'utf8');assert.equal(/JSON\.parse\s*\(/.test(source),false);assert.equal(/innerHTML/.test(source),false);
console.log('Workspace worker: bounded raw bytes reach fixed Python intake unchanged; pinned source integrity and safe UI text boundary passed. No browser/WASM claim.');

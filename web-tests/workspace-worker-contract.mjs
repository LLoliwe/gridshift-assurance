import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateMessage,handleMessage,verifyAsset,ASSETS,ADAPTER_SHA256,ENVELOPE_LIMIT,REQUEST_LIMIT,OPEN_PYTHON} from '../web/workspace/workspace-worker.js';
import {publicError,structured} from '../web/workspace/engine-controller.js';
const raw=new TextEncoder().encode('{"quantity":"1.000","quantity":"2"}');
assert.doesNotThrow(()=>validateMessage({id:1,type:'review',activities:{operation:'open',raw}})); // Python, not JS, owns strict parsing.
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'open',raw:'{}'}}));
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'open',raw:new Uint8Array(ENVELOPE_LIMIT+1)}}));
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'open',raw:new Uint8Array(0)}}),{message:'Open expects 1 byte to 768 KiB (786432 bytes) of original raw file bytes.'});
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'review',case:{note:'\\'.repeat(REQUEST_LIMIT)}}}));
assert.throws(()=>validateMessage({id:1,type:'review',activities:{operation:'accept',case:{},proposal_sha256:'wrong',reviewer_id:'user'}}));
let written,code,removed=false;const runtime={FS:{writeFile:(path,bytes)=>{assert.equal(path,'/tmp/gridshift-workspace-raw.json');written=bytes;},unlink:()=>{removed=true;}},runPythonAsync:async value=>{code=value;return '{"operation":"open","case":{},"result":null}';}};
let result;await handleMessage({id:3,type:'review',activities:{operation:'open',raw}},m=>result=m,async()=>runtime);
assert.equal(written,raw);assert.equal(code,OPEN_PYTHON);assert.equal(removed,true);assert.equal(result.id,3);assert.equal(result.type,'result');
// Regression: intake refusals are structured {kind, exception, message, detail}; the traceback never reaches `message`.
{const userMessage='data_year at $.report.data_year is a JSON float or exponent form. It must be the JSON integer 2024, written without a decimal point, exponent or quotes (not 2024.0, 2.024e3 or "2024"). Numbers are not coerced; this case was not opened and the original input was not changed.';
const trace=`Traceback (most recent call last):\n  File "/lib/python314.zip/_pyodide/_base.py", line 597, in eval_code_async\n    await CodeRunner(\n  File "/gridshift/src/case_adapter.py", line 24, in _require\n    raise ValueError(message)\nValueError: ${userMessage}\n`;
const failing={FS:{writeFile:()=>{},unlink:()=>{}},runPythonAsync:async()=>{const e=new Error(trace);e.name='PythonError';throw e;}};
let refusal;await handleMessage({id:4,type:'review',activities:{operation:'open',raw}},m=>refusal=m,async()=>failing);
assert.deepEqual({id:refusal.id,type:refusal.type,kind:refusal.kind,exception:refusal.exception,message:refusal.message},{id:4,type:'error',kind:'intake_refusal',exception:'ValueError',message:userMessage});
assert.equal(refusal.message.includes('Traceback'),false);assert.equal(refusal.detail,trace.trimEnd());
const reviewFail=publicError(trace.replace('ValueError: ','KeyError: '),'review');assert.equal(reviewFail.kind,'python_error');assert.equal(reviewFail.exception,'KeyError');
const multi=publicError('Traceback (most recent call last):\n  File "x", line 1\nValueError: first line\nsecond line','open');assert.equal(multi.message,'first line\nsecond line');
const plain=publicError(new Error('Open expects 1 byte'),'open');assert.deepEqual(plain,{kind:'runtime_error',exception:null,message:'Open expects 1 byte',detail:null});
const legacy=structured({type:'error',message:trace});assert.equal(legacy.message,userMessage);assert.match(legacy.detail,/^Traceback/);
const mislabeled=structured({type:'error',kind:'intake_refusal',message:trace});assert.equal(mislabeled.message.includes('Traceback'),false);
const opaque=publicError('Traceback (most recent call last):\n  File "x", line 1\n','open');assert.equal(opaque.message.includes('Traceback'),false);}
// The bounded 'intake' operation is an intake path too: its ValueError (and quarantine IntakeRefused) is an intake_refusal, not a crash.
{const t=e=>`Traceback (most recent call last):\n  File "/gridshift/src/quarantine.py", line 91, in _bounded\n${e}: Intake requires raw bytes. Nothing was stored.`;
for(const exception of ['ValueError','IntakeRefused','quarantine.IntakeRefused']){const p=publicError(t(exception),'intake');assert.deepEqual([p.kind,p.exception,p.message],['intake_refusal',exception.split('.').pop(),'Intake requires raw bytes. Nothing was stored.']);assert.match(p.detail,/^Traceback/);}
const failing={FS:{writeFile:()=>{},unlink:()=>{}},runPythonAsync:async()=>{throw new Error(t('ValueError'));}};
let out;await handleMessage({id:8,type:'review',activities:{operation:'intake',raw}},m=>out=m,async()=>failing);
assert.deepEqual([out.type,out.kind,out.exception,out.message],['error','intake_refusal','ValueError','Intake requires raw bytes. Nothing was stored.']);
assert.equal(publicError(t('KeyError'),'intake').kind,'python_error');assert.equal(publicError(t('ValueError'),'review').kind,'python_error');}
// C17: the worker's own size refusal (before Python) carries the same kind and exception name as native open_case, for open and intake.
for(const operation of ['open','intake'])for(const bad of [new Uint8Array(0),new Uint8Array(ENVELOPE_LIMIT+1)]){
 let out,loaded=false;await handleMessage({id:9,type:'review',activities:{operation,raw:bad}},m=>out=m,async()=>{loaded=true;return runtime;});
 assert.equal(loaded,false,'size refusal must not reach Python');
 assert.deepEqual(out,{id:9,type:'error',kind:'intake_refusal',exception:'ValueError',message:'Open expects 1 byte to 768 KiB (786432 bytes) of original raw file bytes.',detail:null});
 assert.equal(`${out.exception}: ${out.message}`,'ValueError: Open expects 1 byte to 768 KiB (786432 bytes) of original raw file bytes.');
}
for(const [path,hash] of ASSETS)await verifyAsset(await readFile(new URL(`../web/engine/${path}`,import.meta.url)),hash);
await verifyAsset(await readFile(new URL('../web/workspace/case_adapter.py',import.meta.url)),ADAPTER_SHA256);
await assert.rejects(verifyAsset(new Uint8Array([0]),ADAPTER_SHA256),/INTEGRITY/);
const source=await readFile(new URL('../web/workspace/workspace.js',import.meta.url),'utf8');assert.equal(/JSON\.parse\s*\(/.test(source),false);assert.equal(/innerHTML/.test(source),false);
console.log('Workspace worker: bounded raw bytes reach fixed Python intake unchanged; pinned source integrity and safe UI text boundary passed. No browser/WASM claim.');

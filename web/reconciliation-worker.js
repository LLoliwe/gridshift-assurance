// Actual Python reconciliation bridge. No JavaScript accounting or lineage inference.
export const RUNTIME_VERSION='314.0.7';
export const ASSETS=Object.freeze([
 ['src/emissions.py','82f8e3e9a99f6fa354fa3be097d764e475159ff8bbd3c300733a1215e0a85655'],
 ['src/reconciliation.py','5f328d7f9acb4aa955ca2da64279a26dd6754a5ed93ee46c43a3ec97f87996cd'],
 ['fixtures/za_grid_factor_2024.json','13f30d6c4b20bcefee4bb26dae1ca30aa5ba32ea4fdb1717e718ce5389ca14d3']
]);
const CDN=`https://cdn.jsdelivr.net/pyodide/v${RUNTIME_VERSION}/full/`;
export function validateRequest(request){
 if(!request||typeof request!=='object'||Array.isArray(request))throw new Error('A reconciliation request object is required.');
 const expected=request.operation==='review'?['operation','package']:request.operation==='accept'?['operation','package','proposal_sha256','reviewer_id']:null;
 if(!expected||Object.keys(request).sort().join('|')!==expected.sort().join('|'))throw new Error('Unsupported reconciliation operation or fields.');
 if(request.operation==='accept'&&(!/^[a-f0-9]{64}$/.test(request.proposal_sha256)||typeof request.reviewer_id!=='string'||!request.reviewer_id.trim()||request.reviewer_id.length>2000))throw new Error('Acceptance requires a current proposal hash and declared reviewer identifier.');
 const json=JSON.stringify(request);
 if(new TextEncoder().encode(json).length>2*1024*1024)throw new Error('Reconciliation request exceeds 2 MiB.');
 return json;
}
export async function verifyAsset(bytes,expected){const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');if(actual!==expected)throw new Error('RECONCILIATION_INTEGRITY: bundled source does not match reviewed bytes.');}
let initialization;
async function initialize(){if(!initialization)initialization=(async()=>{
 const assets=await Promise.all(ASSETS.map(async([path,hash])=>{const r=await fetch(new URL(`./engine/${path}`,import.meta.url),{cache:'no-store'});if(!r.ok)throw new Error(`Source unavailable: ${path}`);const bytes=new Uint8Array(await r.arrayBuffer());await verifyAsset(bytes,hash);return[path,bytes];}));
 const {loadPyodide}=await import(`${CDN}pyodide.mjs`);const runtime=await loadPyodide({indexURL:CDN});await runtime.loadPackagesFromImports('import hashlib');runtime.FS.mkdirTree('/gridshift/src');runtime.FS.mkdirTree('/gridshift/fixtures');for(const[path,bytes]of assets)runtime.FS.writeFile(`/gridshift/${path}`,bytes);
 await runtime.runPythonAsync("import sys, json, hashlib\nassert hashlib.sha256(b'abc').hexdigest() == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'\nsys.path.insert(0, '/gridshift/src')\nfrom reconciliation import reconcile_package, accept_proposal, export_package\n");return runtime;
})();return initialization;}
export const REVIEW_PYTHON=`
_request = json.loads(_reconciliation_request_json)
_package = _request['package']
if _request['operation'] == 'accept':
    _package = accept_proposal(_package, _request['proposal_sha256'], _request['reviewer_id'])
_result = reconcile_package(_package)
_export = export_package(_package)
json.dumps({'package': _package, 'result': _result, 'export_json': _export}, allow_nan=False)
`;
export async function handleMessage(message,post,load=initialize){
 const id=message?.id;
 try{
  if(!Number.isSafeInteger(id)||id<1)throw new Error('Request ID must be a positive safe integer.');
  if(message.type==='init'){await load();post({id,type:'ready'});return;}
  if(message.type!=='review')throw new Error('Unsupported worker message.');
  const json=validateRequest(message.activities);const runtime=await load();runtime.globals.set('_reconciliation_request_json',json);
  const response=JSON.parse(await runtime.runPythonAsync(REVIEW_PYTHON));post({id,type:'result',...response});
 }catch(error){post({id,type:'error',message:String(error?.message||error)});}
}
if(typeof WorkerGlobalScope!=='undefined'&&self instanceof WorkerGlobalScope){let queue=Promise.resolve();self.addEventListener('message',event=>{queue=queue.then(()=>handleMessage(event.data,result=>self.postMessage(result))).catch(error=>self.postMessage({id:event.data?.id,type:'error',message:String(error)}));});}

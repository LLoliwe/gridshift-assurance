/** UI-only lifecycle adapter. Never calculates, substitutes, or fabricates results. */
/**
 * Split a worker/Pyodide error into a user-facing message and optional technical detail.
 * A Python traceback is never part of `message`; it is kept only in `detail`.
 */
/** Operations that admit raw bytes; a ValueError from them is an intake refusal, not a crash. */
export const INTAKE_OPERATIONS=Object.freeze(['open','intake']);
const INTAKE_EXCEPTIONS=Object.freeze(['ValueError','IntakeRefused']);
/** A worker-side intake refusal, labelled exactly as native Python labels the same refusal. */
export function intakeRefusal(message){const error=Error(message);error.publicKind='intake_refusal';error.exception='ValueError';return error;}
export function publicError(error,operation){
  const raw=String(error?.message??error??'').replace(/\s+$/,'');
  // A refusal the worker raised itself (before Python) already carries its public kind and exception name.
  if(error&&typeof error==='object'&&typeof error.publicKind==='string')return {kind:error.publicKind,exception:error.exception??null,message:raw,detail:null};
  if(!/Traceback \(most recent call last\):/.test(raw))return {kind:'runtime_error',exception:null,message:raw,detail:null};
  const lines=raw.split('\n');
  for(let i=lines.length-1;i>=0;i--){
    const match=lines[i].match(/^([A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt|Refused|Refusal)): ?(.*)$/);
    if(!match)continue;
    const exception=match[1].split('.').pop();
    const message=[match[2],...lines.slice(i+1)].join('\n').trim()||exception;
    const kind=INTAKE_OPERATIONS.includes(operation)&&INTAKE_EXCEPTIONS.includes(exception)?'intake_refusal':'python_error';
    return {kind,exception,message,detail:raw};
  }
  return {kind:'python_error',exception:null,message:'Python reported an error without a readable message.',detail:raw};
}
/** Accept a structured worker error; never let a traceback reach `message`, even from an older worker. */
export function structured(m){
  const safe=m?.kind?{kind:m.kind,exception:m.exception??null,message:String(m.message||'Review failed'),detail:m.detail??null}:publicError(m?.message||'Review failed');
  if(/Traceback \(most recent call last\):/.test(safe.message)){const again=publicError(safe.message);safe.message=again.message;safe.detail=safe.detail||again.detail;}
  return safe;
}
export class EngineController {
  constructor({workerFactory,onState=()=>{},onResult=()=>{},onError=()=>{},timeoutMs=90000}) {
    if(typeof workerFactory!=='function') throw new TypeError('workerFactory is required');
    if(!Number.isFinite(timeoutMs)||timeoutMs<=0) throw new TypeError('timeoutMs must be positive');
    this.factory=workerFactory;this.onState=onState;this.onResult=onResult;this.onError=onError;
    this.timeoutMs=timeoutMs;this.state='loading';this.worker=null;this.generation=0;
    this.sequence=0;this.initId=null;this.active=null;this.timer=null;this.destroyed=false;
  }
  _state(value){this.state=value;this.onState(value);}
  _disposeWorker(){
    clearTimeout(this.timer);this.timer=null;
    if(this.worker){
      this.worker.removeEventListener?.('message',this.messageListener);
      this.worker.removeEventListener?.('error',this.errorListener);
      this.worker.terminate();this.worker=null;
    }
    this.initId=null;this.active=null;
  }
  _fail(message,phase){
    this.generation++;this._disposeWorker();this._state('failed');
    {const safe=publicError(message);this.onError({phase,message:safe.message,detail:safe.detail});}
  }
  start(){
    if(this.destroyed) throw new Error('EngineController has been destroyed');
    this.generation++;this._disposeWorker();const generation=this.generation;
    this._state('loading');
    try{this.worker=this.factory();}
    catch(error){this._fail(error?.message||error,'init');return;}
    this.messageListener=event=>{
      if(this.destroyed||generation!==this.generation)return;
      const m=event.data;
      if(!m||typeof m!=='object')return;
      if(m.id===this.initId&&this.initId!==null){
        if(m.type==='ready'){
          clearTimeout(this.timer);this.timer=null;this.initId=null;this._state('ready');
        }else if(m.type==='error') this._fail(m.message||'Engine initialization failed','init');
        return;
      }
      if(!this.active||m.id!==this.active.id)return;
      if(m.type!=='result'&&m.type!=='error')return;
      const eligible=this.active.eligible;this.active=null;this._state('ready');
      if(!eligible)return;
      if(m.type==='error')this.onError({phase:'review',...structured(m)});
      else this.onResult(m);
    };
    this.errorListener=event=>{
      if(!this.destroyed&&generation===this.generation)
        this._fail(event.message||'Worker runtime failed',this.initId!==null?'init':'runtime');
    };
    this.worker.addEventListener('message',this.messageListener);
    this.worker.addEventListener('error',this.errorListener);
    const id=++this.sequence;this.initId=id;
    this.timer=setTimeout(()=>{
      if(!this.destroyed&&generation===this.generation&&this.initId===id)
        this._fail('Runtime download or initialization timed out','init');
    },this.timeoutMs);
    try{this.worker.postMessage({id,type:'init'});}
    catch(error){this._fail(error?.message||error,'init');}
  }
  review(activities){
    if(this.destroyed||!this.worker||this.state!=='ready'||this.active)return false;
    const id=++this.sequence;this.active={id,eligible:true};this._state('checking');
    try{this.worker.postMessage({id,type:'review',activities});}
    catch(error){this.active=null;this._state('ready');this.onError({phase:'review',...publicError(error)});return false;}
    return true;
  }
  invalidate(){
    // Editing invalidates display eligibility, not the running worker operation.
    // Keep the slot occupied until its response, preventing concurrent requests.
    if(this.destroyed)return;
    if(this.active)this.active.eligible=false;
  }
  suspend(){
    // Reversible page-lifecycle release; no calculations or input mutations.
    if(this.destroyed)return;
    this.generation++;this._disposeWorker();this._state('suspended');
  }
  destroy(){
    if(this.destroyed)return;
    this.destroyed=true;this.generation++;this._disposeWorker();
  }
}
export default EngineController;

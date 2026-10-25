/** UI-only lifecycle adapter. Never calculates, substitutes, or fabricates results. */
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
    this.onError({phase,message:String(message)});
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
      if(m.type==='error')this.onError({phase:'review',message:String(m.message||'Review failed')});
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
    catch(error){this.active=null;this._state('ready');this.onError({phase:'review',message:String(error?.message||error)});return false;}
    return true;
  }
  invalidate(){
    // Editing invalidates display eligibility, not the running worker operation.
    // Keep the slot occupied until its response, preventing concurrent requests.
    if(this.destroyed)return;
    if(this.active)this.active.eligible=false;
  }
  destroy(){
    if(this.destroyed)return;
    this.destroyed=true;this.generation++;this._disposeWorker();
  }
}
export default EngineController;

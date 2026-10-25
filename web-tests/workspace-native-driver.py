"""Test-only native transport. Not an application server or browser/WASM proof."""
from pathlib import Path
import json,sys,base64
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'web/engine/src'),str(ROOT/'web/workspace')]
from case_adapter import open_case,execute
from quarantine import intake,quarantine_execute
try:
 r=json.load(sys.stdin)
 op=r['operation']
 if op in ('open','intake'):result=(open_case if op=='open' else intake)(base64.b64decode(r['raw_base64']))
 elif op in ('quarantine_view','quarantine_export'):result=quarantine_execute(r)
 else:result=execute(r)
 print(json.dumps({'ok':True,'value':result},ensure_ascii=False,allow_nan=False))
except Exception as error:
 print(json.dumps({'ok':False,'message':str(error),'exception':type(error).__name__}))

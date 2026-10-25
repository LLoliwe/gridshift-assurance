// WITHHOLD screens name the releasing evidence only from what the engine itself reports.
// Uses the live native engine output for frozen E1-W10 (not a hand-written fixture). Synthetic data.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {releaseEvidence,describeAffected,isSchemaRejection} from '../web/workspace/workspace-state.js';
const root=new URL('..',import.meta.url).pathname;
const review=file=>JSON.parse(execFileSync('python3',['-c',`import sys,json;sys.path[:0]=['web/engine/src','web/workspace']
from case_adapter import open_case,execute
o=open_case(open(sys.argv[1],'rb').read());print(json.dumps(execute({'operation':'review','case':o['case']})))`,file],{cwd:root,encoding:'utf8'}));
const w10=review('lane-b/e1-frozen/cases/E1-W10.json');
assert.equal(w10.result.decision,'WITHHOLD');assert.equal(w10.result.findings[0].code,'SOURCE_NOT_SUPPORTED');
const records=JSON.parse(readFileSync(new URL('../lane-b/e1-frozen/cases/E1-W10.json',import.meta.url),'utf8')).records;
const rel=releaseEvidence(w10.result,records);
assert.deepEqual(rel.engine,w10.result.required_evidence,'engine text is passed through verbatim');
assert.match(rel.engine[0],/kWh or MWh/);
assert.deepEqual(rel.affected,[{record_id:'A',meter_id:'M1',period_start:'2024-01-01',period_end:'2025-01-01',declared_unit:'ZAR'}]);
assert.equal(describeAffected(rel.affected[0]),'Record A: meter M1, 2024-01-01 to 2025-01-01 (end exclusive), currently declared in ZAR');
// No engine requirement → nothing is suggested (no invented text).
assert.equal(releaseEvidence({...w10.result,required_evidence:[]},records),null);
// A record ID the case does not contain is named by ID only, with no invented meter or period.
assert.deepEqual(releaseEvidence({...w10.result,findings:[{...w10.result.findings[0],record_ids:['Z']}]},records).affected,[{record_id:'Z'}]);
// Schema rejections and non-WITHHOLD results never get a release section.
const schema={decision:'WITHHOLD',findings:[{code:'INVALID_SCHEMA',message:'x',record_ids:[]}],required_evidence:['x']};
assert.ok(isSchemaRejection(schema));assert.equal(releaseEvidence(schema,records),null);
assert.equal(releaseEvidence({decision:'CORRECT',findings:[],required_evidence:['x']},records),null);
console.log('Release evidence: E1-W10 names the engine requirement (kWh or MWh) for declared record A, meter M1, 2024; no requirement → none suggested.');

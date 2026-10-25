"""Run the frozen cases through native CPython using the same adapter entry points and
step semantics as the browser worker. Native reference only: no JS round-trip."""
from base64 import b64decode
from hashlib import sha256
import json
import platform
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from cases import build, export_for_browser  # noqa: E402
from case_adapter import open_case, execute  # noqa: E402


def outcome(step, value=None, error=None):
    o = {'step': step, 'ok': error is None}
    if error is not None:
        o['error'] = error
        return o
    case = value['case']
    o['raw_sha256'] = case['original']['raw_sha256']
    o['revision'] = case['revision']
    o['history_len'] = len(case['history'])
    o['cached_review_null'] = case['cached_review'] is None
    res = case['working'].get('resolutions') if isinstance(case['working'], dict) else None
    o['active_resolutions'] = len(res) if isinstance(res, list) else None
    r = value.get('result')
    o['decision'] = r['decision'] if r else None
    if r:
        rep = r.get('accepted_report') or r.get('proposed_report')
        o['emissions'] = rep['emissions_tco2e'] if rep else None
        o['proposal_sha256'] = r.get('proposal_sha256')
        o['resolution_accepted'] = r.get('resolution_accepted')
        o['finding_codes'] = [f['code'] for f in r.get('findings', [])]
    if 'export_json' in value:
        o['export_sha256'] = sha256(value['export_json'].encode('utf-8')).hexdigest()
        o['export_json'] = value['export_json']
    return o


def run_case(c):
    raw = b64decode(c['raw_base64'])
    out, case, last = [], None, None
    for step in c['steps']:
        try:
            if step == 'open':
                value = open_case(raw)
            elif step == 'reopen_export':
                value = open_case(last['export_json'].encode('utf-8'))
            elif step == 'review':
                value = execute({'operation': 'review', 'case': case})
            elif step == 'accept_current':
                value = execute({'operation': 'accept', 'case': case,
                                 'proposal_sha256': last['result']['proposal_sha256'], 'reviewer_id': c['reviewer']})
            elif step.startswith('accept_hash:'):
                value = execute({'operation': 'accept', 'case': case, 'proposal_sha256': step.split(':', 1)[1],
                                 'reviewer_id': c['reviewer']})
            else:
                raise RuntimeError('unknown step')
        except Exception as error:  # record and stop, exactly like the browser runner
            out.append(outcome(step, error=f'{type(error).__name__}: {error}'))
            break
        out.append(outcome(step, value))
        case = value['case']
        if 'export_json' in value or value.get('result'):
            last = value
    return out


if __name__ == '__main__':
    cases = export_for_browser(build())
    if len(sys.argv) > 2 and sys.argv[1] == '--emit-browser-input':
        Path(sys.argv[2]).write_text(json.dumps(cases))
        raise SystemExit(0)
    result = {'runtime': 'native-cpython', 'python': platform.python_version(),
              'cases': {c['id']: run_case(c) for c in cases}}
    Path(sys.argv[1]).write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(f"native run complete: {len(cases)} cases, python {result['python']}")

"""Workspace envelope only. The reviewed Decimal reconciliation core is unchanged.
Raw inputs always pass through reconciliation.load_package before normalization.
"""
from base64 import b64decode, b64encode
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
from reconciliation import load_package, reconcile_package, accept_proposal, canonical

VERSION = 'gridshift.workspace.case.v1'
RAW_LIMIT = 64 * 1024
ENVELOPE_LIMIT = 768 * 1024
REQUEST_LIMIT = 2 * 1024 * 1024
HISTORY_LIMIT = 100
INTAKE_PATH = Path('/tmp/gridshift-workspace-intake.json')


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _load(raw, limit):
    _require(isinstance(raw, bytes) and 0 < len(raw) <= limit,
             f'Input must contain 1–{limit} UTF-8 bytes.')
    # Fixed internal path, never derived from user content. The worker is serialized.
    INTAKE_PATH.write_bytes(raw)
    try:
        return load_package(INTAKE_PATH)
    finally:
        INTAKE_PATH.unlink(missing_ok=True)


def _same(a, b):
    return canonical(a) == canonical(b)


def _keys(value, keys, label):
    _require(isinstance(value, dict) and set(value) == set(keys),
             f'{label} has missing or unsupported fields; original input was not changed.')


def _package(value):
    _require(isinstance(value, dict), 'An engine package must be a JSON object.')
    _require(value.get('schema_version') == 'gridshift.reconciliation.input.v1',
             'Supply a reconciliation input package or a workspace case v1. Other envelope versions are not supported.')
    _require(len(canonical(value).encode('utf-8')) <= RAW_LIMIT,
             'The supported working package limit is 64 KiB.')
    # Do not normalize unknown fields, numeric types, limitations or evidence.
    # The actual engine will withhold and explain unsupported package semantics.
    return deepcopy(value)


def _history(value):
    _require(isinstance(value, list) and len(value) <= HISTORY_LIMIT,
             'Case history exceeds the supported 100 entries.')
    for item in value:
        _require(isinstance(item, dict), 'Each history item must be an object.')
    return deepcopy(value)


def _bounded_envelope(case):
    _require(len(canonical(case).encode('utf-8')) + 1 <= ENVELOPE_LIMIT,
             'Case envelope exceeds the supported 768 KiB limit after normalization. No evidence or history was dropped and no export was produced.')


def _validate_case(case):
    _keys(case, ['schema_version', 'original', 'working', 'revision', 'history', 'cached_review'], 'Workspace case')
    _require(case['schema_version'] == VERSION, 'Unsupported workspace envelope version.')
    original = case['original']
    _keys(original, ['raw_base64', 'raw_sha256', 'parsed'], 'Original evidence')
    _require(isinstance(original['raw_base64'], str) and len(original['raw_base64']) <= 4 * ((RAW_LIMIT + 2) // 3),
             'Original raw evidence exceeds the supported 64 KiB limit.')
    try:
        raw = b64decode(original['raw_base64'], validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError('Original evidence is not valid base64.') from error
    parsed = _package(_load(raw, RAW_LIMIT))
    _require(original['raw_sha256'] == sha256(raw).hexdigest(), 'Original raw-byte SHA-256 mismatch. No representation was selected.')
    _require(_same(parsed, original['parsed']), 'Original raw bytes and parsed evidence conflict. No representation was selected.')
    _package(case['working'])
    _require(type(case['revision']) is int and 0 <= case['revision'] <= 1000000, 'Invalid revision identity.')
    _history(case['history'])
    _require(case['cached_review'] is None or isinstance(case['cached_review'], dict), 'Invalid cached review representation.')
    _bounded_envelope(case)
    return deepcopy(case)


def _append_history(case, item):
    _require(len(case['history']) < HISTORY_LIMIT, 'History is full (100 entries). No prior history was removed.')
    case['history'].append(item)


def _clear_resolutions(case, reason):
    working = case['working']
    if isinstance(working.get('resolutions'), list) and working['resolutions']:
        _append_history(case, {'kind': 'historical_imported_resolution', 'reason': reason,
                              'revision': case['revision'], 'resolutions': deepcopy(working['resolutions']),
                              'trust': 'IMPORTED_SELF_REPORT_NOT_CURRENT_APPROVAL'})
        working['resolutions'] = []


def open_case(raw):
    """Strict raw UTF-8 intake. Imported cached decisions never become current."""
    parsed = _load(raw, ENVELOPE_LIMIT)
    if isinstance(parsed, dict) and parsed.get('schema_version') == VERSION:
        case = _validate_case(parsed)
        case['cached_review'] = None
        _clear_resolutions(case, 'Reopened case requires a fresh exact-proposal confirmation.')
    else:
        _require(len(raw) <= RAW_LIMIT, 'Raw engine packages are limited to 64 KiB; workspace envelopes to 768 KiB.')
        package = _package(parsed)
        case = {'schema_version': VERSION,
                'original': {'raw_base64': b64encode(raw).decode('ascii'),
                             'raw_sha256': sha256(raw).hexdigest(), 'parsed': deepcopy(package)},
                'working': deepcopy(package), 'revision': 0, 'history': [], 'cached_review': None}
        _clear_resolutions(case, 'Imported acceptance is history only, not current approval.')
    _bounded_envelope(case)
    return {'case': case, 'result': None, 'operation': 'open',
            'notice': 'Original bytes preserved. Run a fresh Python review; imported decisions are historical only.'}


def execute(request):
    _require(isinstance(request, dict), 'Workspace request must be an object.')
    _require(len(canonical(request).encode('utf-8')) <= REQUEST_LIMIT, 'Workspace request exceeds 2 MiB.')
    operation = request.get('operation')
    expected = {'operation', 'case'}
    if operation == 'accept':
        expected |= {'proposal_sha256', 'reviewer_id'}
    _keys(request, expected, 'Workspace request')
    _require(operation in ('review', 'accept', 'save', 'export'), 'Unsupported workspace operation.')
    case = _validate_case(request['case'])
    if operation == 'save':
        # A draft never carries a current approved result, even if an earlier review exists.
        case['cached_review'] = None
        _clear_resolutions(case, 'Saved unreviewed draft; prior acceptance is history only.')
        _bounded_envelope(case)
        return {'case': case, 'result': None, 'operation': operation,
                'export_json': canonical(case) + '\n', 'summary': summary(case, None)}
    if operation == 'accept':
        case['working'] = accept_proposal(case['working'], request['proposal_sha256'], request['reviewer_id'])
    result = reconcile_package(case['working'])
    if operation == 'accept':
        _require(result.get('resolution_accepted') is True and result.get('proposal_sha256') == request['proposal_sha256'],
                 'Acceptance did not return the exact current proposal.')
        _append_history(case, {'kind': 'reviewer_acceptance', 'revision': case['revision'],
                              'proposal_sha256': request['proposal_sha256'], 'reviewer_id': request['reviewer_id'],
                              'trust': 'SELF_REPORTED_NOT_AUTHENTICATED'})
    case['cached_review'] = deepcopy(result)
    _bounded_envelope(case)
    return {'case': case, 'result': result, 'operation': operation,
            'export_json': canonical(case) + '\n', 'summary': summary(case, result)}


def summary(case, result):
    working = case['working']
    original = case['original']['parsed']
    lines = ['GRIDSHIFT — REVIEW HANDOFF', '', f"Case: {working.get('package_id', '(not supplied)')}",
             f"Revision: {case['revision']}", 'Scope: South Africa · 2024 · location-based purchased electricity',
             'Declared package only; not organizational completeness or independent assurance.',
             'Published factor: 0.960 tCO2e/MWh. Factor source reconciliation remains unresolved.',
             '', 'ORIGINAL REPORT (preserved)', json.dumps(original.get('report'), ensure_ascii=False, indent=2),
             '', 'CURRENT REVIEW']
    if result is None:
        lines.append('UNREVIEWED DRAFT — no current decision or approval.')
    elif result['decision'] == 'WITHHOLD':
        lines.append('MORE EVIDENCE REQUIRED — no accepted or proposed total.')
    elif result.get('resolution_accepted'):
        lines.append('REVIEWER ACCEPTED THIS EXACT CORRECTION (self-reported identity).')
    elif result['decision'] == 'CORRECT':
        lines.append('CORRECTION PROPOSED — explicit reviewer acceptance still required.')
    else:
        lines.append('CONSISTENT WITH THIS CALCULATION POLICY — not a human approval.')
    if result:
        if result['decision'] != 'WITHHOLD':
            report = result.get('accepted_report') or result.get('proposed_report')
            if report:
                lines.extend([f"Supported report: {report['energy_mwh']} MWh / {report['emissions_tco2e']} tCO2e",
                              f"Exact proposal: {result.get('proposal_sha256') or 'No correction proposal'}"])
        lines.extend(['', 'FINDINGS / FIRST BLOCKER MAY NOT BE THE ONLY ISSUE',
                      json.dumps(result.get('findings', []), ensure_ascii=False, indent=2),
                      '', 'RECORD TRACE', json.dumps(result.get('trace', []), ensure_ascii=False, indent=2)])
    lines.extend(['', 'WORKING DECLARATIONS', json.dumps(working, ensure_ascii=False, indent=2),
                  '', 'HISTORY (imported entries are unverified historical self-reports)',
                  json.dumps(case['history'], ensure_ascii=False, indent=2), '',
                  f"Original raw-byte SHA-256: {case['original']['raw_sha256']}",
                  'Unsigned content fingerprints are not signatures, identity checks or tamper-proof seals.',
                  'Reopen the companion JSON in GRIDSHIFT /workspace/ and recompute. Cached decisions are not authoritative.',
                  'Original raw bytes are embedded as base64 in the companion case. Nothing is uploaded or persistently stored by this workspace.'])
    return '\n'.join(lines) + '\n'

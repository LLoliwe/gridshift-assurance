"""AC-5: bounded raw-file quarantine with a byte-exact diagnostic export.

Intake path for untrusted bytes. Supported input opens exactly as case_adapter.open_case
does. Input that intake rejects is held as a QUARANTINED record: the original bytes are
kept exactly (base64 + sha256), are viewable and exportable, and are never admitted to
calculation, proposal or acceptance (see quarantine_state.refuse_if_quarantined, which
case_adapter.open_case/execute call). A quarantine is a SCHEMA_REJECTION intake result,
never an engine WITHHOLD decision. No coercion and no rewriting of bytes.

Bounds: the existing native intake limits, 1–786432 (ENVELOPE_LIMIT) bytes. Empty or
oversized input raises IntakeRefused and nothing is stored.
"""
from base64 import b64decode, b64encode
from binascii import Error as BinasciiError
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import sys

import case_adapter
from case_adapter import ENVELOPE_LIMIT, RAW_LIMIT, SAFE_INTEGER, VERSION as CASE_VERSION, open_case
from emissions import _check_json_depth, _unique_object
from quarantine_state import (ADMITTED, DIAGNOSTIC_VERSION, QUARANTINE_VERSION, QUARANTINED,
                              SCHEMA_REJECTION, QuarantineRefusal, is_quarantined)

MODULE_VERSION = 'gridshift.workspace.quarantine.module.v1'
QUARANTINE_LIMIT = ENVELOPE_LIMIT  # existing native intake bound; not widened
TOKEN_PREVIEW = 64
REASON_LIMIT = 50
STATEMENT = ('NO CALCULATION, NO PROPOSAL AND NO ACCEPTANCE OCCURRED. This file is a diagnostic export of '
             'untrusted input that was rejected at intake (SCHEMA_REJECTION) and held in quarantine. It is '
             'not an engine decision, not a reconciliation result and not evidence of any total. The original '
             'bytes are reproduced exactly in original.raw_base64 and are verified by original.raw_sha256.')
NUMBER_NOTE = ('Float and exponent JSON number tokens are refused conservatively, even when numerically '
               'integral (2024.0, 2.024e3): they cannot be carried exactly across the browser boundary. '
               'The ±(2^53−1) integer bound is a transport limit of JSON numbers in JavaScript, not an '
               'accounting limit; exact quantities belong in decimal strings.')
RECORD_KEYS = {'schema_version', 'state', 'intake_result', 'engine_decision', 'admitted_to_calculation',
               'acceptance_possible', 'original', 'rejection', 'quarantined_at_utc', 'tool'}
ORIGINAL_KEYS = {'raw_base64', 'raw_sha256', 'byte_length'}


class IntakeRefused(ValueError):
    """Empty, oversized or non-bytes input. Refused before storage; nothing is retained."""


def _now(now=None):
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _file_sha(path):
    try:
        return sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _commit(commit=None):
    if commit:
        return commit, 'argument'
    if os.environ.get('GRIDSHIFT_COMMIT'):
        return os.environ['GRIDSHIFT_COMMIT'], 'GRIDSHIFT_COMMIT'
    if sys.platform != 'emscripten':
        try:
            import subprocess
            out = subprocess.run(['git', '-C', str(Path(__file__).resolve().parent), 'rev-parse', 'HEAD'],
                                 capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and len(out.stdout.strip()) == 40:
                return out.stdout.strip(), 'git rev-parse HEAD (source files may differ; see *_sha256)'
        except (OSError, ValueError, Exception):  # noqa: BLE001 - provenance is best effort
            pass
    return None, 'unavailable in this runtime; use the source sha256 values'


def tool_identity(commit=None):
    value, source = _commit(commit)
    return {'module_version': MODULE_VERSION, 'quarantine_schema': QUARANTINE_VERSION,
            'case_envelope_schema': CASE_VERSION, 'commit': value, 'commit_source': source,
            'quarantine_py_sha256': _file_sha(__file__),
            'quarantine_state_py_sha256': _file_sha(Path(__file__).with_name('quarantine_state.py')),
            'case_adapter_py_sha256': _file_sha(case_adapter.__file__),
            'runtime': f'{sys.implementation.name} {sys.version.split()[0]} on {sys.platform}'}


def _bounded(raw):
    if not isinstance(raw, (bytes, bytearray)):
        raise IntakeRefused('Intake requires raw bytes. Nothing was stored.')
    if not 0 < len(raw) <= QUARANTINE_LIMIT:
        raise IntakeRefused(f'Input must contain 1–{QUARANTINE_LIMIT} bytes; received {len(raw)}. '
                            'Refused before storage; nothing was quarantined or retained.')
    return bytes(raw)


class _Number:
    """Diagnosis only: keeps the exact source token. Never used for calculation."""
    __slots__ = ('kind', 'token')

    def __init__(self, kind, token):
        self.kind, self.token = kind, token


def _preview(token):
    return token if len(token) <= TOKEN_PREVIEW else f'{token[:TOKEN_PREVIEW]}… ({len(token)} characters)'


def _walk(value, path, reasons):
    if len(reasons) >= REASON_LIMIT:
        return
    if isinstance(value, _Number):
        if value.kind == 'float':
            reasons.append({'code': 'FLOAT_OR_EXPONENT_NUMBER', 'path': path, 'token': _preview(value.token),
                            'message': f'JSON number at {path} is a non-integer or exponent token; '
                                       'exact quantities must be decimal strings.'})
        else:
            digits = value.token.lstrip('-')
            if len(digits) > 16 or abs(int(value.token)) > SAFE_INTEGER:
                reasons.append({'code': 'INTEGER_OUTSIDE_PORTABLE_RANGE', 'path': path,
                                'token': _preview(value.token),
                                'message': f'JSON integer at {path} is outside ±(2^53−1), a transport '
                                           '(not accounting) limit; use a decimal string.'})
    elif isinstance(value, dict):
        for key, item in value.items():
            _walk(item, f'{path}.{key}', reasons)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk(item, f'{path}[{index}]', reasons)


def _reject_constant(name):
    raise ValueError(f'non-finite JSON constant {name} is not permitted')


def diagnose(raw):
    """Field-specific reasons, computed in memory from the exact bytes. Never coerces."""
    reasons = []
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as error:
        return [{'code': 'INVALID_UTF8', 'path': None, 'byte_offset': error.start,
                 'message': f'Invalid UTF-8 at byte offset {error.start}: {error.reason}.'}]
    if text.startswith('\ufeff'):
        reasons.append({'code': 'UTF8_BOM', 'path': None, 'byte_offset': 0,
                        'message': 'Input begins with a UTF-8 byte-order mark, which intake does not accept.'})
    try:
        _check_json_depth(text)
        parsed = json.loads(text.lstrip('\ufeff'), object_pairs_hook=_unique_object,
                            parse_float=lambda token: _Number('float', token),
                            parse_int=lambda token: _Number('int', token),
                            parse_constant=_reject_constant)
    except json.JSONDecodeError as error:
        return reasons + [{'code': 'JSON_SYNTAX', 'path': None, 'line': error.lineno, 'column': error.colno,
                           'message': f'JSON syntax error: {error.msg} (line {error.lineno}, column {error.colno}).'}]
    except (ValueError, RecursionError) as error:
        code = 'DUPLICATE_KEY' if 'duplicate JSON key' in str(error) else (
            'NON_FINITE_CONSTANT' if 'non-finite' in str(error) else 'PARSE_REJECTION')
        return reasons + [{'code': code, 'path': None, 'message': str(error)}]
    _walk(parsed, '$', reasons)
    if len(reasons) >= REASON_LIMIT:
        reasons.append({'code': 'REASONS_TRUNCATED', 'path': None,
                        'message': f'Only the first {REASON_LIMIT} field findings are listed.'})
    if isinstance(parsed, dict) and parsed.get('schema_version') in (QUARANTINE_VERSION, DIAGNOSTIC_VERSION):
        reasons.append({'code': 'QUARANTINE_DIAGNOSTIC_NOT_ADMISSIBLE', 'path': '$.schema_version',
                        'message': 'A quarantine record or diagnostic export can never be admitted as a case.'})
    return reasons


def _record(raw, error, now, commit):
    return {'schema_version': QUARANTINE_VERSION, 'state': QUARANTINED, 'intake_result': SCHEMA_REJECTION,
            'engine_decision': None, 'admitted_to_calculation': False, 'acceptance_possible': False,
            'original': {'raw_base64': b64encode(raw).decode('ascii'), 'raw_sha256': sha256(raw).hexdigest(),
                         'byte_length': len(raw)},
            'rejection': {'adapter_message': str(error), 'error_type': type(error).__name__,
                          'reasons': diagnose(raw), 'number_policy': NUMBER_NOTE},
            'quarantined_at_utc': _now(now), 'tool': tool_identity(commit)}


def intake(raw, *, now=None, commit=None):
    """Open supported input exactly like open_case; quarantine anything intake rejects."""
    raw = _bounded(raw)
    try:
        opened = open_case(raw)
    except (ValueError, TypeError, RecursionError) as error:
        record = _record(raw, error, now, commit)
        return {'operation': 'intake', 'state': QUARANTINED, 'intake_result': SCHEMA_REJECTION,
                'case': None, 'result': None, 'quarantine': record,
                'notice': 'Input rejected at intake and quarantined. Original bytes kept exactly for inspection '
                          'and diagnostic export; no calculation, proposal or acceptance is possible.'}
    return dict(opened, operation='intake', state='OPEN', intake_result=ADMITTED, quarantine=None)


def _fail(message):
    raise ValueError(f'Invalid quarantine record: {message}')


def validate_quarantine(record):
    """Strict check; returns the exact original bytes. Raises on any mismatch."""
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        _fail('unexpected or missing keys.')
    if (record['schema_version'] != QUARANTINE_VERSION or record['state'] != QUARANTINED
            or record['intake_result'] != SCHEMA_REJECTION or record['engine_decision'] is not None
            or record['admitted_to_calculation'] is not False or record['acceptance_possible'] is not False):
        _fail('state labels do not match a quarantine.')
    original = record['original']
    if not isinstance(original, dict) or set(original) != ORIGINAL_KEYS or not isinstance(original['raw_base64'], str):
        _fail('original must hold raw_base64, raw_sha256 and byte_length.')
    try:
        raw = b64decode(original['raw_base64'].encode('ascii'), validate=True)
    except (BinasciiError, ValueError, UnicodeEncodeError):
        _fail('raw_base64 is not strict base64.')
    if b64encode(raw).decode('ascii') != original['raw_base64']:
        _fail('raw_base64 is not canonical.')
    if not 0 < len(raw) <= QUARANTINE_LIMIT or original['byte_length'] != len(raw):
        _fail('byte length is outside bounds or does not match.')
    if sha256(raw).hexdigest() != original['raw_sha256']:
        _fail('raw_sha256 does not match the original bytes.')
    if not isinstance(record['rejection'], dict) or not isinstance(record['rejection'].get('reasons'), list):
        _fail('rejection reasons are missing.')
    return raw


def original_bytes(record):
    return validate_quarantine(record)


def view(record):
    """Inspection view. The bytes are evidence; the text is display only."""
    raw = validate_quarantine(record)
    try:
        text, exact = raw.decode('utf-8'), True
    except UnicodeDecodeError:
        text, exact = raw.decode('utf-8', errors='backslashreplace'), False
    return {'operation': 'quarantine_view', 'state': QUARANTINED, 'intake_result': SCHEMA_REJECTION,
            'display_text': text, 'display_is_exact_utf8': exact,
            'raw_sha256': record['original']['raw_sha256'], 'byte_length': len(raw),
            'reasons': record['rejection']['reasons'],
            'notice': 'Display only. Quarantined input cannot be calculated, proposed or accepted.'}


def export_diagnostic(record, *, now=None, commit=None):
    raw = validate_quarantine(record)
    recheck = None
    try:
        open_case(raw)
        still_rejected = False
    except (ValueError, TypeError, RecursionError) as error:
        still_rejected, recheck = True, error
    diagnostic = {
        'schema_version': DIAGNOSTIC_VERSION, 'state': QUARANTINED, 'intake_result': SCHEMA_REJECTION,
        'engine_decision': None, 'statement': STATEMENT,
        'calculation_performed': False, 'proposal_created': False, 'acceptance_performed': False,
        'original': dict(record['original']), 'rejection': record['rejection'],
        'quarantined_at_utc': record['quarantined_at_utc'], 'exported_at_utc': _now(now),
        'tool_at_quarantine': record['tool'], 'tool_at_export': tool_identity(commit),
        'export_recheck': {'raw_sha256_verified': True,
                           'still_rejected_by_current_intake': still_rejected,
                           'current_adapter_message': None if recheck is None else str(recheck),
                           'reasons_match_record': diagnose(raw) == record['rejection']['reasons']}}
    text = json.dumps(diagnostic, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    data = text.encode('utf-8')
    return {'operation': 'quarantine_export', 'state': QUARANTINED, 'intake_result': SCHEMA_REJECTION,
            'filename': f'gridshift-quarantine-{record["original"]["raw_sha256"][:12]}.json',
            'mime': 'application/json', 'text': text, 'export_sha256': sha256(data).hexdigest(),
            'diagnostic': diagnostic}


def export_original_bytes(diagnostic):
    """Round-trip helper: the exact original bytes from a diagnostic export, sha256-checked."""
    original = diagnostic['original']
    raw = b64decode(original['raw_base64'].encode('ascii'), validate=True)
    if sha256(raw).hexdigest() != original['raw_sha256'] or len(raw) != original['byte_length']:
        raise ValueError('Diagnostic export bytes do not match their recorded sha256.')
    return raw


def quarantine_execute(request):
    """Worker/UI entry for quarantine-only operations. Nothing here reaches the engine."""
    if not isinstance(request, dict) or set(request) != {'operation', 'quarantine'}:
        raise ValueError('Quarantine request must contain exactly operation and quarantine.')
    if request['operation'] == 'quarantine_export':
        return export_diagnostic(request['quarantine'])
    if request['operation'] == 'quarantine_view':
        return view(request['quarantine'])
    raise QuarantineRefusal('Only quarantine_view and quarantine_export are available for quarantined input.')


__all__ = ['IntakeRefused', 'QuarantineRefusal', 'QUARANTINE_LIMIT', 'RAW_LIMIT', 'diagnose', 'intake',
           'is_quarantined', 'validate_quarantine', 'original_bytes', 'view', 'export_diagnostic',
           'export_original_bytes', 'quarantine_execute', 'tool_identity']

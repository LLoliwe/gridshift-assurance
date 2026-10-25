"""GRIDSHIFT offline electricity-emissions prototype.

Calculations are estimates, not verified inventories, savings or carbon credits.
Period end is exclusive; no proxy-year factor selection is supported.
"""
import hashlib
import json
import os
import tempfile
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, localcontext, Context
from urllib.parse import urlparse
from pathlib import Path

# Pins this manual transcription, not the authenticity of the government PDF.
_FACTOR_BYTES = (Path(__file__).resolve().parents[1] / 'fixtures/za_grid_factor_2024.json').read_bytes()
if hashlib.sha256(_FACTOR_BYTES).hexdigest() != '13f30d6c4b20bcefee4bb26dae1ca30aa5ba32ea4fdb1717e718ce5389ca14d3':
    raise ValueError('CURATED_FACTOR_INTEGRITY: curated transcription file changed; review source before use')
CURATED_FACTOR = json.loads(_FACTOR_BYTES)

MAX_ACTIVITIES = 1000
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_ISSUES_PER_ROW = 16

BOUNDARY = 'SCOPE2_LOCATION_BASED_PURCHASED_ELECTRICITY'
FACTOR_FIELDS = ('factor_id', 'value', 'unit', 'country', 'data_year', 'boundary',
                 'source_url', 'source_title', 'source_locator', 'published_on',
                 'gwp_basis', 'uncertainty', 'transcription_status')
ACTIVITY_FIELDS = ('activity_id', 'site_id', 'meter_id', 'country', 'period_start',
                   'period_end', 'quantity', 'unit', 'source_status', 'source_note')

def _required(record, fields, label):
    if not isinstance(record, dict):
        raise ValueError(f'{label}: object required')
    if set(record) != set(fields):
        raise ValueError(f'{label}: missing or unknown fields are not accepted')
    for field in fields:
        if field not in record or record[field] is None or record[field] == '':
            raise ValueError(f'{label}: missing {field}')
        if field not in ('quantity', 'value', 'data_year'):
            if not isinstance(record[field], str) or not record[field].strip() or len(record[field]) > 2000:
                raise ValueError(f'{label}: {field} requires a meaningful string of at most 2000 characters')
            if record[field] != record[field].strip():
                raise ValueError(f'{label}: {field} must not contain outer whitespace')

def _decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('quantity/value: exact decimal string or integer required')
    if isinstance(value, str) and len(value) > 128:
        raise ValueError('NUMERIC_TOKEN_LIMIT: at most 128 characters')
    if isinstance(value, int) and value.bit_length() > 256:
        raise ValueError('NUMERIC_TOKEN_LIMIT: integer magnitude too large')
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError('quantity/value: invalid decimal') from None
    if not number.is_finite() or number < 0 or abs(number.adjusted()) > 24 or len(number.as_tuple().digits) > 24:
        raise ValueError('quantity/value: finite nonnegative decimal with at most 24 digits and exponent magnitude 24 required')
    return Decimal(0) if number.is_zero() else number

def _date(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError()
        return parsed
    except (TypeError, ValueError):
        raise ValueError('date must be YYYY-MM-DD') from None

def calculate(activity, factor):
    """Return a traceable, same-year purchased-electricity estimate or fail closed."""
    _required(activity, ACTIVITY_FIELDS, 'activity')
    _required(factor, FACTOR_FIELDS, 'factor')
    if type(factor['data_year']) is not int or not 1900 <= factor['data_year'] <= 9998:
        raise ValueError('factor data_year: integer year required')
    if factor['boundary'] != BOUNDARY or factor['unit'] != 'tCO2e/MWh':
        raise ValueError('factor boundary/unit not supported for Scope 2 location-based estimate')
    if factor['country'] != 'ZA' or activity['country'] != factor['country']:
        raise ValueError('country mismatch: prototype supports South Africa only')
    if factor['uncertainty'] != 'NOT_QUANTIFIED_IN_SOURCE':
        raise ValueError('only unquantified source uncertainty is supported')
    if activity['source_status'] not in ('SYNTHETIC', 'UNVERIFIED_USER_INPUT'):
        raise ValueError('activity must remain explicitly synthetic or unverified')
    if factor['transcription_status'] != 'MANUALLY_TRANSCRIBED_OFFICIAL_SOURCE':
        raise ValueError('factor transcription status not supported')
    source = urlparse(factor['source_url'])
    if source.scheme != 'https' or not source.netloc:
        raise ValueError('factor requires HTTPS source URL')
    _date(factor['published_on'])
    if factor != CURATED_FACTOR:
        raise ValueError('UNRECOGNIZED_FACTOR: only exact curated ZA 2024 NGGEF provenance is supported')
    start, end = _date(activity['period_start']), _date(activity['period_end'])
    if end <= start:
        raise ValueError('period end must be later than start (exclusive)')
    if start.year != factor['data_year'] or (end - timedelta(days=1)).year != factor['data_year']:
        raise ValueError('FACTOR_YEAR_MISMATCH: split periods or supply a matching-year factor; no automatic proxy')
    if activity['unit'] not in ('kWh', 'MWh'):
        raise ValueError('activity unit must be kWh or MWh; currency/power are not energy')
    quantity, rate = _decimal(activity['quantity']), _decimal(factor['value'])
    with localcontext(Context(prec=80, Emin=-999999, Emax=999999)) as context:
        context.prec = 80
        mwh = quantity / (1000 if activity['unit'] == 'kWh' else 1)
        value = mwh * rate
        result = format(value.normalize(), 'f')
        energy_mwh = format(mwh.normalize(), 'f')
    payload = {'schema_version': 'gridshift.emissions.v1',
               'emissions_tco2e': result, 'energy_mwh': energy_mwh,
               'activity_status': activity['source_status'], 'activity': deepcopy(activity),
               'factor': deepcopy(factor), 'uncertainty': factor['uncertainty'],
               'method': 'ENERGY_MWH_TIMES_GRID_FACTOR',
               'limitations': ['NOT_AN_INDEPENDENT_VERIFICATION', 'NOT_BLOCKCHAIN',
                               'NOT_MEASURED_SAVINGS', 'EXCLUDES_SCOPE3_T_AND_D',
                               'ANNUAL_AVERAGE_NOT_TIME_OF_USE', 'ACTIVITY_NOT_VERIFIED',
                               'PUBLISHED_FACTOR_INPUT_RECONCILIATION_UNRESOLVED',
                               'MARKET_BASED_NOT_COMPUTED', 'ORGANIZATIONAL_BOUNDARY_NOT_REVIEWED',
                               'NOT_FULL_SCOPE2_COMPLIANCE']}
    payload['receipt_sha256'] = _digest(payload)
    return payload


def _digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def verify_receipt(receipt):
    """Check only internal byte-content integrity, never truth or authenticity."""
    if not isinstance(receipt, dict):
        return False
    payload = deepcopy(receipt)
    expected = payload.pop('receipt_sha256', None)
    try:
        return isinstance(expected, str) and _digest(payload) == expected
    except (TypeError, ValueError):
        return False


def calculate_batch(activities, factor):
    """All-or-nothing same-factor estimate; reject duplicate or overlapping meter data."""
    if not isinstance(activities, list) or not activities:
        raise ValueError('nonempty activity list required')
    if len(activities) > MAX_ACTIVITIES:
        raise ValueError('ACTIVITY_COUNT_LIMIT: at most 1000 records per batch')
    receipts = []
    seen = set()
    intervals = {}
    for activity in activities:
        receipt = calculate(activity, factor)
        key = activity['activity_id']
        if key in seen:
            raise ValueError('duplicate activity ID')
        seen.add(key)
        meter = (activity['country'], activity['site_id'], activity['meter_id'])
        start, end = _date(activity['period_start']), _date(activity['period_end'])
        for previous_start, previous_end in intervals.get(meter, []):
            if start < previous_end and end > previous_start:
                raise ValueError('overlapping meter intervals would double-count energy')
        intervals.setdefault(meter, []).append((start, end))
        receipts.append(receipt)
    with localcontext(Context(prec=80, Emin=-999999, Emax=999999)) as context:
        context.prec = 80
        total = sum((Decimal(r['emissions_tco2e']) for r in receipts), Decimal(0))
        total_text = format(total.normalize(), 'f')
    return {'count': len(receipts), 'total_emissions_tco2e': total_text,
            'receipts': receipts, 'uncertainty': 'NOT_QUANTIFIED_IN_SOURCE',
            'activity_statuses': sorted(set(r['activity_status'] for r in receipts))}



def preflight(activities, factor):
    """Trace every row and conflict without emitting a misleading partial inventory."""
    if not isinstance(activities, list) or not activities:
        raise ValueError('nonempty activity list required')
    if len(activities) > MAX_ACTIVITIES:
        raise ValueError('ACTIVITY_COUNT_LIMIT: at most 1000 records per batch')
    rows, eligible = [], []
    for index, activity in enumerate(activities):
        identity = activity.get('activity_id') if isinstance(activity, dict) else None
        row = {'index': index, 'activity_id': identity if isinstance(identity, str) else None,
               'status': 'READY', 'issues': [], 'issue_count': 0, 'omitted_issue_count': 0}
        try:
            receipt = calculate(activity, factor)
            row['activity_status'] = receipt['activity_status']
            eligible.append(index)
        except ValueError as error:
            message = str(error)
            code = 'FACTOR_YEAR_MISMATCH' if 'FACTOR_YEAR_MISMATCH' in message else 'INVALID_INPUT'
            action = ('Use a supported same-year dataset; do not relabel activity dates or silently proxy a factor.'
                      if code == 'FACTOR_YEAR_MISMATCH' else
                      'Correct the cited field using traceable source data, then rerun the complete batch.')
            row['issues'].append({'code': code, 'message': message, 'action': action})
            row['issue_count'] += 1
        rows.append(row)
    for offset, left in enumerate(eligible):
        a = activities[left]
        for right in eligible[offset + 1:]:
            b = activities[right]
            issues = []
            if a['activity_id'] == b['activity_id']:
                issues.append(('DUPLICATE_ID', 'Activity ID occurs more than once.',
                               'Resolve duplicate records against the source; do not simply rename a duplicate.'))
            if (a['country'], a['site_id'], a['meter_id']) == (b['country'], b['site_id'], b['meter_id']):
                if a['period_start'] < b['period_end'] and a['period_end'] > b['period_start']:
                    issues.append(('OVERLAPPING_PERIOD', 'Same-meter activity periods overlap.',
                                   'Reconcile meter intervals and source quantities; do not sum overlapping totals.'))
            for code, message, action in issues:
                for current, other in ((left, right), (right, left)):
                    rows[current]['issue_count'] += 1
                    if len(rows[current]['issues']) < MAX_ISSUES_PER_ROW:
                        rows[current]['issues'].append({'code': code, 'message': message,
                                                       'action': action, 'related_index': other})
                    else:
                        rows[current]['omitted_issue_count'] += 1
    for row in rows:
        if row['issues']:
            row['status'] = 'BLOCKED'
    blocked = sum(row['status'] == 'BLOCKED' for row in rows)
    return {'schema_version': 'gridshift.preflight.v1', 'status': 'BLOCKED' if blocked else 'READY',
            'input_count': len(rows), 'blocked_count': blocked, 'rows': rows,
            'input_authenticity_verified': False,
            'next_action': 'Resolve every blocked row and rerun the entire batch.' if blocked else
                           'Structural checks passed. Calculate only with the same unchanged inputs; source truth remains unverified.'}


def _check_json_depth(text):
    """Bound parser nesting while ignoring bracket characters inside JSON strings."""
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in '[{':
            depth += 1
            if depth > 32:
                raise ValueError('JSON_NESTING_LIMIT: maximum nesting depth is 32')
        elif char in ']}':
            depth -= 1


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _write_exclusive_atomic(destination, contents):
    """Publish a complete same-filesystem file without overwriting an existing path.

    Caught write errors remove the temporary file. A process/host crash may leave
    a private temporary file; this is not a durable transaction protocol.
    """
    destination = Path(destination)
    fd, temporary = tempfile.mkstemp(prefix='.' + destination.name + '.', suffix='.tmp',
                                     dir=destination.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as target:
            target.write(contents)
            target.flush()
            os.fsync(target.fileno())
        # A hard link publishes the fully-written inode, and fails if the path
        # exists (including symlinks). Never use replacing rename here.
        os.link(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main(argv=None):
    import argparse
    import sys
    parser = argparse.ArgumentParser(description='GRIDSHIFT: offline Scope 2 estimate, not verified savings.')
    parser.add_argument('--activities', required=True, type=Path, help='JSON object with activities list')
    parser.add_argument('--output', type=Path, help='Write JSON only after all inputs validate; otherwise stdout')
    parser.add_argument('--format', choices=('json', 'html'), default='json', help='Machine-readable JSON or offline human-readable HTML')
    parser.add_argument('--preflight', action='store_true', help='Return per-row diagnostics only; exit 2 if blocked, no partial total')
    args = parser.parse_args(argv)
    try:
        if not args.activities.is_file():
            raise ValueError('INPUT_FILE_REQUIRED: regular JSON file required')
        with args.activities.open('rb') as source:
            raw = source.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError('INPUT_SIZE_LIMIT: maximum JSON input is 2 MiB')
        text = raw.decode('utf-8-sig')
        _check_json_depth(text)
        data = json.loads(text, object_pairs_hook=_unique_object)
        if not isinstance(data, dict) or set(data) != {'activities'}:
            raise ValueError('input must contain exactly an activities list')
        if args.preflight and args.format != 'json':
            raise ValueError('preflight diagnostics support JSON only')
        report = preflight(data['activities'], CURATED_FACTOR) if args.preflight else calculate_batch(data['activities'], CURATED_FACTOR)
        if args.format == 'html':
            from emissions_report import render_report
            encoded = render_report(report)
        else:
            encoded = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        if args.output:
            _write_exclusive_atomic(args.output, encoded)
        else:
            sys.stdout.write(encoded)
        return 2 if args.preflight and report['status'] == 'BLOCKED' else 0
    except (ValueError, OSError, RecursionError) as error:
        print(f'BLOCKED: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

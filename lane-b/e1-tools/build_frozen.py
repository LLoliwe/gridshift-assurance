"""Builds the E1 frozen folder (data only). Expected outcomes are hand-derived from the
written policy (docs/RECONCILIATION.md, factor 0.960 tCO2e/MWh); this script never imports
or runs the engine, the adapter or any comparator. Synthetic, invented data only."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'lane-b/e1-frozen'
F = Decimal('0.960')
LIMITS = ['NOT_AN_INDEPENDENT_VERIFICATION', 'NOT_BLOCKCHAIN', 'NOT_MEASURED_SAVINGS', 'EXCLUDES_SCOPE3_T_AND_D',
          'ANNUAL_AVERAGE_NOT_TIME_OF_USE', 'ACTIVITY_NOT_VERIFIED', 'PUBLISHED_FACTOR_INPUT_RECONCILIATION_UNRESOLVED',
          'MARKET_BASED_NOT_COMPUTED', 'ORGANIZATIONAL_BOUNDARY_NOT_REVIEWED', 'NOT_FULL_SCOPE2_COMPLIANCE']
Y0, Y1, MID = '2024-01-01', '2025-01-01', '2024-07-01'


def fmt(x):
    return format(x.normalize(), 'f') if x else '0'


def rec(rid, meter, q, unit='MWh', start=Y0, end=Y1, action='ORIGINAL', target=None, site='SITE'):
    return {'record_id': rid, 'source_id': f'doc-{rid}', 'entity_id': 'E1-ENTITY', 'site_id': site, 'meter_id': meter,
            'country': 'ZA', 'period_start': start, 'period_end': end, 'quantity': q, 'unit': unit,
            'source_status': 'SYNTHETIC', 'source_note': 'Invented E1 test evidence, not a real meter.',
            'action': action, 'target_record_id': target}


def cov(meter, start=Y0, end=Y1, site='SITE'):
    return {'entity_id': 'E1-ENTITY', 'site_id': site, 'meter_id': meter, 'country': 'ZA', 'period_start': start, 'period_end': end}


def pkg(cid, records, coverage, energy, emissions=None, year=2024, limitations=None):
    if emissions is None:
        emissions = fmt(Decimal(energy) * F)
    return {'schema_version': 'gridshift.reconciliation.input.v1', 'package_id': cid, 'records': records,
            'coverage': coverage, 'report': {'claim_type': 'CONDITIONAL_INVENTORY_ESTIMATE', 'energy_mwh': energy,
            'emissions_tco2e': emissions, 'factor_id': 'ZA_NGGEF_2024_DFFE_2026', 'data_year': year,
            'boundary': 'SCOPE2_LOCATION_BASED_PURCHASED_ELECTRICITY', 'activity_statuses': ['SYNTHETIC'],
            'limitations': list(LIMITS if limitations is None else limitations)}, 'resolutions': []}


cases = []


def add(cid, family, package, decision, energy=None, reason=None, note=''):
    exp = {'decision': decision, 'primary_reason': reason, 'note': note}
    if energy is not None:
        exp.update(energy_mwh=fmt(Decimal(energy)), emissions_tco2e=fmt(Decimal(energy) * F))
    cases.append((cid, family, package, exp))


# CORRECT (20)
for i, (a, b, claim) in enumerate([('100', '20', '200'), ('55.5', '44.5', '90'), ('12', '0.75', '13'), ('300', '1', '0.3')]):
    cid = f'E1-C{i+1:02d}'; tot = Decimal(a) + Decimal(b)
    add(cid, 'F1_REPORT_TOTAL_MISMATCH', pkg(cid, [rec('A', 'M1', a), rec('B', 'M2', b)], [cov('M1'), cov('M2')], claim),
        'CORRECT', tot, 'REPORT_TOTAL_MISMATCH', 'Two complete meters; report total differs from the sum.')
for i, (a, b, c) in enumerate([('100', '80', '20'), ('50', '60', '5'), ('9.9', '9.1', '1'), ('400', '390.5', '0.5')]):
    cid = f'E1-C{i+5:02d}'
    add(cid, 'F2_EXPLICIT_FULL_REPLACEMENT', pkg(cid, [rec('A', 'M1', a), rec('B', 'M1', b, action='FULL_REPLACEMENT', target='A'), rec('C', 'M2', c)],
        [cov('M1'), cov('M2')], fmt(Decimal(a) + Decimal(c))), 'CORRECT', Decimal(b) + Decimal(c), 'SUPPORTED_LINEAGE_CORRECTION',
        'B explicitly fully replaces A (same scope and interval); report used A.')
for i, (a, x) in enumerate([('70', '70'), ('33', '12'), ('8.25', '8.25')]):
    cid = f'E1-C{i+9:02d}'
    add(cid, 'F3_EXPLICIT_VOID_OF_DUPLICATE', pkg(cid, [rec('A', 'M1', a), rec('X', 'M1', x), rec('V', 'M1', '0', action='FULL_VOID', target='X')],
        [cov('M1')], fmt(Decimal(a) + Decimal(x))), 'CORRECT', Decimal(a), 'SUPPORTED_LINEAGE_CORRECTION',
        'V explicitly voids duplicate original X; report counted both.')
for i, (kwh, claim) in enumerate([('50000', '50000'), ('1250', '1250'), ('999', '0.0999')]):
    cid = f'E1-C{i+12:02d}'
    add(cid, 'F4_KWH_UNIT_TRAP', pkg(cid, [rec('A', 'M1', kwh, unit='kWh')], [cov('M1')], claim), 'CORRECT', Decimal(kwh) / 1000,
        'REPORT_TOTAL_MISMATCH', 'Record is in kWh; the report misreads the unit.')
for i, (h1, h2, claim) in enumerate([('40', '60', '60'), ('10.5', '10.5', '10.5'), ('1', '2', '4')]):
    cid = f'E1-C{i+15:02d}'
    add(cid, 'F5_SPLIT_PERIOD_PARTIAL_COUNT', pkg(cid, [rec('H1', 'M1', h1, end=MID), rec('H2', 'M1', h2, start=MID)], [cov('M1')], claim),
        'CORRECT', Decimal(h1) + Decimal(h2), 'REPORT_TOTAL_MISMATCH', 'Two contiguous half-year records; report counts one half or errs.')
for i, (a, b, c) in enumerate([('100', '90', '95'), ('20', '30', '25'), ('5', '5.5', '6')]):
    cid = f'E1-C{i+18:02d}'
    add(cid, 'F6_REPLACEMENT_CHAIN', pkg(cid, [rec('A', 'M1', a), rec('B', 'M1', b, action='FULL_REPLACEMENT', target='A'),
        rec('C', 'M1', c, action='FULL_REPLACEMENT', target='B')], [cov('M1')], b), 'CORRECT', Decimal(c), 'SUPPORTED_LINEAGE_CORRECTION',
        'C fully replaces B, which fully replaced A; report used the intermediate B.')
# WITHHOLD (12)
add('E1-W01', 'W1_INCOMPLETE_COVERAGE', pkg('E1-W01', [rec('A', 'M1', '100')], [cov('M1'), cov('M2')], '100'), 'WITHHOLD', None, 'COVERAGE_UNRESOLVED', 'Declared meter M2 has no record; missing is not zero.')
add('E1-W02', 'W1_INCOMPLETE_COVERAGE', pkg('E1-W02', [rec('H1', 'M1', '40', end=MID)], [cov('M1')], '80'), 'WITHHOLD', None, 'COVERAGE_UNRESOLVED', 'Second half-year missing.')
add('E1-W03', 'W2_UNEXPLAINED_OVERLAP', pkg('E1-W03', [rec('A', 'M1', '100'), rec('B', 'M1', '100')], [cov('M1')], '100'), 'WITHHOLD', None, 'AMBIGUOUS_OVERLAP', 'Two originals, same meter and period, no lineage (possible duplicate, not assumed).')
add('E1-W04', 'W2_UNEXPLAINED_OVERLAP', pkg('E1-W04', [rec('A', 'M1', '60', end='2024-08-01'), rec('B', 'M1', '50', start=MID)], [cov('M1')], '110'), 'WITHHOLD', None, 'AMBIGUOUS_OVERLAP', 'Periods overlap by one month.')
for i in range(2):
    cid = f'E1-W{5+i:02d}'
    add(cid, 'W3_CONFLICTING_SUCCESSORS', pkg(cid, [rec('A', 'M1', '100'), rec('B', 'M1', '90', action='FULL_REPLACEMENT', target='A'),
        rec('C', 'M1', str(80 + i), action='FULL_REPLACEMENT', target='A')], [cov('M1')], '100'), 'WITHHOLD', None, 'CONFLICTING_SUCCESSORS', 'Two documents each claim to replace A.')
add('E1-W07', 'W4_PARTIAL_OR_CROSS_SCOPE', pkg('E1-W07', [rec('A', 'M1', '100'), rec('B', 'M1', '45', end=MID, action='FULL_REPLACEMENT', target='A')], [cov('M1')], '100'), 'WITHHOLD', None, 'PARTIAL_OR_CROSS_SCOPE', 'Replacement covers only half of the original interval.')
add('E1-W08', 'W4_PARTIAL_OR_CROSS_SCOPE', pkg('E1-W08', [rec('A', 'M1', '100'), rec('B', 'M2', '90', action='FULL_REPLACEMENT', target='A')], [cov('M1'), cov('M2')], '100'), 'WITHHOLD', None, 'PARTIAL_OR_CROSS_SCOPE', 'Replacement names a different meter.')
add('E1-W09', 'W5_MISSING_TARGET', pkg('E1-W09', [rec('B', 'M1', '90', action='FULL_REPLACEMENT', target='A')], [cov('M1')], '90'), 'WITHHOLD', None, 'MISSING_TARGET', 'Replacement references a record that was not supplied.')
add('E1-W10', 'W6_NON_ENERGY_UNIT', pkg('E1-W10', [rec('A', 'M1', '25000', unit='ZAR')], [cov('M1')], '25'), 'WITHHOLD', None, 'SOURCE_NOT_SUPPORTED', 'A currency amount is not energy.')
add('E1-W11', 'W7_WRONG_DATA_YEAR', pkg('E1-W11', [rec('A', 'M1', '100')], [cov('M1')], '100', year=2023), 'WITHHOLD', None, 'REPORT_FACTOR_MISMATCH', 'Report declares data year 2023 (a valid JSON integer) against the 2024 factor.')
add('E1-W12', 'W8_LIMITATION_DROPPED', pkg('E1-W12', [rec('A', 'M1', '100')], [cov('M1')], '100', limitations=LIMITS[:-1]), 'WITHHOLD', None, 'LIMITATIONS_LOSS', 'A required limitation was dropped from the report.')
# ACCEPT (8)
for i, q in enumerate(['100', '7.125']):
    cid = f'E1-A{i+1:02d}'; add(cid, 'A1_CONSISTENT_SINGLE_METER', pkg(cid, [rec('A', 'M1', q)], [cov('M1')], q), 'ACCEPT', Decimal(q), None, 'Consistent single complete meter.')
for i, (a, b) in enumerate([('100', '20'), ('0.5', '0.25')]):
    cid = f'E1-A{i+3:02d}'; add(cid, 'A2_CONSISTENT_TWO_METERS', pkg(cid, [rec('A', 'M1', a), rec('B', 'M2', b)], [cov('M1'), cov('M2')], fmt(Decimal(a) + Decimal(b))), 'ACCEPT', Decimal(a) + Decimal(b), None, 'Consistent two complete meters.')
for i, kwh in enumerate(['50000', '1250']):
    cid = f'E1-A{i+5:02d}'; add(cid, 'A3_CONSISTENT_KWH', pkg(cid, [rec('A', 'M1', kwh, unit='kWh')], [cov('M1')], fmt(Decimal(kwh) / 1000)), 'ACCEPT', Decimal(kwh) / 1000, None, 'kWh record correctly converted in the report.')
for i, (h1, h2) in enumerate([('40', '60'), ('1', '2')]):
    cid = f'E1-A{i+7:02d}'; add(cid, 'A4_CONSISTENT_SPLIT_PERIOD', pkg(cid, [rec('H1', 'M1', h1, end=MID), rec('H2', 'M1', h2, start=MID)], [cov('M1')], fmt(Decimal(h1) + Decimal(h2))), 'ACCEPT', Decimal(h1) + Decimal(h2), None, 'Contiguous half-years, consistent report.')

assert len(cases) == 40 and [e['decision'] for *_, e in cases].count('CORRECT') == 20
OUT.mkdir(parents=True, exist_ok=True); (OUT / 'cases').mkdir(exist_ok=True)
expected = {}
for cid, family, package, exp in cases:
    (OUT / 'cases' / f'{cid}.json').write_text(json.dumps(package, indent=2, ensure_ascii=False) + '\n')
    expected[cid] = {'family': family, **exp}
(OUT / 'EXPECTED_OUTCOMES.json').write_text(json.dumps({'schema': 'gridshift.laneb.e1.expected.v1', 'factor_tco2e_per_mwh': '0.960',
    'authorship': 'BUILDER_AUTHORED_FROM_WRITTEN_POLICY_NOT_INDEPENDENT', 'cases': expected}, indent=1, ensure_ascii=False) + '\n')
print(len(cases))

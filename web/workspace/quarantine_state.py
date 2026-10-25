"""AC-5 state labels and the hard quarantine guard. No imports from the adapter.

Three distinct things that must never be merged or relabelled:
  QUARANTINED       storage/inspection STATE. Untrusted original bytes kept exactly,
                    viewable and exportable as a diagnostic, never admitted to
                    calculation and never acceptable.
  SCHEMA_REJECTION  INTAKE RESULT. The input is unsupported. Not an engine decision.
  WITHHOLD          POLICY RESULT of the reconciliation engine, only for supported input
                    that was admitted and has no established total. Never produced here.
"""

QUARANTINE_VERSION = 'gridshift.workspace.quarantine.v1'
DIAGNOSTIC_VERSION = 'gridshift.workspace.quarantine-diagnostic.v1'
QUARANTINED = 'QUARANTINED'
SCHEMA_REJECTION = 'SCHEMA_REJECTION'
ADMITTED = 'ADMITTED'
WITHHOLD = 'WITHHOLD'  # engine policy label; listed only so tests can prove it is never used here
STATE_LABELS = {'storage_state': QUARANTINED, 'intake_result': SCHEMA_REJECTION, 'engine_policy_result': WITHHOLD}

REFUSAL = ('QUARANTINED: this input was rejected at intake (SCHEMA_REJECTION) and is held for inspection '
           'and diagnostic export only. Calculation, proposal, acceptance, save and case export are refused; '
           'no engine decision exists for it.')


class QuarantineRefusal(ValueError):
    """Raised when any calculation/proposal/acceptance path is handed quarantined material."""


def is_quarantined(value):
    return isinstance(value, dict) and (
        value.get('schema_version') in (QUARANTINE_VERSION, DIAGNOSTIC_VERSION)
        or value.get('state') == QUARANTINED
        or value.get('intake_result') == SCHEMA_REJECTION)


def refuse_if_quarantined(request):
    """Hard refusal. Checks the request itself, its case and any attached quarantine record."""
    if not isinstance(request, dict):
        return
    candidates = [request, request.get('case'), request.get('quarantine')]
    if 'quarantine' in request or any(is_quarantined(item) for item in candidates):
        raise QuarantineRefusal(REFUSAL)

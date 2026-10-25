# AC-5: bounded raw-file quarantine and diagnostic export

Development prototype, synthetic tests only. Not an independent review.

## Three states that are never merged or relabelled

| Label | Kind | Meaning |
|---|---|---|
| `QUARANTINED` | storage / inspection **state** | Untrusted original bytes kept exactly (base64 + sha256). Viewable and exportable as a diagnostic. Never admitted to calculation, never proposable, never acceptable. |
| `SCHEMA_REJECTION` | intake **result** | The input is unsupported. It is **not** an engine decision; `engine_decision` is always `null`. |
| `WITHHOLD` | engine **policy result** | Only for valid, supported input that was admitted and has no established total (e.g. `web/reconcile/missing-edge.json`). Never produced by quarantine. |

A schema failure is never labelled WITHHOLD by the quarantine path; the record and the
diagnostic export do not contain that word (tested).

## Entry points (`web/workspace/quarantine.py`)

- `intake(raw)` — bounded intake. Supported input opens exactly as `case_adapter.open_case`
  (state `OPEN`, intake result `ADMITTED`). Anything `open_case` rejects becomes a
  quarantine record (state `QUARANTINED`, intake result `SCHEMA_REJECTION`).
- `view(record)` — display text for inspection (`display_is_exact_utf8` says whether the text is
  exact; the bytes, not the text, are the evidence).
- `export_diagnostic(record)` — canonical JSON diagnostic containing: the original bytes as
  byte-exact base64 and their sha256 and length; the adapter's refusal message plus
  field-specific reasons (code, JSON path, exact source token where applicable);
  `quarantined_at_utc` and `exported_at_utc`; tool identity at quarantine and at export
  (module/schema versions, sha256 of `quarantine.py`, `quarantine_state.py` and
  `case_adapter.py`, git commit when available); an export-time recheck; and the explicit
  statement **"NO CALCULATION, NO PROPOSAL AND NO ACCEPTANCE OCCURRED"** with
  `calculation_performed`, `proposal_created` and `acceptance_performed` all `false`.
- `export_original_bytes(diagnostic)` — returns the exact original bytes, sha256-checked.

Field-specific reasons are computed in memory from the exact bytes with the same strict
parser settings (UTF-8, depth bound, duplicate-key rejection, non-finite rejection), but
number tokens are kept as source text, so every offending number is reported with its path
(`FLOAT_OR_EXPONENT_NUMBER`, `INTEGER_OUTSIDE_PORTABLE_RANGE`), up to 50 findings. Parse-level
failures report `INVALID_UTF8` (byte offset), `UTF8_BOM`, `JSON_SYNTAX` (line/column),
`DUPLICATE_KEY`, `NON_FINITE_CONSTANT` or `PARSE_REJECTION`. Re-intake of a quarantine record or
diagnostic is itself quarantined with `QUARANTINE_DIAGNOSTIC_NOT_ADMISSIBLE`.

## Hard refusal

`quarantine_state.refuse_if_quarantined` is called by `case_adapter.open_case` and
`case_adapter.execute` (a two-line hook; no existing message strings changed). Review
(calculation and proposal), accept, save and export raise `QuarantineRefusal` for a quarantine
record or diagnostic passed as the case, as the request, or under a `quarantine` key. The
worker also refuses these before Python. Quarantine-only operations are `quarantine_view` and
`quarantine_export`.

## Bounds

The existing native intake limits apply unchanged: 1–786432 bytes (`ENVELOPE_LIMIT`). Empty,
oversized or non-bytes input raises `IntakeRefused` before anything is stored; no record is
produced and the fixed intake temp file does not remain. Raw engine packages above 64 KiB are
still refused by the adapter; within 786432 bytes such input is quarantined, not opened.

## Number policy

Float and exponent JSON number tokens (`2024.0`, `2.024e3`, `1.0`, `1e400`) are rejected
**conservatively**, even when numerically integral, because JSON numbers do not survive the
browser/JavaScript boundary as exact tokens. The ±(2^53−1) integer bound is a **transport**
limit of JSON numbers in JavaScript, **not an accounting limit**. Exact quantities belong in
decimal strings, which the engine reads with `Decimal`.

## Runtime status

- Native CPython: implemented and tested (`web-tests/test_workspace_quarantine.py`).
- Worker bridge (`workspace-worker.js`): new `intake`, `quarantine_view` and `quarantine_export`
  operations; quarantine modules pinned by sha256 and loaded like the adapter; `open` unchanged.
  Contract-tested with a mocked runtime (`web-tests/workspace-quarantine-contract.mjs`).
- Pyodide 314.0.7 (WASM) in Node, driving the worker's real `handleMessage` with real Python:
  intake states and reasons matched native for the tested inputs, export round-trips were
  byte-exact and refusals held (lane evidence log, not committed). The git commit is
  unavailable in WASM, so the source sha256 values identify the tool there.
- **Not done:** no real browser/Web Worker run (Playwright), and no workspace UI for
  quarantine (`workspace.js` is unchanged; the UI still uses `open`). Browser parity is not claimed.

## Known gap (not changed here)

The protected reconciliation engine labels its own schema failures (for example an unknown
string-valued field that `open_case` admits) as `WITHHOLD` with finding `INVALID_SCHEMA`.
Those inputs are portable JSON, so they open and are reviewed by the engine rather than
quarantined. That conflicts with the three-state semantics above and needs an owner decision
on the engine or the adapter. The frozen C12/C13/C14/C31 expectations (`open OK → WITHHOLD`)
also still disagree with the current intake refusal; they are frozen and were not edited.

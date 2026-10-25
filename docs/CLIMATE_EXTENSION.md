# GRIDSHIFT electricity-emissions evidence extension

Reviewed release candidate, 25 October 2026. The owner approved the scoped MIT source release. This extends the existing GRIDSHIFT project; it is not a newly invented venture.

## What actually runs
Python 3.10+ standard library, offline, no account or package install:

```sh
python -m unittest discover -s tests -v
python src/emissions.py --activities fixtures/demo_energy_2024.json
python src/emissions.py --activities fixtures/demo_energy_2024.json --format html --output my-report.html
```

The output path must be new. Existing files are never overwritten. Open the generated HTML in a normal browser locally. It contains no remote scripts, fonts or telemetry. The HTML renderer recalculates the report before presenting it. Browser visual/interactive QA in this executor has not been established; JSON/HTML semantic and escaping tests are executed.

The packaged 500 MWh activity is invented, matching the official report's worked-example quantity. The estimate is 480 tCO2e, **not measured savings**. The original 2026 invoice fixtures remain unchanged and are NOT silently relabelled to 2024. No automatic invoice-to-emissions integration is claimed.

## Scientific boundary
The only supported factor is the manually transcribed South African 2024 NGGEF, 0.960 tCO2e/MWh, published 11 September 2026. It is for purchased-electricity Scope 2 location-based estimation. It excludes transmission/distribution losses assigned to Scope 3. It is an annual national average, not a supplier-specific, hourly or marginal factor. Only matching 2024 activity periods are accepted; the end date is exclusive.

Source: DFFE, Government Gazette 55353, Notice 7891, South Africa's 2024 Grid Emission Factors Report, Table 1 printed page 3 and Appendix A printed page 19.
https://www.gov.za/sites/default/files/gcis_document/202609/55353gon7891.pdf

The source's GWP basis is IPCC Second Assessment Report. No numerical uncertainty interval or gas-by-gas breakdown is supplied here. Source metadata labels uncertainty NOT_QUANTIFIED_IN_SOURCE; exact decimal arithmetic does not remove measurement/transcription uncertainty. The report contains some ambiguous loss-adjustment prose and outdated 2023 labels in its contents; the explicit Scope 2/Scope 3 methodology and 2024 factor table govern this transcription. The PDF is not bundled, and no open-content redistribution licence is asserted.

## Refusal and integrity behavior
- Strict schema: unknown fields, claimed verified activity, or embedded savings fields are rejected.
- Factor identity/value/year/source/boundary must match the curated transcription exactly. Its file checksum detects accidental local changes, not malicious source edits or government authenticity.
- Exact decimal strings/integer inputs, no floats; finite nonnegative values; bounded precision and exponent. Only kWh/MWh, never currency-to-energy inference.
- Country/year/unit/boundary mismatch stops calculation. No proxy factor fallback.
- Duplicate activity IDs and overlapping intervals for the same country/site/meter stop batch aggregation. Adjacent periods are allowed; different names for the same physical meter remain an external identity-quality risk.
- Synthetic/unverified labels remain attached to each result.
- Receipts are deterministic SHA-256 integrity checksums. Anyone can recompute a checksum; **not a signature, blockchain, immutable ledger, proof of truthful input or independent assurance**.
- Batch results are all-or-nothing. The renderer rejects altered totals/receipts by recalculation.

## What remains unproved
No real customer data, meter authentication, field pilot, causal avoided emissions, carbon credits, production security, customer adoption or superiority to a well-built spreadsheet is demonstrated. Original baseline tariff figures are invented. The test suite and benchmark use authored synthetic cases, not representative field data. Original invoice-engine tests and unrelated funding-registry tests must not be counted as evidence of climate measurement.

## Provenance and publication
The original source archive was retrieved from the existing GRIDSHIFT Library asset dated 11 October 2026. All 17 original internal manifest entries matched before extension. The retrieved archive hash differs from a hash in historical Linear records; this remains unresolved and must be disclosed rather than calling the archives identical. Original manifest-listed files were preserved; the new module, tests, fixtures and documentation are additions on 25 October 2026 after explicit authorization.

Development and review are AI-assisted. The owner approved the isolated invoice/emissions source, synthetic fixtures, tests and documentation for public MIT release with Pryntor (Pty) Ltd as copyright holder on 25 October 2026. Private funding/GTM/strategy documents are excluded. This source release does not establish video publication, hosted deployment, final competition submission or organizer eligibility approval.

## Batch preflight

```sh
python src/emissions.py --activities fixtures/demo_energy_2024.json --preflight
```

Preflight returns one diagnostic row for every supplied record, including row index, activity ID, source status when structurally valid, issues and suggested corrective actions. Both sides of duplicate/overlap conflicts are identified. BLOCKED exits with code 2 and emits **no partial emissions total**. READY means structural checks passed, not that input data were independently verified. Calculate using the same unchanged input after resolving all issues. Physical meter aliases cannot be resolved without a trusted external identity mapping.

## Resource limits and conservative year policy
The hardened working revision accepts at most 1,000 records per batch and 2 MiB of CLI JSON input. Numeric tokens are at most 128 characters before decimal parsing, in addition to the 24-digit/exponent arithmetic bounds. Preflight keeps at most 16 issue examples per row and reports the complete issue count plus omitted-issue count explicitly. Every input row still appears and remains blocked when any conflict exists; this is a bounded diagnostic display, not silently dropped records or partial inventory reporting.

Matching factor/activity years is a deliberately conservative prototype policy, not a claim that every accounting standard universally prohibits disclosed proxy factors. The current official source supports retrospective 2024 activity only in this implementation. There is no implicit permission to apply it to 2026, and no proxy methodology or invented uncertainty band is offered. Current-year usefulness requires a separately reviewed factor/proxy policy and transparent assumptions.

## Published-factor reconciliation and reporting scope
The published 0.960 factor is retained, not independently re-derived. A separate arithmetic audit could not reconcile the report's input tables and auxiliary-consumption footnotes; see [SOURCE_RECONCILIATION.md](SOURCE_RECONCILIATION.md). This unresolved source discrepancy is a mandatory machine-readable and rendered limitation. This electricity-only location-based estimate does not compute market-based emissions, review organizational boundaries or establish full Scope 2 compliance.

## Serialization and output failure contract
Receipts use the exact preserved input strings with Python sorted-key JSON serialization, not RFC 8785 JCS. Equivalent numeric spellings and Unicode normalization forms can produce different hashes. No semantic equivalence, issuer identity, signature or authenticity is asserted. Signed zero is displayed as zero while its original input spelling remains recorded.

The emissions CLI writes a temporary file in the target directory, flushes and fsyncs its content, then publishes it by an exclusive hard link and removes the temporary name. Existing destinations are not replaced. Caught failures before publication leave no final output; abrupt process or machine failure can leave temporary files. A cleanup failure after publication can leave a complete final file and temporary name while the command reports failure. This is not a power-loss durability guarantee or multi-file transaction. Filesystems without suitable hard-link support fail closed; no unsafe overwrite fallback is used.

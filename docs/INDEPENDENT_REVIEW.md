# GRIDSHIFT emissions extension: independent adversarial review

Review date: 25 October 2026 UTC. Scope: offline deterministic Python calculator, its CLI and HTML renderer. No external publication, provider submission, cloud deployment or browser rendering is implied by this review.

## Threat model and limits

The implementation is intended to fail closed on malformed or inconsistent untrusted activity data and accidental report edits. It is not a security boundary against a malicious operator who can modify Python source, the curated factor registry or original inputs. A SHA-256 receipt is reproducible content integrity, not a signature, timestamp, blockchain, independent verification or evidence that an energy quantity was measured. An attacker can change data and recompute its hash. The renderer separately recalculates quantities and compares the report, but still cannot establish input truth.

The official factor is a manually transcribed annual national average. Exact Decimal arithmetic does not remove transcription risk, measurement error, source methodology limits or unquantified source uncertainty. Results cannot establish avoided emissions, time-of-use optimization, carbon credits, renewable procurement or measured savings. Input statuses remain synthetic or unverified. Country/year mismatch is rejected, not silently proxied.

## Independent test design

`tests/test_emissions_adversarial.py` tests behavior against literal worked values and an independent rational arithmetic oracle. The randomized holdout uses Python `random.Random(20241025)` to generate 100 energy quantities, six fractional places, both kWh and MWh. Expected values use `fractions.Fraction` with the independently reduced rate 24/25 and optional division by 1000; they do not call implementation arithmetic helpers. The test also exercises exponent boundaries, local Decimal context perturbation, duplicate and containing periods, adjacent periods, mixed statuses, malformed metadata and URL types, spoofed factor provenance, unknown claim fields, CLI input preservation and aliased output paths.

Original adversarial runs found real defects, not only happy-path coverage:

- Changed rate or year could retain the official factor identity; arbitrary HTTPS sources were accepted. Fixed by exact curated-factor identity/provenance comparison.
- Blank/nonstring metadata was accepted; numeric URL types could raise an unexpected exception. Fixed by typed meaningful string validation.
- Accepted Decimal object inputs failed receipt JSON serialization. Fixed by explicitly accepting only exact decimal strings or integers.
- Ambient Decimal exponent limits could make valid arithmetic overflow. Fixed by explicit computation context.
- Unrecognized input fields could smuggle verification or savings claims into the receipt. Fixed by exact schema validation.
- Outer whitespace in meter/site identifiers bypassed overlap detection. Fixed by rejecting outer whitespace.
- CLI output could overwrite its own source activity file or an alias. Fixed by exclusive no-clobber output creation, tested for direct path, symbolic link and hard link.
- A forged numeric result with a recomputed SHA-256 hash is correctly rejected by renderer recalculation.
- A malformed but hash-valid receipt without activity caused `KeyError` rather than a validation error. Fixed by explicit receipt-shape validation; independent regression now passes.

## Evidence

Execution logs are in `outputs/climate/adversarial-*.txt`. Initial failures are retained. Independent terminal verification at 05:09 UTC: `python -m unittest discover -s tests -v` passed all **105 tests**, exit code 0, in 0.337 seconds. This includes 30 independent adversarial test methods (the rational-oracle method contains 100 deterministic generated cases), existing invoice/funding tests and new core/CLI/renderer tests. Passing counts alone do not constitute certification.

Reviewed source hashes are recorded in `outputs/climate/independent-reviewed-sha256.txt`:

- `src/emissions.py`: `095f3df6f7cb01328a2e6103d8dfcb9ebf06d5392f8d40799542cefef6c8e762`
- `src/emissions_report.py`: `0ea3af51231f23097485c467cea932dbcc58eb5323a6e7ad2b6a1d3c710338f6`
- `tests/test_emissions_adversarial.py`: `b945c9f1acf1abb6e1f297dc4fc4ac19fa3624a113c236ea89f19a604d419867`
- `fixtures/za_grid_factor_2024.json`: `13f30d6c4b20bcefee4bb26dae1ca30aa5ba32ea4fdb1717e718ce5389ca14d3`

No unresolved correctness defect was reproduced in this bounded review at that checkpoint. Browser pixel rendering, public deployment, competition eligibility, rights/publication approval and the original source ZIP lineage mismatch were outside this verification. Later source changes require rerunning affected and full checks.

No production source was changed by this independent reviewer. All changes were isolated to independent tests and review evidence.


## Preflight extension review — 05:13 UTC

The new preflight API was independently exercised with 196 ordered two-record combinations of valid, malformed, wrong-year, bad-unit, duplicate and overlapping inputs. For every case, READY was equivalent to successful `calculate_batch`; every row retained its original index and there were no partial emissions totals. Separate checks confirmed permutation-stable conflict identities and reciprocal related-row indexes, mixed status preservation, unchanged input/factor objects and invalid factors blocking all records. This is a structural consistency check, not independent measurement or source verification.

Latest independent full-suite run: **115 tests passed**, exit 0, 0.417 seconds, including **34 independent adversarial test methods** (100 seeded rational arithmetic cases and 196 explicit pair combinations within two methods, not presented as separate test counts). Includes current preflight CLI integration tests. No additional defect was reproduced. Earlier 105-test hashes above are historical and superseded by the following current hashes:

```text
c368f0ef3ac91ecf42fa8a182f099597396ff8bd0ebfc68d477163beb4cf6909  src/emissions.py
0ea3af51231f23097485c467cea932dbcc58eb5323a6e7ad2b6a1d3c710338f6  src/emissions_report.py
742fe1ba3ffe07b9110dfb366ec609daa2afe7a787410612e673a1e71d2a22e8  tests/test_emissions_adversarial.py
13f30d6c4b20bcefee4bb26dae1ca30aa5ba32ea4fdb1717e718ce5389ca14d3  fixtures/za_grid_factor_2024.json
```

Final execution log: `outputs/climate/adversarial-final-suite.txt`; preflight-specific independent log: `outputs/climate/adversarial-preflight-run.txt`.


## Resource-hardening revision review — 05:22 UTC

New independent edge tests confirm exactly 1000 valid rows are accepted, a128-character numeric token is accepted while129characters are rejected, valid JSON padded to exactly2MiB is accepted, and deeply nested JSON fails cleanly without traceback. Dense duplicate-plus-overlap graphs preserve complete issue counts even when only16examples are stored. The current full suite passes **124 tests**, including39independent methods; exit0,0.606seconds. No new unresolved defect reproduced.

Single local maximum-row observation:1000identical records, each with1998directed issues(duplicate ID plus overlap against999others),16stored examples and1982explicit omissions. All1000rows BLOCKED. Runtime0.497seconds; JSON output3,240,119bytes. This is a single machine observation, not a comparative benchmark, SLA or capacity guarantee. See `independent-resource-observation.json` for runtime environment and source hash. The2MiB limit is on input, not output.

Current reviewed hashes supersede earlier checkpoints:
```text
533dc1fb08b40c04fe8240af8ece593b1f427e53b9b725d3001e08e3a06d2a24  src/emissions.py
0ea3af51231f23097485c467cea932dbcc58eb5323a6e7ad2b6a1d3c710338f6  src/emissions_report.py
2fd927f896fe07ce3d4148a0f9853c8915d8a9f1d4d152580a3c54674719826b  tests/test_emissions_adversarial.py
13f30d6c4b20bcefee4bb26dae1ca30aa5ba32ea4fdb1717e718ce5389ca14d3  fixtures/za_grid_factor_2024.json
```

### Correction: deeper parser recursion regression — 05:24 UTC

The earlier 2,000-array-level case was parsed successfully by this Python 3.12 decoder and then rejected on input shape; it did **not** establish parser recursion safety. At the implementer's request, the test now explicitly sets subprocess recursion limit to 1,000 and supplies 10,000 nested arrays (20,001 bytes, within the byte ceiling). This reproduces an unhandled `RecursionError`: process exit 1 instead of clean BLOCKED exit 2. Red evidence is in `adversarial-deep-json-red.txt`. Previous resource review's no-unresolved-defect conclusion is superseded pending this fix and revalidation.


## Frozen v2 independent checkpoint — 05:25 UTC

Parser recursion gap is now closed: bounded JSON nesting is checked before parsing, ignoring brackets within quoted strings, with defensive RecursionError handling. The strengthened10,000-array-level subprocess regression now passes cleanly. Full final suite: **126/126 tests pass**, exit0,0.774seconds, including39independent adversarial test methods. No unresolved defect reproduced within this review scope. This final checkpoint supersedes earlier statuses and hashes; no further scope expansion is part of this review.

```text
132279311d043d49eabd8e618c43f6f8ae309e32ffe40e94e2d371e5697d1d9f  src/emissions.py
0ea3af51231f23097485c467cea932dbcc58eb5323a6e7ad2b6a1d3c710338f6  src/emissions_report.py
fd486ce323b7b45c09111c62d816b0ee68fa68b055c41346196532230a3733f7  tests/test_emissions_adversarial.py
13f30d6c4b20bcefee4bb26dae1ca30aa5ba32ea4fdb1717e718ce5389ca14d3  fixtures/za_grid_factor_2024.json
```

## Post-v2 narrow failure review — 05:30 UTC

A real filesystem failure injection reproduced a gap not covered by successful no-clobber tests: after 64 actual bytes were written and flushed, an injected ENOSPC caused CLI exit 2 but left the truncated file visible at its final path. Test `test_cli_partial_write_failure_leaves_no_final_or_temporary_report` and log `adversarial-torn-write-red.txt` preserve proof. Only the nondeterministic I/O exception is mocked; the file contents/state and CLI result are real. A fix must preserve existing-file and alias protection while staging output before publication. Cleanup after caught failures is testable; no guarantee of zero temporary residue after SIGKILL or power failure should be made.

Representation assessment: quantity strings `1` and `1.0` give equal arithmetic results but distinct receipt hashes; Unicode NFC/NFD strings also remain distinct. This is consistent with preserving exact supplied values rather than semantic equivalence. The existing documentation does not claim RFC 8785 conformance. Recommend explicitly documenting sorted-key Python JSON serialization and lack of semantic/Unicode normalization, without changing values or adding signing keys.


## v3 staged-output review checkpoint — 05:32 UTC

Confirmed torn-write defect fixed by staging a same-directory private temporary file, flush/fsync, then no-clobber hard-link publication. Independent failure injection moved to the actual os.fdopen handle:64real bytes were written/flushed before ENOSPC. Additional fsync and publication-link EIO failures were injected separately. All return exit2, leave no final file and clean temporary residue before publication. Existing files and symlink/hardlink aliases remain unchanged. These tests assert real filesystem state, not mockcall counts.

Precise guarantee boundary: this is not a crash-durable transaction protocol. Process/host crash can leave a private temporary file; a failure removing the temporary name after successful publication can leave a complete final file and residue with a failure status. No general power-loss, hostile filesystem or cross-platform hard-link guarantee is claimed.

Current full suite: **129/129 passed**, exit0,0.861seconds, including42independent test methods. No unresolved reproduced prepublication partial-output defect. Current hashes:
```text
8170567f23655ad2a6d05208beec49373f9ec561e572df18400e2d360ef95e77  src/emissions.py
0ea3af51231f23097485c467cea932dbcc58eb5323a6e7ad2b6a1d3c710338f6  src/emissions_report.py
e81ad47c9c26b6ddbd037eea96d7c9dc7d20334b86a47f85391ad62e54f1d85a  tests/test_emissions_adversarial.py
13f30d6c4b20bcefee4bb26dae1ca30aa5ba32ea4fdb1717e718ce5389ca14d3  fixtures/za_grid_factor_2024.json
```

## Final source-disclosure review checkpoint — 05:41 UTC, recorded 05:43 UTC

The published 2024 NGGEF remains **0.960 tCO2e/MWh**. Independent regression checks reject substituted 0.9555 and 0.8576 values rather than deriving a replacement factor. The unresolved source-table/footnote reconciliation is now an explicit machine-readable limitation and a visible HTML warning. This review does not resolve that scientific source discrepancy or independently validate the published factor.

Four material limitations were independently removed one at a time and each altered receipt was rehashed: unresolved factor-input reconciliation, market-based emissions not computed, organizational boundaries not reviewed, and not a full Scope 2 compliance assessment. The integrity-only hash check accepted the recomputed checksum, as expected; the renderer rejected each altered report through deterministic recalculation. This demonstrates why a checksum alone is insufficient. Separate rendered-output checks confirm the source warning, narrow compliance caveats and explicit “Input note (unverified assertion)” label remain visible in generated HTML. Actual browser pixel rendering is not established by these semantic tests.

Final independent full-suite execution: **134/134 tests passed**, exit code 0, 0.856 seconds. The isolated publication subset is reported by the packaging workflow as **126/126 passing**, excluding eight unrelated legacy funding-registry tests; that isolated execution was not independently rerun by this reviewer at this checkpoint. These counts describe executed checks, not certification, field accuracy or superiority.

Current reviewed hashes supersede earlier source checkpoints:

```text
82f8e3e9a99f6fa354fa3be097d764e475159ff8bbd3c300733a1215e0a85655  src/emissions.py
01dcc02b4e3dba3eb0141215de3ce54a3b45c4205f2aabdbdac5459ab18dac74  src/emissions_report.py
33dfbd8a32702709695a33965ad5d195ff91a1c37154ce15cbb26308d4425a5c  tests/test_emissions_adversarial.py
13f30d6c4b20bcefee4bb26dae1ca30aa5ba32ea4fdb1717e718ce5389ca14d3  fixtures/za_grid_factor_2024.json
```

No new implementation defect was reproduced within this bounded final review. The unresolved source reconciliation, original archive-lineage discrepancy, unverified/synthetic activity, unsigned receipt limitations, limited filesystem guarantees and unestablished visual browser QA remain disclosed limitations. Later source changes require renewed checks. No production code was edited by this reviewer.

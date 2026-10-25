# Independent synthetic benchmark review

Run: 2026-10-25T05:08:45.890665+00:00
Target source SHA-256: 24279f1a12ad932670961f815a8be1d51fb25833900f641875837ba2d1d742b3
Frozen expected-case manifest SHA-256: 8dfaeb4fd25f66c6e20b44eb7cfd313a03f727f57de0c99ca6c22d4fc4ea869a

## Main conclusion
GRIDSHIFT matched the competent independently coded rules baseline on all24 constructed cases. **No performance or market advantage over competent spreadsheet-style validation was demonstrated.** The gap versus simple multiplication shows the value of validation gates, not novel technology.

## What was compared
The existing GRIDSHIFT emissions calculate/calculate_batch API against a deliberately simple arithmetic baseline. The baseline converts kWh to MWh, handles MWh directly and rejects unrecognized activity units and negative/nonfinite numbers, but does not check country, data year, source provenance, accounting boundary, duplicate identifiers or overlapping meter periods. This is a transparent feature-ablation comparison, **not a claim that all spreadsheets or competing products lack safeguards**.

An independent agent authored and froze 24 synthetic cases before running either implementation. It read the supplied fixtures, function signatures/docstrings and factor-review report, not implementation internals or existing tests. Expected semantics were defined first and hashed. This is a small purpose-built challenge set, not representative field validation, a statistically meaningful accuracy estimate, blinded human evaluation or real-world carbon verification.

## Results
| Measure | Simple arithmetic | Competent rules reference | GRIDSHIFT |
|---|---:|---:|---:|
| Valid cases, arithmetic correct | 8/8 | 8/8 | 8/8 |
| Valid cases falsely rejected | 0/8 | 0/8 | 0/8 |
| Invalid cases accepted | 12/16 | 0/16 | 0/16 |
| Invalid cases rejected | 4/16 | 16/16 | 16/16 |

Valid cases cover fractional, equivalent-unit, zero, small and large quantities; adjacent periods; distinct meters; distinct sites. Invalid cases cover geography, activity/data year, cross-year period, money/power in place of energy, negative/nonfinite input, factor unit/boundary/value/source tampering, unsupported verified-activity claims, duplicated identifiers and overlapping periods.

All three implementations computed the valid arithmetic correctly. The observed difference is **refusal of unsupported inputs**, not better multiplication. GRIDSHIFT made no false rejection in these eight selected valid cases. All per-case outputs and exception messages are in holdout_results.json. No manifest changes were made after observing results.

## Competent baseline and timing disclosure
The second baseline is an independently authored protected-factor worksheet/rules reference: pin the reviewed factor fixture, enforce synthetic status/country/year/unit/numeric validity, unique identifiers and nonoverlapping intervals per site/meter; calculate Decimal totals. It was authored after the frozen case list and first run result were visible. Its protocol and source were frozen before its own run; it is **not blinded or preregistered before case design**. The target source/tests were not read. The same manifest remained unchanged. This baseline is neither a commercial product nor a certified audit. Full protocol/source and results accompany the report.

## Strongest defensible demo claim
“In this independently authored, pre-frozen 24-case synthetic challenge, both implementations calculated all eight valid cases correctly. GRIDSHIFT rejected all16 intentionally invalid cases; the disclosed simple multiplication baseline accepted12. A competent independently coded rules baseline matched GRIDSHIFT on every case. This demonstrates these specific validation gates, not measured emissions reductions, novelty or superiority over full-featured spreadsheets.”

## Important limits and remaining winning blockers
- Synthetic hand-selected cases are not independent real-meter truth or broad adversarial coverage.
- Acceptance does not authenticate the activity source, establish ownership of a meter, or prove inputs were measured. A user can still invent plausible valid inputs.
- A hash proves bytes match a receipt, not that data or emissions are true; no blockchain exists here.
- Factor/source review establishes a cited numeric basis, not certified regulatory assurance; uncertainty remains unquantified.
- No avoided emissions, customer savings, deployment adoption or market novelty is demonstrated.
- Stronger claims require permissioned real inputs, external reviewer/judge reproduction, usability/field tests and a fair baseline configured with equivalent safeguards.
- Public source rights, contest prior-work eligibility and competition submission and video publication approval remain separate gates; the scoped MIT code release was approved on 25 October 2026.

## Reproduce
Second reference: python benchmarks/run_competent_baseline.py
From gridshift_v0_2: python benchmarks/run_holdout.py
Do not rerun freeze_holdout.py to change the expected manifest after seeing results. Preserve this exact frozen set; future cases must be new separately versioned manifests.

Files created only under benchmarks/ and the separate evidence directory. Existing source and tests were not changed by this reviewer. No network calls, paid services or publication were used.

## Current-candidate rerun, 05:10 UTC
The unchanged frozen manifest was rerun against core SHA256 `095f3df6f7cb01328a2e6103d8dfcb9ebf06d5392f8d40799542cefef6c8e762`. Results were unchanged for all three implementations. First-run JSON files were preserved in `outputs/climate/holdout_first_run.json` and `competent_first_run.json`; current rerun JSON remains under benchmarks/. This repeat is regression verification, not a new holdout sample.

## Preflight-candidate rerun, 05:13 UTC
After additive preflight diagnostics, the same manifest and baselines were rerun against core SHA256 `c368f0ef3ac91ecf42fa8a182f099597396ff8bd0ebfc68d477163beb4cf6909`; all results remained unchanged. This is the candidate used by the current demo capture. The new preflight functionality is independently tested but is not claimed as an advantage established by this 24-case arithmetic/refusal benchmark.

## Frozen safety-hardened v2 rerun, 05:26 UTC
The unchanged cases/baselines were rerun against frozen core SHA256 `132279311d043d49eabd8e618c43f6f8ae309e32ffe40e94e2d371e5697d1d9f`. Results are unchanged. Resource limits and explicit JSON depth guarding are implementation safety refinements, not evidence of a competitive advantage or expanded climate-science capability.

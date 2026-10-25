# E1: Does GRIDSHIFT improve reviewer decisions over a competent checklist on messy evidence? (hypothesis, not a claim)

**Status:** specified prospectively. Not run. No result exists.

**Decision under test:** a reviewer must decide, for a reported purchased-electricity (Scope 2, location-based) total, between three outcomes:
- ACCEPT the total as reported;
- CORRECT it to an exact, supported proposal;
- WITHHOLD it pending named evidence.

**H1:** with equal information, GRIDSHIFT-assisted review makes fewer *unsafe outcomes* than a competent spreadsheet/checklist review. An unsafe outcome is accepting or correcting to a wrong total, or accepting stale or forged prior approval.
**H0:** no difference, or the comparator is better. A tie is the expected prior, given the earlier benchmarks.

**Frozen cases.** There are 40 new synthetic packages, generated and hashed before any arm runs, and written to a separately versioned manifest.
- They include aliases, partial and overlapping corrections, incomplete coverage, unit traps, stale imported approvals, tampered envelopes and non-portable numbers.
- 50% have a defensible CORRECT answer, 30% WITHHOLD and 20% ACCEPT.
- Keys hold the correct decision, plus the exact total where one exists. They are authored by someone who has not read either arm's internals. That person is to be named by the owner; until then the experiment is blocked.

**Comparator.** A competent spreadsheet/checklist:
- the same records, the same published factor (0.960 tCO2e/MWh), and the same written policy;
- Decimal arithmetic;
- explicit checks for duplicates, coverage, period overlap and prior-approval provenance.
It is authored and frozen before the run.

**Primary metric:** the unsafe-outcome rate. Secondary metrics:
- exact-decision agreement with the key;
- false WITHHOLD rate;
- whether the cited reason matches the key's reason;
- whether re-exported bytes reproduce the decision when reopened.
Report per-case tables and exact counts. No significance claim at n=40.

**Falsifier:** if the comparator's unsafe-outcome count is less than or equal to GRIDSHIFT's, H1 is rejected and reported as such.

**Limits:**
- This is a rules-vs-rules run. A claim about human productivity requires real participants.
- The cases are synthetic, not measured.

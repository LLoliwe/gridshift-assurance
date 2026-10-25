# E1 frozen case set (lane B, private, v1)

**Status:** frozen before any arm has run. **No candidate or comparator run has been performed on these cases.** Any later run must be stored outside this folder, under its own immutable, hashed directory, and must never edit this folder.

**What this is:** 40 constructed, synthetic software test cases (invented data, not real meters, not company records) for the hypothesis in `lane-b/EXPERIMENT_E1.md`: whether GRIDSHIFT-assisted review makes fewer unsafe ACCEPT/CORRECT decisions than a competent checklist with equal information. **These are constructed software tests, not evidence of usefulness.**

**Contents:**
- `cases/E1-*.json`: 40 complete input packages (`gridshift.reconciliation.input.v1`), one per case.
- `EXPECTED_OUTCOMES.json`: decision, primary reason, and exact proposed totals where they exist (factor 0.960 tCO2e/MWh, Decimal arithmetic).
- `EXCLUSIONS.md`: what is deliberately not in this set.
- `RECONCILIATION_POINTER.md`: the policy the key was derived from, pinned by hash.
- `SHA256SUMS`: hashes of every other file.

**Mix (as specified):** 20 CORRECT (50%), 12 WITHHOLD (30%), 8 ACCEPT (20%).
- CORRECT families: F1 report-total mismatch ×4, F2 explicit full replacement ×4, F3 explicit void of duplicate ×3, F4 kWh unit trap ×3, F5 split-period partial count ×3, F6 replacement chain ×3.
- WITHHOLD families: incomplete coverage ×2, unexplained overlap ×2, conflicting successors ×2, partial or cross-scope replacement ×2, missing target, non-energy unit, wrong (integer) data year, dropped limitation.
- ACCEPT families: single meter ×2, two meters ×2, kWh ×2, split period ×2.

**How the key was made:** I (the builder) derived it by hand from the written policy, without running the engine, the adapter or any comparator on these cases. `lane-b/e1-tools/build_frozen.py` is only the generator that wrote these files; it is kept outside this folder and imports no engine code.

**This deviates from EXPERIMENT_E1.md.** The key there must be authored by someone who has read neither arm. That condition is **not met**: this key is builder-authored (`authorship: BUILDER_AUTHORED_FROM_WRITTEN_POLICY_NOT_INDEPENDENT`). Before E1 can count as more than a self-test, a named non-builder must re-derive or audit the key.

**Open gates (not done, not simulated):**
1. A real non-builder checker or key author. None is available, so this gate is open.
2. A competent checklist comparator, authored and frozen before any run. It does not exist yet.
3. A non-builder rendered review of the workspace. This gate is open.

**Separation:**
- Implementation-integrity attacks are not part of this business comparison and are excluded; see EXCLUSIONS.md. They include tampered envelopes, stale imported approvals, non-portable JSON numbers, limits, and malformed schemas.
- The **previous tie is preserved, not replaced**. `benchmarks/competent_baseline_results.json` reports 8/8 valid, 16/16 invalid and 0 unsafe acceptances for both the candidate and the competent checklist. E1 is a new, separately versioned manifest and does not change that result.
- The 5 R1 portability regression tests (`web-tests/test_workspace_portability.py`) and the 31-case adversarial manifest with its 8 frozen expectation misses (4 cases × 2 runtimes) (`lane-b/adversarial/`) are separate artifacts. They are excluded from E1 scoring.

**Frozen at:** parent commit be8280c9f9830acc07e3a06f32d2ac5d2482706b, on 2026-10-25, branch lane-b/private-r1 (local only, never pushed).

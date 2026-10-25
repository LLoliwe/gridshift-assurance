# Unresolved challenges, ranked (Lane B R1)

Ranking criterion: how much each challenge blocks a truthful decision-quality claim, times whether Lane B can make verifiable progress at R0 now.
- Worked on this round: #2. A verdict that is correct but wrongly transported or reopened invalidates every downstream claim.
- Specified as an experiment: #1, in EXPERIMENT_E1.md.

## 1. No demonstrated advantage over competent practice (most consequential, unsolved)
- **Prior attempt:** a pre-frozen 24-case synthetic holdout, compared with a simple-multiplication baseline and an independently coded competent rules worksheet.
- **Known result:** GRIDSHIFT and the competent baseline tied, both 8/8 valid and 16/16 invalid, with 0 unsafe acceptances. The simple baseline accepted 12 invalid cases. The repaired reconciliation comparisons also tied.
- **Source:** `benchmarks/competent_baseline_results.json`, `docs/BENCHMARK_REVIEW.md`.
- **Unknown:** whether any advantage exists on messy evidence, correction proposals or reopen/approval integrity once the comparator has equal information.
- **Experiment:** E1 (EXPERIMENT_E1.md).
- **Acceptance evidence:** E1's prospectively frozen metrics, scored blind against the frozen keys.
- **Stop condition:** if E1 ties or loses, report a tie or loss and claim no advantage. A claim about real users needs participant evidence that Lane B cannot produce.

## 2. Import/reopen/acceptance correctness across runtimes (worked this round)
- **Prior attempt:** strict parser, byte preservation and proposal-hash binding. One Playwright journey passed.
- **Known result this round:**
  - 31 frozen synthetic adversarial cases (commit 3fbd448) were run natively (Python 3.13.5) and in the real Chromium + Pyodide 3.14.2 worker.
  - Run 1 found a **real divergence** in C12, C13, C14 and C31. A JSON float or an integer above 2^53 opened in the browser, but every review then failed with "raw bytes and parsed evidence conflict". Natively, the same case gave WITHHOLD. Cause: the JS Number round-trip.
  - The divergence failed closed (no total, no acceptance), but the reviewer could neither get a reason nor export. The UI also showed a raw Python traceback.
  - The fix (commit 1b3aae5) refuses non-portable numbers at intake, giving a JSON path, in both runtimes. Run 2 had 0 policy divergences.
  - The 4 cases now miss their frozen "open then WITHHOLD" expectation; this is disclosed and the cases were not rewritten.
  - The C28 XSS strings stayed inert in the real UI.
- **Source:** `lane-b/adversarial/results/run1_pre_fix`, `results/run2_post_fix`.
- **Unknown:**
  - Firefox and WebKit.
  - Concurrent tabs or double-click races during accept.
  - Worker crash or recovery mid-accept.
  - The UI showing raw tracebacks (still present).
  - Whether intake refusal (rather than WITHHOLD) is what the owner wants for floats.
- **Experiment:** extend the same frozen manifest runner to Firefox and WebKit, then add a new, separately versioned manifest for race and recovery cases.
- **Acceptance evidence:** 0 policy divergences, and no accepted result surviving a reopen, in every runtime.
- **Stop condition:** a divergence that cannot be repaired without changing the reconciliation core. Escalate that to the owner.

## 3. Real messy evidence is not the neat fixture
- **Prior attempt:** declared bounded coverage and full-period replacement/void semantics.
- **Known result:** aliases, partial corrections and incomplete records are not supported. They are WITHHOLD at best.
- **Source:** `docs/RECONCILIATION.md`, `src/reconciliation.py`.
- **Unknown:** the real record shapes. There are no rights-cleared records, and the context pack is outstanding.
- **Experiment:** E1 uses synthetic messy shapes. Real shapes require a supplied, permissioned sample.
- **Acceptance evidence:** documented ambiguity model; a human-resolution path; no inferred physical truth.
- **Stop condition:** no permissioned records are available. Remain synthetic and say so.

## 4. Factor/source reconciliation unresolved
- **Prior attempt:** the published 2024 NGGEF of 0.960 tCO2e/MWh is retained, and the source tables were reconstructed.
- **Known result:** the reconstructions give about 0.955 or 0.858. Neither reproduces 0.960. Tables 3–4 and footnotes 3/5 appear to conflict.
- **Source:** `docs/SOURCE_RECONCILIATION.md`, `docs/FACTOR_REVIEW.md`.
- **Unknown:** the publisher's exact denominator definition.
- **Experiment:** trace every table boundary in the primary PDF and document the contradictions.
- **Acceptance evidence:** an authoritative clarification, obtained only through a separately authorized contact.
- **Stop condition:** without authorization to contact DFFE, "unresolved" stays the truthful state. Do not substitute a factor.

## 5. Annual inventories do not identify causal avoided emissions
- **Prior attempt:** none beyond the stated limits.
- **Known result:** average-factor multiplication cannot identify a counterfactual.
- **Source:** owner's instructions, `docs/CLIMATE_EXTENSION.md`.
- **Unknown:** n/a. This is an identification limit, not an engineering gap.
- **Experiment:** stay within inventory decisions. Any causal work needs separate temporal data and a validated method.
- **Acceptance evidence:** no avoided-emissions claims anywhere.
- **Stop condition:** any request to claim avoided emissions. Refuse and escalate.

## 6. Access/deployment is a separate bottleneck
- **Prior attempt:** browser CI succeeded.
- **Known result:** local launch on port 8766 returned 200. There is no hosted service and no authenticated reviewer.
- **Source:** `docs/EXPERIMENTAL_BROWSER_CI.md`, baseline `http_server_8766.log`.
- **Unknown:** hosting, permissions, data boundaries.
- **Experiment:** none until hosting is authorized.
- **Acceptance evidence:** a verified hosted launch, done only with authorization.
- **Stop condition:** no authorization (the current state).

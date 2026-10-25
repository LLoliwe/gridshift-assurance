# Adversarial runs: notes and known harness defects (lane B, private)

The frozen artifacts are unchanged: `FROZEN_MANIFEST.json`, `results/run1_pre_fix/` and `results/run2_post_fix/`. They are not edited by these notes.

## Harness defect H1: UI state leaked between UI cases (run 1 and run 2)

- **What:** the real-UI section of `browser-tests/cross-runtime.spec.mjs` loaded C28, then C12, then C14 into the same page without resetting it. C12 and C14 are refused at open, so the earlier C28 case stayed on screen. As a result, the `ui` entries for C12_float_year and C14_big_int_unknown_field in `run2_post_fix/browser.json` (and in run 1) show `opened: true` and C28's case title.
- **Impact:** those two `ui` entries are **not evidence** of anything and must not be cited. This was found by the Engineering Lead's review.
  - The worker-level results for every case are not affected. They come from a fresh worker message per step, and C12 and C14 were refused there, matching native.
  - The C28 `ui` entry is not affected either: it was the first case loaded.
- **Fix (round 2):** the harness now reloads the page and waits for the runtime before each UI case, and records `ui_reset` in each entry. The fix applies only to future runs, which must be written to a new results directory. Runs 1 and 2 are not rewritten.

## C17_empty message-only divergence (run 2)

- **Recorded:** native said "Input must contain 1–786432 UTF-8 bytes."; the browser worker said "Open expects 1–768 KiB of original raw file bytes."
- **Reason:** the worker refused in JavaScript before Python ran. Both runtimes refused, so there was no policy difference.
- **Fix (round 2, commit 840f636):** both runtimes now emit the identical string from `web/workspace/intake-limits.json`: "Open expects 1 byte to 768 KiB (786432 bytes) of original raw file bytes." Regression tests are in `web-tests/test_workspace_shared_limits.py` and `web-tests/workspace-worker-contract.mjs`.
- The run 2 record keeps the old divergence as it happened.

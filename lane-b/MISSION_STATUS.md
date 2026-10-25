# Mission status: Lane B R1 (private, local)

**State:** Gate 1 is complete, and the first implementation step is committed locally. Nothing has been pushed, published or sent.

## Repository state

The remote was verified by anonymous `ls-remote` at the start and again at the end of the session. It was unchanged:
- `main` = ae8f53d466a7d203635972c5b414b7977a7858c6
- `experiment/workspace-browser-r2` = d084b7ffa09d4c920ff998105e6941934024964f

The experiment tree has 75 tracked files. The sha256 of each one is recorded in a private evidence file outside the repository (`protected_tree_d084b7f.sha256`). Those hashes still verify against the pristine worktree, which has a clean status.

## Baseline (on d084b7f, all exit 0 except where noted)

- `python3 -m unittest discover -s tests`: 157 tests OK.
- CLI checks: default (480), `--preflight`, `--format html`.
- `run_holdout`, `run_competent_baseline`.
- source-exhibit: 10 tests. web-tests unittest: 30 tests.
- node ui-lifecycle, workspace-state, workspace-worker-contract.
- workspace-ui-native: **exit 1 on the first run.** The cause was environmental: `python` is not on PATH. It reran at exit 0 with a test shim.
- `npm ci`, `playwright install chromium`: OK.
- Real browser journey: 1 test passed.
- `http.server` on port 8766, `curl /workspace/`: HTTP 200.

## Implementation (branch `lane-b/private-r1`)

1. **3fbd448:** 31 frozen synthetic adversarial cases, committed before any execution.
2. **8340fe6:** native runner, real-browser (Chromium + Pyodide) cross-runtime spec, comparator, and the **run-1 first failures preserved**. There was a divergence on 4 cases, caused by the JS Number round-trip.
3. **1b3aae5:** fix. Non-portable JSON numbers are refused at intake, with a JSON path, in every runtime. The adapter was repinned and 5 regression tests were added.
   - Run 2: 0 policy divergences.
   - The 4 cases now miss their frozen open-then-WITHHOLD expectation. This is disclosed; the cases were not rewritten.
   - All suites pass: 157 + 35 tests; node 4/4; journey 1/1; cross-runtime 1/1.
4. This docs commit.

## Remaining weaknesses

- **Biggest:** there is still no demonstrated advantage over a competent checklist. All evidence is synthetic.
- The browser UI shows raw Python tracebacks in `#notice`.
- Only Chromium was tested.
- No race or recovery tests yet.

## Next milestone

The next milestone is waiting on owner decisions:
- whether intake refusal for float and >2^53 numbers is the intended policy;
- who authors E1's blind keys;
- review of the patches.

After those, run the same manifest on Firefox and WebKit and freeze the E1 manifest. No dates are promised.

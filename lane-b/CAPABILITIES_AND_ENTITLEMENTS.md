# Lane B capabilities and entitlements (R1)

Recorded: 2026-10-25, session work about 19:00–20:00 UTC (the box clock was checked with `date -u`; this commit was written at about 19:52 UTC).

| Capability | Status | Evidence |
|---|---|---|
| Anonymous HTTPS clone of public repo | Used. No credentials were used | `git ls-remote https://github.com/LLoliwe/gridshift-assurance` |
| Local git, worktrees, local commits | Used. Branch `lane-b/private-r1` only | `git log d084b7f..lane-b/private-r1` |
| Python 3.13.5 (native), Node, npm | Used | baseline logs in the private evidence folder (outside the repository) |
| Headless Chromium 156.0.8078.4 via Playwright 1.64.1, `chromiumSandbox: true` | Working | the existing journey spec passed, and the new cross-runtime spec passed |
| Pyodide 314.0.7 (Python 3.14.2) from jsDelivr, using the repo's sha256-pinned assets | Working; this is free public CDN access | results/run2_post_fix/browser.json |
| Public web read (Devpost page) | Used read-only | CONTEXT_MANIFEST.md |
| Paid APIs (OPENAI_API_KEY, MOONSHOT_API_KEY, DECISIONMODELS_API_KEY, others) | **Not used.** Incremental spend is R0 | No network calls to those services |
| Grok/X or other connectors | Not used. Not verified for this work | — |
| git push, PR, publication, hosting, posting, contacting anyone | **Not authorized. Not done** | `git status`, branch heads in MISSION_STATUS.md |
| Changes to `main`, `experiment/workspace-browser-r2`, Lane A | **Not authorized. Not done** | protected tree hashes match |
| Curated company context pack | Not supplied. Not sought | CONTEXT_MANIFEST.md |

Environmental note: `python` is not on PATH. `web-tests/workspace-ui-native.mjs` spawns `python` and failed with exit 1 (ENOENT) on its first run. It passed with a local test-only shim (`python` → `python3` on PATH). Both logs are kept.

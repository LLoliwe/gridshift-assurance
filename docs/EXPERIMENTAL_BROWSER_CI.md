# Experimental workspace browser validation — NOT a production release

This branch adds a review-only workspace and a minimal real-browser development test. Existing public routes, shared controller, engine and reconciliation UI remain unchanged. The workspace uses an isolated controller copy; that copy is not an upgrade of the incumbent public controller.

The workflow runs only for pushes to `experiment/workspace-browser-r2` in the public `LLoliwe/gridshift-assurance` repository. It uses one standard `ubuntu-22.04` GitHub-hosted VM, a read-only contents token, no persistent checkout credentials, no cache action, no artifact upload, no deployment, no pull-request write and no paid runner. No secrets or private workbooks are required. It uses only the existing public synthetic flagship fixture. Runner-local temporary downloads are not uploaded. Results and any failure diagnostics are public synthetic logs.

Chromium is explicitly launched with `chromiumSandbox: true`; defaults are not sufficient. A sandbox failure is a blocked test, not permission to disable sandboxing or modify OS security policy. There are no unsafe launch arguments, kernel/sysctl/AppArmor edits or privileged browser containers. The browser is not replaced by native Python, DOM simulation or prerecorded evidence.

## What a pass would and would not establish

A passing run would establish the tested real Chromium/worker/Pyodide synthetic intake → correction → keyboard confirmation → acceptance → download → reopen/recompute path, preservation of original bytes, and basic 1440/390px document-overflow assertions for this exact commit. It is a development test, not independent evaluation. It does not establish broad browser compatibility, screen-reader usability, comprehensive accessibility, owner visual/aesthetic acceptance, production readiness, authenticated review, source authentication or accounting assurance. Those gates remain separate.

No screenshot or trace artifacts are uploaded because storage cost/allowance has not been verified. Any future artifact retention, deployment, public prototype, default-branch merge or changed source requires separate authorization.

## Dependency and licence inventory

- Existing project and proposed project-authored additions: repository `LICENSE`, MIT, copyright 2026 Pryntor (Pty) Ltd. New additions require owner publication authorization; existing public licensing does not grant authority to disclose private source.
- `@playwright/test`, `playwright`, `playwright-core`: exact 1.64.1, Apache-2.0; npm integrity hashes recorded in `browser-tests/package-lock.json`. Source/licence: https://github.com/microsoft/playwright/tree/v1.64.1 . Browser binaries and their upstream notices are installed on the ephemeral runner, not committed or redistributed in this bundle.
- Official `actions/checkout` v6: `d23441a48e516b6c34aea4fa41551a30e30af803`, MIT; https://github.com/actions/checkout/blob/d23441a48e516b6c34aea4fa41551a30e30af803/LICENSE .
- Official `actions/setup-node` v6: `249970729cb0ef3589644e2896645e5dc5ba9c38`, MIT; https://github.com/actions/setup-node/blob/249970729cb0ef3589644e2896645e5dc5ba9c38/LICENSE .
- Pyodide 314.0.7: runtime fetched from versioned jsDelivr URL by the existing workspace bridge, MPL-2.0 plus upstream third-party notices; https://github.com/pyodide/pyodide/blob/314.0.7/LICENSE . No runtime distribution is vendored. Project-source integrity checks do not authenticate every remote runtime dependency.
- Node 24 and Python 3 are execution tools provided/installed on the runner, not bundled project dependencies.

Dependency versions and action pins were read from official repositories on 2026-10-25. Version pinning does not prove absence of vulnerabilities. A runtime download or dependency failure blocks validation; it does not authorize credentials, billing changes, security workarounds or unreviewed substitutions.

## Cost and availability boundaries

GitHub documents standard public-repository runner usage as free, but artifact/cache accounting is separate. This workflow deliberately omits cache and artifact-storage operations. Actions availability/account restrictions were not established by the read-only connector: a successful empty runs listing is not proof that a first workflow will execute. If GitHub refuses the ordinary branch-push run, stop and report the exact failure. Do not alter account/repository settings, add credentials or enable spend without fresh authority.

References:
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://docs.github.com/en/actions/reference/security/secure-use
- https://playwright.dev/docs/ci
- https://playwright.dev/docs/api/class-browsertype#browser-type-launch-option-chromium-sandbox

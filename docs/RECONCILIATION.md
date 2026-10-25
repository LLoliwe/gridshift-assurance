# GRIDSHIFT reconciliation prototype

This additive module preserves original electricity records and report, evaluates a bounded declared package, proposes a computational correction, and requires explicit acceptance of an exact proposal before rerun. The supplied examples are invented development cases. They do not establish field impact, authentic supplier error, measured savings, or superiority over a competent spreadsheet/rules workflow.

## Reproduce
From the repository root, run `python -m unittest discover -s tests -p 'test_reconciliation*.py'`, `node web-tests/ui-lifecycle.mjs`, and `python -m unittest discover -s web-tests`. Serve `web/` with any ordinary static HTTP server and open `/reconcile/`. The browser downloads pinned Pyodide 314.0.7 from jsDelivr and verifies bundled Python/factor bytes. It needs network access; it does not send the fixture or reviewer ID to a server.

Select Explicit replacement link and run. A100 is explicitly replaced by B80 for the same interval; distinct C20 remains. The original report 200 MWh / 192 t stays visible. Proposed 100 MWh / 96 t is a report correction, not 96 tonnes avoided. Review the trace, select the explicit acceptance checkbox and rerun. Export retains all original records and the original report. Missing replacement link instead withholds because overlapping records lack supported lineage.

CLI: `python src/reconciliation.py web/reconcile/flagship.json`. Exit 3 means CORRECT, 0 ACCEPT, 2 WITHHOLD/error. Review the displayed proposal hash before using `--accept-proposal HASH --reviewer ID`; the reviewer ID is self-reported, not authenticated. `--output PATH` refuses overwriting existing output.

## Supported policy
ORIGINAL, unique exact-full-scope replacement chains, and ORIGINAL-only full voids are supported. Void does not prove zero consumption. Accepted interval union must exactly cover declared slots with no overlap or extra coverage. Missing targets, cycles, branches, ambiguous overlaps, partial corrections, aliases, parent/component aggregation, and unsupported claims are withheld. No physical source authentication or organization-wide completeness is inferred. WITHHOLD may report only the first blocker.

## Scientific boundaries
Published 2024 NGGEF 0.960 tCO2e/MWh is retained. Manual AI-assisted source review found unresolved arithmetic/footnote reconciliation in the source tables; software did not discover this automatically or independently validate the factor. Source uncertainty is unquantified. No marginal/causal estimate, carbon credits, blockchain, full Scope 2 compliance or independent assurance is claimed. The hash is unsigned.

## Evaluation status
The original 24-case competent baseline tied. Frozen reconciliation r1 matched 12/12 unseen synthetic decisions/ledgers/totals, but raw full-check score 11/12 is retained: a scorer field-location discrepancy was separately adjudicated as no evidence loss. Both systems had 7/8 actionable refusal explanations. R2a repairs schema diagnostics only. In one fresh independently authored eight-case constructed group, candidate and equally repaired comparator both passed 8/8 automated checks, 4/4 manually reviewed schema diagnostics and 2/2 correction/approval/reruns; repeated outputs were byte-identical. Seven applicable opaque-ID checks passed, with one not applicable. This is software-agent evaluation, not human usability or empirical provider sampling. Previous 24 cases are regression only; do not combine them as 32 independent holdouts. Do not claim superiority or field validation.

## Rights and distribution
Proposed additional original source/tests/docs are under the repository MIT licence, copyright Pryntor (Pty) Ltd, subject to explicit approval of this new subset. Pyodide runtime is fetched, not vendored or relicensed; its own licences apply. System fonts are referenced only. No third-party artwork or customer data is included. The proposed public copy says research prototype and synthetic cases. Public hosting/access requires separate approval; no private Site identity/config is included. The intended public deployment must contain only this web/ subtree, not earlier private experiments.

## Exact release version boundary
This bundle retains the earlier browser-tested reconciliation UI. The later private pagehide/pageshow preventive lifecycle patch is excluded because its actual browser validation is still pending. Renderer error9 crashes were observed during recording preparation; their cause is unresolved. This release does not claim uninterrupted browser/recorder reliability. The private Site also contains research/readiness routes not included here. Publishing these files does not authorize making that Site public.

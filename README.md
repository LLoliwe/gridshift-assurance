# GRIDSHIFT Assurance: electricity evidence prototype

**Reviewed release candidate v3 — MIT, copyright 2026 Pryntor (Pty) Ltd.**

An extension of the existing GRIDSHIFT project, not a separate venture. Offline Python 3.10+ standard library. No account, package installation, API, blockchain or billing.

## Run

```sh
python -m unittest discover -s tests -v
python src/emissions.py --activities fixtures/demo_energy_2024.json
python src/emissions.py --activities fixtures/demo_energy_2024.json --preflight
python src/emissions.py --activities fixtures/demo_energy_2024.json --format html --output my-report.html
python benchmarks/run_holdout.py
python benchmarks/run_competent_baseline.py
```

Open the newly created HTML locally. The emissions CLI refuses existing output paths. Benchmark scripts intentionally regenerate their result JSON files, so rerunning them can change those manifest-listed output files. The synthetic 2024 example returns 480 tCO2e from 500 MWh and an attributed annual NGGEF of 0.960 tCO2e/MWh. This is an inventory estimate, not measured savings, a carbon credit, a verified customer footprint or evidence of carbon neutrality.

The original invoice/tariff model is retained as `src/assurance.py`; its 2026 figures are invented. It is not automatically connected to the new emissions calculator, and its fixture dates have not been relabelled to fit an older factor.

See `docs/CLIMATE_EXTENSION.md` for units, strict year/provenance/refusal gates, uncertainty, receipt limitations and reproducibility. `docs/BENCHMARK_REVIEW.md` discloses a tie with a competent rules baseline on the authored synthetic challenge: no market superiority or field validation is claimed.

Development and review were AI-assisted. Pre-existing source dates to 11 October 2026; the bounded emissions extension was authorized and implemented 25 October 2026. Owner approved this isolated source subset for public MIT release on 25 October 2026. Government facts are attributed; the government PDF is not redistributed. Funding, venture strategy, grant and GTM materials are excluded.

### Browser evidence workspace (private working candidate)

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory web
# then open http://127.0.0.1:8765/workspace/
```

**Needs internet on first load.** The workspace runs the same Python engine in the browser through Pyodide 314.0.7, which is fetched from `cdn.jsdelivr.net` (it is not vendored in this repository). The GRIDSHIFT Python files are served locally and hash-checked before use. Wait until the status reads **Ready**; opening a case stays disabled until then. Without internet access the status reads "Not available" and no case can be opened. Case files are never uploaded.

## Important source limitation
The published 0.960 factor is retained, not independently re-derived. A separate audit could not reconcile the official source input tables and auxiliary-consumption footnotes. See [source reconciliation](docs/SOURCE_RECONCILIATION.md). No market-based result or organizational-boundary review is provided; this is not a full Scope 2 compliance assessment.

## Reproducibility and limits
The receipt is exact-input sorted-key JSON plus SHA-256, not a signature, blockchain or RFC 8785 canonicalization. Unverified source notes remain assertions, not evidence of authenticity. CLI output uses exclusive same-directory publication; see the documented failure and filesystem limits.

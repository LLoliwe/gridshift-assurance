# GRIDSHIFT Assurance: agent and engineer instructions

This file applies to this repository unless a deeper `AGENTS.md` imposes stricter scope. It is an onboarding aid for new/existing agents and human software engineers, **not** an authorisation to publish, spend or deploy.

## Identity and status

Public offline emissions/electricity-evidence prototype using Python standard library and synthetic examples. Not verified customer inventory, carbon neutrality, carbon credits or measured savings.

## Operating contract

1. Read this file, project README, actual source, any nested instructions and test/runbook before editing.
2. Keep PRs focused; never self-merge, add telemetry/secrets, run paid services or claim tests/deployments you did not observe.
3. Respect original/licensed assets and all contributors' rights. Work from synthetic examples and never leak customer/private data.
4. Include in every handoff: branch/commit/PR, changed paths, exact test commands and results (or `NOT_RUN`), unverified assumptions and safe next action.

## Project-specific safeguards

1. Read `docs/CLIMATE_EXTENSION.md` and `docs/BENCHMARK_REVIEW.md` before changing factor/provenance/uncertainty logic.
2. Preserve precise year, quantity, units, data source and uncertainty. Do not relabel synthetic/legacy numbers as audited customer results.
3. Tests and benchmarks are documented in the README; note that benchmark scripts regenerate output artefacts, so review working-tree state before running them.
4. Never turn calculated estimates into verified climate claims without independent domain review and source evidence.

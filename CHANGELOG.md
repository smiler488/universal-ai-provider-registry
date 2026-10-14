# Changelog

Software and public schema changes are recorded here. Catalog content changes use the separate `data_version` recorded in each JSON document.

## 0.1.1 — 2026-10-14

- Present the registry as a general directory across developers and providers, with provider-neutral documentation and examples.
- Add a direct-download quick start and explain JSON envelopes, record joins, and provider selection.
- Consolidate selected official observations into `data/reviewed-evidence.json` and retain their original sources and review dates.
- Remove the dedicated provider coverage report; ordinary provider records and source evidence remain part of the catalog.

## 0.1.0 — 2026-10-14

Initial end-to-end registry implementation with schema `1.0.0`.

- Import the full Models.dev exports, OpenClaw Catalog V2, and selected reviewed official evidence.
- Separate model identity, developer attribution, serving provider, and deployment; preserve source observations and unknown status.
- Generate validated `catalog.json`, `models.json`, `providers.json`, `deployments.json`, and per-provider JSON.
- Add content-derived data versions, reproducible cached-input builds, and release snapshots.
- Add scheduled and manual GitHub Actions synchronization and GitHub Pages publication.
- Add source/license review, focused tests, and Python/JavaScript/shell clients.

Initial limitations: no authenticated inference probes, no SLA or real-time completeness guarantee, no implied free service from zero pricing, and no fuzzy identity merging. Reviewed official mappings require maintenance. Check Actions and live JSON metadata for actual deployment and freshness status.

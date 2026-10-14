# Repository instructions

## Scope and working style

Build and maintain a public, reproducible AI model metadata registry. Keep unknown facts and disagreements visible. Do not turn a proposal, an upstream claim, or a successful JSON fetch into a verified inference capability.

For simple but large repetitive work, including bulk translation, renaming, or repetitive content edits, prepare a transferable prompt file for a cheaper agent instead of completing the entire batch here. Establish the framework, provide representative examples, and write validation checks. This does not replace necessary implementation or verification of the requested task.

## Architecture

- `registry/`: fetch, normalization, publication, and validation logic.
- `schema/`: public JSON Schema contract.
- `data/`: explicitly reviewed identity/evidence inputs.
- `public/v1/`: generated current JSON documents and per-provider documents.
- `public/v1/source-snapshots/`: intentionally published compressed public inputs, with verified reuse terms and source hashes, for reproducible builds.
- `docs/`: source/license audit and MiMo coverage notes.
- `examples/`: small clients that read the published JSON.
- `tests/`: focused tests of source parsing, normalization, provenance, and release behavior.
- `.cache/`: local working fetch cache; do not commit this directory or secrets. The selected published snapshots above are distinct from this working cache.

Run these commands from the repository root:

```sh
python -m pip install -r requirements.txt
python -m registry sync
python -m registry validate
python -m unittest discover -s tests
```

For an offline build, use `python -m registry build` followed by validation. A missing working cache is restored from tracked source snapshots. An offline build does not demonstrate that live sources are reachable. Execute meaningful tests for the changed behavior; do not claim success from syntax checks alone.

## Evidence and identity rules

1. Keep `model`, `developer`, `provider`, and `deployment` distinct. A reseller is not automatically the model developer.
2. Merge model identities only through exact `canonical_model_id` evidence or a reviewed official mapping. Preserve unresolved provider-scoped identities; never fuzzy-merge by display name.
3. Preserve source URLs, fetch/evidence context, upstream IDs, source claims, and disagreements. Do not silently discard one source to manufacture agreement.
4. Use `null` or the schema's explicit unknown status for missing facts. Do not invent endpoints, protocols, prices, context limits, capabilities, availability, or developer attribution.
5. Zero prices require interpretation. Subscription/included-use zeros are not verified free API access. Preserve `zero_requires_verification` where applicable.
6. A source's presence in two related exports is not independent confirmation. Keep source-specific coverage and count definitions explicit.
7. MiMo changes must be checked against official Xiaomi evidence and both imported catalog families. Record the date and source scope; retain unresolved differences.
8. Check source licenses and applicable reuse terms before adding or copying material. Preserve required notices. MIT applies to original repository work, not automatically to all upstream content.

## Safety and publication

- Never commit credentials, private configuration, authentication output, `.env` files, or raw authenticated responses.
- Fetch only reviewed public metadata URLs. No paid model calls or credential inputs are required for this project.
- Validate every generated JSON type and cross-reference before publication. Do not manually patch generated JSON to make tests pass.
- Keep builds deterministic for identical inputs. Content comparison must exclude incidental fetch/build timestamps; unchanged data must not generate a commit.
- Fetch/schema failure must stop the release and preserve the last valid publication. Never publish partial success as a complete catalog.
- Protect immutable snapshots from overwrite; use content-derived release identity. Distinguish schema version, code release, and data version.
- Use read-only GitHub permissions by default, with narrow job-level write access only where needed. Pin third-party Actions and dependencies. Pull requests must not obtain publication credentials.
- Keep workflow concurrency controlled. Do not bypass branch rules or environment protections. Report the exact failed operation and required repository setting.
- Verify publication using real public URLs after deployment. A green build alone does not establish Pages availability. Compare published `data_version` to the built release.

## Maintenance and reporting

Update README and CHANGELOG for contract/operational changes. Update the source audit for new endpoints or license findings, and the MiMo review for material coverage changes. Distinguish verified results, upstream assertions, unresolved issues, and planned work.

Check failed scheduled runs and release freshness. GitHub schedules may be delayed or disabled after inactivity; do not promise an unattended service-level guarantee. When work is blocked, leave reproducible code and a precise blocker rather than claiming deployment is complete.

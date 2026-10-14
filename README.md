# Universal AI Provider Registry

An evidence-preserving public registry of AI models, their developers, providers, and deployments. It imports public catalogs, keeps disagreements and unknowns visible, and publishes validated JSON through GitHub Pages. No model API keys or paid inference calls are required.

Repository: [smiler488/universal-ai-provider-registry](https://github.com/smiler488/universal-ai-provider-registry) · [Actions](https://github.com/smiler488/universal-ai-provider-registry/actions) · [source and license audit](docs/SOURCES.md) · [MiMo coverage review](docs/MIMO.md)

## Public JSON

The synchronization workflow publishes the following endpoints. Check the latest successful Actions run for fetch and publication status. `generated_at` identifies the content build; it stays unchanged when a later fetch finds no changes, so it is not a last-checked timestamp.

| Endpoint | Contents |
| --- | --- |
| [catalog.json](https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json) | Complete catalog, including developers and sources |
| [models.json](https://smiler488.github.io/universal-ai-provider-registry/v1/models.json) | Model identities |
| [developers.json](https://smiler488.github.io/universal-ai-provider-registry/v1/developers.json) | Known model developers |
| [providers.json](https://smiler488.github.io/universal-ai-provider-registry/v1/providers.json) | Serving organizations or services |
| [deployments.json](https://smiler488.github.io/universal-ai-provider-registry/v1/deployments.json) | Provider-specific model offerings and source observations |
| [schema.json](https://smiler488.github.io/universal-ai-provider-registry/v1/schema.json) | JSON Schema used for validation |
| [mimo-report.json](https://smiler488.github.io/universal-ai-provider-registry/v1/mimo-report.json) | Source-by-source Xiaomi coverage and reviewed official evidence |
| [provider-models/xiaomi.json](https://smiler488.github.io/universal-ai-provider-registry/v1/provider-models/xiaomi.json) | Ordinary Xiaomi API provider, with model and deployment records |

Per-provider documents use `v1/provider-models/<provider-id>.json`. Obtain the exact ID from `providers.json`; do not substitute a provider's display name. Each document contains `provider`, `models`, `deployments`, and `sources` with the same release metadata. Consult the full catalog when resolving developer references.

```sh
curl --fail --location \
  https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json \
  --output catalog.json
```

Runnable clients: [Python](examples/read_catalog.py), [JavaScript](examples/read_catalog.mjs), and [shell](examples/read_catalog.sh). They retrieve public metadata only. A deployment record does not establish that an endpoint accepts requests, that a model is available to your account, or that an advertised price is currently payable.

```sh
python examples/read_catalog.py
node examples/read_catalog.mjs
sh examples/read_catalog.sh
```

The Python example uses the standard library; JavaScript requires Node.js 18 or newer; the shell example requires `curl` and `python3`. Each accepts an optional catalog URL for testing a local HTTP preview.

## Data contract

| Entity | Meaning |
| --- | --- |
| `model` | A model identity; unresolved identities remain scoped to the source provider |
| `developer` | The organization known to have developed a model; unknown attribution stays `null` |
| `provider` | An organization or service offering model access |
| `deployment` | A specific provider/model offering, retaining upstream claims |

A developer is not inferred from its hosting provider. Cross-provider merging requires an exact upstream `canonical_model_id` or an explicitly reviewed official mapping. Similar names alone are insufficient evidence.

The complete catalog is an object with `schema_version`, `data_version`, `generated_at`, `kind`, `models`, `developers`, `providers`, `deployments`, and `sources`. Split documents carry matching release metadata and their respective arrays. Compare `data_version` when downloading multiple files: if releases changed during retrieval, retry until versions agree or use one complete `catalog.json` download.

`schema_version` starts at `1.0.0` and describes the contract. `data_version` starts with `sha256-` and identifies catalog content; it is independent of schema versions. A new fetch timestamp alone must not create a new content version. Release snapshots retain previously published content.

Unknowns are meaningful data. Missing capabilities, prices, developer attribution, protocol details, or endpoints are not synthesized. Capabilities use `supported`, `unsupported`, and `unknown`: an explicit unopposed source claim is retained, while contradictory explicit claims resolve to `unknown` and appear in `conflicts`. Missing source values remain unknown; differences in modality lists remain visible in the observations and conflict fields. `supported` therefore means a reported or documented claim, not a successful inference test. A listed price of zero can mean included subscription usage or a placeholder; `zero_requires_verification` must never be interpreted as a verified free service.

## Sources and MiMo

The first version imports [Models.dev's full API](https://models.dev/api.json?type=all), its [full catalog](https://models.dev/catalog.json?type=all), OpenClaw Catalog V2, and reviewed public MiMo documentation. The two Models.dev exports are related upstream views, not independent corroboration. Exact source URLs, license findings, attribution, and limitations are in [docs/SOURCES.md](docs/SOURCES.md).

The [MiMo review](docs/MIMO.md) records coverage and disagreements between Xiaomi's official documentation and imported catalogs. Model existence, serving provider, model ID, API compatibility, price, and capability are separate assertions. An official documentation reference does not automatically verify every downstream provider's implementation. Reviewed mappings require maintenance when official documentation changes.

## Build and validate

Use Python 3.11 or newer in a virtual environment:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m registry sync
python -m registry validate
python -m unittest discover -s tests
```

`sync` retrieves the public inputs, normalizes them, and validates the output under `public/v1/`. Local fetch caches are kept in `.cache/`. The release also tracks compressed, licensed public source snapshots under `public/v1/source-snapshots/`, together with their hashes and attribution. If the local cache is absent, the builder restores it from those snapshots. To reproduce a build without refetching:

```sh
python -m registry build
python -m registry validate
```

Use the same code revision and reviewed evidence as the snapshot. Keep the cache when reproducing an unpublished build that has no committed snapshots yet. Public source data can change between fetches. Do not edit generated JSON by hand; change the importer or reviewed evidence, then rebuild. See [AGENTS.md](AGENTS.md) for contribution rules.

## Automation and operations

GitHub Actions runs synchronization at 00:23, 06:23, 12:23, and 18:23 UTC, and supports **Actions → Sync and publish registry → Run workflow**. It fetches sources, tests and validates the generated data, compares content, and publishes releases to GitHub Pages. An unchanged catalog does not produce an empty update commit; publication can still be retried. A failed fetch or validation stops publication and preserves the last published release.

For a downloadable archive, run **Actions → Release immutable data snapshot → Run workflow** on `main`. It validates the committed catalog and publishes a content-addressed `data-…` release with a ZIP and `SHA256SUMS`. The workflow leaves an existing release of the same content unchanged. This manual archive release is separate from the scheduled Pages publication.

The workflow runs on GitHub and does not require Dot, Hermes, Codex, or another agent to stay online. It uses the job's short-lived `GITHUB_TOKEN`, with write permissions limited to jobs that commit releases or deploy Pages. Pull-request validation must not receive those write permissions. Do not add provider credentials to the repository or workflow.

GitHub schedules can be delayed; scheduled workflows in public repositories can be disabled after 60 days without repository activity. This is a best-effort update service, not a permanent unattended availability guarantee. See [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). Check failed runs and data freshness, re-enable disabled schedules, and rerun a failed sync after fixing its cause.

If publication is blocked, inspect repository **Settings → Pages**, workflow token permissions, the `github-pages` environment, and any branch rules that restrict automation commits. Keep the existing release available while resolving the failure; do not bypass protections silently. The repository's Pages deployment source must be **GitHub Actions**.

## License and versioning

Original code and documentation use the [MIT license](LICENSE). Imported material retains its upstream attribution and applicable terms; the repository license does not relicense third-party data or documentation. Read [docs/SOURCES.md](docs/SOURCES.md) before redistributing source material. The reviewed, licensed public snapshots are intentionally published; the working `.cache/` directory and any credentials stay out of Git. Full Xiaomi documentation pages are not redistributed.

See [CHANGELOG.md](CHANGELOG.md) for contract and software changes. Source coverage is bounded by what the current importers and reviewed mappings can verify; the project name is not a claim of exhaustive or real-time coverage.

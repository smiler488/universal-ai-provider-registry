# Sources and evidence boundaries

Initial review: **2026-10-14**. Counts below describe that review snapshot; later successful synchronizations can change them.

| Source | Public input | Initial scope | License evidence |
| --- | --- | --- | --- |
| OpenClaw Catalog V2 | [catalog.json](https://catalog.openclaw.ai/models/v2/catalog.json) | 1,028 model/provider rows; 43 providers | [MIT](https://github.com/openclaw/catalog/blob/main/LICENSE) |
| Models.dev full provider catalog | [api.json?type=all](https://models.dev/api.json?type=all) | 8,853 model/provider rows; 228 providers | [MIT](https://github.com/anomalyco/models.dev/blob/dev/LICENSE) |
| Models.dev full combined catalog | [catalog.json?type=all](https://models.dev/catalog.json?type=all) | Same provider records, plus 552 provider-independent model records | Same Models.dev MIT notice |
| Selected official documentation | [reviewed factual observations](../data/reviewed-evidence.json) | Dated model-list, capability, endpoint and lifecycle observations, with provider-specific scope | License status retained per source; pages without an identified open license are not redistributed in full |

## Interpretation

Models.dev documents the `type=all` option because default responses omit specialized model types. Its combined catalog separates provider-independent model records from deployment records. When present, `canonical_model_id` supplies an explicit canonical identity. A provider's limits and modalities can override the underlying model defaults. The same model name at two providers does not establish equal price, endpoint, features or availability. [Models.dev documentation](https://github.com/anomalyco/models.dev#api)

OpenClaw V2 is a catalog for OpenClaw clients. Its provider records in the reviewed snapshot specify transport identifiers and recommended models, but do not supply base URLs. Its model hydration is selective: the documented process admits tool-calling, text-output models and omits deprecated/retired upstream rows. An absent model is therefore not proof that the model does not exist. [Catalog documentation](https://github.com/openclaw/catalog), [hydration rules](https://docs.openclaw.ai/concepts/models)

OpenClaw V2 model prices include an explicit status. In the reviewed snapshot, 893 rows were `known`, 127 `unknown` and 8 `unavailable`. Missing or unavailable prices must not become zero. Models.dev documents its token cost fields in USD per million tokens; preserve additional dimensions and tiers instead of flattening them. Subscription-plan zero values are source observations and do not establish a free account or free service. [Models.dev cost field definitions](https://github.com/anomalyco/models.dev#schema-reference)

Sources are related: OpenClaw itself can hydrate metadata or pricing from Models.dev. Agreement between them is not independent confirmation. Preserve each observation and its source; expose differences instead of silently combining capability sets. Standalone OpenClaw pricing entries are not, by themselves, evidence for a serving deployment.

## Reviewed official evidence

The [evidence file](../data/reviewed-evidence.json) stores dated manual reviews and their original source links. Automated synchronization must not advance a review's `checked_at` date. A maintainer must read the cited official material and review the recorded facts before changing that date. A model-list example in documentation remains an example response, not an authenticated live inventory. This registry does not submit API keys or perform authenticated model-list requests.

Selected facts carry specific evidence URLs and apply only to the identified provider or deployment. Unknown values stay null. Documentation for an ordinary API must not grant capabilities or entitlement to subscription plans, regional endpoints, or resellers. Capability descriptions, endpoint paths, lifecycle dates and pricing units retain their original scope; no endpoints or token-price conversions are inferred from broad compatibility claims.

## Reuse and attribution

Redistributed upstream data retains its upstream attribution. Exact reviewed MIT notices are in [licenses/](../licenses/); see [third-party notices](../THIRD_PARTY_NOTICES.md). Catalog reuse permission does not license model weights, provider services, trademarks or third-party datasets referenced by a record. An `open_weights` observation is not a license grant. Where a model or service license is absent, its status remains unknown.

Upstream strings, URLs and JSON are untrusted data, not executable configuration or instructions. Fetch only approved source URLs. Do not use published model endpoints to issue inference or credential-bearing requests during catalog validation.

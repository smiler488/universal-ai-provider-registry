# Sources and evidence boundaries

Initial review: **2026-10-14**. Counts below describe that review snapshot; later successful synchronizations can change them.

| Source | Public input | Initial scope | License evidence |
| --- | --- | --- | --- |
| OpenClaw Catalog V2 | [catalog.json](https://catalog.openclaw.ai/models/v2/catalog.json) | 1,028 model/provider rows; 43 providers | [MIT](https://github.com/openclaw/catalog/blob/main/LICENSE) |
| Models.dev full provider catalog | [api.json?type=all](https://models.dev/api.json?type=all) | 8,853 model/provider rows; 228 providers | [MIT](https://github.com/anomalyco/models.dev/blob/dev/LICENSE) |
| Models.dev full combined catalog | [catalog.json?type=all](https://models.dev/catalog.json?type=all) | Same provider records, plus 552 provider-independent model records | Same Models.dev MIT notice |
| Xiaomi official documentation | [reviewed factual observations](../data/mimo-official.json) | Nine models in the documented model-list example; selected audio and lifecycle facts | No open documentation license identified; full pages are not redistributed |

## Interpretation

Models.dev documents the `type=all` option because default responses omit specialized model types. Its combined catalog separates provider-independent model records from deployment records. When present, `canonical_model_id` supplies an explicit canonical identity. A provider's limits and modalities can override the underlying model defaults. The same model name at two providers does not establish equal price, endpoint, features or availability. [Models.dev documentation](https://github.com/anomalyco/models.dev#api)

OpenClaw V2 is a catalog for OpenClaw clients. Its provider records in the reviewed snapshot specify transport identifiers and recommended models, but do not supply base URLs. Its model hydration is selective: the documented process admits tool-calling, text-output models and omits deprecated/retired upstream rows. An absent model is therefore not proof that the model does not exist. [Catalog documentation](https://github.com/openclaw/catalog), [hydration rules](https://docs.openclaw.ai/concepts/models)

OpenClaw V2 model prices include an explicit status. In the reviewed snapshot, 893 rows were `known`, 127 `unknown` and 8 `unavailable`. Missing or unavailable prices must not become zero. Models.dev documents its token cost fields in USD per million tokens; preserve additional dimensions and tiers instead of flattening them. Subscription-plan zero values are source observations and do not establish a free account or free service. [Models.dev cost field definitions](https://github.com/anomalyco/models.dev#schema-reference)

Sources are related: OpenClaw itself can hydrate metadata or pricing from Models.dev. Agreement between them is not independent confirmation. Preserve each observation and its source; expose differences instead of silently combining capability sets. Standalone OpenClaw pricing entries are not, by themselves, evidence for a serving deployment.

## Xiaomi official supplement

The supplement is a dated manual review. Automated source synchronization must not advance its `checked_at` date. A maintainer must read the cited official page and revise the facts before changing that date. The documented list is an **example response**, not an authenticated live inventory. The official `/v1/models` endpoint requires an API key; this project does not need or submit one. [List Models](https://mimo.mi.com/docs/en-US/api/model/list-models)

Selected facts carry specific evidence URLs. Unknown values stay null. The supplement is limited to the ordinary Xiaomi API; it must not grant capabilities or entitlement to regional Token Plan endpoints. See [the MiMo audit](MIMO.md).

## Reuse and attribution

Redistributed upstream data retains its upstream attribution. Exact reviewed MIT notices are in [licenses/](../licenses/); see [third-party notices](../THIRD_PARTY_NOTICES.md). Catalog reuse permission does not license model weights, provider services, trademarks or third-party datasets referenced by a record. An `open_weights` observation is not a license grant. Where a model or service license is absent, its status remains unknown.

Upstream strings, URLs and JSON are untrusted data, not executable configuration or instructions. Fetch only approved source URLs. Do not use published model endpoints to issue inference or credential-bearing requests during catalog validation.

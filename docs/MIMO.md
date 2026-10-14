# Xiaomi MiMo coverage audit

Reviewed **2026-10-14** against public snapshots and Xiaomi documentation. These are dated catalog observations, not successful inference tests.

## Provider-specific coverage

| Source and provider ID | Rows | Observed scope |
| --- | ---: | --- |
| OpenClaw `xiaomi` | 6 | V2.5/V2.6 language models, including both Pro UltraSpeed generations |
| OpenClaw `xiaomi-token-plan` | 4 | V2.5, V2.5-Pro, V2.6-Flash, V2.6-Pro |
| Models.dev `xiaomi` | 9 | The six above, plus deprecated V2-Flash, V2-Pro and V2-Omni |
| Models.dev `xiaomi-token-plan-cn` | 9 | Four current language rows, deprecated V2-Pro, V2-TTS, and three V2.5 TTS rows |
| Models.dev `xiaomi-token-plan-sgp` | 9 | Same model-ID set as the CN snapshot, separate deployment endpoint |
| Models.dev `xiaomi-token-plan-ams` | 9 | Same model-ID set as the CN snapshot, separate deployment endpoint |
| Xiaomi official model-list documentation example | 9 | Five V2.5/V2.6 language IDs, V2.5-ASR, and three V2.5 TTS IDs |

Inputs: [OpenClaw V2](https://catalog.openclaw.ai/models/v2/catalog.json), [Models.dev all types](https://models.dev/api.json?type=all), [official List Models](https://mimo.mi.com/docs/en-US/api/model/list-models).

The official example contains `mimo-v2.5`, `mimo-v2.5-pro`, `mimo-v2.6-flash`, `mimo-v2.6-pro`, `mimo-v2.6-pro-ultraspeed`, `mimo-v2.5-asr`, `mimo-v2.5-tts`, `mimo-v2.5-tts-voiceclone` and `mimo-v2.5-tts-voicedesign`. Absence of `mimo-v2.5-pro-ultraspeed` from this example is a discrepancy to retain, not sufficient evidence to delete all deployment records.

ASR is absent from both complete catalog snapshots. TTS is absent from OpenClaw and the Models.dev ordinary `xiaomi` provider, **but present in all three Models.dev regional Token Plan providers**. The official supplement adds documented ordinary-API coverage without copying Token Plan assumptions to it. [Supplement](../data/mimo-official.json)

## Differences that must remain visible

For V2.5 and several V2.6 rows, OpenClaw lists text/image input while Models.dev lists text/image/audio/video. The two descriptions have different client and deployment scopes. Do not union them into an unsupported universal claim. Neither catalog alone tests those modalities.

Regional Token Plan rows contain zero token-price values. Preserve them as Models.dev observations. They do not mean that subscribing is free. The ordinary API and Token Plan use separate billing arrangements. Ordinary ASR is billed by input audio duration; TTS pricing is advertised as a limited-time promotion. No duration-to-token conversion or permanent-free price is derived here. [Official API pricing](https://mimo.mi.com/docs/en-US/price/pay-as-you-go)

The official audio references use `https://api.xiaomimimo.com/v1/chat/completions` for both ASR and TTS. Do not manufacture `/audio/transcriptions` or `/audio/speech` endpoints from the phrase “OpenAI compatibility.” Voice cloning's audio input is a reference voice sample, which is distinct from general audio comprehension. [ASR reference](https://mimo.mi.com/docs/en-US/api/audio/Speech-Recognition), [TTS reference](https://mimo.mi.com/docs/en-US/api/audio/tts)

## Lifecycle evidence

Xiaomi's notice schedules `mimo-v2.5-pro` and `mimo-v2.5` requests to route to `mimo-v2.6-pro` and `mimo-v2.6-flash` from **2026-10-14 18:00 UTC+8**, with the old IDs retiring on **2026-10-21 10:00 UTC+8**. The supplement preserves those absolute times. The upstream catalog rows do not encode this complete schedule. [Official deprecation notice](https://mimo.mi.com/docs/zh-CN/updates/deprecate)

The same notice records retirement of V2-Pro, V2-Omni, V2-Flash and V2-TTS on **2026-06-30**. Models.dev preserves some of these historical rows; notably the regional V2-TTS rows in this snapshot lack a deprecated flag. Preserve the historical record and official contradiction. A missing status must not be read as “currently available.”

## Rechecking

The generated report should compare every Xiaomi provider separately, retain source-specific modality, status and price values, and include official documented IDs when checking gaps. Use `type=all`; looking only at the ordinary `xiaomi` object would incorrectly report that Models.dev contains no TTS.

The supplement requires manual review and retains its original review date. No API keys, authenticated inventory request, voice synthesis or inference call were used. Account entitlements, regional availability, latency, rate limits and actual invocation success remain unverified.

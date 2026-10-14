"""Versioned JSON Schema for every published JSON envelope."""
S = {'type': 'string'}
N = {'type': ['string', 'null']}
I = {'type': ['integer', 'null'], 'minimum': 0}
STRINGS = {'type': 'array', 'items': S, 'uniqueItems': True}
CAPS = ['reasoning', 'vision', 'audio_input', 'audio_output', 'video_input', 'image_generation', 'video_generation', 'tool_calling', 'structured_output', 'streaming', 'embedding']
STATE = {'enum': ['supported', 'unsupported', 'unknown']}

def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required, 'additionalProperties': False}

def arr(ref):
    return {'type': 'array', 'items': {'$ref': '#/$defs/' + ref}}

CAPABILITIES = obj({k: STATE for k in CAPS})
SOURCE = obj({'id': S, 'name': S, 'url': S, 'sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}, 'license': S, 'verification': S})
OBSERVATION = obj({'source_id': S, 'source_record_id': S, 'verification': {'enum': ['registry_reported', 'officially_documented']}, 'presence': {'enum': ['listed', 'removed_from_source']}, 'name': S, 'capabilities': CAPABILITIES, 'input_modalities': {'type': ['array', 'null'], 'items': S}, 'output_modalities': {'type': ['array', 'null'], 'items': S}, 'context_window': I, 'max_output_tokens': I, 'pricing': {'type': ['object', 'null']}, 'lifecycle': S})
MODEL = obj({'id': S, 'name': S, 'developer_id': N, 'identity_status': {'enum': ['registry_reported', 'officially_documented', 'unknown']}, 'source_ids': STRINGS})
DEVELOPER = obj({'id': S, 'name': S, 'verification': S, 'source_ids': STRINGS})
ENDPOINT = obj({'base_url': N, 'protocol': N, 'source_id': S, 'verification': S})
PROVIDER = obj({'id': {'type': 'string', 'pattern': '^[a-zA-Z0-9_.-]+$'}, 'name': S, 'region': N, 'plan': N, 'endpoints': arr('endpoint'), 'source_ids': STRINGS})
DEPLOYMENT = obj({'id': S, 'provider_id': S, 'provider_model_id': S, 'model_id': S, 'verification': S, 'availability': {'enum': ['listed', 'removed_from_source']}, 'lifecycle': S, 'capabilities': CAPABILITIES, 'pricing_status': {'enum': ['unknown', 'reported', 'conflicting', 'zero_requires_verification']}, 'conflicts': STRINGS, 'observations': arr('observation')})
PROPERTIES = {'schema_version': {'const': '1.0.0'}, 'data_version': S, 'generated_at': {'type': 'string', 'format': 'date-time'}, 'kind': {'enum': ['catalog', 'models', 'developers', 'providers', 'deployments', 'provider', 'diff', 'mimo-report']}, 'sources': arr('source'), 'models': arr('model'), 'developers': arr('developer'), 'providers': arr('provider'), 'deployments': arr('deployment'), 'provider': {'$ref': '#/$defs/provider'}, 'report': {'type': 'object'}}
SCHEMA = {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'https://smiler488.github.io/universal-ai-provider-registry/v1/schema.json', **obj(PROPERTIES, ['schema_version', 'data_version', 'generated_at', 'kind', 'sources']), '$defs': {'source': SOURCE, 'model': MODEL, 'developer': DEVELOPER, 'provider': PROVIDER, 'endpoint': ENDPOINT, 'deployment': DEPLOYMENT, 'observation': OBSERVATION}, 'allOf': []}
for kind, fields in {'catalog': ['models','developers','providers','deployments'], 'models':['models'], 'developers':['developers'], 'providers':['providers'], 'deployments':['deployments'], 'provider':['provider','models','deployments'], 'diff':['report'], 'mimo-report':['report']}.items():
    SCHEMA['allOf'].append({'if': {'properties': {'kind': {'const': kind}}}, 'then': {'required': fields}})

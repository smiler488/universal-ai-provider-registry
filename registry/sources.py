"""Fetch allowlisted public feeds only; never execute source data or request inference."""
import hashlib
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

SOURCES = {
    'openclaw': 'https://catalog.openclaw.ai/models/v2/catalog.json',
    'models-dev': 'https://models.dev/api.json?type=all',
    'models-dev-canonical': 'https://models.dev/catalog.json?type=all',
}
MAX_BYTES = 50 * 1024 * 1024


class PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from urllib.parse import urlparse
        target = urlparse(newurl)
        if target.scheme != 'https' or target.hostname not in ('models.dev', 'catalog.openclaw.ai') or target.username or target.password:
            raise ValueError('Source redirect is outside the public allowlist')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


urlopen = build_opener(PublicRedirects()).open


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def check_source(name, data):
    if name == 'openclaw':
        if data.get('schemaVersion') != 2 or not isinstance(data.get('models'), list) or not data['models']:
            raise ValueError('OpenClaw V2 contract changed or empty')
        keys = [(r['provider'], r['id']) for r in data['models']]
        if len(set(keys)) != len(keys):
            raise ValueError('Duplicate OpenClaw deployment keys')
    else:
        providers = data if name == 'models-dev' else data.get('providers')
        if not isinstance(providers, dict) or not providers:
            raise ValueError('Empty/invalid Models.dev providers')
        if not any(p.get('models') for p in providers.values()):
            raise ValueError('Models.dev has no deployments')
        for key, provider in providers.items():
            if provider.get('id') != key or not isinstance(provider.get('models'), dict):
                raise ValueError('Models.dev provider contract changed')
            for key, model in provider['models'].items():
                if model.get('id') != key:
                    raise ValueError('Models.dev model key mismatch')
        if name == 'models-dev-canonical' and not isinstance(data.get('models'), dict):
            raise ValueError('Models.dev canonical model map missing')


def fetch(name, cache=Path('.cache')):
    """Conditional GET, bounded size, retries; bad/failed sources never replace a valid cache."""
    cache.mkdir(parents=True, exist_ok=True)
    path, meta_path = cache / f'{name}.json', cache / f'{name}.meta.json'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    headers = {'User-Agent': 'universal-ai-provider-registry/0.1 (+https://github.com/smiler488/universal-ai-provider-registry)', 'Accept': 'application/json'}
    if path.exists() and meta.get('etag'):
        headers['If-None-Match'] = meta['etag']
    error = None
    for attempt in range(3):
        try:
            with urlopen(Request(SOURCES[name], headers=headers), timeout=45) as response:
                if not response.url.startswith('https://'):
                    raise ValueError('HTTPS downgrade rejected')
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ValueError('Source exceeds byte limit')
                value = json.loads(raw)
                check_source(name, value)
                tmp = path.with_suffix('.tmp')
                tmp.write_bytes(raw)
                tmp.replace(path)
                meta_path.write_bytes(encoded({'etag': response.headers.get('ETag'), 'sha256': hashlib.sha256(raw).hexdigest()}))
                return value
        except HTTPError as exc:
            if exc.code == 304 and path.exists():
                value = json.loads(path.read_text())
                check_source(name, value)
                return value
            error = exc
            if exc.code not in (408, 429, 500, 502, 503, 504):
                break
            delay = exc.headers.get('Retry-After', '')
            time.sleep(min(int(delay), 30) if delay.isdigit() else 2 ** attempt)
        except (URLError, TimeoutError, OSError) as exc:
            error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f'{name} unavailable; publication aborted, last public catalog retained: {error}')


def load_sources(online=False, cache=Path('.cache')):
    result = {}
    for name in SOURCES:
        result[name] = fetch(name, cache) if online else json.loads((cache / f'{name}.json').read_text())
        check_source(name, result[name])
    return result

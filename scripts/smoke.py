#!/usr/bin/env python3
"""Verify deployed public files against a locally validated snapshot (stdlib only)."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


CORE = ('catalog.json', 'models.json', 'providers.json', 'deployments.json')
MAX_RESPONSE_BYTES = 100 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_response(url: str, headers: dict[str, str] | None = None):
    request = Request(url, headers={'User-Agent': 'universal-ai-provider-registry-smoke/1', **(headers or {})})
    with urlopen(request, timeout=30) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError('Response exceeds 100 MiB safety limit')
        return response.status, response.headers, body


def check_file(base: str, directory: Path, path: Path, attempts: int, delay: float) -> dict:
    relative = path.relative_to(directory).as_posix()
    url = base.rstrip('/') + '/' + quote(relative, safe='/')
    expected = path.read_bytes()
    last_error = None
    for attempt in range(attempts):
        try:
            status, headers, body = read_response(url)
            if status != 200:
                raise ValueError(f'Expected HTTP 200; received {status}')
            mime = headers.get('Content-Type', '').split(';')[0].strip().lower()
            if path.suffix == '.json':
                if mime != 'application/json' and not mime.endswith('+json'):
                    raise ValueError(f'Wrong JSON Content-Type: {mime!r}')
                json.loads(body)
            if headers.get('Access-Control-Allow-Origin') != '*':
                raise ValueError('Expected Access-Control-Allow-Origin: * for unauthenticated public data')
            if not headers.get('Cache-Control'):
                raise ValueError('Missing Cache-Control')
            etag = headers.get('ETag')
            if not etag:
                raise ValueError('Missing ETag')
            if digest(body) != digest(expected):
                raise ValueError('SHA-256 mismatch; deployment or edge cache does not match the validated snapshot')
            conditional = None
            if relative == 'catalog.json':
                try:
                    next_status, next_headers, next_body = read_response(url, {'If-None-Match': etag})
                except HTTPError as error:
                    if error.code != 304:
                        raise
                    conditional = 304
                    if error.headers.get('ETag', etag) != etag:
                        raise ValueError('ETag changed during conditional request')
                else:
                    if next_status != 200 or next_headers.get('ETag') != etag or next_body != body:
                        raise ValueError('Conditional response changed unexpectedly')
                    conditional = 200
            return {'path': relative, 'status': status, 'sha256': digest(body), 'etag': etag,
                    'cache_control': headers['Cache-Control'], 'cors': '*',
                    'conditional_status': conditional, 'bytes': len(body)}
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            last_error = str(error)
            if attempt + 1 < attempts:
                time.sleep(delay)
    raise RuntimeError(f'{relative}: {last_error}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, help='Public v1 root, e.g. https://owner.github.io/repo/v1')
    parser.add_argument('--directory', type=Path, default=Path('public/v1'))
    parser.add_argument('--attempts', type=int, default=3)
    parser.add_argument('--retry-delay', type=float, default=5)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--report', type=Path, help='Optional detailed JSON report')
    args = parser.parse_args()
    if urlparse(args.base).scheme != 'https':
        parser.error('--base must be an HTTPS URL')
    if not (1 <= args.attempts <= 12 and 1 <= args.workers <= 16 and 0 <= args.retry_delay <= 30):
        parser.error('Use 1–12 attempts, 1–16 workers, and a 0–30 second retry delay')
    directory = args.directory.resolve()
    for name in CORE:
        if not (directory / name).is_file():
            parser.error(f'Missing local required file: {directory / name}')
    files = sorted(p for p in directory.rglob('*') if p.is_file())
    if any(p.is_symlink() for p in files):
        parser.error('Local snapshot must not contain symlinks')
    provider_files = [p for p in files if p.parent == directory / 'provider-models' and p.suffix == '.json']
    if not provider_files:
        parser.error('No provider shard exists under provider-models/ in the local snapshot')
    reports, failures = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(check_file, args.base, directory, p, args.attempts, args.retry_delay): p for p in files}
        for future in as_completed(pending):
            try:
                reports.append(future.result())
            except Exception as error:
                failures.append(str(error))
    result = {'base_url': args.base.rstrip('/'), 'checked_files': len(files), 'passed_files': len(reports),
              'provider_file_count': len(provider_files),
              'failures': sorted(failures), 'files': sorted(reports, key=lambda item: item['path'])}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

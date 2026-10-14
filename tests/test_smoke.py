"""Public-access regression checks, using the actual provider-models contract."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlparse

from scripts import smoke


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        for name in smoke.CORE:
            (self.directory / name).write_text('{"data_version":"test"}\n')
        (self.directory / 'provider-models').mkdir()
        (self.directory / 'provider-models/xiaomi.json').write_text('{"kind":"provider"}\n')
        (self.directory / 'source-snapshots').mkdir()
        (self.directory / 'source-snapshots/test.json.gz').write_bytes(b'compressed-public-snapshot')
        self.headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                        'Cache-Control': 'max-age=600', 'ETag': '"test"'}

    def response(self, url, headers=None):
        if headers and headers.get('If-None-Match'):
            raise HTTPError(url, 304, 'Not Modified', self.headers, None)
        relative = urlparse(url).path.removeprefix('/v1/')
        return 200, self.headers, (self.directory / relative).read_bytes()

    def test_actual_provider_shard_path_and_all_files_checked(self):
        output = io.StringIO()
        with patch('sys.argv', ['smoke', '--base', 'https://example.org/v1', '--directory', str(self.directory)]), \
                patch.object(smoke, 'read_response', side_effect=self.response), redirect_stdout(output):
            self.assertEqual(smoke.main(), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['xiaomi_files'], ['provider-models/xiaomi.json'])
        self.assertEqual(report['passed_files'], 6)

    def test_old_provider_path_cannot_satisfy_xiaomi_check(self):
        (self.directory / 'provider-models').rename(self.directory / 'providers')
        with patch('sys.argv', ['smoke', '--base', 'https://example.org/v1', '--directory', str(self.directory)]), \
                redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            smoke.main()

    def test_rejects_stale_json(self):
        with patch.object(smoke, 'read_response', return_value=(200, self.headers, b'{}')):
            with self.assertRaisesRegex(RuntimeError, 'SHA-256 mismatch'):
                smoke.check_file('https://example.org/v1', self.directory, self.directory / 'catalog.json', 1, 0)

    def test_rejects_bad_http_headers(self):
        for name, value in [('Content-Type', 'text/html'), ('Access-Control-Allow-Origin', ''),
                            ('Cache-Control', ''), ('ETag', '')]:
            with self.subTest(header=name):
                headers = {**self.headers, name: value}
                with patch.object(smoke, 'read_response', return_value=(200, headers, b'{}')):
                    with self.assertRaises(RuntimeError):
                        smoke.check_file('https://example.org/v1', self.directory, self.directory / 'catalog.json', 1, 0)

    def test_conditional_get_and_transient_failure_retry(self):
        expected = (self.directory / 'catalog.json').read_bytes()
        responses = [OSError('temporary'), (200, self.headers, expected),
                     HTTPError('https://example.org/v1/catalog.json', 304, 'Not Modified', self.headers, None)]
        with patch.object(smoke, 'read_response', side_effect=responses):
            result = smoke.check_file('https://example.org/v1', self.directory, self.directory / 'catalog.json', 2, 0)
        self.assertEqual(result['conditional_status'], 304)


if __name__ == '__main__':
    unittest.main()

"""Small evidence fixtures exercise public contract and publication failure modes."""
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request

from registry.core import build, normalize, validate
from registry.sources import PublicRedirects, SOURCES, check_source, encoded, fetch


def fixtures():
    providers = {
        'lab': {
            'id': 'lab', 'name': 'Lab', 'api': 'https://api.example.test/v1',
            'models': {'model-one': {'id': 'model-one', 'name': 'Example'}},
        }
    }
    data = {
        'models-dev': providers,
        'models-dev-canonical': {
            'providers': copy.deepcopy(providers),
            'models': {'lab/model-one': {'id': 'lab/model-one', 'name': 'Example'}},
        },
        'openclaw': {
            'schemaVersion': 2, 'generatedAt': 1000, 'sourceCommit': 'a' * 40,
            'models': [{'provider': 'lab', 'id': 'model-one', 'name': 'Example'}],
            'providers': {'lab': {'api': 'openai-completions'}},
            'providerPricing': {}, 'upstreamPricing': {},
        },
    }
    reviewed = {'sources': [{
        'source_id': 'example-official',
        'provider_id': 'example', 'provider_name': 'Example Provider',
        'developer_id': 'example-lab',
        'identity_provider_ids': ['example', 'example-plan'],
        'checked_at': '2026-10-14', 'refresh_policy': 'manual-review-required',
        'base_url': 'https://api.example.test/v1',
        'models': [{
            'id': 'speech-one', 'developer_id': 'example-lab',
            'capabilities': {'input_modalities': ['audio'], 'output_modalities': ['text']},
            'lifecycle': {'status': 'documented'},
        }],
    }]}
    return data, reviewed


def dep(catalog, provider='lab', model='model-one'):
    return next(d for d in catalog['deployments']
                if d['provider_id'] == provider and d['provider_model_id'] == model)


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.data, self.reviewed = fixtures()

    def test_omitted_capabilities_and_absent_prices_remain_unknown(self):
        result = normalize(self.data, self.reviewed)
        row = dep(result)
        self.assertEqual(set(row['capabilities'].values()), {'unknown'})
        self.assertEqual(row['pricing_status'], 'unknown')
        self.assertTrue(all(o['pricing'] is None for o in row['observations']))
        self.assertEqual(row['lifecycle'], 'unknown')

    def test_explicit_boolean_disagreement_is_unknown_with_both_claims(self):
        self.data['models-dev']['lab']['models']['model-one']['reasoning'] = True
        self.data['openclaw']['models'][0]['reasoning'] = False
        row = dep(normalize(self.data, self.reviewed))
        self.assertEqual(row['capabilities']['reasoning'], 'unknown')
        self.assertIn('capabilities.reasoning', row['conflicts'])
        self.assertEqual({o['capabilities']['reasoning'] for o in row['observations']},
                         {'supported', 'unsupported'})

    def test_audio_output_and_subscription_zero_survive_without_free_claim(self):
        self.data['models-dev']['voice-plan'] = {
            'id': 'voice-plan', 'name': 'Voice subscription',
            'models': {'voice-one': {
                'id': 'voice-one', 'name': 'Voice',
                'modalities': {'input': ['text'], 'output': ['audio']},
                'reasoning': False, 'tool_call': False,
                'cost': {'input': 0, 'output': 0},
            }},
        }
        row = dep(normalize(self.data, self.reviewed), 'voice-plan', 'voice-one')
        self.assertEqual(row['capabilities']['audio_output'], 'supported')
        self.assertEqual(row['capabilities']['audio_input'], 'unknown')
        self.assertEqual(row['capabilities']['reasoning'], 'unsupported')
        self.assertEqual(row['pricing_status'], 'zero_requires_verification')
        self.assertEqual(row['observations'][0]['pricing']['raw'], {'input': 0, 'output': 0})

    def test_unknown_or_unavailable_openclaw_pricing_is_not_reported_price(self):
        for status in ('unknown', 'unavailable'):
            with self.subTest(status=status):
                self.data['openclaw']['models'][0]['pricing'] = {'status': status}
                row = dep(normalize(self.data, self.reviewed))
                self.assertIn(row['pricing_status'], ('unknown', 'unavailable'))
                claim = next(o for o in row['observations'] if o['source_id'].startswith('openclaw:'))
                self.assertEqual(claim['pricing']['raw']['status'], status)

    def test_same_display_name_does_not_merge_unresolved_providers(self):
        for pid in ('relay-a', 'relay-b'):
            self.data['models-dev'][pid] = {
                'id': pid, 'name': pid,
                'models': {'brand/model': {'id': 'brand/model', 'name': 'Example'}},
            }
        result = normalize(self.data, self.reviewed)
        first = dep(result, 'relay-a', 'brand/model')
        second = dep(result, 'relay-b', 'brand/model')
        self.assertNotEqual(first['model_id'], second['model_id'])
        indexed = {m['id']: m for m in result['models']}
        for row in (first, second):
            self.assertEqual(indexed[row['model_id']]['identity_status'], 'unknown')
            self.assertIsNone(indexed[row['model_id']]['developer_id'])

    def test_explicit_canonical_identity_applies_to_openclaw_peer(self):
        self.data['models-dev-canonical']['models']['developer/real-model'] = {
            'id': 'developer/real-model', 'name': 'Real model',
        }
        self.data['models-dev']['lab']['models']['model-one']['canonical_model_id'] = 'developer/real-model'
        row = dep(normalize(self.data, self.reviewed))
        self.assertEqual(row['model_id'], 'developer/real-model')
        self.assertEqual(len(row['observations']), 2)

    def test_similar_provider_name_does_not_grant_reviewed_identity(self):
        self.data['models-dev']['example-impostor'] = {
            'id': 'example-impostor', 'name': 'Unreviewed relay',
            'models': {'speech-one': {'id': 'speech-one', 'name': 'Speech'}},
        }
        result = normalize(self.data, self.reviewed)
        row = dep(result, 'example-impostor', 'speech-one')
        model = next(m for m in result['models'] if m['id'] == row['model_id'])
        self.assertEqual(model['identity_status'], 'unknown')
        self.assertIsNone(model['developer_id'])

    def test_multiple_reviewed_sources_keep_providers_and_developers_distinct(self):
        another = copy.deepcopy(self.reviewed['sources'][0])
        another.update({
            'source_id': 'another-official',
            'provider_id': 'another', 'provider_name': 'Another Provider',
            'developer_id': 'another-lab',
            'identity_provider_ids': ['another', 'another-plan'],
            'base_url': 'https://api.another.example.test/v1',
        })
        another['models'][0]['developer_id'] = 'another-lab'
        self.reviewed['sources'].append(another)
        result = normalize(self.data, self.reviewed)
        indexed_models = {m['id']: m for m in result['models']}
        indexed_providers = {p['id']: p for p in result['providers']}
        evidence_ids = {s['id'] for s in result['sources']}
        for provider, developer in (('example', 'example-lab'), ('another', 'another-lab')):
            row = dep(result, provider, 'speech-one')
            self.assertEqual(row['model_id'], developer + '/speech-one')
            self.assertEqual(indexed_models[row['model_id']]['developer_id'], developer)
            self.assertEqual(row['verification'], 'officially_documented')
            self.assertEqual(row['capabilities']['audio_input'], 'supported')
            self.assertEqual(row['capabilities']['audio_output'], 'unknown')
            self.assertTrue(set(indexed_providers[provider]['source_ids']) <= evidence_ids)
        self.assertNotEqual(dep(result, 'example', 'speech-one')['model_id'],
                            dep(result, 'another', 'speech-one')['model_id'])

    def test_only_reviewed_provider_aliases_share_documented_identity(self):
        self.data['models-dev']['example-plan'] = {
            'id': 'example-plan', 'name': 'Example Plan',
            'models': {'speech-one': {'id': 'speech-one', 'name': 'Speech'}},
        }
        result = normalize(self.data, self.reviewed)
        row = dep(result, 'example-plan', 'speech-one')
        self.assertEqual(row['model_id'], 'example-lab/speech-one')
        # Identity evidence does not turn a separate plan's serving claims into
        # officially tested or documented plan capabilities.
        self.assertEqual(row['verification'], 'registry_reported')
        self.assertEqual(row['capabilities']['audio_input'], 'unknown')

    def test_empty_reviewed_sources_adds_no_provider_or_hardcoded_model(self):
        result = normalize(self.data, {'sources': []})
        self.assertEqual({p['id'] for p in result['providers']}, {'lab'})
        self.assertEqual({m['id'] for m in result['models']}, {'lab/model-one'})
        self.assertEqual({d['id'] for d in result['developers']}, {'lab'})
        self.assertEqual(len(result['deployments']), 1)

    def test_successful_disappearance_retains_tombstone_and_source_evidence(self):
        self.data['models-dev']['lab']['models']['gone'] = {'id': 'gone', 'name': 'Former model'}
        previous = normalize(self.data, self.reviewed)
        before = copy.deepcopy(previous)
        old_row = dep(previous, 'lab', 'gone')
        del self.data['models-dev']['lab']['models']['gone']
        current = normalize(self.data, self.reviewed, previous)
        row = dep(current, 'lab', 'gone')
        self.assertEqual(row['availability'], 'removed_from_source')
        self.assertEqual(row['verification'], 'unverified')
        self.assertTrue(all(o['presence'] == 'removed_from_source' for o in row['observations']))
        self.assertEqual(row['model_id'], old_row['model_id'])
        self.assertTrue({o['source_id'] for o in row['observations']} <= {s['id'] for s in current['sources']})
        self.assertEqual(previous, before)

    def test_partial_source_disappearance_does_not_remove_other_claim(self):
        self.data['openclaw']['models'].append({'provider': 'lab', 'id': 'other', 'name': 'Other'})
        previous = normalize(self.data, self.reviewed)
        self.data['openclaw']['models'] = self.data['openclaw']['models'][1:]
        row = dep(normalize(self.data, self.reviewed, previous))
        self.assertEqual(row['availability'], 'listed')
        present = {o['source_id'].split(':')[0]: o['presence'] for o in row['observations']}
        self.assertEqual(present, {'models-dev': 'listed', 'openclaw': 'removed_from_source'})


class SourceContractTests(unittest.TestCase):
    def test_redirects_cannot_leave_public_source_allowlist(self):
        handler = PublicRedirects()
        request = Request(SOURCES['models-dev'])
        for target in ('https://127.0.0.1/private', 'http://models.dev/api.json',
                       'https://models.dev.attacker.test/api.json',
                       'https://user:password@models.dev/api.json'):
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError, 'allowlist'):
                    handler.redirect_request(request, None, 302, 'Found', {}, target)
        target = 'https://models.dev/catalog.json?type=all'
        redirected = handler.redirect_request(request, None, 302, 'Found', {}, target)
        self.assertEqual(redirected.full_url, target)

    def test_invalid_or_empty_contracts_fail_closed(self):
        data, _ = fixtures()
        bad = []
        wrong_version = copy.deepcopy(data['openclaw'])
        wrong_version['schemaVersion'] = 3
        bad.append(('openclaw', wrong_version))
        duplicate = copy.deepcopy(data['openclaw'])
        duplicate['models'].append(copy.deepcopy(duplicate['models'][0]))
        bad.append(('openclaw', duplicate))
        wrong_id = copy.deepcopy(data['models-dev'])
        wrong_id['lab']['models']['model-one']['id'] = 'different'
        bad.append(('models-dev', wrong_id))
        bad.extend([
            ('models-dev', {}),
            ('models-dev', {'lab': {'id': 'lab', 'name': 'Lab', 'models': {}}}),
            ('models-dev-canonical', {'providers': data['models-dev']}),
        ])
        for name, value in bad:
            with self.subTest(name=name, value=value):
                with self.assertRaises(ValueError):
                    check_source(name, value)

    def test_failed_http_does_not_replace_valid_cached_bytes(self):
        data, _ = fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            path = cache / 'openclaw.json'
            original = encoded(data['openclaw'])
            path.write_bytes(original)
            with patch('registry.sources.urlopen', side_effect=OSError('network unavailable')), \
                 patch('registry.sources.time.sleep'):
                with self.assertRaises(RuntimeError):
                    fetch('openclaw', cache)
            self.assertEqual(path.read_bytes(), original)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.before_cwd = Path.cwd()
        self.root = Path(self.tmp.name)
        os.chdir(self.root)
        self.data, self.reviewed = fixtures()
        Path('data').mkdir()
        Path('data/reviewed-evidence.json').write_bytes(encoded(self.reviewed))
        Path('licenses').mkdir()
        Path('licenses/Fixture-MIT.txt').write_text('Test license fixture\n')
        self.output = Path('public/v1')
        self.cache = Path('.cache')
        self.cache.mkdir()
        self.write_cache()

    def tearDown(self):
        os.chdir(self.before_cwd)
        self.tmp.cleanup()

    def write_cache(self):
        for name, value in self.data.items():
            (self.cache / (name + '.json')).write_bytes(encoded(value))

    def files(self):
        return {str(p.relative_to(self.output)): p.read_bytes()
                for p in self.output.rglob('*') if p.is_file()}

    def test_build_validates_partitions_snapshots_and_is_idempotent(self):
        self.assertTrue(build(output=self.output, cache=self.cache))
        first = self.files()
        catalog = validate(self.output)
        for source in catalog['sources']:
            path = self.output / 'source-snapshots' / (source['id'].replace(':', '-') + '.json.gz')
            self.assertEqual(hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest(), source['sha256'])
        self.assertFalse(build(output=self.output, cache=self.cache))
        self.assertEqual(self.files(), first)
        self.data['openclaw']['generatedAt'] += 1
        self.data['openclaw']['sourceCommit'] = 'b' * 40
        self.write_cache()
        self.assertFalse(build(output=self.output, cache=self.cache))
        self.assertEqual(self.files(), first)

    def test_invalid_source_preserves_entire_previous_publication(self):
        build(output=self.output, cache=self.cache)
        first = self.files()
        self.data['openclaw']['schemaVersion'] = 999
        self.write_cache()
        with self.assertRaises(ValueError):
            build(output=self.output, cache=self.cache)
        self.assertEqual(self.files(), first)

    def test_credential_bearing_endpoint_is_rejected_before_publish(self):
        build(output=self.output, cache=self.cache)
        first = self.files()
        self.data['models-dev']['lab']['api'] = 'https://fixture-user:fixture-password@example.test/v1'
        self.write_cache()
        with self.assertRaisesRegex(ValueError, 'Unsafe source endpoint'):
            build(output=self.output, cache=self.cache)
        self.assertEqual(self.files(), first)

    def test_corrupt_source_snapshot_fails_integrity_check(self):
        build(output=self.output, cache=self.cache)
        path = next((self.output / 'source-snapshots').glob('*.json.gz'))
        path.write_bytes(gzip.compress(b'{}\n', mtime=0))
        with self.assertRaisesRegex(ValueError, 'Source snapshot hash mismatch'):
            validate(self.output)


if __name__ == '__main__':
    unittest.main()

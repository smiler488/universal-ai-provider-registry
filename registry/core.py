import copy
import gzip
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

from jsonschema import Draft202012Validator, FormatChecker
from .schema import SCHEMA, CAPS
from .sources import SOURCES, encoded, digest, load_sources, check_source

VERSION = '1.0.0'
OUT = Path('public/v1')


def source_record(name, data, previous):
    # Publisher timestamps are not model changes. Reuse the original reproducible
    # snapshot when its useful payload is unchanged.
    semantic = {k: v for k, v in data.items() if k not in ('generatedAt', 'sourceCommit', 'upstreamPricing')} if name == 'openclaw' else data
    sid = name + ':' + digest(semantic)[:20]
    prior = next((s for s in previous.get('sources', []) if s['id'] == sid), None)
    if prior:
        return prior
    return {'id': sid, 'name': name, 'url': SOURCES.get(name, 'https://github.com/smiler488/universal-ai-provider-registry/blob/main/data/reviewed-evidence.json'), 'sha256': hashlib.sha256(encoded(data)).hexdigest(), 'license': 'MIT' if name in SOURCES else 'selected factual observations; official documentation not relicensed', 'verification': 'registry_reported' if name in SOURCES else 'officially_documented'}


def states(row, source):
    caps = {k: 'unknown' for k in CAPS}
    for original, key in [('reasoning','reasoning'),('tool_call','tool_calling'),('structured_output','structured_output')]:
        if isinstance(row.get(original), bool):
            caps[key] = 'supported' if row[original] else 'unsupported'
    modes = row.get('modalities') or {}
    ins = row.get('input') if source == 'openclaw' else modes.get('input')
    outs = modes.get('output')
    for mode, key in [('image','vision'),('audio','audio_input'),('video','video_input')]:
        if ins and mode in ins:
            caps[key] = 'supported'
    for mode, key in [('image','image_generation'),('audio','audio_output'),('video','video_generation')]:
        if outs and mode in outs:
            caps[key] = 'supported'
    if row.get('type') == 'embedding':
        caps['embedding'] = 'supported'
    return caps, ins, outs


def observation(row, source, sid, record):
    caps, ins, outs = states(row, source)
    limits = row.get('limit') or {}
    price = row.get('pricing') if source == 'openclaw' else row.get('cost')
    if price is not None:
        price = {'raw': price, 'currency': price.get('currency') if source == 'openclaw' else None, 'unit': price.get('unit') if source == 'openclaw' else None, 'note': 'Source claim only; zero does not imply free access. Null currency/unit are unverified.'}
    return {'source_id': sid, 'source_record_id': record, 'verification': 'registry_reported', 'presence': 'listed', 'name': row.get('name', row['id']), 'capabilities': caps, 'input_modalities': ins, 'output_modalities': outs, 'context_window': row.get('contextWindow') if source == 'openclaw' else limits.get('context'), 'max_output_tokens': row.get('maxTokens') if source == 'openclaw' else limits.get('output'), 'pricing': price, 'lifecycle': row.get('status', 'unknown')}


def summarize(dep):
    observations = [o for o in dep['observations'] if o['presence'] == 'listed']
    dep['availability'] = 'listed' if observations else 'removed_from_source'
    dep['verification'] = 'officially_documented' if any(o['verification'] == 'officially_documented' for o in observations) else ('registry_reported' if observations else 'unverified')
    conflicts = []
    for cap in CAPS:
        vals = {o['capabilities'][cap] for o in observations} - {'unknown'}
        dep['capabilities'][cap] = next(iter(vals)) if len(vals) == 1 else 'unknown'
        if len(vals) > 1:
            conflicts.append('capabilities.' + cap)
    for field in ('input_modalities', 'output_modalities', 'context_window', 'max_output_tokens', 'lifecycle'):
        vals = {json.dumps(o[field], sort_keys=True) for o in observations if o[field] not in (None, 'unknown', 'documented')}
        if len(vals) > 1:
            conflicts.append(field)
    life = {o['lifecycle'] for o in observations} - {'unknown', 'documented'}
    dep['lifecycle'] = next(iter(life)) if len(life) == 1 else ('conflicting' if life else 'unknown')
    prices = [o['pricing'] for o in observations if o['pricing'] is not None and o['pricing']['raw'].get('status') not in ('unknown','unavailable')]
    numeric = [v for p in prices for k,v in p['raw'].items() if k in ('input','output','cache_read','cacheRead') and isinstance(v,(int,float))]
    # Only compare like-for-like prices with explicit equal currency and units.
    comparable = {}
    for p in prices:
        if p['currency'] and p['unit']:
            comparable.setdefault((p['currency'], p['unit']), set()).add(json.dumps(p['raw'], sort_keys=True))
    pricing_conflict = any(len(v) > 1 for v in comparable.values())
    dep['pricing_status'] = 'unknown' if not prices else 'zero_requires_verification' if numeric and all(v == 0 for v in numeric) else 'conflicting' if pricing_conflict else 'reported'
    if pricing_conflict:
        conflicts.append('pricing')
    dep['conflicts'] = sorted(conflicts)


def reviewed_sources(reviewed):
    sources = {}
    for source in reviewed.get('sources', []):
        key = source['source_id']
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+', key) or key in sources or key in SOURCES:
            raise ValueError('Invalid or duplicate reviewed source ID')
        sources[key] = source
    return sources


def normalize(data, reviewed, previous=None):
    previous = previous or {}
    supplements = reviewed_sources(reviewed)
    source_map = {name: source_record(name, value, previous) for name,value in {**data, **supplements}.items()}
    models, developers, providers, deployments = {}, {}, {}, {}
    canonical = data['models-dev-canonical']['models']
    md = data['models-dev']
    identity_map = {}
    for source in supplements.values():
        identities = {r['id']:r.get('developer_id', source['developer_id']) for r in source['models']}
        identities.update({mid:source['developer_id'] for notice in source.get('lifecycle_notices',[]) for mid in notice['model_ids']})
        for pid in source.get('identity_provider_ids', [source['provider_id']]):
            for mid, developer in identities.items():
                key = (pid, mid)
                canonical_id = developer + '/' + mid
                if key in identity_map and identity_map[key] != canonical_id:
                    raise ValueError('Conflicting reviewed identity mapping')
                identity_map[key] = canonical_id

    def identity(pid, mid, row=None):
        candidate = (row or {}).get('canonical_model_id')
        if candidate in canonical:
            return candidate, 'registry_reported'
        if (pid, mid) in identity_map:
            return identity_map[(pid,mid)], 'officially_documented'
        peer = md.get(pid, {}).get('models', {}).get(mid, {})
        if peer.get('canonical_model_id') in canonical:
            return peer['canonical_model_id'], 'registry_reported'
        if pid + '/' + mid in canonical:
            return pid + '/' + mid, 'registry_reported'
        return 'unresolved/' + pid + '/' + quote(mid, safe=''), 'unknown'

    def add_model(key, name, status, sid):
        developer = key.split('/')[0] if status != 'unknown' else None
        m = models.setdefault(key, {'id':key, 'name':name, 'developer_id':developer, 'identity_status':status, 'source_ids':[]})
        if sid not in m['source_ids']:
            m['source_ids'].append(sid)
        if status == 'officially_documented':
            m['identity_status'] = status
        if developer:
            d = developers.setdefault(developer, {'id':developer, 'name':developer, 'verification':status, 'source_ids':[]})
            if sid not in d['source_ids']:
                d['source_ids'].append(sid)
        return m

    def provider(pid, name, sid, base=None, protocol=None):
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+', pid) or pid in ('.','..'):
            raise ValueError('Unsafe provider ID')
        p = providers.setdefault(pid, {'id':pid, 'name':name, 'region':None, 'plan':None, 'endpoints':[], 'source_ids':[]})
        if sid not in p['source_ids']:
            p['source_ids'].append(sid)
        if base and not base.startswith(('https://','http://')):
            base = None  # e.g. an environment-variable template; raw claim stays in source snapshot.
        if base or protocol:
            # Keep untrusted source claims as data; no request is ever made to them.
            ep = {'base_url':base, 'protocol':protocol, 'source_id':sid, 'verification':'registry_reported'}
            if ep not in p['endpoints']:
                p['endpoints'].append(ep)
        return p

    def deploy(pid, row, obs):
        mid = row['id']
        key, status = identity(pid, mid, row)
        add_model(key, row.get('name', mid), status, obs['source_id'])
        did = pid + ':' + quote(mid, safe='')
        dep = deployments.setdefault(did, {'id':did, 'provider_id':pid, 'provider_model_id':mid, 'model_id':key, 'verification':'registry_reported', 'availability':'listed', 'lifecycle':'unknown', 'capabilities':{k:'unknown' for k in CAPS}, 'pricing_status':'unknown', 'conflicts':[], 'observations':[]})
        if dep['model_id'] != key:
            raise ValueError('Conflicting explicit canonical identities: ' + did)
        dep['observations'].append(obs)

    sid = source_map['models-dev-canonical']['id']
    for key, row in sorted(canonical.items()):
        if '/' not in key or key != row['id']:
            raise ValueError('Canonical model contract changed')
        add_model(key, row.get('name', key), 'registry_reported', sid)
    for pid,p in sorted(md.items()):
        sid = source_map['models-dev']['id']
        provider(pid,p['name'],sid,p.get('api'))
        for mid,row in sorted(p['models'].items()):
            deploy(pid,row,observation(row,'models-dev',sid,pid + '/' + mid))
    oc = data['openclaw']
    sid = source_map['openclaw']['id']
    for row in sorted(oc['models'], key=lambda r:(r['provider'],r['id'])):
        pid = row['provider']
        provider(pid,pid,sid,protocol=oc.get('providers',{}).get(pid,{}).get('api'))
        deploy(pid,row,observation(row,'openclaw',sid,pid + '/' + row['id']))
    for source_name, supplement in sorted(supplements.items()):
        sid = source_map[source_name]['id']
        pid = supplement['provider_id']
        p = provider(pid,supplement.get('provider_name',pid),sid,supplement.get('base_url'))
        for endpoint in p['endpoints']:
            if endpoint['source_id'] == sid:
                endpoint['verification'] = 'officially_documented'
        for row in supplement['models']:
            caps = row.get('capabilities', {})
            translated = {'id':row['id'], 'name':row.get('name',row['id']), 'modalities':{'input':caps.get('input_modalities'), 'output':caps.get('output_modalities')}, 'status':row.get('lifecycle',{}).get('status','unknown')}
            obs = observation(translated,'official',sid,row['id'])
            obs['verification'] = 'officially_documented'
            deploy(pid,translated,obs)
        for notice in supplement.get('lifecycle_notices', []):
            for mid in notice['model_ids']:
                row = {'id':mid, 'status':notice['status']}
                obs = observation(row,'official',sid,'lifecycle/' + mid)
                obs['verification'] = 'officially_documented'
                deploy(pid,row,obs)

    # Successful omission is not retirement. Keep absent claims and entities;
    # transport failure aborts before this function, retaining last valid release.
    prev_sources = {s['id']:s for s in previous.get('sources',[])}
    for old in previous.get('deployments',[]):
        did = old['id']
        if did not in deployments:
            deployments[did] = copy.deepcopy(old)
            for obs in deployments[did]['observations']:
                obs['presence'] = 'removed_from_source'
        else:
            current_names = {o['source_id'].split(':')[0] for o in deployments[did]['observations']}
            for obs in old['observations']:
                if obs['source_id'].split(':')[0] not in current_names:
                    archived = copy.deepcopy(obs)
                    archived['presence'] = 'removed_from_source'
                    if archived not in deployments[did]['observations']:
                        deployments[did]['observations'].append(archived)
    for field, target in [('models',models),('developers',developers),('providers',providers)]:
        for old in previous.get(field,[]):
            target.setdefault(old['id'],old)
    for dep in deployments.values():
        dep['observations'].sort(key=lambda o:(o['source_id'],o['source_record_id']))
        summarize(dep)
    for target in (models,developers,providers):
        for entity in target.values():
            entity['source_ids'].sort()
    for p in providers.values():
        p['endpoints'].sort(key=lambda e:(e['source_id'],e['base_url'] or '',e['protocol'] or ''))
    sources = {s['id']:s for s in source_map.values()}
    refs = {o['source_id'] for d in deployments.values() for o in d['observations']}
    refs |= {sid for group in (models,developers,providers) for e in group.values() for sid in e['source_ids']}
    for sid in refs:
        if sid not in sources:
            sources[sid] = prev_sources[sid]
    return {'models':sorted(models.values(), key=lambda r:r['id']), 'developers':sorted(developers.values(),key=lambda r:r['id']), 'providers':sorted(providers.values(),key=lambda r:r['id']), 'deployments':sorted(deployments.values(),key=lambda r:r['id']), 'sources':sorted(sources.values(),key=lambda r:r['id'])}


def diff_report(previous, current):
    def facts(value):
        if isinstance(value, list):
            return [facts(v) for v in value]
        if isinstance(value, dict):
            return {k: ([x.split(':')[0] for x in v] if k == 'source_ids' else v.split(':')[0] if k == 'source_id' else facts(v)) for k,v in value.items()}
        return value
    report = {}
    for group in ('models','providers','deployments'):
        before = {r['id']:r for r in previous.get(group,[])}
        after = {r['id']:r for r in current[group]}
        report[group] = {'added':sorted(after.keys()-before.keys()), 'updated':sorted(k for k in after.keys() & before.keys() if facts(after[k])!=facts(before[k])), 'provenance_only':sorted(k for k in after.keys() & before.keys() if after[k]!=before[k] and facts(after[k])==facts(before[k])), 'removed':sorted(before.keys()-after.keys())}
    report['removed_from_source'] = [d['id'] for d in current['deployments'] if d['availability']=='removed_from_source']
    report['conflicting_metadata'] = [d['id'] for d in current['deployments'] if d['conflicts']]
    return report


def validate(directory=OUT):
    validator = Draft202012Validator(SCHEMA,format_checker=FormatChecker())
    Draft202012Validator.check_schema(SCHEMA)
    catalog = json.loads((directory/'catalog.json').read_text())
    content = {k:catalog[k] for k in ('models','developers','providers','deployments','sources')}
    if catalog['data_version'] != 'sha256-'+digest({'schema':SCHEMA,'content':content}):
        raise ValueError('Catalog content does not match its data_version')
    model_ids = {r['id'] for r in catalog['models']}
    developer_ids = {r['id'] for r in catalog['developers']}
    provider_ids = {r['id'] for r in catalog['providers']}
    source_ids = {r['id'] for r in catalog['sources']}
    for group in ('models','developers','providers','deployments','sources'):
        if len({r['id'] for r in catalog[group]}) != len(catalog[group]):
            raise ValueError('Duplicate ' + group)
    for m in catalog['models']:
        if m['developer_id'] is not None and m['developer_id'] not in developer_ids:
            raise ValueError('Dangling developer')
    for group in ('models','developers','providers'):
        for r in catalog[group]:
            if not set(r['source_ids']) <= source_ids:
                raise ValueError('Dangling source')
    for p in catalog['providers']:
        for e in p['endpoints']:
            if e['source_id'] not in source_ids:
                raise ValueError('Dangling endpoint source')
            if e['base_url']:
                u=urlparse(e['base_url'])
                if u.scheme not in ('https','http') or u.username or u.password or u.query or u.fragment:
                    raise ValueError('Unsafe source endpoint')
    for d in catalog['deployments']:
        if d['model_id'] not in model_ids or d['provider_id'] not in provider_ids:
            raise ValueError('Dangling deployment relation')
        if not d['observations'] or any(o['source_id'] not in source_ids for o in d['observations']):
            raise ValueError('Missing observation provenance')
    count = 0
    for path in sorted(directory.rglob('*.json')):
        value=json.loads(path.read_text())
        if path.name == 'schema.json':
            Draft202012Validator.check_schema(value)
            if value != SCHEMA:
                raise ValueError('Published schema mismatch')
            continue
        validator.validate(value)
        if value['sources'] != catalog['sources']:
            raise ValueError('Envelope sources differ from catalog')
        if any(value[k] != catalog[k] for k in ('schema_version','data_version','generated_at')):
            raise ValueError('Mixed data versions')
        count += 1
    for group in ('models','developers','providers','deployments'):
        if json.loads((directory/(group+'.json')).read_text())[group] != catalog[group]:
            raise ValueError('Split file mismatch')
    for p in catalog['providers']:
        sub=json.loads((directory/'provider-models'/(p['id']+'.json')).read_text())
        expected=[d for d in catalog['deployments'] if d['provider_id']==p['id']]
        mids={d['model_id'] for d in expected}
        if sub['provider'] != p or sub['deployments'] != expected or sub['models'] != [m for m in catalog['models'] if m['id'] in mids]:
            raise ValueError('Provider partition mismatch')
    for source in catalog['sources']:
        path = directory/'source-snapshots'/(source['id'].replace(':','-')+'.json.gz')
        if not path.exists() or hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() != source['sha256']:
            raise ValueError('Source snapshot hash mismatch: '+source['id'])
    sums=directory/'checksums.sha256'
    if not sums.exists():
        raise ValueError('Missing checksum manifest')
    if sums.exists():
        entries={}
        for line in sums.read_text().splitlines():
            checksum, name=line.split('  ',1)
            target=directory/name
            if not target.is_relative_to(directory) or '..' in Path(name).parts:
                raise ValueError('Unsafe checksum path')
            if hashlib.sha256(target.read_bytes()).hexdigest()!=checksum:
                raise ValueError('Checksum mismatch: '+name)
            entries[name]=checksum
        expected={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p.name!='checksums.sha256'}
        if set(entries)!=expected:
            raise ValueError('Checksum inventory mismatch')
    print(f'Validated {count} JSON envelopes; {len(model_ids)} models, {len(provider_ids)} providers, {len(catalog["deployments"])} deployments')
    return catalog


def build(online=False, output=OUT, cache=Path('.cache')):
    previous=json.loads((output/'catalog.json').read_text()) if (output/'catalog.json').exists() else {}
    # Git carries compressed source snapshots; restores deterministic offline build.
    cache.mkdir(parents=True,exist_ok=True)
    for name in SOURCES:
        if not (cache/(name+'.json')).exists():
            candidates=[s for s in previous.get('sources',[]) if s['name']==name]
            # Source referenced by current listed observations, not a tombstone.
            active={o['source_id'] for d in previous.get('deployments',[]) for o in d['observations'] if o['presence']=='listed'}
            candidates.sort(key=lambda s:s['id'] in active,reverse=True)
            if candidates:
                p=output/'source-snapshots'/(candidates[0]['id'].replace(':','-')+'.json.gz')
                if p.exists():
                    (cache/(name+'.json')).write_bytes(gzip.decompress(p.read_bytes()))
    data=load_sources(online,cache)
    reviewed=json.loads(Path('data/reviewed-evidence.json').read_text())
    supplements=reviewed_sources(reviewed)
    content=normalize(data,reviewed,previous)
    # Fail closed on unexpected mass disappearance even when the HTTP response is 200.
    if previous:
        old={d['id'] for d in previous['deployments'] if d['availability']=='listed'}
        new={d['id'] for d in content['deployments'] if d['availability']=='listed'}
        if len(old-new) > max(20,len(old)*0.2):
            raise ValueError('More than 20% of deployments disappeared; manual adapter review required')
        for name in SOURCES:
            def memberships(catalog):
                return {d['id'] for d in catalog.get('deployments',[]) if any(o['presence']=='listed' and o['source_id'].split(':')[0]==name for o in d['observations'])}
            before, after = memberships(previous), memberships(content)
            if len(before-after)>max(20,len(before)*0.2):
                raise ValueError('Mass source disappearance requires manual review: '+name)
    version='sha256-'+digest({'schema':SCHEMA, 'content':content})
    if previous.get('data_version')==version:
        validate(output)
        print('No semantic change; no files rewritten')
        return False
    meta={'schema_version':VERSION,'data_version':version,'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'sources':content['sources']}
    catalog={**meta,'kind':'catalog',**content}
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.catalog-',dir=output.parent))
    def write(name,value):
        path=temp/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(encoded(value))
    try:
        write('catalog.json',catalog)
        for group in ('models','developers','providers','deployments'):
            write(group+'.json',{**meta,'kind':group,group:content[group]})
        for p in content['providers']:
            deps=[d for d in content['deployments'] if d['provider_id']==p['id']]
            mids={d['model_id'] for d in deps}
            write('provider-models/'+p['id']+'.json',{**meta,'kind':'provider','provider':p,'models':[m for m in content['models'] if m['id'] in mids],'deployments':deps})
        write('diff.json',{**meta,'kind':'diff','report':diff_report(previous,content)})
        write('schema.json',SCHEMA)
        for source in content['sources']:
            rel=Path('source-snapshots')/(source['id'].replace(':','-')+'.json.gz')
            dest=temp/rel
            dest.parent.mkdir(exist_ok=True)
            if (output/rel).exists():
                shutil.copyfile(output/rel,dest)
            else:
                value=supplements[source['name']] if source['name'] in supplements else data[source['name']]
                dest.write_bytes(gzip.compress(encoded(value),mtime=0))
        # License notices travel with downloadable data, not only the source repo.
        license_dir=temp/'licenses'
        license_dir.mkdir()
        for p in Path('licenses').glob('*.txt'):
            shutil.copyfile(p,license_dir/p.name)
        for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):
            if Path(name).exists():
                shutil.copyfile(name,temp/name)
        sums=[]
        for p in sorted(temp.rglob('*')):
            if p.is_file():
                sums.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(temp)))
        (temp/'checksums.sha256').write_text('\n'.join(sums)+'\n')
        validate(temp)
        # Do not replace the public tree until every file and relation has passed.
        if output.exists():
            shutil.rmtree(output)
        temp.replace(output)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    (output.parent/'.nojekyll').touch()
    (output.parent/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Universal AI Provider Registry</title><h1>Universal AI Provider Registry</h1><p>Public model metadata with source evidence and explicit unknowns.</p><ul>'+''.join(f'<li><a href="v1/{name}">{name}</a></li>' for name in ['catalog.json','models.json','providers.json','deployments.json','schema.json','checksums.sha256'])+'</ul><p><a href="https://github.com/smiler488/universal-ai-provider-registry">Documentation and source</a></p>')
    print('Published local data version '+version)
    return True

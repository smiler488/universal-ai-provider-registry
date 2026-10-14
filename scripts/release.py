#!/usr/bin/env python3
"""Create a deterministic, content-addressed public-data release bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import zipfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path('public'))
    parser.add_argument('--output', type=Path, default=Path('release'))
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not (directory / 'v1/catalog.json').is_file():
        parser.error('Validated public/v1/catalog.json is required')
    files = sorted(p for p in directory.rglob('*') if p.is_file())
    if any(p.is_symlink() for p in files):
        parser.error('Release files must not contain symlinks')
    manifest = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(directory).as_posix()}\n' for p in files)
    tree_digest = hashlib.sha256(manifest.encode()).hexdigest()
    tag = f'data-{tree_digest[:16]}'
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f'{tag}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(directory).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes(), compresslevel=9)
        info = zipfile.ZipInfo('FILES.sha256', date_time=(1980, 1, 1, 0, 0, 0))
        info.external_attr = 0o100644 << 16
        bundle.writestr(info, manifest.encode())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (args.output / 'SHA256SUMS').write_text(f'{checksum}  {archive.name}\n', encoding='utf-8')
    (args.output / 'notes.md').write_text(
        f'Public registry data snapshot `{tag}`.\n\n'
        f'- Contains {len(files)} published files, including normalized JSON, schema, provenance, and cached public source snapshots.\n'
        '- `SHA256SUMS` verifies the ZIP; `FILES.sha256` inside it verifies each extracted file.\n'
        '- The release workflow never overwrites an existing release or moves its tag.\n'
        '- Sources retain their original licenses and attribution. Unknown price, endpoint, or capability values remain unknown.\n\n'
        f'Public file manifest SHA-256: `{tree_digest}`.\n', encoding='utf-8')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as handle:
            handle.write(f'tag={tag}\narchive={archive.as_posix()}\n')
    print(json.dumps({'tag': tag, 'archive': str(archive), 'sha256': checksum, 'files': len(files)}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Append RC4 corresponding modifications to the unchanged RC1 upstream archives."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'dist/TopDF-1.0.0-rc.1-sources.zip'
OUT = ROOT / 'dist/TopDF-1.0.0-rc.4-sources.zip'
assert BASE.is_file(), 'Download the published RC1 corresponding sources first'
shutil.copyfile(BASE, OUT)
files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
records = []
with zipfile.ZipFile(OUT, 'a', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for relative in sorted(set(filter(None, files))):
        path = ROOT / relative
        assert path.is_file(), relative
        data = path.read_bytes()
        name = 'topdf-rc4/' + relative
        archive.writestr(name, data)
        records.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    for path in sorted((ROOT / 'Engines/FallbackFonts').glob('*')):
        if path.is_file():
            name = 'topdf-rc4/Engines/FallbackFonts/' + path.name
            data = path.read_bytes()
            archive.writestr(name, data)
            records.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    archive.writestr('TOPDF-RC4-MANIFEST.json', json.dumps(records, indent=2))
    archive.writestr('README-RC4.txt',
        'TopDF 1.0.0-rc.4 corresponding sources.\n'
        'The original SOURCE-MANIFEST.json and sources/ archives are unchanged RC1 engine/dependency inputs.\n'
        'topdf-rc4/ contains current application/build/pruning code and licenses.\n'
        'Reproduce the modified HWP engine with scripts/build-hwp-gothic.py (Rust 1.93.0).\n'
        'legal/NanumGothic-manifest.json fixes the additional unmodified OFL font inputs.\n'
        'Android has a separate RC4 application/JNI/dependency source ZIP; upstream LibreOffice Android source is linked in release notes.\n'
        'Private signing keys, downloads, build outputs and unrelated local files are excluded.\n')
with zipfile.ZipFile(OUT) as archive:
    assert len(archive.namelist()) == len(set(archive.namelist()))
    assert archive.testzip() is None
print(json.dumps({'file': OUT.name, 'bytes': OUT.stat().st_size, 'rc4_files': len(records)}))

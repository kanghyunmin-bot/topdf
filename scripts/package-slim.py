#!/usr/bin/env python3
"""Package a verified local slim app without overwriting published RC artifacts."""
import hashlib
import json
import os
import shutil
import pathlib
import subprocess
import sys

version = os.environ.get('TOPDF_VERSION', '1.0.0-rc.4')
root = pathlib.Path(__file__).resolve().parent.parent
app = pathlib.Path(sys.argv[1]).resolve()
arch = sys.argv[2]
if arch not in ('arm64', 'intel'):
    raise SystemExit('architecture must be arm64 or intel')
subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
report = json.loads((app / 'Contents/Resources/engine-size-report.json').read_text())
assert report['after_bytes'] < report['before_bytes']
payload_bytes=int(subprocess.check_output(['du','-sk',str(app)],text=True).split()[0])*1024
assert payload_bytes <= 500_000_000, 'Installed payload exceeds 500 MB'
stage = root / ('build/slim-dmg-' + version + '-' + arch)
stage.mkdir(exist_ok=True)
if (stage / app.name).exists():
    shutil.rmtree(stage / app.name)
subprocess.run(['ditto', str(app), str(stage / app.name)], check=True)
if not (stage / 'Applications').exists():
    (stage / 'Applications').symlink_to('/Applications')
(stage / 'READ-ME-FIRST.txt').write_text(
    f'TopDF {version} local slim preview / macOS 13+.\n'
    'No Developer ID signature or Apple notarization. macOS may block opening.\n'
    'The LibreOffice headless engine is trimmed and resealed. Fonts, document filters, '
    'dictionaries and hyphenation are preserved.\n'
    'Original corresponding desktop engine sources remain available with v1.0.0-rc.1: '
    'https://github.com/kanghyunmin-bot/topdf/releases/tag/v1.0.0-rc.1\n'
    'Pruning source: scripts/slim-libreoffice.py in the TopDF source checkout.\n'
    'Intel conversion under Rosetta is separate from independent physical Intel Mac validation.\n'
)
out = root / f'dist/TopDF-{version}-macos-{arch}-MAX500MB-UNSIGNED.dmg'
subprocess.run(['hdiutil', 'create', '-quiet', '-ov', '-volname', 'TopDF RC4',
                '-srcfolder', str(stage), '-format', 'UDZO', '-imagekey', 'zlib-level=9', str(out)], check=True)
subprocess.run(['hdiutil', 'verify', str(out)], check=True, stdout=subprocess.DEVNULL)
with out.open('rb') as stream:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
(out.parent / (out.stem + '-SHA256.txt')).write_text(digest.hexdigest() + '  ' + out.name + '\n')
print(json.dumps({'file': str(out), 'bytes': out.stat().st_size, 'installed_allocated_bytes': payload_bytes, 'engine': report}, indent=2))

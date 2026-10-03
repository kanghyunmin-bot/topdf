#!/usr/bin/env python3
"""Fetch pinned OFL fallback fonts and verify existing downloads."""
import hashlib,json,pathlib,urllib.request
root=pathlib.Path(__file__).resolve().parent.parent
dest=root/'Engines/FallbackFonts';dest.mkdir(parents=True,exist_ok=True)
for entry in json.loads((root/'legal/NanumGothic-manifest.json').read_text())['files']:
 path=dest/entry['file']
 data=path.read_bytes() if path.exists() else urllib.request.urlopen(entry['url'],timeout=60).read()
 if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
  raise SystemExit('Font checksum mismatch: '+entry['file'])
 if not path.exists():path.write_bytes(data)
print('Verified NanumGothic Regular and Bold (OFL-1.1)')

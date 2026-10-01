#!/usr/bin/env python3
import pathlib,json,tarfile,html
r=pathlib.Path(__file__).resolve().parent.parent
for row in json.loads((r/'legal/android-hwp-dependencies.json').read_text()):
 if not row['notices']:
  name,ver=row['name'],row['version'];dest=r/'legal/android-hwp-dependencies'/name/ver;dest.mkdir(parents=True,exist_ok=True)
  with tarfile.open(r/'downloads/android-hwp-crates'/f'{name}-{ver}.crate') as t:
   for m in t.getmembers():
    if m.isfile() and m.name.endswith(('Cargo.toml','README.md','src/lib.rs')):(dest/pathlib.Path(m.name).name).write_bytes(t.extractfile(m).read())
  (dest/'LICENSE-APACHE-2.0.txt').write_bytes((r/'legal/hwp-LICENSE-APACHE.txt').read_bytes())
  (dest/'LICENSE-CHOICE.txt').write_text('This dual-licensed crate is distributed under its Apache-2.0 option. Original crate source and metadata retained. Upstream archive SHA-256 is in android-hwp-dependencies.json. No upstream NOTICE or license file was present in this crate archive.\n')
body='''<meta charset="utf-8"><title>TopDF Android notices</title><h1>Third-party notices</h1><p>TopDF own code: MIT. org/libreoffice/kit Java files: MPL-2.0. LibreOfficeKit.java was modified to accept Context instead of Activity for an isolated engine service. Native libraries and assets are preserved from F-Droid LibreOffice 26.2.6.3 APKs. Original corresponding source archive SHA-256: 0e102144a7cce24e7291e744bef87a573dfb629d595e6a40f0d9fc8a4accb82b. Modified Java sources: https://github.com/kanghyunmin-bot/topdf/tree/main/platforms/android/src/org/libreoffice/kit</p><p>PDFBox-Android 2.0.27.0: Apache-2.0. Bouncy Castle 1.86: MIT. HWP JNI wrapper: MIT; hwp-cli 1.3.1 and Rust dependencies retain their original licenses. Exact original source archives accompany the Android release.</p>'''
for p in sorted((r/'legal').rglob('*')):
 if p.is_file() and p.suffix in ['.txt','.md']:
  body+='<h2>'+html.escape(str(p.relative_to(r/'legal')))+'</h2><pre>'+html.escape(p.read_text(errors='replace'))+'</pre>'
(r/'legal/android/THIRD_PARTY.html').write_text(body)

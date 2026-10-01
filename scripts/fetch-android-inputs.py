#!/usr/bin/env python3
import hashlib,json,pathlib,urllib.request,tarfile
r=pathlib.Path(__file__).resolve().parent.parent;downloads=r/'downloads';downloads.mkdir(exist_ok=True)
rows=json.loads((r/'legal/android-artifacts.json').read_text())+json.loads((r/'legal/android-bouncycastle.json').read_text())
for row in rows:
 name=row['file']
 if name.endswith('_src.tar.gz'):continue # Large engine source is distributed separately, not needed to link prebuilt JNI.
 if name.startswith('org.documentfoundation.'):url='https://f-droid.org/repo/'+name
 elif name.startswith('pdfbox-android-'):url='https://repo.maven.apache.org/maven2/com/tom-roush/pdfbox-android/2.0.27.0/'+name
 elif name=='hwp-cli-v1.3.1-source.tar.gz':url='https://github.com/STAIxBWLB/hwp-cli/archive/refs/tags/v1.3.1.tar.gz'
 else:url=row['url']
 destination=downloads/name
 if not destination.exists():
  with urllib.request.urlopen(url,timeout=60) as source,destination.open('wb') as output:
   while True:
    b=source.read(1048576)
    if not b:break
    output.write(b)
 assert hashlib.sha256(destination.read_bytes()).hexdigest()==row['sha256'],name
 print('Verified',name)
source=downloads/'hwp-cli-v1.3.1-source.tar.gz';upstream=r/'build/upstream';upstream.mkdir(parents=True,exist_ok=True)
if not (upstream/'hwp-cli-1.3.1/Cargo.toml').exists():
 with tarfile.open(source) as archive:archive.extractall(upstream,filter='data')

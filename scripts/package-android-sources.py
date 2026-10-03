#!/usr/bin/env python3
import pathlib,hashlib,json,zipfile,subprocess
R=pathlib.Path(__file__).resolve().parent.parent
files=[]
for p in (R/'downloads/android-hwp-crates').glob('*.crate'):files.append((p,'hwp/crates/'+p.name))
files.append((R/'downloads/hwp-cli-v1.3.1-source.tar.gz','hwp/hwp-cli-v1.3.1-source.tar.gz'))
for name in ['pdfbox-android-2.0.27.0-sources.jar','pdfbox-android-2.0.27.0.pom']:
 files.append((R/'downloads'/name,'maven/'+name))
for p in (R/'downloads').glob('bc*-1.86-sources.jar'):files.append((p,'maven/'+p.name))
for p in (R/'platforms/android').rglob('*'):
 if p.is_file() and 'target' not in p.parts:files.append((p,'topdf/'+str(p.relative_to(R))))
for p in (R/'legal').rglob('*'):
 if p.is_file():files.append((p,'licenses/'+str(p.relative_to(R/'legal'))))
for name in subprocess.check_output(['git','ls-files'],cwd=R,text=True).splitlines():
 if name.startswith(('scripts/','Assets/')):files.append((R/name,'topdf/'+name))
for p in (R/'Engines/FallbackFonts').glob('*'):files.append((p,'topdf/Engines/FallbackFonts/'+p.name))
manifest=[{'path':n,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,n in files]
out=R/'dist/TopDF-1.0.0-rc.4-android-sources.zip'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as z:
 for p,n in files:z.write(p,n)
 z.write(R/'LICENSE','topdf/LICENSE')
 z.writestr('SOURCE-MANIFEST.json',json.dumps(manifest,indent=2))
 z.writestr('README.txt','TopDF Android corresponding JNI, modified MPL Java and dependency sources. LibreOffice 26.2.6.3 full original Android source is provided separately as org.documentfoundation.libreoffice_131_src.tar.gz (SHA256 0e102144a7cce24e7291e744bef87a573dfb629d595e6a40f0d9fc8a4accb82b). Original APK source URLs: https://f-droid.org/repo/org.documentfoundation.libreoffice_131_src.tar.gz and https://f-droid.org/repo/org.documentfoundation.libreoffice_129_src.tar.gz . Both ABI engines use the same LibreOffice source release and the original source archive contains the F-Droid build definitions. Desktop engine corresponding source bundle remains available with v1.0.0-rc.1. Keep those sources and license notices available when redistributing. TopDF own code MIT does not replace any third-party license.\n')
print(out,out.stat().st_size)

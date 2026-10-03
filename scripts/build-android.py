#!/usr/bin/env python3
"""Build a standalone offline APK using Android SDK tools; no Gradle/network at runtime."""
import hashlib,json,os,pathlib,shutil,subprocess,zipfile,secrets
ROOT=pathlib.Path(__file__).resolve().parent.parent
SDK=pathlib.Path(os.environ.get('ANDROID_SDK_ROOT',str(pathlib.Path.home()/'Library/Android/sdk')))
JAVA=pathlib.Path(os.environ.get('JAVA_HOME','/Library/Java/JavaVirtualMachines/amazon-corretto-11.jdk/Contents/Home'))
TOOLS=SDK/'build-tools/35.0.0';ANDROID=SDK/'platforms/android-35/android.jar'
BUILD=ROOT/'build/android';BUILD.mkdir(parents=True,exist_ok=True)
ASSETS=BUILD/'assets';ASSETS.mkdir(exist_ok=True)
# Preserve original native libraries, resources, MPL notices and corresponding source provenance.
for version,abi in [(131,'arm64-v8a'),(129,'x86_64')]:
 archive=ROOT/f'downloads/org.documentfoundation.libreoffice_{version}.apk'
 expected={131:'751ac3836890b79a56801bf6d9a2788cda3761ab5131a4f0b6abfbad822bb475',129:'cfaf9eea5fd695c449e92eb10cc0b1617ec51d068345068cea9b7e1c67968df5'}
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected[version], 'LibreOffice APK checksum mismatch'
 with zipfile.ZipFile(archive) as z:
  for n in z.namelist():
   if n.startswith(('assets/','lib/'+abi+'/')) and not n.endswith('/') and '/dexopt/' not in n:
    p=BUILD/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
for abi,target in [('arm64-v8a','aarch64-linux-android'),('x86_64','x86_64-linux-android')]:
 d=BUILD/'lib'/abi;d.mkdir(parents=True,exist_ok=True)
 shutil.copy2(ROOT/f'platforms/android/native/target/{target}/release/libtopdf_hwp.so',d/'libtopdf_hwp.so')
with zipfile.ZipFile(ROOT/'downloads/pdfbox-android-2.0.27.0.aar') as z:
 (BUILD/'pdfbox.jar').write_bytes(z.read('classes.jar'))
 for n in z.namelist():
  if n.startswith('assets/') and not n.endswith('/'):
   p=BUILD/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
subprocess.run(['python3',str(ROOT/'scripts/prepare-fonts.py')],check=True)
shutil.copytree(ROOT/'Engines/FallbackFonts',ASSETS/'fallback-fonts',dirs_exist_ok=True)
licenses=ASSETS/'Licenses'
shutil.copytree(ROOT/'legal',licenses,dirs_exist_ok=True)
shutil.copy2(ROOT/'LICENSE',licenses/'TopDF-MIT.txt')
for src in (ROOT/'platforms/android').glob('*.txt'):shutil.copy2(src,licenses/src.name)
res=BUILD/'res/drawable';res.mkdir(parents=True,exist_ok=True)
subprocess.run(['sips','-z','192','192',str(ROOT/'Assets/AppIcon.png'),'--out',str(res/'app_icon.png')],check=True,stdout=subprocess.DEVNULL)
gen=BUILD/'gen';gen.mkdir(exist_ok=True)
subprocess.run([str(TOOLS/'aapt2'),'compile','--dir',str(BUILD/'res'),'-o',str(BUILD/'resources.zip')],check=True)
subprocess.run([str(TOOLS/'aapt2'),'link','-I',str(ANDROID),'--manifest',str(ROOT/'platforms/android/AndroidManifest.xml'),'--java',str(gen),'-A',str(ASSETS),'-R',str(BUILD/'resources.zip'),'-o',str(BUILD/'unsigned.apk')],check=True)
classes=BUILD/'classes';classes.mkdir(exist_ok=True)
for row in json.loads((ROOT/'legal/android-bouncycastle.json').read_text()):
 assert hashlib.sha256((ROOT/'downloads'/row['file']).read_bytes()).hexdigest()==row['sha256'], row['file']
for row in json.loads((ROOT/'legal/android-artifacts.json').read_text()):
 if row['file'].endswith('.aar'):
  assert hashlib.sha256((ROOT/'downloads'/row['file']).read_bytes()).hexdigest()==row['sha256'], row['file']
jars=[BUILD/'pdfbox.jar']+[ROOT/'downloads'/r['file'] for r in json.loads((ROOT/'legal/android-bouncycastle.json').read_text()) if not r['file'].endswith('-sources.jar')]
classpath=os.pathsep.join(map(str,[ANDROID,*jars]))
sources=[str(p) for p in (ROOT/'platforms/android/src').rglob('*.java')]+[str(p) for p in gen.rglob('*.java')]
subprocess.run([str(JAVA/'bin/javac'),'-source','8','-target','8','-encoding','UTF-8','-classpath',classpath,'-d',str(classes),*sources],check=True)
subprocess.run([str(JAVA/'bin/jar'),'cf',str(BUILD/'classes.jar'),'-C',str(classes),'.'],check=True)
dex=BUILD/'dex';dex.mkdir(exist_ok=True)
env=os.environ.copy();env['JAVA_HOME']=str(JAVA)
subprocess.run([str(TOOLS/'d8'),'--min-api','26','--lib',str(ANDROID),'--output',str(dex),str(BUILD/'classes.jar'),*map(str,jars)],env=env,check=True)
with zipfile.ZipFile(BUILD/'unsigned.apk','a',compression=zipfile.ZIP_DEFLATED) as z:
 for p in (BUILD/'lib').rglob('*.so'):z.write(p,str(p.relative_to(BUILD)))
 for p in dex.glob('*.dex'):z.write(p,p.name)
subprocess.run([str(TOOLS/'zipalign'),'-f','-P','16','4',str(BUILD/'unsigned.apk'),str(BUILD/'aligned.apk')],check=True)
# Persistent preview key is private and excluded from Git. Production signing can override both paths.
keys=ROOT/'build/private-keys';keys.mkdir(mode=0o700,exist_ok=True)
key=pathlib.Path(os.environ.get('TOPDF_ANDROID_KEYSTORE',str(keys/'topdf-preview.jks')))
password=pathlib.Path(os.environ.get('TOPDF_ANDROID_PASSWORD_FILE',str(keys/'topdf-preview.password')))
if not key.exists():
 if os.environ.get('TOPDF_ANDROID_KEYSTORE'):raise SystemExit('Requested keystore does not exist')
 password.write_text(secrets.token_urlsafe(32)+'\n');password.chmod(0o600)
 subprocess.run([str(JAVA/'bin/keytool'),'-genkeypair','-alias','topdf','-keyalg','RSA','-keysize','2048','-validity','10000','-dname','CN=TopDF Preview, O=kanghyunmin-bot, C=KR','-keystore',str(key),'-storepass:file',str(password),'-keypass:file',str(password)],check=True)
 key.chmod(0o600)
out=ROOT/'dist/TopDF-1.0.0-rc.4-android-offline-preview.apk';out.parent.mkdir(exist_ok=True)
subprocess.run([str(TOOLS/'apksigner'),'sign','--ks',str(key),'--ks-key-alias','topdf','--ks-pass','file:'+str(password),'--out',str(out),str(BUILD/'aligned.apk')],env=env,check=True)
subprocess.run([str(TOOLS/'apksigner'),'verify','--verbose',str(out)],env=env,check=True)
# APK plus the selected ABI libraries and first-run engine assets must fit under 500 MB.
with zipfile.ZipFile(out) as apk:
 for abi in ['arm64-v8a','x86_64']:
  payload=out.stat().st_size+sum(i.file_size for i in apk.infolist() if i.filename.startswith(('lib/'+abi+'/','assets/unpack/','assets/fallback-fonts/')))
  if payload>500_000_000:raise SystemExit('Android installation payload exceeds 500 MB: '+str(payload))
print('Built:',out)

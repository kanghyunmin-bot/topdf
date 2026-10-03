#!/usr/bin/env python3
import hashlib,json,os,pathlib,plistlib,shutil,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
VERSION=os.environ.get('TOPDF_VERSION','1.0.0-rc.4')
ARCH=os.environ.get('TOPDF_ARCH','arm64')
if ARCH not in ['arm64','x86_64']:raise SystemExit('TOPDF_ARCH must be arm64 or x86_64')
engine_root=ROOT/'Engines' if ARCH=='arm64' else ROOT/'Engines/intel'
app=ROOT/os.environ.get('TOPDF_OUTPUT_DIR', 'build/release' if ARCH=='arm64' else 'build/release-intel')/'PDF로 변환.app'
if app.exists(): shutil.rmtree(app)
mac=app/'Contents/MacOS';resources=app/'Contents/Resources'
mac.mkdir(parents=True);resources.mkdir(parents=True)
subprocess.run(['swiftc','-O','-target',ARCH+'-apple-macos13',str(ROOT/'Sources/main.swift'),'-o',str(mac/'TopDF'),'-framework','AppKit','-framework','PDFKit'],check=True)
for name in ['pages','keynote','numbers']:
 # Clean build machines may not have Apple's optional office applications/dictionaries.
 result=subprocess.run(['osacompile','-o',str(resources/f'{name}.scpt'),str(ROOT/f'scripts/{name}.applescript')],capture_output=True)
 if result.returncode:
  shutil.copy2(ROOT/f'scripts/{name}.applescript',resources/f'{name}.applescript')
engines=app/'Contents/Helpers';engines.mkdir()
subprocess.run(['ditto',str(engine_root/'LibreOffice.app'),str(engines/'LibreOffice.app')],check=True)
# Trim the copied engine; upstream downloads remain untouched.
trim=json.loads(subprocess.check_output([sys.executable,str(ROOT/'scripts/slim-libreoffice.py'),str(engines/'LibreOffice.app')],text=True))
(resources/'engine-size-report.json').write_text(json.dumps(trim,indent=2))
hwp_source=ROOT/('build/hwp-gothic-src/target/aarch64-apple-darwin/release/hwp' if ARCH=='arm64' else 'build/hwp-gothic-src/target/x86_64-apple-darwin/release/hwp')
if not hwp_source.is_file(): raise SystemExit('Build the Gothic-aware engine with python3 scripts/build-hwp-gothic.py first.')
shutil.copy2(hwp_source,engines/'hwp')
subprocess.run([sys.executable,str(ROOT/'scripts/prepare-fonts.py')],check=True)
for name in ['NanumGothic-Regular.ttf','NanumGothic-Bold.ttf']:
 source=ROOT/'Engines/FallbackFonts'/name
 target=engines/'LibreOffice.app/Contents/Resources/fonts/truetype'/name
 shutil.copy2(source,target)
subprocess.run(['codesign','--force','--sign',os.environ.get('TOPDF_SIGN_IDENTITY') or '-',str(engines/'LibreOffice.app')],check=True)
hwp_compaction=json.loads(subprocess.check_output([sys.executable,str(ROOT/'scripts/compact-native.py'),str(engines/'hwp')],text=True))
(resources/'hwp-size-report.json').write_text(json.dumps(hwp_compaction,indent=2))
shutil.copytree(ROOT/'legal',resources/'Licenses')
shutil.copy2(ROOT/'Assets/AppIcon.icns',resources/'AppIcon.icns')
shutil.copy2(ROOT/'LICENSE',resources/'TopDF-LICENSE.txt')
for name in ['사용 안내.html','개인정보 안내.html']:
 if (ROOT/'docs'/name).exists(): shutil.copy2(ROOT/'docs'/name,resources/name)
subprocess.run([sys.executable,str(ROOT/'scripts/install-quick-action.py'),str(resources/'PDF화.workflow')],check=True)
info={'CFBundleIdentifier':'local.topdf.finder','CFBundleName':'PDF로 변환','CFBundleDisplayName':'PDF로 변환',
'CFBundleExecutable':'TopDF','CFBundleIconFile':'AppIcon','CFBundlePackageType':'APPL','CFBundleVersion':'6','CFBundleShortVersionString':VERSION.split('-')[0],
'LSMinimumSystemVersion':'13.0','NSHighResolutionCapable':True,
'NSAppleEventsUsageDescription':'Pages, Keynote, Numbers 형식은 설치된 Apple 문서 앱에서 임시 복사본을 PDF로 내보냅니다.',
'CFBundleDocumentTypes':[{'CFBundleTypeName':'변환 문서','CFBundleTypeRole':'Viewer','LSHandlerRank':'None','LSItemContentTypes':['public.data','com.apple.package']}]}
with (app/'Contents/Info.plist').open('wb') as f:plistlib.dump(info,f)
identity=os.environ.get('TOPDF_SIGN_IDENTITY')
if identity:
 subprocess.run(['codesign','--force','--options','runtime','--timestamp','--sign',identity,str(engines/'hwp')],check=True)
 subprocess.run(['codesign','--force','--options','runtime','--timestamp','--entitlements',str(ROOT/'scripts/entitlements.plist'),'--sign',identity,str(app)],check=True)
else:
 subprocess.run(['codesign','--force','--sign','-',str(engines/'hwp')],check=True)
 subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
logical_bytes=sum(p.stat().st_size for p in app.rglob('*') if p.is_file() and not p.is_symlink())
allocated_bytes=int(subprocess.check_output(['du','-sk',str(app)],text=True).split()[0])*1024
limit=500_000_000
if logical_bytes > limit or allocated_bytes > limit: raise SystemExit(f'App exceeds 500 MB: logical={logical_bytes}, allocated={allocated_bytes}')
print('Built:',app, 'logical bytes:',logical_bytes, 'allocated bytes:',allocated_bytes)

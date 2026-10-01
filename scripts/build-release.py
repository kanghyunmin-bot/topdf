#!/usr/bin/env python3
import hashlib,json,os,pathlib,plistlib,shutil,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
VERSION='1.0.0-rc.1'
app=ROOT/'build/release/PDF로 변환.app'
if app.exists(): shutil.rmtree(app)
mac=app/'Contents/MacOS';resources=app/'Contents/Resources'
mac.mkdir(parents=True);resources.mkdir(parents=True)
subprocess.run(['swiftc','-O','-target','arm64-apple-macos13',str(ROOT/'Sources/main.swift'),'-o',str(mac/'TopDF'),'-framework','AppKit','-framework','PDFKit'],check=True)
for name in ['pages','keynote','numbers']:
 subprocess.run(['osacompile','-o',str(resources/f'{name}.scpt'),str(ROOT/f'scripts/{name}.applescript')],check=True)
engines=app/'Contents/Helpers';engines.mkdir()
subprocess.run(['ditto',str(ROOT/'Engines/LibreOffice.app'),str(engines/'LibreOffice.app')],check=True)
shutil.copy2(ROOT/'Engines/hwp/hwp',engines/'hwp')
shutil.copytree(ROOT/'legal',resources/'Licenses')
shutil.copy2(ROOT/'Assets/AppIcon.icns',resources/'AppIcon.icns')
for name in ['사용 안내.html','개인정보 안내.html']:
 if (ROOT/'docs'/name).exists(): shutil.copy2(ROOT/'docs'/name,resources/name)
subprocess.run([sys.executable,str(ROOT/'scripts/install-quick-action.py'),str(resources/'PDF화.workflow')],check=True)
info={'CFBundleIdentifier':'local.topdf.finder','CFBundleName':'PDF로 변환','CFBundleDisplayName':'PDF로 변환',
'CFBundleExecutable':'TopDF','CFBundleIconFile':'AppIcon','CFBundlePackageType':'APPL','CFBundleVersion':'3','CFBundleShortVersionString':'1.0.0',
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
print('Built:',app)

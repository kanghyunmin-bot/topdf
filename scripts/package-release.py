import hashlib,json,os,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
VERSION=os.environ.get('TOPDF_VERSION','1.0.0-rc.4')
APP=ROOT/'build/release/PDF로 변환.app'
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
checks=json.loads((ROOT/'tests/release-output/test-report.json').read_text())
assert len(checks)>=26 and all(r['passed'] for r in checks),'Conversion verification failed'
assert json.loads((ROOT/'tests/release-output/network-report.json').read_text())['passed']
assert len(list((ROOT/'downloads/hwp-crates').glob('*.crate')))==276
assert len(json.loads((ROOT/'legal/libreoffice-external-sources.json').read_text()))==149
assert (APP/'Contents/Resources/AppIcon.icns').is_file()
subprocess.run(['codesign','--verify','--deep','--strict',str(APP)],check=True)
OUT=ROOT/'dist';OUT.mkdir(exist_ok=True)
STAGE=ROOT/'build/dmg-stage'
if STAGE.exists():shutil.rmtree(STAGE)
STAGE.mkdir()
subprocess.run(['ditto',str(APP),str(STAGE/APP.name)],check=True)
(STAGE/'Applications').symlink_to('/Applications')
(STAGE/'먼저 읽어주세요.txt').write_text('PDF로 변환 '+VERSION+'\n\n이 파일은 서명·공증 전 공개 사전 릴리스 RC입니다. 정식 배포 버전이 아닙니다.\nApple Silicon / macOS 13 이상\n앱을 응용 프로그램 폴더로 복사한 뒤 한 번 실행하면 Finder의 PDF화 메뉴를 설치합니다.\nHWP/HWPX는 실험적 지원이며 수식·차트 등 제한이 있습니다.\n사용 안내, 개인정보 안내, 제3자 라이선스는 앱의 도움말에서 볼 수 있습니다.\n대응 소스 번들을 앱과 함께 제공해야 합니다.\n',encoding='utf-8')
dmg=OUT/f'TopDF-{VERSION}-arm64-UNSIGNED.dmg'
if dmg.exists():dmg.unlink()
subprocess.run(['hdiutil','create','-quiet','-volname','PDF로 변환 RC','-srcfolder',str(STAGE),'-format','UDZO',str(dmg)],check=True)
subprocess.run(['hdiutil','verify',str(dmg)],check=True,stdout=subprocess.DEVNULL)
# Explicit allowlist prevents unrelated workspace files from entering either package.
sourcezip=OUT/f'TopDF-{VERSION}-sources.zip'
files=[]
for path in sorted((ROOT/'downloads').glob('libreoffice-*.tar.xz')):files.append((path,'sources/libreoffice/'+path.name))
files.append((ROOT/'downloads/hwp-cli-v1.3.1-source.tar.gz','sources/hwp/hwp-cli-v1.3.1-source.tar.gz'))
for path in sorted((ROOT/'downloads/hwp-crates').glob('*.crate')):files.append((path,'sources/hwp/crates/'+path.name))
for path in sorted((ROOT/'downloads/libreoffice-external').iterdir()):
 if path.is_file() and not path.name.endswith('.part'):files.append((path,'sources/libreoffice/external/'+path.name))
for path in sorted((ROOT/'legal').rglob('*')):
 if path.is_file():files.append((path,'licenses/'+str(path.relative_to(ROOT/'legal'))))
manifest=[{'path':name,'bytes':path.stat().st_size,'sha256':digest(path)} for path,name in files]
with zipfile.ZipFile(sourcezip,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as z:
 for path,name in files:z.write(path,name)
 z.writestr('SOURCE-MANIFEST.json',json.dumps(manifest,indent=2))
 z.writestr('README.txt','Corresponding engine sources and dependency archives for TopDF '+VERSION+'.\nLibreOffice 26.2.6.3 native code with a trimmed headless application bundle. Removed files are documented by scripts/slim-libreoffice.py and engine-size-report.json; upstream source archives are unchanged. Source tarballs include core, dictionaries, help and translations, plus all 149 download.lst external archives.\nHWP CLI: v1.3.1 plus all 276 Cargo.lock registry archives (including inactive platform/build dependencies).\nAll archive hashes were checked against upstream metadata. This bundle preserves each upstream archive and its license files.\nDistribute this source bundle with the app. Keep public source links available.\nTopDF application source is MIT-licensed at https://github.com/kanghyunmin-bot/topdf/tree/v1.0.0-rc.1. Its MIT license does not replace third-party engine licenses.\n')
with zipfile.ZipFile(sourcezip) as z:assert z.testzip() is None
artifacts=[]
for path in [dmg,sourcezip]:artifacts.append({'file':path.name,'sha256':digest(path),'bytes':path.stat().st_size})
(OUT/'SHA256SUMS.txt').write_text(''.join(r['sha256']+'  '+r['file']+'\n' for r in artifacts))
(OUT/'release-manifest.json').write_text(json.dumps({'version':VERSION,'status':'unsigned_release_candidate','architecture':'arm64','minimum_macos':'13.0','artifacts':artifacts,'publish_blockers':['Developer ID signing and Apple notarization','independent clean Mac installation test'],'engines':{'libreoffice':'26.2.6.3 headless trimmed, unchanged executable code and public symbols','hwp':'1.3.1 upstream binary, signature only changed'}},ensure_ascii=False,indent=2))
print('Packaged:',*[p.name for p in [dmg,sourcezip]],sep='\n')

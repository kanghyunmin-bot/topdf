#!/usr/bin/env python3
import pathlib,shutil,subprocess,hashlib,json,os
VERSION=os.environ.get('TOPDF_VERSION','1.0.0-rc.4')
R=pathlib.Path(__file__).resolve().parent.parent;app=R/'build/release/PDF로 변환.app';stage=R/'build/preview-dmg';stage.mkdir(exist_ok=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
subprocess.run(['ditto',str(app),str(stage/app.name)],check=True)
if not (stage/'Applications').exists():(stage/'Applications').symlink_to('/Applications')
shutil.copy2(R/'LICENSE',stage/'LICENSE.txt')
(stage/'READ-ME-FIRST.txt').write_text('TopDF '+VERSION+' Apple Silicon/macOS 13+ preview. No Developer ID signature or Apple notarization. Native offline converters bundled; headless resources trimmed and resealed; original corresponding desktop engine sources remain available with v1.0.0-rc.1. Copy app to Applications and run once to register Finder PDF conversion. Third-party licenses and Help included. Independent clean Mac/minimum OS and actual printer tests remain required before production distribution.\n')
out=R/f'dist/TopDF-{VERSION}-macos-arm64-UNSIGNED.dmg'
subprocess.run(['hdiutil','create','-quiet','-ov','-volname','TopDF Offline Preview','-srcfolder',str(stage),'-format','UDZO',str(out)],check=True)
subprocess.run(['hdiutil','verify',str(out)],check=True)
(R/'dist/arm64-SHA256.txt').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n')
print(out)

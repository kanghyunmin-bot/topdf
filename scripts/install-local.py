import datetime,pathlib,shutil,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
app=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'build/release/PDF로 변환.app'
if not app.exists():raise SystemExit('Build with scripts/build-release.py first.')
target=pathlib.Path.home()/'Applications/PDF로 변환.app'
# Never replace a running app: the caller must close it first.
processes=subprocess.run(['ps','-axo','command='],capture_output=True,text=True,check=True).stdout.splitlines()
if any(line.strip()==str(target/'Contents/MacOS/TopDF') or line.strip().endswith('/Applications/PDF로 변환.app/Contents/MacOS/TopDF') for line in processes):raise SystemExit('Close the installed PDF converter before updating.')
target.parent.mkdir(exist_ok=True)
if target.exists():
 backup=ROOT/'build/backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
 shutil.move(str(target),str(backup/target.name));print('Backup:',backup)
subprocess.run(['ditto',str(app),str(target)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(target)],check=True)
subprocess.run(['/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister','-f',str(target)],check=True)
print('Installed:',target)

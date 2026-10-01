import concurrent.futures,hashlib,json,pathlib,tarfile,tomllib,urllib.request,time
root=pathlib.Path(__file__).resolve().parent.parent
packages=tomllib.loads((root/'platforms/android/native/Cargo.lock').read_text())['package']
registry=[p for p in packages if p.get('source','').startswith('registry+')]
out=root/'legal/android-hwp-dependencies';out.mkdir(parents=True,exist_ok=True)
archives=root/'downloads/android-hwp-crates';archives.mkdir(exist_ok=True)
def fetch(p):
 name,ver=p['name'],p['version'];url=f'https://static.crates.io/crates/{name}/{name}-{ver}.crate';dest=archives/f'{name}-{ver}.crate'
 if not dest.exists():
  for attempt in range(3):
   try: dest.write_bytes(urllib.request.urlopen(url,timeout=40).read());break
   except Exception:
    if attempt==2:raise
    time.sleep(1)
 assert hashlib.sha256(dest.read_bytes()).hexdigest()==p['checksum'],str(dest)
 notices=[]
 with tarfile.open(dest) as t:
  cfg=tomllib.loads(t.extractfile(f'{name}-{ver}/Cargo.toml').read().decode())['package']
  for m in t.getmembers():
   leaf=pathlib.PurePosixPath(m.name).name.lower()
   if m.isfile() and (leaf.startswith(('license','copying','notice','copyright'))):
    blob=t.extractfile(m).read()
    if len(blob)<500000:
     target=out/name/ver;target.mkdir(parents=True,exist_ok=True)
     (target/(hashlib.sha256(m.name.encode()).hexdigest()[:8]+'-'+pathlib.PurePosixPath(m.name).name)).write_bytes(blob)
     notices.append(m.name)
 return {'name':name,'version':ver,'license':cfg.get('license'),'license_file':cfg.get('license-file'),'source':url,'sha256':p['checksum'],'notices':notices}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(fetch,registry))
(root/'legal/android-hwp-dependencies.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('Verified registry packages:',len(results))
print('License expressions:',sorted(set(str(r['license']) for r in results)))
print('Without license files:',[r['name'] for r in results if not r['notices']])
print('Non-registry external:',[p for p in packages if p.get('source') and not p['source'].startswith('registry+')])

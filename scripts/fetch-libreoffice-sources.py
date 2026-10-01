import concurrent.futures,hashlib,json,pathlib,re,time,urllib.request
root=pathlib.Path(__file__).resolve().parent.parent
text=(root/'build/upstream/libreoffice-26.2.6.3/download.lst').read_text()
values=dict(re.findall(r'^([A-Z0-9_]+)\s*:?=\s*(\S+)',text,re.M))
items=[]
for key,name in values.items():
 if key.endswith('_TARBALL'):
  prefix=key[:-8];sha=values.get(prefix+'_SHA256SUM')
  for _ in range(4): name=re.sub(r'\$\(([A-Z0-9_]+)\)',lambda m:values[m[1]],name)
  if sha:items.append({'name':name,'sha256':sha,'url':'https://dev-www.libreoffice.org/src/'+name})
out=root/'downloads/libreoffice-external';out.mkdir(exist_ok=True)
def fetch(item):
 dest=out/item['name'];tmp=dest.with_name(dest.name+'.part')
 if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==item['sha256']: return item
 for attempt in range(3):
  try:
   with urllib.request.urlopen(item['url'],timeout=60) as response,tmp.open('wb') as f:
    while data:=response.read(1024*1024):f.write(data)
   if hashlib.sha256(tmp.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Hash mismatch: '+item['name'])
   tmp.replace(dest);return item
  except Exception as e:
   if attempt==2:return dict(item,error=str(e))
   time.sleep(1)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(fetch,items))
(root/'legal/libreoffice-external-sources.json').write_text(json.dumps(results,indent=2))
errors=[r for r in results if 'error' in r]
print('Verified external source archives:',len(results)-len(errors),'/',len(results));print('Errors:',errors)
if errors:raise SystemExit(1)

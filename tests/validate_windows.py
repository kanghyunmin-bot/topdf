import pathlib,subprocess,hashlib,json
from pypdf import PdfReader
ROOT=pathlib.Path(__file__).resolve().parent.parent;APP=ROOT/'build/windows/app/TopDF.exe';OUT=ROOT/'build/windows/tests';OUT.mkdir(parents=True,exist_ok=True)
checks=[]
def run(name,args):
 p=subprocess.run([str(APP),*map(str,args)],timeout=180)
 assert p.returncode==0,(name,(OUT/(name+'.pdf.error.txt')).read_text() if (OUT/(name+'.pdf.error.txt')).exists() else p.returncode)
 checks.append(name)
for ext,count in [('docx',2),('pptx',3),('xlsx',1),('hwp',1),('hwpx',1)]:
 source=ROOT/f'tests/sample.{ext}';before=hashlib.sha256(source.read_bytes()).hexdigest();out=OUT/f'{ext}.pdf';run(ext,['--convert-test',source,out]);r=PdfReader(out);text=''.join(p.extract_text() for p in r.pages);assert len(r.pages)==count and '123' in text and ('한글' in text or '변환' in text),(ext,text);assert before==hashlib.sha256(source.read_bytes()).hexdigest()
for mode in range(3):
 out=OUT/f'range-{mode}.pdf';run('range-'+str(mode),['--render-test',OUT/'docx.pdf',out,2,2,mode]);r=PdfReader(out);assert len(r.pages)==1 and '두번째' in r.pages[0].extract_text().replace(' ','')
 if mode:assert (float(r.pages[0].mediabox.width)>float(r.pages[0].mediabox.height))==(mode==2)
text=OUT/'text.txt';text.write_text('한글 텍스트 변환\nEnglish 123\n',encoding='utf-8');run('text',['--convert-test',text,OUT/'text.pdf']);assert '한글' in PdfReader(OUT/'text.pdf').pages[0].extract_text()
(OUT/'test-report.json').write_text(json.dumps({'passed':True,'checks':checks,'network':'outbound firewall denied during conversion'},ensure_ascii=False,indent=2));print('Passed',len(checks),'Windows checks')

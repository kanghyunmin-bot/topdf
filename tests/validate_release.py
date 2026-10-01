import hashlib,json,pathlib,subprocess,sys,tempfile
from PIL import Image,ImageDraw
from pypdf import PdfReader,PdfWriter
from pypdf.generic import RectangleObject
from reportlab.pdfgen import canvas
ROOT=pathlib.Path(__file__).resolve().parent.parent
APP=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'build/release/PDF로 변환.app'
EXE=APP/'Contents/MacOS/TopDF'
OUT=ROOT/'tests/release-output';OUT.mkdir(exist_ok=True)
FIX=ROOT/'tests/release-fixtures';FIX.mkdir(exist_ok=True)
results=[]
def run(name,args,expected=True):
 p=subprocess.run([str(EXE),*map(str,args)],capture_output=True,text=True,timeout=60)
 passed=(p.returncode==0)==expected
 results.append({'test':name,'passed':passed,'exit':p.returncode,'output':(p.stdout+p.stderr).strip()[:800]})
 if not passed: raise AssertionError(results[-1])
 return p
# Documents exercise Korean, English, actual app engines and multiple pages.
for ext,pages in [('docx',2),('pptx',3),('xlsx',1),('hwp',1),('hwpx',1)]:
 src=ROOT/f'tests/sample.{ext}';before=hashlib.sha256(src.read_bytes()).hexdigest()
 dst=OUT/f'{ext}.pdf';run('convert-'+ext,['--convert-test',src,dst])
 r=PdfReader(dst);assert len(r.pages)==pages
 text=''.join(p.extract_text() for p in r.pages)
 assert '123' in text and ('한글' in text or '변환' in text),(ext,text)
 assert hashlib.sha256(src.read_bytes()).hexdigest()==before
 results.append({'test':'original-preserved-'+ext,'passed':True})
# Argument quoting: punctuation, spaces, Korean, newline and shell metacharacters are literal.
name=FIX/'한글 "quote" $() `literal`\n문서.docx';name.write_bytes((ROOT/'tests/sample.docx').read_bytes())
run('literal-path',['--convert-test',name,OUT/'literal.pdf'])
# Image format paths, including multipage TIFF.
a=Image.new('RGB',(640,360),'#EAF0FF');ImageDraw.Draw(a).text((40,40),'IMAGE PAGE 1',fill='black')
b=Image.new('RGB',(360,640),'#FFEEEE');ImageDraw.Draw(b).text((40,40),'IMAGE PAGE 2',fill='black')
a.save(FIX/'image.png');a.save(FIX/'image.tiff',save_all=True,append_images=[b])
for ext,count in [('png',1),('tiff',2)]:
 run('image-'+ext,['--convert-test',FIX/f'image.{ext}',OUT/f'image-{ext}.pdf']);assert len(PdfReader(OUT/f'image-{ext}.pdf').pages)==count
# Offset media box plus rotation catches clipping and double rotation errors.
c=canvas.Canvas(str(FIX/'geometry.pdf'),pagesize=(600,400))
for n in range(1,4):
 c.setFillColorRGB(.96,.97,1);c.rect(0,0,600,400,fill=1,stroke=0)
 for x,y,label in [(20,20,'BOTTOM LEFT'),(410,20,'BOTTOM RIGHT'),(20,360,'TOP LEFT'),(420,360,'TOP RIGHT')]:
  c.setFillColorRGB(0,0,0);c.setFont('Helvetica',14);c.drawString(x,y,label)
 c.drawString(250,200,f'PAGE {n}');c.showPage()
c.save();r=PdfReader(FIX/'geometry.pdf');w=PdfWriter()
for i,p in enumerate(r.pages):
 if i==1:p.rotate(90)
 if i==2:p.mediabox=RectangleObject([-20,-10,620,410])
 w.add_page(p)
w.write(FIX/'geometry-input.pdf')
for mode,label in [(0,'original'),(1,'portrait'),(2,'landscape')]:
 dst=OUT/f'geometry-{label}.pdf'
 run('range-and-'+label,['--render-test',FIX/'geometry-input.pdf',dst,2,3,mode])
 pages=PdfReader(dst).pages;assert len(pages)==2
 assert 'PAGE 2' in pages[0].extract_text() and 'PAGE 3' in pages[1].extract_text()
 if mode:
  for p in pages:assert (float(p.mediabox.width)>float(p.mediabox.height))==(mode==2)
for a,b in [(0,1),(2,1),(1,4),(-1,2)]:run(f'invalid-range-{a}-{b}',['--render-test',FIX/'geometry-input.pdf',OUT/'invalid.pdf',a,b,0],False)
run('invalid-layout',['--render-test',FIX/'geometry-input.pdf',OUT/'invalid.pdf',1,1,99],False)
(FIX/'broken.docx').write_text('not a zip document')
(FIX/'unknown.bin').write_bytes(b'123')
(FIX/'broken.pdf').write_bytes(b'not PDF')
for file in ['broken.docx','unknown.bin','broken.pdf']:run('reject-'+file,['--convert-test',FIX/file,OUT/'rejected.pdf'],False)
w=PdfWriter();w.add_blank_page(300,400);w.encrypt('secret');w.write(FIX/'locked.pdf')
run('reject-locked-pdf',['--convert-test',FIX/'locked.pdf',OUT/'locked.pdf'],False)
(FIX/'한글.txt').write_text('한글 텍스트 변환\nEnglish 123\n',encoding='utf-8')
run('utf8-text',['--convert-test',FIX/'한글.txt',OUT/'text.pdf'])
assert '한글' in PdfReader(OUT/'text.pdf').pages[0].extract_text(), repr(PdfReader(OUT/'text.pdf').pages[0].extract_text())
(OUT/'test-report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('PASS:',len(results),'checks')

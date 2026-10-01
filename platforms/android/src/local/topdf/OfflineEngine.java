package local.topdf;
import android.content.*;
import android.graphics.*;
import android.graphics.pdf.PdfDocument;
import android.content.res.AssetManager;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.libreoffice.kit.*;
import com.tom_roush.pdfbox.pdmodel.PDDocument;
import com.tom_roush.pdfbox.pdmodel.PDPage;
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream;
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle;
import com.tom_roush.pdfbox.pdmodel.graphics.form.PDFormXObject;
import com.tom_roush.pdfbox.multipdf.LayerUtility;
import com.tom_roush.pdfbox.util.Matrix;
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader;

final class OfflineEngine {
 static void copyAsset(AssetManager a,String name,File target)throws IOException {
  String[] list=a.list(name);if(list!=null&&list.length>0){if(!target.exists()&&!target.mkdirs())throw new IOException("엔진 폴더 생성 실패");for(String x:list)copyAsset(a,name+"/"+x,new File(target,x));}
  else {File parent=target.getParentFile();if(!parent.exists())parent.mkdirs();try(InputStream in=a.open(name);OutputStream out=new FileOutputStream(target)){byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}}
 }
 static void prepare(Context context)throws Exception {
  File marker=new File(context.getFilesDir(),"engine-26.2.6.3-ready");
  if(!marker.exists()){copyAsset(context.getAssets(),"unpack",new File(context.getApplicationInfo().dataDir));marker.createNewFile();}
  File preferences=new File(context.getApplicationInfo().dataDir,"user/registrymodifications.xcu");preferences.getParentFile().mkdirs();
  String settings="<?xml version=\"1.0\" encoding=\"UTF-8\"?><oor:items xmlns:oor=\"http://openoffice.org/2001/registry\"><item oor:path=\"/org.openoffice.Office.Common/Security/Scripting\"><prop oor:name=\"MacroSecurityLevel\" oor:op=\"fuse\"><value>3</value></prop></item><item oor:path=\"/org.openoffice.Office.Calc/Content/Update\"><prop oor:name=\"Link\" oor:op=\"fuse\"><value>0</value></prop></item><item oor:path=\"/org.openoffice.Office.Writer/Content/Update\"><prop oor:name=\"Link\" oor:op=\"fuse\"><value>0</value></prop></item></oor:items>";
  try(OutputStream out=new FileOutputStream(preferences)){out.write(settings.getBytes(StandardCharsets.UTF_8));}
  PDFBoxResourceLoader.init(context);
 }
 static void convert(Context c,File input,File output)throws Exception {
  prepare(c);if(input.length()>512L*1024*1024)throw new IOException("512MB 이하의 파일을 선택하세요.");
  String name=input.getName().toLowerCase(Locale.ROOT),ext=name.substring(name.lastIndexOf('.')+1);
  if(Arrays.asList("docx","docm","dotx","pptx","pptm","ppsx","xlsx","xlsm","odt","ods","odp","hwpx","epub").contains(ext)){
   try(java.util.zip.ZipFile zip=new java.util.zip.ZipFile(input)){long total=0;int entries=0;java.util.Enumeration<? extends java.util.zip.ZipEntry> list=zip.entries();while(list.hasMoreElements()){java.util.zip.ZipEntry entry=list.nextElement();long size=entry.getSize();if(size<0||size>1024L*1024*1024||total>1024L*1024*1024-size||++entries>100000)throw new IOException("손상되었거나 압축 해제 크기가 너무 큰 문서입니다.");total+=size;}}
  }
  if(ext.equals("pdf")){try(PDDocument d=PDDocument.load(input)){check(d);if(!d.getCurrentAccessPermission().canPrint())throw new IOException("인쇄가 허용되지 않은 PDF입니다.");}copy(input,output);return;}
  if(ext.equals("tif")||ext.equals("tiff")){
   File directory=new File(input.getParentFile(),"tiff-"+UUID.randomUUID());String error=NativeHwp.decodeTiff(input.getPath(),directory.getPath());if(error!=null)throw new IOException(error);
   PdfDocument pdf=new PdfDocument();try{File[] frames=directory.listFiles();if(frames==null||frames.length==0)throw new IOException("TIFF 페이지가 없습니다.");Arrays.sort(frames);int n=0;for(File frame:frames){BitmapFactory.Options options=new BitmapFactory.Options();options.inJustDecodeBounds=true;BitmapFactory.decodeFile(frame.getPath(),options);options.inSampleSize=Math.max(1,Math.max(options.outWidth,options.outHeight)/4096);options.inJustDecodeBounds=false;Bitmap bitmap=BitmapFactory.decodeFile(frame.getPath(),options);if(bitmap==null)throw new IOException("TIFF 이미지 로드 실패");try{PdfDocument.Page page=pdf.startPage(new PdfDocument.PageInfo.Builder(bitmap.getWidth(),bitmap.getHeight(),++n).create());page.getCanvas().drawBitmap(bitmap,0,0,new Paint(3));pdf.finishPage(page);}finally{bitmap.recycle();frame.delete();}}try(OutputStream out=new FileOutputStream(output)){pdf.writeTo(out);}}finally{pdf.close();MainActivity.remove(directory);}
  } else if(ext.equals("hwp")||ext.equals("hwpx")){
   String error=NativeHwp.render(input.getAbsolutePath(),output.getAbsolutePath(),c.getApplicationInfo().dataDir+"/user/fonts");if(error!=null)throw new IOException(error);
  } else if(Arrays.asList("png","jpg","jpeg","bmp","gif","webp","heic","heif").contains(ext)) {
   BitmapFactory.Options opts=new BitmapFactory.Options();opts.inJustDecodeBounds=true;BitmapFactory.decodeFile(input.getPath(),opts);if(opts.outWidth<=0||opts.outHeight<=0)throw new IOException("이미지를 읽을 수 없습니다.");opts.inSampleSize=Math.max(1,Math.max(opts.outWidth,opts.outHeight)/4096);opts.inJustDecodeBounds=false;
   Bitmap b=BitmapFactory.decodeFile(input.getPath(),opts);if(b==null)throw new IOException("이미지를 읽을 수 없습니다.");
   try {android.media.ExifInterface exif=new android.media.ExifInterface(input.getPath());int orientation=exif.getAttributeInt(android.media.ExifInterface.TAG_ORIENTATION,1);android.graphics.Matrix m=new android.graphics.Matrix();if(orientation==3)m.postRotate(180);if(orientation==6)m.postRotate(90);if(orientation==8)m.postRotate(270);if(orientation!=1){Bitmap rotated=Bitmap.createBitmap(b,0,0,b.getWidth(),b.getHeight(),m,true);if(rotated!=b)b.recycle();b=rotated;}}catch(IOException ignored){}
   PdfDocument d=new PdfDocument();try{int w=b.getWidth(),h=b.getHeight();PdfDocument.Page p=d.startPage(new PdfDocument.PageInfo.Builder(w,h,1).create());p.getCanvas().drawBitmap(b,0,0,new Paint(3));d.finishPage(p);try(OutputStream o=new FileOutputStream(output)){d.writeTo(o);}}finally{d.close();b.recycle();}
  } else {
   List<String> office=Arrays.asList("doc","docx","docm","dot","dotx","ppt","pptx","pptm","pps","ppsx","xls","xlsx","xlsm","odt","ods","odp","rtf","csv","tsv","txt","html","htm","epub");
   if(!office.contains(ext))throw new IOException("이 형식은 내장 엔진에서 지원하지 않습니다.");
   LibreOfficeKit.initializeLibrary();LibreOfficeKit.putenv("SAL_LOK_OPTIONS=compact_fonts");LibreOfficeKit.init(c);
   java.nio.ByteBuffer handle=LibreOfficeKit.getLibreOfficeKitHandle();if(handle==null)throw new IOException("문서 엔진 초기화 실패");
   Office officeEngine=new Office(handle);org.libreoffice.kit.Document doc=officeEngine.documentLoad(android.net.Uri.fromFile(input).toString());
   if(doc==null)throw new IOException("문서를 읽을 수 없습니다: "+officeEngine.getError());
   try {doc.saveAs(android.net.Uri.fromFile(output).toString(),"pdf","");}finally{doc.destroy();}
  }
  if(!output.isFile()||output.length()==0)throw new IOException("PDF가 생성되지 않았습니다.");try(PDDocument d=PDDocument.load(output)){check(d);}
 }
 static void check(PDDocument d)throws IOException {if(d.getNumberOfPages()<1||d.getNumberOfPages()>2000)throw new IOException("1~2000페이지를 지원합니다.");}
 static void export(Context c,File input,File output,int first,int last,int layout)throws Exception {
  PDFBoxResourceLoader.init(c);try(PDDocument source=PDDocument.load(input);PDDocument result=new PDDocument()){
   if(first<1||last<first||last>source.getNumberOfPages()||layout<0||layout>2)throw new IOException("페이지 범위와 용지 설정을 확인하세요.");
   LayerUtility layers=new LayerUtility(result);
   for(int i=first-1;i<last;i++){
    if(Thread.currentThread().isInterrupted())throw new InterruptedIOException("취소했습니다.");
    if(layout==0){result.importPage(source.getPage(i));continue;}
    PDRectangle paper=layout==2?new PDRectangle(842,595):PDRectangle.A4;PDPage page=new PDPage(paper);result.addPage(page);PDFormXObject form=layers.importPageAsForm(source,i);PDRectangle box=form.getBBox();float s=Math.min((paper.getWidth()-36)/box.getWidth(),(paper.getHeight()-36)/box.getHeight());
    try(PDPageContentStream stream=new PDPageContentStream(result,page)){stream.transform(Matrix.getTranslateInstance((paper.getWidth()-box.getWidth()*s)/2,(paper.getHeight()-box.getHeight()*s)/2));stream.transform(Matrix.getScaleInstance(s,s));stream.transform(Matrix.getTranslateInstance(-box.getLowerLeftX(),-box.getLowerLeftY()));stream.drawForm(form);}
   }
   result.save(output);
  }
 }
 static void copy(File a,File b)throws IOException {try(InputStream in=new FileInputStream(a);OutputStream out=new FileOutputStream(b)){byte[] buffer=new byte[65536];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n);}}
}

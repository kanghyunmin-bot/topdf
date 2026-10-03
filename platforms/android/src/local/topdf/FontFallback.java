package local.topdf;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.*;
import java.util.zip.*;

/** Changes only absent, explicitly named fonts in the private conversion copy. */
final class FontFallback {
 static final String FAMILY="NanumGothic";
 static final Pattern TAG=Pattern.compile("<(?:[A-Za-z_][\\w.-]*:)?(?:rFonts|latin|ea|cs|font|name|font-face)\\b[^>]*>");
 static final Pattern ATTRIBUTE=Pattern.compile("(?<![\\w:.-])(w:ascii|w:hAnsi|w:eastAsia|w:cs|typeface|svg:font-family|w:name|val)\\s*=\\s*([\"'])(.*?)\\2");
 static boolean supported(String ext){return Arrays.asList("docx","docm","dotx","pptx","pptm","ppsx","xlsx","xlsm","odt","ods","odp").contains(ext);}
 static boolean selected(String name){return name.endsWith(".xml")&&(name.startsWith("word/")||name.startsWith("ppt/")||name.equals("xl/styles.xml")||name.startsWith("xl/theme/")||name.equals("styles.xml")||name.equals("content.xml"));}
 static String decode(String s){return s.replace("&quot;","\"").replace("&apos;","'").replace("&lt;","<").replace("&gt;",">").replace("&amp;","&");}
 static void fontNames(File file,Set<String> names){
  try(RandomAccessFile f=new RandomAccessFile(file,"r")){
   if(f.length()<12)return;int signature=f.readInt();
   List<Long> faces=new ArrayList<>();
   if(signature==0x74746366){f.readInt();int count=f.readInt();if(count<1||count>256)return;for(int i=0;i<count;i++)faces.add(Integer.toUnsignedLong(f.readInt()));}else faces.add(0L);
   for(long face:faces){if(face+12>f.length())continue;f.seek(face+4);int tables=f.readUnsignedShort();if(tables>1024)continue;
    long table=-1;for(int i=0;i<tables;i++){f.seek(face+12L+i*16);int tag=f.readInt();f.readInt();long offset=Integer.toUnsignedLong(f.readInt());f.readInt();if(tag==0x6e616d65){table=offset;break;}}
    if(table<0||table+6>f.length())continue;f.seek(table+2);int count=f.readUnsignedShort(),start=f.readUnsignedShort();if(count>10000||table+6L+count*12>f.length())continue;
    for(int i=0;i<count;i++){f.seek(table+6L+i*12);int platform=f.readUnsignedShort();f.readUnsignedShort();f.readUnsignedShort();int id=f.readUnsignedShort(),length=f.readUnsignedShort(),offset=f.readUnsignedShort();if((platform!=0&&platform!=3)||!Arrays.asList(1,4,6,16).contains(id)||table+start+offset+length>f.length())continue;byte[] bytes=new byte[length];f.seek(table+start+offset);f.readFully(bytes);names.add(new String(bytes,StandardCharsets.UTF_16BE).toLowerCase(Locale.ROOT));}
   }
  }catch(IOException ignored){}
 }
 static void scan(File dir,Set<String> names){File[] files=dir.listFiles();if(files==null)return;for(File f:files){if(f.isDirectory())scan(f,names);else if(f.getName().toLowerCase(Locale.ROOT).matches(".*\\.(ttf|otf|ttc)"))fontNames(f,names);}}
 static Set<String> available(File privateFonts){Set<String> names=new HashSet<>(Arrays.asList("serif","sans-serif","monospace","system-ui","nanumgothic","나눔고딕"));scan(new File("/system/fonts"),names);scan(new File("/product/fonts"),names);scan(privateFonts,names);return names;}
 static byte[] read(InputStream in)throws IOException {ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1){if(out.size()+n>32*1024*1024)throw new IOException("글꼴 XML 크기가 너무 큽니다.");out.write(b,0,n);}return out.toByteArray();}
 static void apply(File input,String ext,Set<String> available)throws IOException{
  if(!supported(ext))return;
  Set<String> embedded=new HashSet<>();
  File stage=new File(input.getParentFile(),"fonts-"+UUID.randomUUID()+".zip");
  try(ZipFile source=new ZipFile(input)){
   // Embedded font names are preserved even when absent from system fonts.
   Enumeration<? extends ZipEntry> entries=source.entries();
   Pattern embeddedTag=Pattern.compile("<(?:w:font|p:embeddedFont)\\b[^>]*>.*?</(?:w:font|p:embeddedFont)>",Pattern.DOTALL);
   Pattern embeddedName=Pattern.compile("(?:w:name|typeface)=[\"']([^\"']+)[\"']");
   while(entries.hasMoreElements()){ZipEntry e=entries.nextElement();if(!selected(e.getName()))continue;String xml;try(InputStream in=source.getInputStream(e)){xml=new String(read(in),StandardCharsets.UTF_8);}Matcher blocks=embeddedTag.matcher(xml);while(blocks.find()){String block=blocks.group();if(!block.contains("embed"))continue;Matcher name=embeddedName.matcher(block);if(name.find())embedded.add(decode(name.group(1)).toLowerCase(Locale.ROOT));}}
   try(ZipOutputStream target=new ZipOutputStream(new FileOutputStream(stage))){entries=source.entries();while(entries.hasMoreElements()){ZipEntry e=entries.nextElement();ZipEntry copy=new ZipEntry(e.getName());if(e.getTime()>=0)copy.setTime(e.getTime());target.putNextEntry(copy);try(InputStream in=source.getInputStream(e)){
    if(selected(e.getName())){String xml=new String(read(in),StandardCharsets.UTF_8);Matcher tags=TAG.matcher(xml);StringBuffer changed=new StringBuffer();while(tags.find()){String tag=tags.group();Matcher attrs=ATTRIBUTE.matcher(tag);StringBuffer replacement=new StringBuffer();while(attrs.find()){String name=decode(attrs.group(3)).toLowerCase(Locale.ROOT);boolean missing=!name.isEmpty()&&!name.startsWith("+")&&!available.contains(name)&&!embedded.contains(name);String value=missing?attrs.group().replace(attrs.group(3),FAMILY):attrs.group();attrs.appendReplacement(replacement,Matcher.quoteReplacement(value));}attrs.appendTail(replacement);tags.appendReplacement(changed,Matcher.quoteReplacement(replacement.toString()));}tags.appendTail(changed);target.write(changed.toString().getBytes(StandardCharsets.UTF_8));}
    else {byte[] buffer=new byte[65536];int n;while((n=in.read(buffer))!=-1)target.write(buffer,0,n);}
   }target.closeEntry();}}
  }catch(IOException e){stage.delete();throw e;}
  try{java.nio.file.Files.move(stage.toPath(),input.toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING);}finally{stage.delete();}
 }
}

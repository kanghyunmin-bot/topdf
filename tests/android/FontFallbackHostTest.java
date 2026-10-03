package local.topdf;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
public final class FontFallbackHostTest {
 public static void main(String[] args)throws Exception{
  File dir=Files.createTempDirectory("topdf-font-test").toFile();
  Set<String> available=new HashSet<>(Arrays.asList("arial","serif","sans-serif","monospace"));
  File input=new File(dir,"test.docx");
  String document="<w:document><w:rFonts w:ascii=\"Missing Serif\" w:hAnsi=\"Arial\"/><w:rFonts w:ascii=\"Embedded Custom\"/><w:t>Missing Serif</w:t></w:document>";
  try(ZipOutputStream z=new ZipOutputStream(new FileOutputStream(input))){
   z.putNextEntry(new ZipEntry("word/document.xml"));z.write(document.getBytes(StandardCharsets.UTF_8));z.closeEntry();
   z.putNextEntry(new ZipEntry("word/fontTable.xml"));z.write("<w:fonts><w:font w:name=\"Embedded Custom\"><w:embedRegular r:id=\"r1\"/></w:font></w:fonts>".getBytes(StandardCharsets.UTF_8));z.closeEntry();
   z.putNextEntry(new ZipEntry("word/media/raw.bin"));z.write(new byte[]{1,2,3,4});z.closeEntry();
  }
  FontFallback.apply(input,"docx",available);
  try(ZipFile z=new ZipFile(input)){
   String xml=new String(FontFallback.read(z.getInputStream(z.getEntry("word/document.xml"))),StandardCharsets.UTF_8);
   if(!xml.contains("w:ascii=\"NanumGothic\"")||!xml.contains("w:hAnsi=\"Arial\"")||!xml.contains("w:ascii=\"Embedded Custom\"")||!xml.contains("<w:t>Missing Serif</w:t>"))throw new AssertionError(xml);
   if(!Arrays.equals(new byte[]{1,2,3,4},FontFallback.read(z.getInputStream(z.getEntry("word/media/raw.bin")))))throw new AssertionError("media changed");
  }
  Set<String> aliases=new HashSet<>();FontFallback.fontNames(new File(args[0]),aliases);
  if(!aliases.contains("nanumgothic")||!aliases.contains("나눔고딕"))throw new AssertionError(aliases);
  System.out.println("PASS: missing-font replacement, available and embedded preservation, text/media preservation, font aliases");
  for(File f:dir.listFiles())f.delete();dir.delete();
 }
}

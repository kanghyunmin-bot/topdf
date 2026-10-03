package local.topdf;
import java.io.*;
import java.nio.file.*;
import java.util.*;
public final class FileCopyHostTest {
 public static void main(String[] args)throws Exception{
  Path dir=Files.createTempDirectory("topdf-copy-test");File input=dir.resolve("converted.pdf").toFile(),output=dir.resolve("other.pdf").toFile();byte[] content={1,2,3,4};Files.write(input.toPath(),content);
  try{OfflineEngine.copy(input,input);throw new AssertionError("self-copy accepted");}catch(IOException expected){}
  if(!Arrays.equals(content,Files.readAllBytes(input.toPath())))throw new AssertionError("input truncated");
  OfflineEngine.copy(input,output);if(!Arrays.equals(content,Files.readAllBytes(output.toPath())))throw new AssertionError("copy changed bytes");
  input.delete();output.delete();dir.toFile().delete();System.out.println("PASS: self-copy rejected before truncation, original preserved, regular copy exact");
 }
}

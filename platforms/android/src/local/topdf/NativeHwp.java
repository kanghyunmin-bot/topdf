package local.topdf;
final class NativeHwp {
 static {System.loadLibrary("topdf_hwp");}
 static native String decodeTiff(String input,String outputDirectory);
 static native String render(String input,String output,String fonts);
}

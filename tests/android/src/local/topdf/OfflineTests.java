package local.topdf;
import android.app.Instrumentation;
import android.content.*;
import android.os.*;
import java.io.*;
import java.util.concurrent.*;
import com.tom_roush.pdfbox.pdmodel.PDDocument;
import com.tom_roush.pdfbox.text.PDFTextStripper;
public final class OfflineTests extends Instrumentation {
 public void onCreate(Bundle b){super.onCreate(b);start();}
 public void onStart(){Bundle result=new Bundle();try{
  Context c=getTargetContext();File root=new File(c.getExternalFilesDir(null),"offline-tests");root.mkdirs();
  StringBuilder report=new StringBuilder();int serial=1;
  for(String ext:new String[]{"docx","pptx","xlsx","hwp","hwpx","txt","png","tiff"}){
   File input=new File(root,"sample."+ext),output=new File(root,ext+".pdf");
   try(InputStream in=getContext().getAssets().open("sample."+ext);OutputStream out=new FileOutputStream(input)){byte[] buf=new byte[65536];int n;while((n=in.read(buf))!=-1)out.write(buf,0,n);}
   CountDownLatch done=new CountDownLatch(1);String[] error={null};int[] pid={0};final int generation=serial++;
   Messenger reply=new Messenger(new Handler(Looper.getMainLooper()){public void handleMessage(Message m){if(m.arg2!=generation)return;if(m.what==4)pid[0]=m.arg1;else if(m.what==2)done.countDown();else if(m.what==3){error[0]=m.getData().getString("error");done.countDown();}}});
   ServiceConnection conn=new ServiceConnection(){public void onServiceConnected(ComponentName n,IBinder b){try{Message m=Message.obtain(null,1);m.arg1=generation;m.replyTo=reply;Bundle args=new Bundle();args.putString("input",input.getPath());args.putString("output",output.getPath());m.setData(args);new Messenger(b).send(m);}catch(Exception e){error[0]=e.toString();done.countDown();}}public void onServiceDisconnected(ComponentName n){error[0]="engine disconnected";done.countDown();}};
   boolean bound=c.bindService(new Intent().setClassName(c,"local.topdf.EngineService"),conn,Context.BIND_AUTO_CREATE);
   if(!bound)throw new Exception("bind failed");boolean finished=done.await(180,TimeUnit.SECONDS);c.unbindService(conn);if(pid[0]!=0)android.os.Process.killProcess(pid[0]);
   if(!finished||error[0]!=null)throw new Exception(ext+": "+error[0]+" finished="+finished);
   com.tom_roush.pdfbox.android.PDFBoxResourceLoader.init(c);
   try(PDDocument d=PDDocument.load(output)){String text=new PDFTextStripper().getText(d);int expected=(ext.equals("docx")||ext.equals("tiff"))?2:ext.equals("pptx")?3:1;if(d.getNumberOfPages()!=expected||(!ext.equals("png")&&!ext.equals("tiff")&&(!text.contains("123")||!(text.contains("한글")||text.contains("변환")))))throw new Exception(ext+" pages="+d.getNumberOfPages()+" text="+text);report.append(ext+" passed\n");}
  }
  for(int layout=0;layout<3;layout++){
   File out=new File(root,"range-"+layout+".pdf");OfflineEngine.export(c,new File(root,"docx.pdf"),out,2,2,layout);
   try(PDDocument d=PDDocument.load(out)){String text=new PDFTextStripper().getText(d);if(d.getNumberOfPages()!=1||!text.replace(" ","").contains("두번째"))throw new Exception("range text="+text);if(layout!=0&&(d.getPage(0).getMediaBox().getWidth()>d.getPage(0).getMediaBox().getHeight())!=(layout==2))throw new Exception("orientation");report.append("range/layout "+layout+" passed\n");}
  }
  try(Writer w=new OutputStreamWriter(new FileOutputStream(new File(root,"report.txt")),"UTF-8")){w.write(report.toString());}result.putString("result",report.toString());finish(-1,result);
 }catch(Throwable e){result.putString("error",e.toString());finish(0,result);}}
}

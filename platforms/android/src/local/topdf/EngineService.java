package local.topdf;
import android.app.Service;
import android.content.Intent;
import android.os.*;
import java.io.*;
import java.util.concurrent.*;
public final class EngineService extends Service {
 private final ExecutorService worker=Executors.newSingleThreadExecutor();
 private final Messenger incoming=new Messenger(new Handler(Looper.getMainLooper()){
  public void handleMessage(Message m){if(m.what!=1)return;final Messenger reply=m.replyTo;final Bundle args=m.getData();final int generation=m.arg1;try{Message pid=Message.obtain(null,4,android.os.Process.myPid(),generation);reply.send(pid);}catch(RemoteException e){return;}
   worker.submit(()->{try{OfflineEngine.convert(EngineService.this,new File(args.getString("input")),new File(args.getString("output")));Message result=Message.obtain(null,2);result.arg2=generation;reply.send(result);}catch(Throwable e){try{Message result=Message.obtain(null,3);result.arg2=generation;Bundle b=new Bundle();b.putString("error",e.getMessage()==null?e.getClass().getSimpleName():e.getMessage());result.setData(b);reply.send(result);}catch(RemoteException ignored){}}});}
 });
 public IBinder onBind(Intent intent){return incoming.getBinder();}
 public void onDestroy(){worker.shutdownNow();super.onDestroy();}
}

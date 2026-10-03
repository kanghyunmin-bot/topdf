using System.Diagnostics;
using System.Drawing.Imaging;
using System.Drawing.Printing;
using Microsoft.Win32;
using System.Runtime.InteropServices;
using PdfSharp.Drawing;
using PdfSharp.Pdf;
using PdfSharp.Pdf.IO;
using WinPdf = Windows.Data.Pdf.PdfDocument;
using Windows.Storage;
using Windows.Storage.Streams;

namespace TopDF;
static class Program {
 [STAThread] static int Main(string[] args) {
  try { Engine.EnsureStorage(); } catch(Exception e) { if(args.Length>=3 && args[0].EndsWith("-test"))File.WriteAllText(args[2]+".error.txt",e.ToString());else MessageBox.Show(e.Message,"TopDF 설치"); return 1; }
  ApplicationConfiguration.Initialize();
  if(args.Length==3 && args[0]=="--convert-test") {
   try { Engine.Convert(args[1],args[2],CancellationToken.None).GetAwaiter().GetResult(); return 0; }
   catch(Exception e) { File.WriteAllText(args[2]+".error.txt",e.ToString()); return 1; }
  }
  if(args.Length==6 && args[0]=="--render-test") {
   try {Engine.Export(args[1],args[2],int.Parse(args[3]),int.Parse(args[4]),int.Parse(args[5]));return 0;}
   catch(Exception e){File.WriteAllText(args[2]+".error.txt",e.ToString());return 1;}
  }
  Application.Run(new MainForm(args.FirstOrDefault()));return 0;
 }
}
static class Engine {
 public static readonly string Root=AppContext.BaseDirectory;
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern uint GetCompressedFileSizeW(string file,out uint high);
 static long StorageSize(string file){uint high;uint low=GetCompressedFileSizeW(file+":WofCompressedData",out high);if(low!=uint.MaxValue||Marshal.GetLastWin32Error()==0)return((long)high<<32)|low;low=GetCompressedFileSizeW(file,out high);if(low==uint.MaxValue&&Marshal.GetLastWin32Error()!=0)throw new System.ComponentModel.Win32Exception();return((long)high<<32)|low;}
 public static void EnsureStorage() {
  string marker=Path.Combine(Root,".topdf-rc4-storage-ready");if(File.Exists(marker))return;
  var drive=new DriveInfo(Path.GetPathRoot(Root)!);if(!string.Equals(drive.DriveFormat,"NTFS",StringComparison.OrdinalIgnoreCase))throw new IOException("500MB 이하 설치를 위해 NTFS 드라이브의 쓰기 가능한 폴더에 압축을 풀어주세요.");
  var info=new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),"compact.exe")){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
  foreach(var arg in new[]{"/C","/S:"+Root.TrimEnd(Path.DirectorySeparatorChar),"/I","/EXE:LZX","*"})info.ArgumentList.Add(arg);
  using var process=Process.Start(info)??throw new IOException("앱 용량 최적화를 시작할 수 없습니다.");var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();process.WaitForExit();Task.WaitAll(output,error);
  if(Directory.EnumerateFiles(Root,"*",SearchOption.AllDirectories).Sum(StorageSize)>500_000_000)throw new IOException("앱 설치 용량이 500MB를 초과했습니다. NTFS 드라이브의 사용자 폴더에 설치하세요.");
  if(process.ExitCode!=0)throw new IOException("앱 폴더를 쓸 수 없습니다. 사용자 폴더에 압축을 풀어주세요.");File.WriteAllText(marker,"NTFS LZX storage preparation completed.");
 }
 public static async Task Convert(string input,string output,CancellationToken ct) {
  if(!File.Exists(input)||new FileInfo(input).Length>512L*1024*1024)throw new Exception("512MB 이하의 파일을 선택하세요.");
  var ext=Path.GetExtension(input).ToLowerInvariant();
  if(new[]{".docx",".docm",".dotx",".pptx",".pptm",".ppsx",".xlsx",".xlsm",".odt",".ods",".odp",".hwpx",".epub"}.Contains(ext)){using var zip=System.IO.Compression.ZipFile.OpenRead(input);long total=0;if(zip.Entries.Count>100000)throw new Exception("압축 문서의 항목 수가 너무 많습니다.");foreach(var entry in zip.Entries){if(entry.Length>1024L*1024*1024||total>1024L*1024*1024-entry.Length)throw new Exception("압축 해제 크기가 1GB를 초과합니다.");total+=entry.Length;}}
  if(ext==".pdf") { using var d=PdfReader.Open(input,PdfDocumentOpenMode.Import);if(d.PageCount<1||d.PageCount>2000)throw new Exception("지원 페이지 범위를 벗어났습니다.");File.Copy(input,output,true);return; }
  if(new[]{".png",".jpg",".jpeg",".bmp",".gif",".tif",".tiff"}.Contains(ext)) {
   using var image=Image.FromFile(input);using var pdf=new PdfDocument();var frames=(ext==".tif"||ext==".tiff")?image.GetFrameCount(FrameDimension.Page):1;
   if(frames>2000)throw new Exception("이미지 페이지가 너무 많습니다.");
   for(int i=0;i<frames;i++) { ct.ThrowIfCancellationRequested();if(frames>1)image.SelectActiveFrame(FrameDimension.Page,i);using var ms=new MemoryStream();image.Save(ms,ImageFormat.Png);ms.Position=0;using var x=XImage.FromStream(ms);var p=pdf.AddPage();p.Width=XUnit.FromPoint(x.PointWidth);p.Height=XUnit.FromPoint(x.PointHeight);using var g=XGraphics.FromPdfPage(p);g.DrawImage(x,0,0,p.Width.Point,p.Height.Point); }
   pdf.Save(output);return;
  }
  string dir=Path.Combine(Path.GetTempPath(),"TopDF-"+Guid.NewGuid());Directory.CreateDirectory(dir);
  try {
   string copy=Path.Combine(dir,Path.GetFileName(input));File.Copy(input,copy);if(ext==".txt"){var bytes=File.ReadAllBytes(copy);try{new System.Text.UTF8Encoding(false,true).GetString(bytes);if(!(bytes.Length>=3&&bytes[0]==239&&bytes[1]==187&&bytes[2]==191))File.WriteAllBytes(copy,new byte[]{239,187,191}.Concat(bytes).ToArray());}catch(System.Text.DecoderFallbackException){}}var pi=new ProcessStartInfo{UseShellExecute=false,CreateNoWindow=true,RedirectStandardError=true,RedirectStandardOutput=true};
   if(ext==".hwp"||ext==".hwpx") {
    pi.Environment["TOPDF_HWP_FALLBACK_FONT"]=FontFallback.Family;pi.FileName=Path.Combine(Root,"Engines","hwp.exe");foreach(var a in new[]{"render",copy,"--output",output,"--format","pdf","--font-dir",Path.Combine(Root,"Engines","LibreOffice","share","fonts","truetype"),"--font-dir",Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Microsoft","Windows","Fonts"),"--font-dir",Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"Fonts")})pi.ArgumentList.Add(a);
   } else {
    var formats=new[]{".doc",".docx",".docm",".dot",".dotx",".ppt",".pptx",".pptm",".pps",".ppsx",".xls",".xlsx",".xlsm",".odt",".ods",".odp",".rtf",".csv",".tsv",".txt",".html",".htm",".epub"};
    if(!formats.Contains(ext))throw new Exception("지원하지 않는 파일 형식입니다.");
    FontFallback.Apply(copy);string profile=Path.Combine(dir,"profile");Directory.CreateDirectory(profile+"/user");
    File.WriteAllText(profile+"/user/registrymodifications.xcu","<?xml version=\"1.0\"?><oor:items xmlns:oor=\"http://openoffice.org/2001/registry\"><item oor:path=\"/org.openoffice.Office.Common/Security/Scripting\"><prop oor:name=\"MacroSecurityLevel\" oor:op=\"fuse\"><value>3</value></prop></item><item oor:path=\"/org.openoffice.Office.Calc/Content/Update\"><prop oor:name=\"Link\" oor:op=\"fuse\"><value>0</value></prop></item><item oor:path=\"/org.openoffice.Office.Writer/Content/Update\"><prop oor:name=\"Link\" oor:op=\"fuse\"><value>0</value></prop></item></oor:items>");
    pi.FileName=Path.Combine(Root,"Engines","LibreOffice","program","soffice.com");pi.Environment["PYTHONDONTWRITEBYTECODE"]="1";
    foreach(var a in new[]{"-env:UserInstallation="+new Uri(profile).AbsoluteUri,"--headless","--nologo","--nodefault","--norestore","--convert-to","pdf","--outdir",dir,copy})pi.ArgumentList.Add(a);
   }
   using var p=Process.Start(pi)??throw new Exception("변환 엔진을 시작할 수 없습니다.");var stdout=p.StandardOutput.ReadToEndAsync();var stderr=p.StandardError.ReadToEndAsync();using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);timeout.CancelAfter(TimeSpan.FromSeconds(180));
   try {await p.WaitForExitAsync(timeout.Token);}catch{if(!p.HasExited)p.Kill(true);throw;}
   var err=await stderr;await stdout;if(p.ExitCode!=0)throw new Exception("변환 엔진 오류: "+err[..Math.Min(err.Length,600)]);
   if(ext!=".hwp"&&ext!=".hwpx") {var result=Path.Combine(dir,Path.GetFileNameWithoutExtension(copy)+".pdf");if(!File.Exists(result))throw new Exception("PDF가 생성되지 않았습니다.");File.Copy(result,output,true);}
   using var check=PdfReader.Open(output,PdfDocumentOpenMode.Import);if(check.PageCount<1||check.PageCount>2000)throw new Exception("출력 PDF의 페이지 수가 지원 범위를 벗어났습니다.");
  } finally {try{Directory.Delete(dir,true);}catch{}}
 }
 public static string Adjacent(string input) { string root=Path.Combine(Path.GetDirectoryName(input)!,Path.GetFileNameWithoutExtension(input));string p=root+".pdf";for(int n=1;File.Exists(p);n++)p=root+" ("+n+").pdf";return p; }
 public static void Export(string input,string output,int first,int last,int layout) {
  using var src=PdfReader.Open(input,PdfDocumentOpenMode.Import);if(first<1||last<first||last>src.PageCount)throw new Exception("페이지 범위를 확인하세요.");using var dst=new PdfDocument();
  if(layout==0) {for(int i=first-1;i<last;i++)dst.AddPage(src.Pages[i]);}
  else {using var form=XPdfForm.FromFile(input);for(int i=first;i<=last;i++){form.PageNumber=i;var p=dst.AddPage();p.Width=XUnit.FromPoint(layout==2?842:595);p.Height=XUnit.FromPoint(layout==2?595:842);using var g=XGraphics.FromPdfPage(p);double w=p.Width.Point,h=p.Height.Point,s=Math.Min((w-36)/form.PointWidth,(h-36)/form.PointHeight);g.DrawImage(form,(w-form.PointWidth*s)/2,(h-form.PointHeight*s)/2,form.PointWidth*s,form.PointHeight*s);}}
  dst.Save(output);
 }
}
sealed class MainForm:Form {
 readonly Label status=new(){AutoSize=true,Text="문서·이미지를 선택하세요"};readonly PictureBox preview=new(){Dock=DockStyle.Fill,SizeMode=PictureBoxSizeMode.Zoom,BackColor=Color.White};
 readonly NumericUpDown first=new(){Minimum=1,Maximum=2000,Value=1,Width=65},last=new(){Minimum=1,Maximum=2000,Value=1,Width=65};readonly ComboBox layout=new(){DropDownStyle=ComboBoxStyle.DropDownList,Width=180};readonly CheckBox beside=new(){Text="원본 옆에 저장",Checked=true,AutoSize=true};
 readonly Button save=new(){Text="PDF 저장",Enabled=false},print=new(){Text="인쇄창",Enabled=false};string? source,temp,previewTemp;WinPdf? pdf;CancellationTokenSource? job;readonly Queue<string> queue=new();int pageIndex;
 public MainForm(string? input) {
  Text="TopDF — PDF로 변환";Width=1000;Height=780;MinimumSize=new Size(760,600);AllowDrop=true;try{Icon=new Icon(Path.Combine(Engine.Root,"AppIcon.ico"));}catch{}
  var top=new FlowLayoutPanel{Dock=DockStyle.Top,AutoSize=true,Padding=new Padding(12)};var choose=new Button{Text="파일 선택"};choose.Click+=(_,_)=>{using var d=new OpenFileDialog{Multiselect=true};if(d.ShowDialog()==DialogResult.OK)Enqueue(d.FileNames);};top.Controls.Add(choose);top.Controls.Add(status);
  var bottom=new FlowLayoutPanel{Dock=DockStyle.Bottom,AutoSize=true,Padding=new Padding(12)};layout.Items.AddRange(new object[]{"원본 크기·방향","A4 세로","A4 가로"});layout.SelectedIndex=0;bottom.Controls.Add(layout);bottom.Controls.Add(new Label{Text="페이지",AutoSize=true});bottom.Controls.Add(first);bottom.Controls.Add(new Label{Text="~",AutoSize=true});bottom.Controls.Add(last);var apply=new Button{Text="미리보기"};apply.Click+=async(_,_)=>{if(temp==null)return;try{string path=Path.Combine(Path.GetTempPath(),"TopDF-layout-"+Guid.NewGuid()+".pdf");Engine.Export(temp,path,(int)first.Value,(int)last.Value,layout.SelectedIndex);pdf=await WinPdf.LoadFromFileAsync(await StorageFile.GetFileFromPathAsync(path));if(previewTemp!=null)File.Delete(previewTemp);previewTemp=path;pageIndex=0;await Preview(0);}catch(Exception e){MessageBox.Show(e.Message);}};bottom.Controls.Add(apply);bottom.Controls.Add(beside);bottom.Controls.Add(save);bottom.Controls.Add(print);
  var prev=new Button{Text="◀"};var next=new Button{Text="▶"};prev.Click+=async(_,_)=>{if(pageIndex>0)await Preview(--pageIndex);};next.Click+=async(_,_)=>{if(pdf!=null&&pageIndex+1<pdf.PageCount)await Preview(++pageIndex);};bottom.Controls.Add(prev);bottom.Controls.Add(next);
  var cancel=new Button{Text="취소"};cancel.Click+=(_,_)=>job?.Cancel();bottom.Controls.Add(cancel);
  var register=new Button{Text="우클릭 메뉴 추가",AutoSize=true};register.Click+=(_,_)=>Register();bottom.Controls.Add(register);var unregister=new Button{Text="메뉴 제거"};unregister.Click+=(_,_)=>{Registry.CurrentUser.DeleteSubKeyTree(@"Software\Classes\*\shell\TopDF",false);MessageBox.Show("현재 사용자의 TopDF 메뉴를 제거했습니다.");};bottom.Controls.Add(unregister);
  Controls.Add(preview);Controls.Add(top);Controls.Add(bottom);save.Click+=async(_,_)=>await Save();print.Click+=async(_,_)=>await Print();DragEnter+=(_,e)=>{if(e.Data?.GetDataPresent(DataFormats.FileDrop)==true)e.Effect=DragDropEffects.Copy;};DragDrop+=(_,e)=>Enqueue((string[])e.Data!.GetData(DataFormats.FileDrop)!);
  FormClosed+=(_,_)=>{job?.Cancel();preview.Image?.Dispose();if(temp!=null)try{File.Delete(temp);}catch{}if(previewTemp!=null)try{File.Delete(previewTemp);}catch{}};Shown+=(_,_)=>{if(input!=null)Enqueue(new[]{input});};
 }
 void Enqueue(IEnumerable<string> paths){foreach(var p in paths)queue.Enqueue(p);if(job==null)_=LoadNext();}
 async Task LoadNext(){if(queue.Count==0)return;source=queue.Dequeue();save.Enabled=print.Enabled=false;status.Text="변환 중: "+Path.GetFileName(source);job=new CancellationTokenSource();try{if(temp!=null)File.Delete(temp);temp=Path.Combine(Path.GetTempPath(),"TopDF-preview-"+Guid.NewGuid()+".pdf");await Engine.Convert(source,temp,job.Token);pdf=await WinPdf.LoadFromFileAsync(await StorageFile.GetFileFromPathAsync(temp));last.Maximum=first.Maximum=pdf.PageCount;first.Value=1;last.Value=pdf.PageCount;layout.SelectedIndex=0;pageIndex=0;await Preview(0);save.Enabled=print.Enabled=true;status.Text=Path.GetFileName(source)+" · "+pdf.PageCount+"페이지";}catch(Exception e){status.Text="변환 실패 또는 취소";MessageBox.Show(e.Message);}finally{job.Dispose();job=null;}}
 async Task<Bitmap> Render(WinPdf d,int n){using var page=d.GetPage((uint)n);using var stream=new InMemoryRandomAccessStream();double scale=Math.Min(2,1600/Math.Max(page.Size.Width,page.Size.Height));await page.RenderToStreamAsync(stream,new Windows.Data.Pdf.PdfPageRenderOptions{DestinationWidth=(uint)Math.Max(1,page.Size.Width*scale),DestinationHeight=(uint)Math.Max(1,page.Size.Height*scale)});stream.Seek(0);using var reader=new DataReader(stream.GetInputStreamAt(0));await reader.LoadAsync((uint)stream.Size);byte[] bytes=new byte[stream.Size];reader.ReadBytes(bytes);using var ms=new MemoryStream(bytes);using var img=Image.FromStream(ms);return new Bitmap(img);}
 async Task Preview(int n){if(pdf==null)return;var image=await Render(pdf,n);var old=preview.Image;preview.Image=image;old?.Dispose();}
 async Task Save(){if(temp==null||source==null)return;string target=Engine.Adjacent(source);bool overwrite=false;if(!beside.Checked){using var d=new SaveFileDialog{Filter="PDF|*.pdf",FileName=Path.GetFileName(target),InitialDirectory=Path.GetDirectoryName(source),OverwritePrompt=true};if(d.ShowDialog()!=DialogResult.OK)return;target=d.FileName;overwrite=true;}
  string stage=Path.Combine(Path.GetDirectoryName(target)!,".topdf-"+Guid.NewGuid()+".pdf");try{Engine.Export(temp,stage,(int)first.Value,(int)last.Value,layout.SelectedIndex);File.Move(stage,target,overwrite);status.Text="저장 완료: "+Path.GetFileName(target);save.Enabled=print.Enabled=false;if(queue.Count>0)await LoadNext();}catch(Exception e){MessageBox.Show(e.Message);}finally{if(File.Exists(stage))File.Delete(stage);}}
 async Task Print(){if(temp==null)return;string file=Path.Combine(Path.GetTempPath(),"TopDF-print-"+Guid.NewGuid()+".pdf");try{Engine.Export(temp,file,(int)first.Value,(int)last.Value,layout.SelectedIndex);var doc=await WinPdf.LoadFromFileAsync(await StorageFile.GetFileFromPathAsync(file));using var printer=new PrintDocument();int index=0;printer.DefaultPageSettings.Landscape=layout.SelectedIndex==2;printer.PrintPage+=(_,e)=>{using var img=Task.Run(()=>Render(doc,index++)).GetAwaiter().GetResult();var b=e.MarginBounds;float s=Math.Min((float)b.Width/img.Width,(float)b.Height/img.Height);e.Graphics!.DrawImage(img,b.X+(b.Width-img.Width*s)/2,b.Y+(b.Height-img.Height*s)/2,img.Width*s,img.Height*s);e.HasMorePages=index<doc.PageCount;};using var dialog=new PrintDialog{Document=printer};if(dialog.ShowDialog()==DialogResult.OK)printer.Print();}catch(Exception e){MessageBox.Show(e.Message);}finally{File.Delete(file);}}
 void Register(){using var k=Registry.CurrentUser.CreateSubKey(@"Software\Classes\*\shell\TopDF");k.SetValue("","PDF로 변환");k.SetValue("Icon",Environment.ProcessPath!);using var c=k.CreateSubKey("command");c.SetValue("","\""+Environment.ProcessPath+"\" \"%1\"");MessageBox.Show("현재 사용자에게 우클릭 메뉴를 추가했습니다. Windows 11에서는 '더 많은 옵션 표시'에 나타날 수 있습니다. 앱을 옮기면 다시 등록하세요.");}
}

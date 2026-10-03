using System.Drawing.Text;
using System.IO.Compression;
using System.Text;
using System.Text.RegularExpressions;
namespace TopDF;
static class FontFallback {
 public const string Family="NanumGothic";
 static readonly Regex Tags=new(@"<(?:[A-Za-z_][\w.-]*:)?(?:rFonts|latin|ea|cs|font|name|font-face)\b[^>]*>");
 static readonly Regex Attributes=new("(w:ascii|w:hAnsi|w:eastAsia|w:cs|typeface|svg:font-family|w:name|val)\\s*=\\s*([\"'])(.*?)\\2");
 static bool Selected(string n)=>n.EndsWith(".xml")&&(n.StartsWith("word/")||n.StartsWith("ppt/")||n=="xl/styles.xml"||n.StartsWith("xl/theme/")||n=="styles.xml"||n=="content.xml");
 static IEnumerable<string> Aliases(string path){
  var result=new List<string>();try{
   using var f=File.OpenRead(path);using var b=new BinaryReader(f);
   int U16(){var bytes=b.ReadBytes(2);if(bytes.Length!=2)throw new EndOfStreamException();return(bytes[0]<<8)|bytes[1];}
   uint U32(){return(uint)((U16()<<16)|U16());}
   if(f.Length<12)return result;var signature=U32();var faces=new List<long>();
   if(signature==0x74746366){U32();var count=U32();if(count>256)return result;for(int i=0;i<count;i++)faces.Add(U32());}else faces.Add(0);
   foreach(var face in faces){if(face+12>f.Length)continue;f.Position=face+4;var tables=U16();if(tables>1024)continue;long table=-1;
    for(int i=0;i<tables;i++){f.Position=face+12+i*16;var tag=U32();U32();var offset=U32();U32();if(tag==0x6e616d65){table=offset;break;}}
    if(table<0||table+6>f.Length)continue;f.Position=table+2;var count=U16();var start=U16();if(count>10000||table+6+count*12>f.Length)continue;
    for(int i=0;i<count;i++){f.Position=table+6+i*12;var platform=U16();U16();U16();var id=U16();var length=U16();var offset=U16();if(platform!=0&&platform!=3||!new[]{1,4,6,16}.Contains(id)||table+start+offset+length>f.Length)continue;f.Position=table+start+offset;result.Add(Encoding.BigEndianUnicode.GetString(b.ReadBytes(length)));}
   }
  }catch(IOException){}return result;
 }
 public static HashSet<string> Available(){
  using var installed=new InstalledFontCollection();var names=new HashSet<string>(installed.Families.Select(f=>f.Name),StringComparer.OrdinalIgnoreCase){"serif","sans-serif","monospace","system-ui",Family,"나눔고딕"};
  var dirs=new[]{Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"Fonts"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Microsoft","Windows","Fonts"),Path.Combine(Engine.Root,"Engines","LibreOffice","share","fonts")};
  foreach(var dir in dirs){if(!Directory.Exists(dir))continue;foreach(var file in Directory.EnumerateFiles(dir,"*",SearchOption.AllDirectories)){if(new[]{".ttf",".otf",".ttc"}.Contains(Path.GetExtension(file).ToLowerInvariant()))names.UnionWith(Aliases(file));}}
  return names;
 }
 public static void Apply(string input){
  if(!new[]{".docx",".docm",".dotx",".pptx",".pptm",".ppsx",".xlsx",".xlsm",".odt",".ods",".odp"}.Contains(Path.GetExtension(input).ToLowerInvariant()))return;
  var available=Available();var embedded=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
  using var zip=ZipFile.Open(input,ZipArchiveMode.Update);
  var entries=zip.Entries.Where(e=>Selected(e.FullName)).ToList();var xmls=new Dictionary<string,string>();
  foreach(var entry in entries){if(entry.Length>32*1024*1024)throw new IOException("글꼴 XML 크기가 너무 큽니다.");using var stream=entry.Open();using var reader=new StreamReader(stream,Encoding.UTF8);var xml=reader.ReadToEnd();xmls[entry.FullName]=xml;
   foreach(Match block in Regex.Matches(xml,@"<(?:w:font|p:embeddedFont)\b[^>]*>.*?</(?:w:font|p:embeddedFont)>",RegexOptions.Singleline)){if(!block.Value.Contains("embed"))continue;var name=Regex.Match(block.Value,"(?:w:name|typeface)=[\"']([^\"']+)[\"']");if(name.Success)embedded.Add(System.Net.WebUtility.HtmlDecode(name.Groups[1].Value));}
  }
  foreach(var entry in entries){var xml=xmls[entry.FullName];var changed=Tags.Replace(xml,tag=>Attributes.Replace(tag.Value,attr=>{var name=System.Net.WebUtility.HtmlDecode(attr.Groups[3].Value);if(string.IsNullOrEmpty(name)||name.StartsWith("+")||available.Contains(name)||embedded.Contains(name))return attr.Value;return attr.Value[..(attr.Groups[3].Index-relative(attr))]+Family+attr.Value[(attr.Groups[3].Index-relative(attr)+attr.Groups[3].Length)..];}));
   if(changed==xml)continue;using var stream=entry.Open();stream.SetLength(0);using var writer=new StreamWriter(stream,new UTF8Encoding(false));writer.Write(changed);
  }
 }
 static int relative(Match match)=>match.Index;
}

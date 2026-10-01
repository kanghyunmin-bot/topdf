use jni::{JNIEnv, objects::{JClass,JString},sys::jstring};
use std::path::{Path,PathBuf};
#[unsafe(no_mangle)]
pub extern "system" fn Java_local_topdf_NativeHwp_render(mut env:JNIEnv,_class:JClass,input:JString,output:JString,fonts:JString)->jstring {
 let result=(||->Result<(),String>{
  let input:String=env.get_string(&input).map_err(|e|e.to_string())?.into();
  let output:String=env.get_string(&output).map_err(|e|e.to_string())?.into();
  let fonts:String=env.get_string(&fonts).map_err(|e|e.to_string())?.into();
  let doc=if input.to_lowercase().ends_with(".hwpx") {hwpx::read_document(Path::new(&input)).map_err(|e|e.to_string())?.document} else {hwp5::read_document(Path::new(&input)).map_err(|e|e.to_string())?.document};
  let pdf=hwp_render::render_document_pdf(&doc,&hwp_render::RenderOptions{dpi:144.,font_dirs:vec![PathBuf::from(fonts),PathBuf::from("/system/fonts")]},None).map_err(|e|e.to_string())?;
  std::fs::write(output,pdf.data).map_err(|e|e.to_string())?;Ok(())
 })();
 match result {Ok(())=>std::ptr::null_mut(),Err(e)=>env.new_string(e).map(|s|s.into_raw()).unwrap_or(std::ptr::null_mut())}
}

#[unsafe(no_mangle)]
pub extern "system" fn Java_local_topdf_NativeHwp_decodeTiff(mut env:JNIEnv,_class:JClass,input:JString,output:JString)->jstring {
 let result=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||->Result<(),String>{
  let input:String=env.get_string(&input).map_err(|e|e.to_string())?.into();let output:String=env.get_string(&output).map_err(|e|e.to_string())?.into();
  std::fs::create_dir_all(&output).map_err(|e|e.to_string())?;
  let mut decoder=tiff::decoder::Decoder::new(std::io::BufReader::new(std::fs::File::open(input).map_err(|e|e.to_string())?)).map_err(|e|e.to_string())?;
  for page in 0..2000 {
   let (w,h)=decoder.dimensions().map_err(|e|e.to_string())?;
   if w==0||h==0||w>20000||h>20000||w as u64*h as u64>64000000{return Err("TIFF image exceeds the decoding limit".into());}
   let color=decoder.colortype().map_err(|e|e.to_string())?;
   let bytes=match decoder.read_image().map_err(|e|e.to_string())? {tiff::decoder::DecodingResult::U8(v)=>v,tiff::decoder::DecodingResult::U16(v)=>v.into_iter().map(|n|(n>>8)as u8).collect(),_=>return Err("Unsupported TIFF sample format".into())};
   let rgba:Vec<u8>=match color {
    tiff::ColorType::RGB(_)=>bytes.chunks_exact(3).flat_map(|p|[p[0],p[1],p[2],255]).collect(),
    tiff::ColorType::RGBA(_)=>bytes,
    tiff::ColorType::Gray(_)=>bytes.into_iter().flat_map(|g|[g,g,g,255]).collect(),
    tiff::ColorType::GrayA(_)=>bytes.chunks_exact(2).flat_map(|p|[p[0],p[0],p[0],p[1]]).collect(),
    tiff::ColorType::CMYK(_)=>bytes.chunks_exact(4).flat_map(|p|{let k=255-p[3]as u16;[((255-p[0]as u16)*k/255)as u8,((255-p[1]as u16)*k/255)as u8,((255-p[2]as u16)*k/255)as u8,255]}).collect(),
    _=>return Err("Unsupported TIFF color format".into())
   };
   image::RgbaImage::from_raw(w,h,rgba).ok_or("Invalid TIFF pixels")?.save(Path::new(&output).join(format!("{page:04}.png"))).map_err(|e|e.to_string())?;
   if !decoder.more_images(){return Ok(());}decoder.next_image().map_err(|e|e.to_string())?;
  }
  Err("TIFF exceeds 2000 pages".into())
 }));
 match result {Ok(Ok(()))=>std::ptr::null_mut(),other=>{let error=match other{Ok(Err(e))=>e,_=>"TIFF decoder failed".into()};env.new_string(error).map(|s|s.into_raw()).unwrap_or(std::ptr::null_mut())}}
}

#!/usr/bin/env python3
"""Build upstream HWP CLI with an opt-in missing-font preference for TopDF."""
import argparse,hashlib,os,pathlib,shutil,subprocess,tarfile,urllib.request
root=pathlib.Path(__file__).resolve().parent.parent
args=argparse.ArgumentParser();args.add_argument('--prepare-only',action='store_true');args.add_argument('--target',action='append');options=args.parse_args()
src=root/'build/hwp-gothic-src'
if not (src/'Cargo.toml').exists():
 upstream=root/'build/upstream/hwp-cli-1.3.1'
 if not upstream.exists():
  archive=root/'downloads/hwp-cli-v1.3.1-source.tar.gz';archive.parent.mkdir(parents=True,exist_ok=True)
  if not archive.exists():
   archive.write_bytes(urllib.request.urlopen('https://github.com/STAIxBWLB/hwp-cli/archive/refs/tags/v1.3.1.tar.gz').read())
  assert hashlib.sha256(archive.read_bytes()).hexdigest()=='2930cec812cf12764ee6113a97a73fe95f9ee870c3556f8b507e2f8163ac0839'
  upstream.parent.mkdir(parents=True,exist_ok=True)
  with tarfile.open(archive) as bundle:
   for member in bundle.getmembers():
    assert not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts
   bundle.extractall(upstream.parent)
 shutil.copytree(root/'build/upstream/hwp-cli-1.3.1',src,ignore=shutil.ignore_patterns('target','.git'),dirs_exist_ok=True)
 subprocess.run(['git','init','-b','khm/gothic-font-fallback',str(src)],check=True,stdout=subprocess.DEVNULL)
p=src/'crates/hwp-render/src/fonts.rs'
s=p.read_text(encoding='utf-8')
needle='''        if let Some(alt) = &alt {
            candidates.push(alt);
        }'''
replacement='''        // TopDF keeps exact matches first, then prefers a clean gothic fallback.
        // No environment override means the upstream resolver remains unchanged.
        let preferred = if cfg!(target_os = "android") {
            Some("NanumGothic".to_owned())
        } else {
            std::env::var("TOPDF_HWP_FALLBACK_FONT").ok()
        };
        if let Some(name) = preferred.as_deref() {
            candidates.push(name);
        }
        if let Some(alt) = &alt {
            candidates.push(alt);
        }'''
if 'TOPDF_HWP_FALLBACK_FONT' in s and 'cfg!(target_os = "android")' not in s:
 s=s.replace('let preferred = std::env::var("TOPDF_HWP_FALLBACK_FONT").ok();','let preferred = if cfg!(target_os = "android") { Some("NanumGothic".to_owned()) } else { std::env::var("TOPDF_HWP_FALLBACK_FONT").ok() };')
 p.write_text(s,encoding='utf-8')
if 'TOPDF_HWP_FALLBACK_FONT' not in s:
 assert needle in s
 p.write_text(s.replace(needle,replacement,1),encoding='utf-8')
if options.prepare_only: print('Prepared Gothic HWP source');raise SystemExit(0)
env=os.environ.copy()
local=root/'build/toolchains/cargo/bin'
if (local/'rustup').exists():
 env['CARGO_HOME']=str(root/'build/toolchains/cargo');env['RUSTUP_HOME']=str(root/'build/toolchains/rustup')
 env['PATH']=str(local)+':'+env['PATH']
env['RUSTUP_TOOLCHAIN']='1.93.0'
rustup=shutil.which('rustup',path=env['PATH']);cargo=shutil.which('cargo',path=env['PATH'])
if not rustup or not cargo: raise SystemExit('Rustup is required to build the HWP engine.')
subprocess.run([rustup,'toolchain','install','1.93.0','--profile','minimal','--component','rustfmt','--component','clippy'],env=env,check=True)
subprocess.run([cargo,'fmt','--all'],cwd=src,env=env,check=True)
for target in options.target or ['aarch64-apple-darwin','x86_64-apple-darwin']:
 subprocess.run([rustup,'target','add',target],env=env,check=True)
 subprocess.run([cargo,'build','--locked','--release','-p','hwp-cli','--target',target],cwd=src,env=env,check=True)
print('Built requested Gothic-aware HWP engine targets')

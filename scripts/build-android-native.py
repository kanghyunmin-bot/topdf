#!/usr/bin/env python3
import os,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parent.parent
ndk=pathlib.Path(os.environ.get('ANDROID_NDK_HOME',r/'build/toolchains/android-ndk-r29'))
prebuilt=ndk/'toolchains/llvm/prebuilt';host=next(prebuilt.iterdir());tool=host/'bin'
for target in ['aarch64-linux-android','x86_64-linux-android']:
 env=os.environ.copy();env['CARGO_TARGET_'+target.upper().replace('-','_')+'_LINKER']=str(tool/(target+'26-clang'));env['CC_'+target.replace('-','_')]=str(tool/(target+'26-clang'));env['AR_'+target.replace('-','_')]=str(tool/'llvm-ar')
 subprocess.run(['cargo','build','--locked','--release','--target',target,'--manifest-path',str(r/'platforms/android/native/Cargo.toml')],env=env,check=True)

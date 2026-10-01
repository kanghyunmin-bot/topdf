#!/usr/bin/env python3
import os,pathlib,subprocess,zipfile
R=pathlib.Path(__file__).resolve().parent.parent
SDK=pathlib.Path.home()/'Library/Android/sdk';J=pathlib.Path('/Library/Java/JavaVirtualMachines/amazon-corretto-11.jdk/Contents/Home');T=SDK/'build-tools/35.0.0';A=SDK/'platforms/android-35/android.jar';B=R/'build/android-tests';B.mkdir(parents=True,exist_ok=True);C=B/'classes';C.mkdir(exist_ok=True);D=B/'dex';D.mkdir(exist_ok=True)
env=os.environ.copy();env['JAVA_HOME']=str(J)
def run(args):subprocess.run(list(map(str,args)),env=env,check=True)
run([T/'aapt2','link','-I',A,'--manifest',R/'tests/android/AndroidManifest.xml','-A',R/'tests/android/assets','-o',B/'unsigned.apk'])
run([J/'bin/javac','-source','8','-target','8','-encoding','UTF-8','-classpath',os.pathsep.join(map(str,[A,R/'build/android/classes.jar',R/'build/android/pdfbox.jar'])),'-d',C,*list((R/'tests/android/src').rglob('*.java'))])
run([J/'bin/jar','cf',B/'tests.jar','-C',C,'.'])
run([T/'d8','--min-api','26','--lib',A,'--classpath',R/'build/android/classes.jar','--classpath',R/'build/android/pdfbox.jar','--output',D,B/'tests.jar'])
with zipfile.ZipFile(B/'unsigned.apk','a') as z:
 for p in D.glob('*.dex'):z.write(p,p.name)
run([T/'zipalign','-f','4',B/'unsigned.apk',B/'aligned.apk'])
run([T/'apksigner','sign','--ks',R/'build/private-keys/topdf-preview.jks','--ks-pass','file:'+str(R/'build/private-keys/topdf-preview.password'),'--out',B/'tests.apk',B/'aligned.apk'])

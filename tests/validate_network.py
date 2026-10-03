import http.server,threading,subprocess,pathlib,json,sys
root=pathlib.Path(__file__).resolve().parent.parent
hits=[]
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  hits.append(self.path);self.send_response(200);self.send_header('Content-Type','image/png');self.end_headers();self.wfile.write((root/'tests/release-fixtures/image.png').read_bytes())
 def log_message(self,*args):pass
server=http.server.HTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
html=root/'tests/release-fixtures/remote.html';html.write_text(f'<html><meta charset="utf-8"><body><p>LOCAL TEXT 123</p><img src="http://127.0.0.1:{server.server_port}/remote.png"></body></html>')
app=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else root/'build/release/PDF로 변환.app'
exe=app/'Contents/MacOS/TopDF'
p=subprocess.run([str(exe),'--convert-test',str(html),str(root/'tests/release-output/remote.pdf')],capture_output=True,text=True,timeout=60)
server.shutdown()
assert p.returncode==0,(p.stdout,p.stderr)
assert hits==[],hits
(root/'tests/release-output/network-report.json').write_text(json.dumps({'passed':True,'test':'engine denies outbound HTTP including loopback','requests':hits}))
print('PASS: outbound HTTP denied, HTML still converted')

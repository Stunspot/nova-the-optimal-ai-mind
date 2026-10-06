#!/usr/bin/env python3
"""Private loopback native-artifact display. No durable record store."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
import argparse, json, secrets, sys, tempfile, subprocess, urllib.request, webbrowser, threading
from launch_runtime import launch,RUNTIME_NONCE
import hashlib
ROOT=Path(__file__).resolve().parent
RUNTIME_SHA=hashlib.sha256(Path(__file__).read_bytes()+(ROOT/"launch_runtime.py").read_bytes()).hexdigest()
CONFIG=json.loads((ROOT/'desk.json').read_text(encoding='utf-8'))
TOKEN=secrets.token_urlsafe(32)
def validate_record(record):
    if not isinstance(record,dict): return ['Native document must be a JSON object.']
    with tempfile.TemporaryDirectory(prefix='native-desk-validation-') as tmp:
        path=Path(tmp)/'record.json'; path.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
        result=subprocess.run([sys.executable,'-B',str(ROOT.parent/'scripts'/CONFIG['validator']),str(path)],capture_output=True,text=True,encoding='utf-8',timeout=20)
        return [] if result.returncode==0 else [(result.stdout+result.stderr).strip() or 'Validator failed.']
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,value,json_value=True):
        raw=json.dumps(value,ensure_ascii=False).encode() if json_value else value
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8' if json_value else 'text/html; charset=utf-8'); self.send_header('Cache-Control','no-store');
        if getattr(self,'issue_session',False):self.send_header('Set-Cookie',f'{self.cookie_name()}={TOKEN}; HttpOnly; SameSite=Strict; Path=/')
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"); self.end_headers(); self.wfile.write(raw)
    def static_asset(self, relative, mime):
        raw=(ROOT/relative).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.end_headers()
        self.wfile.write(raw)
    def cookie_name(self):
        return 'desk_'+hashlib.sha256((CONFIG['id']+'|'+str(ROOT)).encode('utf-8')).hexdigest()[:16]+'_'+str(self.server.server_port)
    def authorized(self):
        origin=f'http://127.0.0.1:{self.server.server_port}'
        cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''));credential=cookie.get(self.cookie_name());valid=self.headers.get('X-Desk-Token')==TOKEN or (credential is not None and credential.value==TOKEN)
        return self.headers.get('Host')==origin.removeprefix('http://') and self.headers.get('Origin',origin)==origin and valid
    def do_GET(self):
        if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}': return self.reply(403,{'error':'Unexpected host'})
        if self.path=='/api/health': return self.reply(200,{'product':CONFIG['id'],'version':CONFIG['version'],'workspace':str(ROOT),'mode':'native-file preparation; no persistent record store','runtime_sha256':RUNTIME_SHA,'instance':RUNTIME_NONCE})
        if self.path=='/': return self.reply(200,(ROOT/'index.html').read_bytes(),False)
        if self.path=='/refinement.css': return self.static_asset('refinement.css','text/css; charset=utf-8')
        if self.path=='/theme.css': return self.static_asset('theme.css','text/css; charset=utf-8')
        if self.path=='/assets/strata-atmosphere.png': return self.static_asset('assets/strata-atmosphere.png','image/png')
        if not self.authorized(): return self.reply(403,{'error':'Open this product through its launcher.'})
        if self.path=='/api/session':return self.reply(200,{'authenticated':True})
        if self.path=='/api/sample': return self.reply(200,json.loads((ROOT/'sample.json').read_text(encoding='utf-8')))
        return self.reply(404,{'error':'Unknown resource'})
    def do_POST(self):
        if not self.authorized(): return self.reply(403,{'error':'Local session or origin mismatch'})
        if self.path=='/api/session':
            self.issue_session=True;return self.reply(200,{'authenticated':True})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>2_000_000: return self.reply(413,{'error':'Native JSON must be under 2 MB'})
            data=json.loads(self.rfile.read(size))
            if self.path!='/api/validate': return self.reply(404,{'error':'No mutation endpoint exists'})
            errors=validate_record(data); self.reply(200,{'valid':not errors,'errors':errors,'scope':'Existing native structural validator only; no semantic truth, execution, approval or repair claim.'})
        except (ValueError,OSError,subprocess.SubprocessError) as error: self.reply(400,{'error':str(error)})
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--no-browser',action='store_true'); parser.add_argument('--port',type=int,default=CONFIG['port']); parser.add_argument('--check',action='store_true'); parser.add_argument('--serve',action='store_true',help=argparse.SUPPRESS); args=parser.parse_args()
    if args.check:
        errors=validate_record(json.loads((ROOT/'sample.json').read_text(encoding='utf-8'))); print(json.dumps({'product':CONFIG['id'],'sample_errors':errors})); return bool(errors)
    identity={'product':CONFIG['id'],'version':CONFIG['version'],'workspace':str(ROOT),'runtime_sha256':RUNTIME_SHA}
    return launch(Handler,args,identity,TOKEN,Path(__file__).resolve())
if __name__=='__main__': raise SystemExit(main())

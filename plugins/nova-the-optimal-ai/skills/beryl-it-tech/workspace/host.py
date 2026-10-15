#!/usr/bin/env python3
"""Local persistent working application with retained native record validation."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
import argparse, json, secrets, sys, tempfile, subprocess, urllib.request, webbrowser, threading
from launch_runtime import launch,RUNTIME_NONCE
import hashlib,os
ROOT=Path(__file__).resolve().parent
RUNTIME_FILES = [ROOT/name for name in ("host.py", "launch_runtime.py", "index.html", "journey.js", "desk.json", "sample.json")]
RUNTIME_FILES += [ROOT.parent/"scripts/validate_case_file.py", ROOT.parent/"schemas/it-case.schema.json"]
RUNTIME_FILES += sorted((ROOT/"assets").glob("*-surface.png"))
RUNTIME_FILES += [ROOT/"assets"/name for name in ("beryl-icon.png", "beryl.ico", "beryl.icns")]
RUNTIME_SHA=hashlib.sha256(b"".join(p.name.encode()+b"\0"+p.read_bytes() for p in RUNTIME_FILES)).hexdigest()
CONFIG=json.loads((ROOT/'desk.json').read_text(encoding='utf-8'))
TOKEN=secrets.token_urlsafe(32)
STORE=None
WRITE_LOCK=threading.Lock()
from contextlib import contextmanager
@contextmanager
def store_lock():
    with open(STORE/".save-lock","a+b") as f:
        if os.name=="nt":
            import msvcrt
            if f.tell()==0:f.write(b"0");f.flush()
            f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(f.fileno(),fcntl.LOCK_EX)
        try:yield
        finally:
            if os.name=="nt":f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f.fileno(),fcntl.LOCK_UN)
def work_revision():
    p=STORE/"work.json";return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "new"
def attachment(a):
    import base64
    if not isinstance(a,dict) or not isinstance(a.get("name"),str) or not isinstance(a.get("data"),str):raise ValueError("Invalid supporting file.")
    data=a["data"]
    if not data.startswith("data:") or ";base64," not in data:raise ValueError("Invalid attachment encoding.")
    base64.b64decode(data.split(",",1)[1],validate=True)
def reject_constant(value):raise ValueError("Non-finite numbers are not supported.")
def validate_work(v):
    if not isinstance(v,dict) or v.get("app")!="beryl-it-benchcraft" or not isinstance(v.get("projects"),list) or len(v["projects"])>200:raise ValueError("Choose a compatible workspace backup.")
    ids=set()
    for p in v["projects"]:
        if not isinstance(p,dict) or not isinstance(p.get("id"),str) or p["id"] in ids:raise ValueError("Every saved item needs a distinct identity.")
        ids.add(p["id"])
        if not p["id"] or len(p["id"])>200:raise ValueError("Invalid saved item identity.")
        if not isinstance(p.get("name"),str) or not isinstance(p.get("materials"),list):raise ValueError("Invalid saved case.")
        validate_data(p.get("record"))
        mids=set()
        for m in p["materials"]:
            attachment(m)
            if not isinstance(m.get("id"),str) or m["id"] in mids:raise ValueError("Invalid attachment identity.")
            mids.add(m["id"])
            if "text" in m and not isinstance(m["text"],str):raise ValueError("Invalid log content.")

    if v.get("active") is not None and v["active"] not in ids:raise ValueError("The selected item is missing from this backup.")
    return v
sys.path.insert(0, str(ROOT.parent / "scripts"))
from validate_case_file import validate_data, consistency_issues, load_json

def validate_record(record):
    try:
        validate_data(record)
        return []
    except (ValueError, RecursionError) as exc:
        return [str(exc)]

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,value,json_value=True):
        raw=json.dumps(value,ensure_ascii=False).encode() if json_value else value
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8' if json_value else 'text/html; charset=utf-8'); self.send_header('Cache-Control','no-store');
        if getattr(self,'issue_session',False):self.send_header('Set-Cookie',f'{self.cookie_name()}={TOKEN}; HttpOnly; SameSite=Strict; Path=/')
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"); self.end_headers(); self.wfile.write(raw)
    def cookie_name(self):
        return 'desk_'+hashlib.sha256((CONFIG['id']+'|'+str(ROOT)).encode('utf-8')).hexdigest()[:16]+'_'+str(self.server.server_port)
    def authorized(self):
        origin=f'http://127.0.0.1:{self.server.server_port}'
        cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''));credential=cookie.get(self.cookie_name());valid=self.headers.get('X-Desk-Token')==TOKEN or (credential is not None and credential.value==TOKEN)
        return self.headers.get('Host')==origin.removeprefix('http://') and self.headers.get('Origin',origin)==origin and valid
    def do_GET(self):
        if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}': return self.reply(403,{'error':'Unexpected host'})
        if self.path=='/api/health': return self.reply(200,{'product':CONFIG['id'],'version':CONFIG['version'],'workspace':str(ROOT),'mode':'persistent private workspace','data_home':str(STORE),'runtime_sha256':RUNTIME_SHA,'instance':RUNTIME_NONCE})
        if self.path=='/': return self.reply(200,(ROOT/'index.html').read_bytes(),False)
        if self.path in ('/journey.js','/journey.css','/prepared-review.html','/index.html'):
            p=ROOT/self.path.lstrip('/')
            if not p.is_file():return self.reply(404,{'error':'Missing asset'})
            raw=p.read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8' if p.suffix=='.js' else 'text/css; charset=utf-8' if p.suffix=='.css' else 'text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw);return

        icons={'/assets/beryl-icon.png':'image/png','/assets/beryl.ico':'image/x-icon','/assets/beryl.icns':'image/icns'}
        if self.path in icons:
            raw=(ROOT/self.path.lstrip('/')).read_bytes();self.send_response(200);self.send_header('Content-Type',icons[self.path]);self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if self.path in ('/assets/moss-surface.png','/assets/night-surface.png','/assets/porcelain-surface.png'):
            raw=(ROOT/self.path.lstrip('/')).read_bytes()
            self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if not self.authorized(): return self.reply(403,{'error':'Open this product through its launcher.'})
        if self.path=='/api/session':return self.reply(200,{'authenticated':True})
        if self.path=='/api/work':
            try:
                with WRITE_LOCK,store_lock():
                    p=STORE/'work.json';data=validate_work(json.loads(p.read_text(encoding='utf-8'),parse_constant=reject_constant)) if p.exists() else None;revision=work_revision()
                return self.reply(200,{'work':data,'revision':revision,'location':str(STORE)})
            except (OSError,ValueError) as error:return self.reply(500,{'error':'Saved work could not be read: '+str(error)})
        if self.path=='/api/sample': return self.reply(200,json.loads((ROOT/'sample.json').read_text(encoding='utf-8')))
        return self.reply(404,{'error':'Unknown resource'})
    def do_POST(self):
        if not self.authorized(): return self.reply(403,{'error':'Local session or origin mismatch'})
        if self.path=='/api/session':
            self.issue_session=True;return self.reply(200,{'authenticated':True})
        if self.path=='/api/work':
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=40*1024*1024:raise ValueError('Workspace exceeds 40 MB. Keep large originals separately.')
                raw=self.rfile.read(size);v=validate_work(json.loads(raw,parse_constant=reject_constant))
                with WRITE_LOCK,store_lock():
                    if self.headers.get('If-Match')!=work_revision():return self.reply(409,{'error':'Another window changed this workspace. Back up your current edits before reloading and combining changes.'})
                    fd,tmp=tempfile.mkstemp(prefix='.work-',dir=STORE)
                    try:
                        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
                        os.replace(tmp,STORE/'work.json')
                    finally:
                        if os.path.exists(tmp):os.unlink(tmp)
                return self.reply(200,{'saved':True,'revision':hashlib.sha256(raw).hexdigest()})
            except (OSError,ValueError,TypeError,KeyError,RecursionError) as error:return self.reply(400,{'error':str(error)})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>2_000_000: return self.reply(413,{'error':'Native JSON must be under 2 MB'})
            data=load_json(self.rfile.read(size))
            if self.path!='/api/validate': return self.reply(404,{'error':'No mutation endpoint exists'})
            errors=validate_record(data); self.reply(200,{'valid':not errors,'errors':errors,'consistency_issues':consistency_issues(data) if not errors else [],'scope':'Structure and bounded declared consistency only; no truth, execution, approval or repair claim.'})
        except (ValueError,OSError,subprocess.SubprocessError,RecursionError) as error: self.reply(400,{'error':str(error)})
def main():
    global STORE
    parser=argparse.ArgumentParser(); parser.add_argument('--no-browser',action='store_true'); parser.add_argument('--port',type=int,default=CONFIG['port']); parser.add_argument('--check',action='store_true'); parser.add_argument('--serve',action='store_true',help=argparse.SUPPRESS); parser.add_argument('--data-home',type=Path); args=parser.parse_args()
    if args.check:
        errors=validate_record(json.loads((ROOT/'sample.json').read_text(encoding='utf-8'))); print(json.dumps({'product':CONFIG['id'],'sample_errors':errors})); return bool(errors)
    base=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'Collaborative Dynamics'/'beryl-it-benchcraft'
    STORE=(args.data_home or Path(os.environ.get('BERYL_WORK_HOME',str(base)))).expanduser().resolve()
    try:
        STORE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryFile(dir=STORE) as f:f.write(b'write check');f.flush()
    except OSError as error:raise SystemExit('Cannot save in '+str(STORE)+': '+str(error)+'\nChoose a writable folder with --data-home. Existing work is unchanged.')
    identity={'product':CONFIG['id'],'version':CONFIG['version'],'workspace':str(ROOT),'runtime_sha256':RUNTIME_SHA,'data_home':str(STORE)}
    return launch(Handler,args,identity,TOKEN,Path(__file__).resolve())
if __name__=='__main__': raise SystemExit(main())

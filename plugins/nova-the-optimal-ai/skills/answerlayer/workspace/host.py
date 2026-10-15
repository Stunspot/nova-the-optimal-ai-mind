#!/usr/bin/env python3
"""Local persistent working application with retained native record validation."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
import argparse, json, secrets, sys, tempfile, subprocess, urllib.request, webbrowser, threading
import hashlib,os,stat
ROOT=Path(__file__).absolute().parent
def guard(path):
    path=Path(path).absolute()
    for node in [path,*path.parents]:
        value=node.lstat()
        if stat.S_ISLNK(value.st_mode) or getattr(value,'st_file_attributes',0)&1024:raise ValueError('Linked runtime refused: '+str(node))
    return path
guard(ROOT)
sys.path.insert(0,str(guard(ROOT.parent/'scripts')))
from io_contract import strict,dumps,LedgerError
from ledgerlib import validate
from launch_runtime import launch,RUNTIME_NONCE
identity=hashlib.sha256()
for current,dirs,names in os.walk(ROOT.parent,followlinks=False):
    dirs[:]=sorted(d for d in dirs if d!='__pycache__')
    for d in dirs:guard(Path(current)/d)
    for name in sorted(names):
        if name.endswith('.pyc'):continue
        path=guard(Path(current)/name)
        if not path.is_file():raise ValueError('Nonregular runtime file')
        identity.update(path.relative_to(ROOT.parent).as_posix().encode());identity.update(path.read_bytes())
RUNTIME_SHA=identity.hexdigest()
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
    if not isinstance(v,dict) or v.get("app")!="answerlayer" or not isinstance(v.get("projects"),list) or len(v["projects"])>200:raise ValueError("Choose a compatible workspace backup.")
    ids=set()
    for p in v["projects"]:
        if not isinstance(p,dict) or not isinstance(p.get("id"),str) or p["id"] in ids:raise ValueError("Every saved item needs a distinct identity.")
        ids.add(p["id"])
        if not p["id"] or len(p["id"])>200:raise ValueError("Invalid saved item identity.")
        def strings(obj,keys):
            if not isinstance(obj,dict) or any(not isinstance(obj.get(k),str) for k in keys):raise ValueError("Invalid answer fields in backup.")
        strings(p,["title","purpose","notes","nextCheck"])
        strings(p.get("baseline"),["text","confidence","asof"])
        strings(p.get("proposal"),["text","mechanism","scope","confidence","action","counterfactual","recheck"])
        if "action" in p["baseline"] and not isinstance(p["baseline"]["action"],str):raise ValueError("Invalid current practical action.")
        if "asof" in p["proposal"] and not isinstance(p["proposal"]["asof"],str):raise ValueError("Invalid proposed information cutoff.")
        if not isinstance(p.get("developments"),list) or not isinstance(p.get("history"),list):raise ValueError("Invalid answer history.")
        dids=set()
        for d in p["developments"]:
            strings(d,["id","kind","detail","source","passage","location","observed","effective","effect"])
            if d["id"] in dids or not isinstance(d.get("examined"),bool):raise ValueError("Invalid development identity or examination state.")
            dids.add(d["id"])
            if "attachment" in d:attachment(d["attachment"])
        for h in p["history"]:
            strings(h,["id","at","basis"])
            strings(h.get("before"),["text","confidence","asof"]);strings(h.get("after"),["text","confidence","asof"])
            strings(h.get("proposal"),["text","mechanism","scope","confidence","action","counterfactual","recheck"])
            if not isinstance(h.get("developments"),list):raise ValueError("Invalid historical evidence snapshot.")

    if v.get("active") is not None and v["active"] not in ids:raise ValueError("The selected item is missing from this backup.")
    return v
def validate_record(record):
    try:return validate(strict(record) if isinstance(record,str) else record)
    except (ValueError,UnicodeError,RecursionError) as error:return [str(error)]
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,value,json_value=True):
        raw=json.dumps(value,ensure_ascii=False).encode() if json_value else value
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8' if json_value else 'text/html; charset=utf-8'); self.send_header('Cache-Control','no-store');
        if getattr(self,'issue_session',False):self.send_header('Set-Cookie',f'{self.cookie_name()}={TOKEN}; HttpOnly; SameSite=Strict; Path=/')
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"); self.end_headers(); self.wfile.write(raw)
    def static_asset(self, relative, mime):
        raw=guard(ROOT/relative).read_bytes()
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
        if self.path=='/api/health': return self.reply(200,{'product':CONFIG['id'],'version':CONFIG['version'],'workspace':str(ROOT),'mode':'persistent private workspace','data_home':str(STORE),'runtime_sha256':RUNTIME_SHA,'instance':RUNTIME_NONCE})
        if self.path=='/': return self.reply(200,(ROOT/'index.html').read_bytes(),False)
        if self.path in ('/journey.js','/journey.css','/prepared-review.html','/index.html'):
            p=ROOT/self.path.lstrip('/')
            if not p.is_file():return self.reply(404,{'error':'Missing asset'})
            raw=p.read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8' if p.suffix=='.js' else 'text/css; charset=utf-8' if p.suffix=='.css' else 'text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw);return

        if self.path=='/refinement.css': return self.static_asset('refinement.css','text/css; charset=utf-8')
        if self.path=='/app.js': return self.static_asset('app.js','text/javascript; charset=utf-8')
        if self.path=='/theme.css': return self.static_asset('theme.css','text/css; charset=utf-8')
        if self.path=='/assets/strata-atmosphere.png': return self.static_asset('assets/strata-atmosphere.png','image/png')
        if self.path=='/assets/answerlayer-icon.png': return self.static_asset('assets/answerlayer-icon.png','image/png')
        if self.path=='/assets/answerlayer.ico': return self.static_asset('assets/answerlayer.ico','image/x-icon')
        if self.path=='/assets/answerlayer.icns': return self.static_asset('assets/answerlayer.icns','image/icns')
        if not self.authorized(): return self.reply(403,{'error':'Open this product through its launcher.'})
        if self.path=='/api/session':return self.reply(200,{'authenticated':True})
        if self.path=='/api/work':
            try:
                with WRITE_LOCK,store_lock():
                    p=STORE/'work.json';data=validate_work(json.loads(p.read_text(encoding='utf-8'),parse_constant=reject_constant)) if p.exists() else None;revision=work_revision()
                return self.reply(200,{'work':data,'revision':revision,'location':str(STORE)})
            except (OSError,ValueError) as error:return self.reply(500,{'error':'Saved work could not be read: '+str(error)})
        if self.path=='/api/sample': return self.static_asset('sample.json','application/json; charset=utf-8')
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
            raw=self.rfile.read(size)
            if len(raw)!=size:return self.reply(400,{'error':'Incomplete request body'})
            native_text=raw.decode('utf-8')
            if self.path!='/api/validate': return self.reply(404,{'error':'No mutation endpoint exists'})
            errors=validate_record(native_text)
            try: data=strict(native_text);fmt=data.get('format') if isinstance(data,dict) else None
            except ValueError:fmt=None
            self.reply(200,{'valid':not errors,'errors':errors,'format':fmt,'sha256':hashlib.sha256(raw).hexdigest(),'scope':'Exact submitted UTF-8 text checked for structure, reference and supplied history integrity. No prior checkpoint was supplied; history completeness, factual truth, consent, adoption and publication are not authenticated.'})
        except (ValueError,OSError,subprocess.SubprocessError) as error: self.reply(400,{'error':str(error)})
def main():
    global STORE
    parser=argparse.ArgumentParser(); parser.add_argument('--no-browser',action='store_true'); parser.add_argument('--port',type=int,default=CONFIG['port']); parser.add_argument('--check',action='store_true'); parser.add_argument('--serve',action='store_true',help=argparse.SUPPRESS); parser.add_argument('--data-home',type=Path); args=parser.parse_args()
    if args.check:
        errors=validate_record(guard(ROOT/'sample.json').read_text(encoding='utf-8-sig')); print(json.dumps({'product':CONFIG['id'],'sample_errors':errors})); return bool(errors)
    base=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'Collaborative Dynamics'/'answerlayer'
    STORE=(args.data_home or Path(os.environ.get('ANSWERLAYER_HOME',str(base)))).expanduser().resolve()
    try:
        STORE.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryFile(dir=STORE) as f:f.write(b'write check');f.flush()
    except OSError as error:raise SystemExit('Cannot save in '+str(STORE)+': '+str(error)+'\nChoose a writable folder with --data-home. Existing work is unchanged.')
    identity={'product':CONFIG['id'],'version':CONFIG['version'],'workspace':str(ROOT),'runtime_sha256':RUNTIME_SHA,'data_home':str(STORE)}
    return launch(Handler,args,identity,TOKEN,Path(__file__).resolve())
if __name__=='__main__': raise SystemExit(main())

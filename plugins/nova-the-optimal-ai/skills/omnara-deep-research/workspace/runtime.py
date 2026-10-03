"""Private loopback workspace transport and portable Open launcher (stdlib only)."""
from __future__ import annotations
import argparse, hashlib, json, os, secrets, subprocess, sys, time, urllib.request, webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

def atomic(path, content):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + secrets.token_hex(6) + '.tmp')
    try:
        with temp.open('wb') as f:
            f.write(content if isinstance(content, bytes) else content.encode('utf-8')); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

@contextmanager
def launch_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell()==0: handle.write(b'0'); handle.flush()
        handle.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX)
        try: yield
        finally:
            handle.seek(0)
            if os.name=='nt': msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(handle.fileno(),fcntl.LOCK_UN)

def launch(product, default_name, adapter, static):
    parser = argparse.ArgumentParser(description='Open '+product+' local workspace')
    parser.add_argument('--data-root', type=Path)
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    root = (args.data_root or Path(os.environ.get(product.upper().replace('-','_')+'_HOME', str(Path.home()/'Documents'/default_name)))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parent
    identity = hashlib.sha256((product+'\n'+str(source)+'\n'+str(root)).encode()).hexdigest()
    registry = root/'.workspace'/('instance-'+identity[:16]+'.json')
    def alive(record):
        try:
            req = urllib.request.Request(record['url']+'/api/health')
            with urllib.request.urlopen(req, timeout=1) as r: return json.load(r).get('identity') == identity
        except Exception: return False
    if not args.serve:
        lock_context=launch_lock(registry.with_suffix('.lock'))
        lock_context.__enter__()
        try: record = json.loads(registry.read_text()) if registry.exists() else {}
        except (ValueError,OSError): record={}
        if not alive(record):
            command = [sys.executable, '-B', str(source/'open.py'), '--serve','--data-root',str(root),'--port',str(args.port)]
            options = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.name == 'nt': options['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            else: options['start_new_session'] = True
            subprocess.Popen(command, **options)
            for _ in range(100):
                time.sleep(.1)
                try: record = json.loads(registry.read_text())
                except Exception: continue
                if alive(record): break
            else: raise SystemExit('Workspace could not start. Run Open with --serve to see the cause.')
        url = record['url']+'/#token='+record['token']
        lock_context.__exit__(None,None,None)
        if not args.no_browser: webbrowser.open(url)
        print(url); return
    token = secrets.token_urlsafe(32)
    app = adapter(root)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def respond(self, code, body, mime='application/json'):
            if not isinstance(body, bytes): body=json.dumps(body).encode() if mime=='application/json' else body.encode()
            self.send_response(code); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers(); self.wfile.write(body)
        def handle_request(self):
            host = self.headers.get('Host','')
            expected='127.0.0.1:'+str(self.server.server_port)
            if host != expected: return self.respond(403,{'error':'Loopback Host required'})
            origin = self.headers.get('Origin')
            if origin and origin != 'http://'+expected: return self.respond(403,{'error':'Foreign Origin refused'})
            path=self.path.split('?',1)[0]
            if path == '/api/health' and self.command=='GET': return self.respond(200, {'product':product,'identity':identity})
            if path.startswith('/api/'):
                if not secrets.compare_digest(self.headers.get('X-Workspace-Token',''),token): return self.respond(403,{'error':'Open the workspace through its launcher'})
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if length>16*1024*1024: raise ValueError('Request exceeds 16 MB')
                    data=json.loads(self.rfile.read(length)) if length else {}
                    result=app.request(self.command,path,data)
                    if isinstance(result, tuple): return self.respond(200,*result)
                    self.respond(200,result)
                except app.Conflict as exc: self.respond(409,{'error':str(exc)})
                except (ValueError,KeyError,OSError) as exc: self.respond(400,{'error':str(exc)})
                except Exception as exc: self.respond(500,{'error':str(exc)})
                return
            if self.command!='GET': return self.respond(405,{'error':'Method not allowed'})
            files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
            if path not in files: return self.respond(404,{'error':'Not found'})
            mime={'index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8','style.css':'text/css; charset=utf-8'}
            self.respond(200,(static/files[path]).read_bytes(),mime[files[path]])
        do_GET=handle_request
        do_POST=handle_request
    try: server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError: server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.daemon_threads=True
    atomic(registry,json.dumps({'product':product,'identity':identity,'url':'http://127.0.0.1:'+str(server.server_port),'token':token,'pid':os.getpid()}))
    if os.name!='nt': registry.chmod(0o600)
    print('Ready: http://127.0.0.1:'+str(server.server_port),flush=True)
    try: server.serve_forever()
    finally: server.server_close()

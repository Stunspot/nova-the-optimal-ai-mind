"""Private loopback workspace transport and portable Open launcher (stdlib only)."""
from __future__ import annotations
import argparse, hashlib, json, os, secrets, subprocess, sys, threading, time, urllib.request, webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from work_io import Materials,select_home

def default_data_root(default_name):
    # Nova's research campaigns are native memory-estate records, not Documents files.
    explicit=os.environ.get('OMNARA_HOME','').strip()
    if explicit:return Path(explicit).expanduser()
    data_root=os.environ.get('NOVA_DATA_ROOT','').strip()
    selectors=Path(data_root)/'estate'/'path-selectors.json' if data_root else Path(r'E:\\Indranet\\Nova\\estate\\path-selectors.json')
    try:
        values=json.loads(selectors.read_text(encoding='utf-8')).get('active_values',{})
        selected=values.get('NOVA_DATA_ROOT')
        if isinstance(selected,str) and selected.strip():
            candidate=Path(selected.strip())/'research'
            if candidate.is_dir():return candidate
    except (OSError,ValueError,TypeError):
        pass
    return Path.home()/'Documents'/default_name

from file_ops import atomic
from custody import reject_links

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
    home_override=args.data_root or (Path(os.environ[product.upper().replace('-','_')+'_HOME']).expanduser() if os.environ.get(product.upper().replace('-','_')+'_HOME','').strip() else None)
    root = reject_links(select_home(product,default_data_root(default_name),home_override))
    root.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parent
    identity = hashlib.sha256((product+'\n'+str(source)+'\n'+str(root)+'\n'+hashlib.sha256(b''.join(p.read_bytes() for p in sorted(source.glob('*')) if p.is_file())).hexdigest()).encode()).hexdigest()
    registry = root/'.workspace'/('instance-'+identity[:16]+'.json')
    def alive(record):
        try:
            req = urllib.request.Request(record['url']+'/api/health')
            with urllib.request.urlopen(req, timeout=1) as r: return json.load(r).get('identity') == identity
        except Exception: return False
    if not args.serve:
        with launch_lock(registry.with_suffix('.lock')):
            try: record = json.loads(registry.read_text()) if registry.exists() else {}
            except (ValueError,OSError): record={}
            if not alive(record):
                workspace_state=root/'.workspace';workspace_state.mkdir(parents=True,exist_ok=True)
                startup_log=workspace_state/'last-startup.log'
                command=[sys.executable,'-B',str(source/'open.py'),'--serve','--data-root',str(root),'--port',str(args.port)]
                options=dict(stdin=subprocess.DEVNULL,stderr=subprocess.STDOUT)
                if os.name=='nt':options['creationflags']=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS
                else:options['start_new_session']=True
                try:
                    with startup_log.open('w',encoding='utf-8') as output:
                        child=subprocess.Popen(command,stdout=output,**options)
                except OSError as exc:
                    startup_log.write_text('Unable to create the local service process: '+str(exc)+'\n',encoding='utf-8')
                    raise SystemExit(f'Workspace could not start. Process creation failed. Startup details are saved at {startup_log}.\n{exc}')
                deadline=time.monotonic()+30
                while True:
                    try:record=json.loads(registry.read_text()) if registry.exists() else {}
                    except (ValueError,OSError):record={}
                    if alive(record):break
                    if child.poll() is not None or time.monotonic()>=deadline:
                        timed_out=child.poll() is None and time.monotonic()>=deadline
                        if child.poll() is None:
                            child.terminate()
                            try:child.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                child.kill();child.wait(timeout=2)
                        detail=''
                        try:detail=startup_log.read_text(encoding='utf-8',errors='replace')[-6000:].strip()
                        except OSError:pass
                        reason='The local service did not become ready within 30 seconds.' if timed_out else 'The local service stopped before it became ready.'
                        message=f'Workspace could not start. {reason} Startup details are saved at {startup_log}.'
                        if detail:message+='\n\n'+detail
                        raise SystemExit(message)
                    time.sleep(.1)
            url=record['url']+'/#token='+record['token']
        if not args.no_browser:webbrowser.open(url)
        print(url);return
    token = secrets.token_urlsafe(32)
    app = adapter(root)
    materials=Materials(root,product,source/'open.py','--data-root')
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
                    if length<0 or length>45*1024*1024: raise ValueError('File exceeds 32 MB')
                    from evidence_contract import loads
                    data=loads(self.rfile.read(length).decode('utf-8')) if length else {}
                    if not isinstance(data,dict):raise ValueError('Request body must be an object')
                    if self.server.closing:return self.respond(409,{'error':'The Reading Room is closing. Reopen its shortcut.'})
                    if path=='/api/lease':
                        client=data.get('client')
                        if not isinstance(client,str) or not 1<=len(client)<=80:raise ValueError('Reconnect this Reading Room tab.')
                        self.server.clients[client]=time.monotonic();return self.respond(200,{'connected':True})
                    if path=='/api/exit':
                        self.server.closing=True
                        threading.Thread(target=self.server.shutdown,daemon=True).start()
                        return self.respond(200,{'closed':True})
                    result=materials.handle(path,data) if path in {'/api/material','/api/material-get','/api/browse','/api/location'} else app.request(self.command,path,data)
                    if isinstance(result, tuple): return self.respond(200,*result)
                    self.respond(200,result)
                except app.Conflict as exc: self.respond(409,{'error':str(exc)})
                except (ValueError,KeyError,OSError) as exc: self.respond(400,{'error':str(exc)})
                except Exception as exc: self.respond(500,{'error':str(exc)})
                return
            if self.command!='GET': return self.respond(405,{'error':'Method not allowed'})
            files={'/work.js':'work.js','/work.css':'work.css','/common.js':'common.js','/advanced':'advanced.html','/':'reading-room.html','/reading-room':'reading-room.html','/app.js':'app.js','/style.css':'style.css','/skins.css':'skins.css',
                   '/reading-room.html':'reading-room.html','/reading-room.js':'reading-room.js','/reading-room.css':'reading-room.css',
                   '/assets/tracework.png':'assets/tracework.png',
                   '/assets/survey-folio.png':'assets/survey-folio.png',
                   '/assets/proof-cabinet.png':'assets/proof-cabinet.png',
                   '/favicon.ico':'assets/omnara.ico','/assets/omnara.ico':'assets/omnara.ico',
                   '/assets/omnara-icon.png':'assets/omnara-icon.png'}
            if path not in files: return self.respond(404,{'error':'Not found'})
            mime={'work.js':'text/javascript; charset=utf-8','common.js':'text/javascript; charset=utf-8','work.css':'text/css; charset=utf-8','advanced.html':'text/html; charset=utf-8','index.html':'text/html; charset=utf-8','reading-room.html':'text/html; charset=utf-8','reading-room.js':'text/javascript; charset=utf-8','reading-room.css':'text/css; charset=utf-8','app.js':'text/javascript; charset=utf-8',
                  'style.css':'text/css; charset=utf-8','skins.css':'text/css; charset=utf-8',
                  'assets/omnara.ico':'image/x-icon'}
            file=files[path]
            self.respond(200,(static/file).read_bytes(),mime.get(file,'image/png'))
        do_GET=handle_request
        do_POST=handle_request
    try: server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError: server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.daemon_threads=True
    server.clients={}; server.closing=False; server.started=time.monotonic()
    atomic(registry,json.dumps({'product':product,'identity':identity,'url':'http://127.0.0.1:'+str(server.server_port),'token':token,'pid':os.getpid()}))
    if os.name!='nt': registry.chmod(0o600)
    print('Ready: http://127.0.0.1:'+str(server.server_port),flush=True)
    def watch_clients():
        while not server.closing:
            time.sleep(5)
            if time.monotonic()-max(server.clients.values(),default=server.started)>90:
                server.closing=True;server.shutdown();return
    threading.Thread(target=watch_clients,daemon=True).start()
    try: server.serve_forever()
    finally: server.server_close()







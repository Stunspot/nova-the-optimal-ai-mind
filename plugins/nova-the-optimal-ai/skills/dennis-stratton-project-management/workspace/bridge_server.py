"""Loopback-only, read-only project route with a separate local reading position."""
from __future__ import annotations
import argparse, json, mimetypes, os, secrets, socket, subprocess, sys, threading, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, quote
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge_runtime import ROOT, PRODUCT, BUILD, safe_data_home, project_list, get_project, load_view, save_view, source_info, source_bytes, DEMO_ID, _project_key
from storage_io import atomic, lock
ASSETS={"index.html","bridge.js","bridge.css","assets/dennis.png","assets/dennis.ico"}

class LocalServer(ThreadingHTTPServer):
    request_queue_size=32; allow_reuse_address=False; allow_reuse_port=False
    def server_bind(self):
        if hasattr(socket,"SO_EXCLUSIVEADDRUSE"): self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def host(self): return self.headers.get("Host")=="127.0.0.1:"+str(self.server.server_port)
    def auth(self): return self.host() and self.headers.get("Origin",self.server.url.rstrip("/"))==self.server.url.rstrip("/") and self.headers.get("X-Companion-Token")==self.server.token
    def reply(self,value,status=200,kind="application/json; charset=utf-8",download=None):
        raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode("utf-8")
        self.send_response(status);self.send_header("Content-Type",kind);self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.send_header("Referrer-Policy","no-referrer");self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if download:self.send_header("Content-Disposition","attachment; filename*=UTF-8''"+quote(download))
        self.end_headers()
        try:self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError):pass
    def json_body(self):
        if self.headers.get("Content-Type","").split(";")[0]!="application/json": raise ValueError("Use a Project Bridge control.")
        size=int(self.headers.get("Content-Length","0"))
        if not 0<size<=65536: raise ValueError("This local request is too large.")
        value=json.loads(self.rfile.read(size))
        if not isinstance(value,dict): raise ValueError("Unsupported request.")
        return value
    def do_GET(self):
        if not self.host():return self.reply({"error":"Open Project Bridge from its local launcher."},403)
        u=urlsplit(self.path); route=u.path; q=parse_qs(u.query)
        if route=="/health":return self.reply(self.server.identity)
        if route.startswith("/api/") and not self.auth():return self.reply({"error":"Reopen Project Bridge to reconnect this tab."},403)
        if route=="/api/state":
            try:
                value=project_list(self.server.store);value["view"]=load_view(self.server.home);value["store_source"]=self.server.store_source
                return self.reply(value)
            except (OSError,ValueError,KeyError) as e:return self.reply({"error":"The project-record estate could not be read. Your native records were not changed. "+str(e)},500)
        if route=="/api/project":
            try:
                project=get_project(self.server.store,q.get("id",[""])[0])
                return self.reply({"project":project} if project else {"error":"That project is no longer available. Refresh the portfolio."},200 if project else 404)
            except (OSError,ValueError,KeyError) as e:return self.reply({"error":"The selected project could not be read. "+str(e)},500)
        if route=="/api/demo":
            try:
                project=get_project(self.server.store,DEMO_ID)
                return self.reply({"project":project} if project else {"error":"The fictional walkthrough is unavailable."},200 if project else 404)
            except (OSError,ValueError,KeyError) as e:return self.reply({"error":"The fictional walkthrough could not be read. "+str(e)},500)
        if route=="/api/history":
            project_id=q.get("id",[""])[0]
            try:
                path=self.server.home/"snapshots"/(_project_key(project_id)+".json")
                value=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"previous":None,"latest":None}
                return self.reply(value)
            except (OSError,ValueError) as e:return self.reply({"error":"The local comparison snapshot could not be read. "+str(e)},500)
        if route=="/api/source":
            try:return self.reply(source_info(self.server.store,q.get("project",[""])[0],q.get("evidence",[""])[0]))
            except (OSError,ValueError,KeyError) as e:return self.reply({"kind":"unavailable","reason":str(e)},404)
        if route=="/api/source-download":
            try:
                name,raw=source_bytes(self.server.store,q.get("project",[""])[0],q.get("evidence",[""])[0])
                kind=mimetypes.guess_type(name)[0] or "application/octet-stream"
                return self.reply(raw,kind=kind,download=name)
            except (OSError,ValueError,KeyError) as e:return self.reply({"error":str(e)},404)
        name=route.lstrip("/") or "index.html"
        if name not in ASSETS:return self.reply({"error":"Page not found."},404)
        try:return self.reply((ROOT/name).read_bytes(),kind=mimetypes.guess_type(name)[0] or "application/octet-stream")
        except OSError:return self.reply({"error":"This Project Bridge asset is unavailable. Preserve the project records before repair."},404)
    def do_POST(self):
        if not self.auth():return self.reply({"error":"Reopen Project Bridge from its local launcher."},403)
        path=urlsplit(self.path).path; held=False
        try:
            value=self.json_body()
            if path=="/api/lease":
                client=value.get("client","")
                if not isinstance(client,str) or not 1<=len(client)<=80:raise ValueError("Reconnect this tab.")
                with self.server.lifecycle:
                    if self.server.closing:return self.reply({"error":"Project Bridge is closing. Reopen its launcher."},409)
                    self.server.clients[client]=time.monotonic()
                return self.reply({"connected":True})
            if path=="/api/exit":
                with self.server.lifecycle:
                    if self.server.active:return self.reply({"error":"A reading-position save is finishing. Wait briefly, then Exit."},409)
                    self.server.closing=True
                threading.Thread(target=self.server.shutdown,daemon=True).start();return self.reply({"closed":True})
            with self.server.lifecycle:
                if self.server.closing:return self.reply({"error":"Project Bridge is closing. Reopen its launcher."},409)
                if self.server.active:return self.reply({"error":"Wait for the current reading-position save to finish."},409)
                self.server.active=True;held=True
            if path=="/api/view":
                with lock(self.server.home/".reading-position.lock"):
                    return self.reply(save_view(self.server.home,self.server.store,value))
            if path=="/api/pick-store":
                proc=subprocess.Popen([sys.executable,"-B",str(ROOT/"pick_folder.py"),str(self.server.store)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,creationflags=0x08000000 if os.name=="nt" else 0)
                try:out,err=proc.communicate(timeout=180)
                except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5);raise ValueError("Folder selection timed out. Try again or relaunch with --store.")
                if proc.returncode:raise ValueError("The folder chooser could not open. Relaunch with --store <folder>.")
                selected=out.decode("utf-8-sig").strip()
                if not selected:return self.reply({"cancelled":True})
                selected_path=Path(selected).resolve(strict=False)
                with lock(self.server.home/".reading-position.lock"):
                    atomic(self.server.home/"selected-store.json",{"path":str(selected_path),"selected_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
                    self.server.store=selected_path;self.server.store_source="explicit-folder-selection"
                return self.reply({"selected":str(selected_path)})
            return self.reply({"error":"Action not found. Project Bridge does not edit native project records."},404)
        except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as e:return self.reply({"error":str(e)},400)
        finally:
            if held:
                with self.server.lifecycle:self.server.active=False

def main():
    p=argparse.ArgumentParser();p.add_argument("--store",type=Path,required=True);p.add_argument("--store-source",default="explicit");p.add_argument("--data-home",type=Path,required=True);p.add_argument("--ready-file",type=Path,required=True);p.add_argument("--port",type=int,default=0);a=p.parse_args()
    home=safe_data_home(a.data_home,ROOT.parent)
    if not home.is_dir():raise SystemExit("The selected Project Bridge preferences folder is unavailable.")
    with lock(home/".listener.lock",False):
        try:server=LocalServer(("127.0.0.1",a.port),Handler)
        except OSError:server=LocalServer(("127.0.0.1",0),Handler)
        with server:
            server.daemon_threads=True;server.home=home;server.store=a.store.resolve(strict=False);server.store_source=a.store_source;server.token=secrets.token_urlsafe(32);server.url="http://127.0.0.1:"+str(server.server_port)+"/";server.identity={"product":PRODUCT,"build":BUILD,"home":str(home),"store":str(server.store),"nonce":secrets.token_hex(16),"protocol":1};server.clients={};server.active=False;server.closing=False;server.lifecycle=threading.Lock()
            ready={**server.identity,"pid":os.getpid(),"url":server.url,"token":server.token};atomic(home/"instance.json",ready);atomic(a.ready_file,ready);started=time.monotonic()
            def watch():
                while True:
                    time.sleep(5)
                    with server.lifecycle:
                        if server.closing:return
                        if server.active or time.monotonic()-max(server.clients.values(),default=started)<=90:continue
                        server.closing=True
                    server.shutdown();return
            threading.Thread(target=watch,daemon=True).start()
            try:server.serve_forever(poll_interval=.2)
            finally:
                try:
                    current=json.loads((home/"instance.json").read_text(encoding="utf-8"))
                    if current.get("nonce")==server.identity["nonce"]:(home/"instance.json").unlink()
                except (OSError,ValueError):pass
if __name__=="__main__":main()







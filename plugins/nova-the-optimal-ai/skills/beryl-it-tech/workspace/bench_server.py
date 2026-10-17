"""Beryl loopback service. The sole execution route is the fixed Windows observation."""
import argparse,base64,hashlib,json,mimetypes,os,secrets,socket,subprocess,sys,tempfile,threading,time,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs,quote
from bench_store import ROOT,PRODUCT,BUILD,STORE,load,public_state,import_bytes,checked_home,sha,source,append_source
from storage_io import atomic,lock
from owned_process import OwnedProcess
ASSETS={'index.html','bench.js','bench.css','assets/beryl.ico','assets/beryl-icon.png','assets/moss-surface.png','assets/night-surface.png','assets/porcelain-surface.png'}
class LocalServer(ThreadingHTTPServer):
 allow_reuse_address=False;allow_reuse_port=False;daemon_threads=True
 def server_bind(self):
  if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
  super().server_bind()
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def valid_host(self):return self.headers.get('Host')=='127.0.0.1:'+str(self.server.server_port)
 def auth(self):return self.valid_host() and self.headers.get('Origin',self.server.url.rstrip('/'))==self.server.url.rstrip('/') and self.headers.get('X-Companion-Token')==self.server.token
 def reply(self,value,status=200,kind='application/json; charset=utf-8',download=None):
  raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
  if download:self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(download))
  self.end_headers()
  try:self.wfile.write(raw)
  except (BrokenPipeError,ConnectionResetError):pass
 def do_GET(self):
  if not self.valid_host():return self.reply({'error':'Open Beryl from its local shortcut.'},403)
  path=urlsplit(self.path).path
  if path=='/health':return self.reply(self.server.identity)
  if path=='/api/state':
   if not self.auth():return self.reply({'error':'Reopen the Beryl shortcut to reconnect.'},403)
   try:return self.reply({'work':public_state(self.server.home),'job':self.server.job,'home':str(self.server.home),'bridge':str(ROOT/'bench_store.py'),'guide':str(ROOT/'HOST-PATHS.md'),'build':BUILD,'windows':os.name=='nt'})
   except Exception as e:return self.reply({'error':str(e)},500)
  if path.startswith(('/original/','/preview/')):
   if parse_qs(urlsplit(self.path).query).get('token',[''])[0]!=self.server.token:return self.reply({'error':'Reopen Beryl to access this original.'},403)
   sid=path.split('/')[-1];s=next((s for s in load(self.server.home)['sources'] if s['id']==sid),None)
   if not s:return self.reply({'error':'This original is not in your selected material.'},404)
   p=self.server.home/'originals'/sid
   if not p.is_file() or sha(p.read_bytes())!=sid:return self.reply({'error':'The original is missing or changed. Keep your saved folder and recover the original.'},409)
   if path.startswith('/preview/'):
    if not s['image_type']:return self.reply({'error':'No image preview is available.'},404)
    return self.reply(p.read_bytes(),kind=s['image_type'])
   return self.reply(p.read_bytes(),kind='application/octet-stream',download=s['name'])
  name=path.lstrip('/') or 'index.html'
  if name not in ASSETS:return self.reply({'error':'Page not found.'},404)
  return self.reply((ROOT/name).read_bytes(),kind=mimetypes.guess_type(name)[0] or 'application/octet-stream')
 def do_POST(self):
  if not self.auth():return self.reply({'error':'Reopen Beryl to reconnect to your local material.'},403)
  try:
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=17*1024*1024:raise ValueError('Choose a file smaller than 12 MB.')
   v=json.loads(self.rfile.read(n));path=urlsplit(self.path).path
   if not isinstance(v,dict):raise ValueError('This action needs an object.')
   if self.server.closing:return self.reply({'error':'Beryl is closing. Reopen the shortcut.'},409)
   if path=='/api/lease':
    client=v.get('client')
    if not isinstance(client,str) or not 1<=len(client)<=80:raise ValueError('Reconnect this tab.')
    self.server.clients[client]=time.monotonic();return self.reply({'connected':True})
   if path=='/api/view':
    view={k:str(v.get(k,''))[:300] for k in ['route','theme','investigation','revision','hypothesis','left','right','source','query','scroll']}
    with lock(self.server.home/'.data.lock'):
     data=load(self.server.home);data['view']=view;atomic(self.server.home/STORE,data)
    return self.reply({'saved':True})
   if path=='/api/cancel':
    request=v.get('request')
    if not isinstance(request,str) or not 1<=len(request)<=80:raise ValueError('Choose Cancel for the active observation.')
    with self.server.publication:
     self.server.cancel_requests.add(request)
     active=self.server.active and self.server.job.get('request')==request
     if active:
      self.server.cancelled.set()
      if self.server.worker:self.server.worker.cancel()
    return self.reply({'cancelled':active,'request':request})
   if path in ['/api/observe','/api/import']:
    with self.server.publication:
     if self.server.closing or not self.server.admission.acquire(False):return self.reply({'error':'Wait for the current operation or cancel the observation.'},409)
     self.server.active=True;self.server.cancelled.clear()
    try:
     if path=='/api/import':
      raw=base64.b64decode(v.get('base64',''),validate=True);result=import_bytes(self.server.home,str(v.get('name','')),raw);return self.reply(result)
     request=v.get('request')
     if not isinstance(request,str) or not 1<=len(request)<=80:raise ValueError('Start a new observation.')
     self.server.job={'state':'observing','request':request,'started':time.time()}
     with self.server.publication:
      if request in self.server.cancel_requests:raise ValueError('Observation cancelled. No sample was saved.')
      self.server.worker=OwnedProcess([sys.executable,'-B',str(ROOT/'observe_windows.py')],cwd=tempfile.gettempdir(),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE);proc=self.server.worker.process
     try:out,err=proc.communicate(timeout=12)
     except subprocess.TimeoutExpired:
      self.server.worker.cancel();proc.communicate();raise ValueError('Windows did not return within 12 seconds. No sample was saved. Try again or ask Beryl about this limitation.')
     with self.server.publication:
      if self.server.cancelled.is_set() or request in self.server.cancel_requests or self.server.closing:raise ValueError('Observation cancelled. No sample was saved.')
      if proc.returncode:raise ValueError('The observation could not finish. No sample was saved. Reopen Beryl or use its local assistant path.')
      result=json.loads(out)
      if result.get('method')!='windows-bounded-observation/v1' or not all(k in result for k in ['cpu','memory','disk','power','started_at','ended_at']):raise ValueError('The observation was incomplete. No sample was saved.')
      result['id']=uuid.uuid4().hex
      with lock(self.server.home/'.data.lock'):
       data=load(self.server.home)
       original=source(self.server.home,'Windows observation '+result['started_at'].replace(':','-')+'.json',json.dumps(result,ensure_ascii=False,indent=2).encode(),'fixed Windows observation')
       append_source(data,original);result['source_id']=original['id'];data['samples'].append(result);atomic(self.server.home/STORE,data)
      self.server.job={'state':'complete','request':request,'sample':result['id']};return self.reply({'sample':result['id']})
    except Exception as e:
     self.server.job={'state':'cancelled' if self.server.cancelled.is_set() or v.get('request') in self.server.cancel_requests else 'failed','message':str(e)};return self.reply({'error':str(e)},400)
    finally:
     with self.server.publication:
      if self.server.worker:self.server.worker.close()
      self.server.worker=None;self.server.active=False;self.server.admission.release()
   if path=='/api/exit':
    with self.server.publication:
     if self.server.active:return self.reply({'error':'An operation is running. Cancel the observation, or wait for the file to finish, then Exit.'},409)
     self.server.closing=True
    threading.Thread(target=self.server.shutdown,daemon=True).start();return self.reply({'closed':True})
   return self.reply({'error':'Action not found. This app cannot run prepared commands.'},404)
  except Exception as e:return self.reply({'error':str(e)},400)

def main():
 p=argparse.ArgumentParser();p.add_argument('--data-home',type=Path,required=True);p.add_argument('--ready-file',type=Path,required=True);p.add_argument('--port',type=int,default=0);a=p.parse_args();home=checked_home(a.data_home)
 with lock(home/'.writer.lock',False):
  try:server=LocalServer(('127.0.0.1',a.port),Handler)
  except OSError:server=LocalServer(('127.0.0.1',0),Handler)
  with server:
   server.home=home;server.url='http://127.0.0.1:'+str(server.server_port)+'/';server.token=secrets.token_urlsafe(32)
   server.identity={'product':PRODUCT,'build':BUILD,'home':str(home),'nonce':secrets.token_hex(16),'protocol':1}
   server.clients={};server.active=False;server.closing=False;server.worker=None;server.admission=threading.Lock();server.publication=threading.Lock();server.cancelled=threading.Event();server.cancel_requests=set();server.job={}
   ready={**server.identity,'pid':os.getpid(),'url':server.url,'token':server.token};atomic(home/'instance.json',ready);atomic(a.ready_file,ready);started=time.monotonic()
   def watch():
    while not server.closing:
     time.sleep(5)
     if not server.active and time.monotonic()-max(server.clients.values(),default=started)>90:
      server.closing=True;server.shutdown();return
   threading.Thread(target=watch,daemon=True).start()
   try:server.serve_forever(poll_interval=.2)
   finally:
    if server.worker:
     server.worker.cancel();server.worker.process.wait(timeout=5);server.worker.close()
    current=json.loads((home/'instance.json').read_text('utf-8')) if (home/'instance.json').exists() else {}
    if current.get('nonce')==server.identity['nonce']:(home/'instance.json').unlink(missing_ok=True)
if __name__=='__main__':main()

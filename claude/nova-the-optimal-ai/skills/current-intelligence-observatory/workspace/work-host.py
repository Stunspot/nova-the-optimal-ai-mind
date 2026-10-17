"""Local product workspace with persistent private work, independent of browser ports."""
import argparse,json,os,secrets,sys,tempfile,threading,webbrowser,hashlib,difflib
sys.dont_write_bytecode=True
from work_io import Materials,select_home
from contextlib import contextmanager
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit,unquote,parse_qs
ROOT=Path(__file__).resolve().parent
PRODUCT='current-intelligence-observatory'
MAX=48*1024*1024
@contextmanager
def lock_store(store):
 with open(store/'.save-lock','a+b') as f:
  if os.name=='nt':
   import msvcrt
   if f.tell()==0:f.write(b'0');f.flush()
   f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_LOCK,1)
  else:
   import fcntl
   fcntl.flock(f.fileno(),fcntl.LOCK_EX)
  try:yield
  finally:
   if os.name=='nt':f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
   else:fcntl.flock(f.fileno(),fcntl.LOCK_UN)
def revision(store):
 p=store/'work.json';return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'new'
def validate_work(v):
 if not isinstance(v,dict) or v.get('app')!=PRODUCT or not isinstance(v.get('projects'),list):raise ValueError('This working copy belongs to a different app.')
 ids=set()
 for project in v['projects']:
  if not isinstance(project,dict) or not isinstance(project.get('id'),str) or project['id'] in ids or not isinstance(project.get('title'),str):raise ValueError('A project in this working copy is incomplete.')
  ids.add(project['id'])
  arrays=['materials','claims','events','explanations']
  for name in arrays:
   if not isinstance(project.get(name),list) or any(not isinstance(row,dict) for row in project[name]):raise ValueError('This working copy has invalid '+name+'.')
  for row in project['materials']:
   if not all(isinstance(row.get(k,''),str) for k in ['key','name','id','text','note','mime','original']):raise ValueError('A source in this working copy is incomplete.')
  for claim in project['claims']:
   if not all(isinstance(claim.get(k),str) for k in ['id','text','kind','limit']) or not isinstance(claim.get('links'),list):raise ValueError('A claim in this working copy is incomplete.')
   for link in claim['links']:
    if not isinstance(link,dict) or not all(isinstance(link.get(k),str) for k in ['id','source','ref','relation','quote','locator','reason']):raise ValueError('An evidence connection is incomplete.')
  if PRODUCT=='insurance-claim-builder':
   for row in project['items']:
    if type(row.get('unit')) is not int or type(row.get('quantity')) is not int or not 0<=row['unit']<=10**12 or not 1<=row['quantity']<=100000:raise ValueError('A requested item has invalid arithmetic.')
   for row in project['payments']+project['adjustments']:
    if type(row.get('amount')) is not int or not 0<=row['amount']<=10**12:raise ValueError('A payment or adjustment has an invalid amount.')
   if sum(row['unit']*row['quantity'] for row in project['items'])>2**53-1:raise ValueError('The requested total is too large for exact arithmetic.')
 return v

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,data,status=200,kind="application/json; charset=utf-8",sandbox=False):
  raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
  self.send_response(status);self.send_header("Content-Type",kind);self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");
  if sandbox:self.send_header("Content-Security-Policy","sandbox; default-src 'none'; style-src 'unsafe-inline'")
  self.end_headers()
  if self.command!="HEAD":self.wfile.write(raw)
 def valid_host(self):
  return self.headers.get('Host') in {'127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port)}
 def do_HEAD(self):self.do_GET()
 def do_GET(self):
  if not self.valid_host():return self.reply({"error":"Local workspace only"},403)
  path=unquote(urlsplit(self.path).path)
  if path=="/api/work":
   try:
    with self.server.write_lock,lock_store(self.server.store):
     p=self.server.store/"work.json";raw=p.read_bytes() if p.exists() else None
     work=json.loads(raw) if raw else None;rev=hashlib.sha256(raw).hexdigest() if raw else "new"
    return self.reply({"work":work,"token":self.server.token,"location":str(self.server.store),"product":PRODUCT,"revision":rev})
   except (OSError,ValueError) as e:return self.reply({"error":"Your saved work could not be read: "+str(e)},500)
  if path=="/api/original":
   query=parse_qs(urlsplit(self.path).query)
   if query.get('token',[''])[0]!=self.server.token:return self.reply({'error':'Reconnect to your workspace'},403)
   key=query.get('id',[''])[0]
   if len(key)!=64 or any(c not in '0123456789abcdef' for c in key):return self.reply({'error':'Invalid original'},400)
   try:
    p=self.server.store/'.materials'/key;meta=json.loads(p.with_suffix('.meta').read_text('utf-8'))
    import mimetypes
    kind=mimetypes.guess_type(meta['name'])[0] or 'application/octet-stream'
    if kind not in {'application/pdf','image/png','image/jpeg','image/gif','image/webp','text/plain'}:kind='application/octet-stream'
    return self.reply(p.read_bytes(),kind=kind,sandbox=True)
   except (OSError,ValueError):return self.reply({'error':'Original not found in this work folder'},404)
  if path=="/health":return self.reply({"product":PRODUCT,"source":str(ROOT)})
  name=path.lstrip('/') or 'index.html';p=(ROOT/name).resolve()
  if not p.is_relative_to(ROOT) or p.suffix.lower() not in {'.json','.html','.js','.css','.png','.jpg','.jpeg','.svg','.ico','.woff2'} or not p.is_file():return self.reply({"error":"Not found"},404)
  try:
   import mimetypes
   return self.reply(p.read_bytes(),kind=mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
  except OSError:return self.reply({"error":"This page asset could not be read"},500)
 def do_POST(self):
  if not self.valid_host():return self.reply({'error':'Local workspace only'},403)
  if self.headers.get('X-Work-Token')!=self.server.token:return self.reply({"error":"Reload this page to reconnect to your workspace."},403)
  path=urlsplit(self.path).path
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=MAX:raise ValueError('This workspace is too large. Download your working copy and start a separate workspace for additional work.')
   raw=self.rfile.read(size);v=json.loads(raw)
   if path=='/api/validate':
    validate_work(v);return self.reply({'valid':True})
   if path=='/api/compare':
    a=str(v.get('before','')).splitlines();b=str(v.get('after','')).splitlines()
    if len(a)>12000 or len(b)>12000:raise ValueError('Compare selected sections of these documents, up to 12,000 lines each.')
    matcher=difflib.SequenceMatcher(None,a,b,autojunk=True)
    return self.reply({'changes':[{'kind':tag,'before':a[i:j],'after':b[k:l]} for tag,i,j,k,l in matcher.get_opcodes() if tag!='equal']})
   if path in {'/api/location','/api/browse','/api/material','/api/material-get'}:
    return self.reply(Materials(self.server.store,PRODUCT,ROOT/'launch.py','--data-home').handle(path,v))
   if path!='/api/work':return self.reply({'error':'Not found'},404)
   validate_work(v)
   with self.server.write_lock,lock_store(self.server.store):
    if self.headers.get('If-Match')!=revision(self.server.store):return self.reply({"error":"This workspace changed in another window. Download your working copy, then reload before combining your edits."},409)
    fd,tmp=tempfile.mkstemp(prefix='.work-',suffix='.tmp',dir=self.server.store)
    try:
     with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
     os.replace(tmp,self.server.store/'work.json')
    finally:
     if os.path.exists(tmp):os.unlink(tmp)
   return self.reply({"saved":True,"revision":hashlib.sha256(raw).hexdigest()})
  except Exception as e:return self.reply({"error":"Could not complete that action: "+str(e)},400)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=0);ap.add_argument('--data-home',type=Path,required=True);ap.add_argument('--ready-file',type=Path,required=True);a=ap.parse_args()
 store=a.data_home
 with ThreadingHTTPServer(('127.0.0.1',a.port),Handler) as server:
  server.store=store;server.token=secrets.token_urlsafe(32);server.write_lock=threading.Lock()
  url='http://127.0.0.1:'+str(server.server_port)+'/'
  a.ready_file.write_text(json.dumps({'url':url,'product':PRODUCT,'data_home':str(store),'pid':os.getpid()}),encoding='utf-8')
  try:server.serve_forever()
  except KeyboardInterrupt:pass
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Registry-mediated read-only knowledge display; no owner data persistence."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
import argparse,json,secrets,subprocess,sys,webbrowser,urllib.request,threading
from launch_runtime import launch,RUNTIME_NONCE
import hashlib
ROOT=Path(__file__).resolve().parent
RUNTIME_SHA=hashlib.sha256(Path(__file__).read_bytes()+(ROOT/"launch_runtime.py").read_bytes()).hexdigest()
TOKEN=secrets.token_urlsafe(32)
PRODUCT='nova-knowledge-desk';VERSION='0.3.0'
OPS=None;ESTATE=None
ALLOWED_ACTIONS={'status','notes','search','pins','people'}
def read_owner(action,payload):
    if action not in ALLOWED_ACTIONS: raise ValueError('Unsupported read; mutation is not exposed')
    scope=['public','personal']+(['private'] if payload.get('include_private') is True else [])
    query=payload.get('query','')
    if not isinstance(query,str) or len(query)>2000: raise ValueError('Query must be under 2,000 characters')
    if action=='status': command=['run','--root',str(ESTATE),'commonplace','--','status','--json'];data=None
    elif action=='notes': command=['run','--root',str(ESTATE),'commonplace','--','list','--stdin-json','--json'];data={'allowed_sensitivities':scope}
    elif action=='search': command=['run','--root',str(ESTATE),'commonplace','--','search','--stdin-json','--json'];data={'query':query,'mode':'lexical','allowed_sensitivities':scope,'limit':30,'graph_hops':0,'allow_degraded':False}
    elif action=='pins':
        command=['run','--root',str(ESTATE),'corkboard','--','list','--stdin-json','--json'];data={}
        project=payload.get('project','')
        if not isinstance(project,str) or len(project)>200: raise ValueError('Project must be under 200 characters')
        if payload.get('all_projects') is True: data={'all_projects':True}
        elif project.strip(): data={'project':project.strip()}
    else:
        if not query.strip(): raise ValueError('Enter a distinctive name or context to query people; no automatic dossier sweep')
        command=['run','--root',str(ESTATE),'commonplace','--','federated-search','--stdin-json','--json'];data={'query':query,'owners':['Dunbar'],'commonplace_mode':'lexical','allowed_sensitivities':scope,'limit':15,'graph_hops':0,'timeout_ms':10000,'allow_degraded':False}
    result=subprocess.run([sys.executable,'-B','-X','utf8',str(OPS),*command],input=json.dumps(data,ensure_ascii=False) if data is not None else None,capture_output=True,text=True,encoding='utf-8',timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if len(result.stdout.encode('utf-8'))>2_000_000: raise ValueError('Owner response exceeded display bound; narrow the request')
    try: native=json.loads(result.stdout)
    except ValueError: native={'status':'unavailable','reason':'Native owner did not return JSON','exit_code':result.returncode,'diagnostic':result.stderr[:1000]}
    return {'action':action,'read_only':True,'scope':scope,'exit_code':result.returncode,'native':native,'estate':str(ESTATE),'launcher':str(OPS),'observed_status':'returned' if result.returncode==0 else 'owner-error'}
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,value,html=False):
        raw=value if html else json.dumps(value,ensure_ascii=False).encode('utf-8');self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8');self.send_header('Cache-Control','no-store');
        if getattr(self,'issue_session',False):self.send_header('Set-Cookie',f'{self.cookie_name()}={TOKEN}; HttpOnly; SameSite=Strict; Path=/')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");self.end_headers();self.wfile.write(raw)
    def cookie_name(self):
        return 'desk_'+hashlib.sha256((PRODUCT+'|'+str(ROOT)+'|'+str(ESTATE)+'|'+str(OPS)).encode('utf-8')).hexdigest()[:16]+'_'+str(self.server.server_port)
    def authorized(self):
        origin=f'http://127.0.0.1:{self.server.server_port}'
        cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''));credential=cookie.get(self.cookie_name());valid=self.headers.get('X-Desk-Token')==TOKEN or (credential is not None and credential.value==TOKEN)
        return self.headers.get('Host')==origin.removeprefix('http://') and self.headers.get('Origin',origin)==origin and valid
    def do_GET(self):
        if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':return self.reply(403,{'error':'Unexpected host'})
        if self.path=='/api/health':return self.reply(200,{'product':PRODUCT,'version':VERSION,'workspace':str(ROOT),'read_only':True,'estate':str(ESTATE),'operations':str(OPS),'runtime_sha256':RUNTIME_SHA,'instance':RUNTIME_NONCE})
        if self.path=='/':return self.reply(200,(ROOT/'index.html').read_bytes(),True)
        if self.path=='/api/session':return self.reply(200,{'authenticated':True}) if self.authorized() else self.reply(403,{'error':'Open this product through its launcher.'})
        return self.reply(404,{'error':'No implicit read or write'})
    def do_POST(self):
        if not self.authorized():return self.reply(403,{'error':'Local session or origin mismatch'})
        if self.path=='/api/session':
            self.issue_session=True;return self.reply(200,{'authenticated':True})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>10000:return self.reply(413,{'error':'Request exceeds read bound'})
            payload=json.loads(self.rfile.read(size))
            if self.path!='/api/read' or not isinstance(payload,dict):return self.reply(404,{'error':'Only bounded owner reads are supported'})
            self.reply(200,read_owner(payload.get('action'),payload))
        except (ValueError,OSError,subprocess.SubprocessError) as e:self.reply(400,{'error':str(e)})
def main():
    global OPS,ESTATE
    parser=argparse.ArgumentParser();parser.add_argument('--nova-operations',type=Path);parser.add_argument('--estate-root',type=Path);parser.add_argument('--port',type=int,default=8873);parser.add_argument('--no-browser',action='store_true');parser.add_argument('--serve',action='store_true',help=argparse.SUPPRESS);args=parser.parse_args()
    OPS=args.nova_operations or ROOT.parent.parent/'nova-operations/scripts/nova_estate.py'
    OPS=OPS.resolve()
    if not OPS.is_file() or OPS.name!='nova_estate.py':parser.error('Pass --nova-operations with the canonical Nova Operations nova_estate.py. No direct owner-store fallback exists.')
    if args.estate_root:ESTATE=args.estate_root.resolve()
    else:
        status=subprocess.run([sys.executable,'-B','-X','utf8',str(OPS),'status'],capture_output=True,text=True,encoding='utf-8',timeout=20)
        try:
            native=json.loads(status.stdout); selected=native.get('root') or native.get('data_root') or native.get('estate_root');ESTATE=Path(selected).resolve() if selected else None
        except (ValueError,TypeError):ESTATE=None
        if ESTATE is None:parser.error('Pass --estate-root for the approved existing estate; no initialization is available.')
    registry=ESTATE/'estate/path-selectors.json'
    try:
        selectors=json.loads(registry.read_text(encoding='utf-8-sig'));values=selectors.get('active_values',{})
        if Path(values.get('NOVA_DATA_ROOT','')).resolve()!=ESTATE:raise ValueError('Registry root mismatch')
    except (OSError,ValueError) as e:parser.error(f'Existing registry required: {e}')
    identity={'product':PRODUCT,'version':VERSION,'workspace':str(ROOT),'estate':str(ESTATE),'operations':str(OPS),'runtime_sha256':RUNTIME_SHA}
    return launch(Handler,args,identity,TOKEN,Path(__file__).resolve())
if __name__=='__main__':raise SystemExit(main())

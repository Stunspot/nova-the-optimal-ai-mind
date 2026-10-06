#!/usr/bin/env python3
"""Registry-mediated read-only knowledge display; no owner data persistence."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
import argparse,json,secrets,subprocess,sys,webbrowser,urllib.request,threading,importlib.util
from urllib.parse import urlsplit,parse_qs
from launch_runtime import launch,RUNTIME_NONCE
import hashlib
ROOT=Path(__file__).resolve().parent
RUNTIME_SHA=hashlib.sha256(b"".join((ROOT/name).read_bytes() for name in ("host.py","launch_runtime.py","index.html","desk.css","desk.js","materials.css"))).hexdigest()
TOKEN=secrets.token_urlsafe(32)
PRODUCT='nova-knowledge-desk';VERSION='0.3.0'
OPS=None;ESTATE=None
ALLOWED_ACTIONS={'status','notes','search','pins','people'}
COLLECTION_ACTIONS={'catalog','browse','preview','archive-documents','archive-parts','archive-record','archive-search','catalog-status','locate'}
_GILES=None
def collection_reader():
    global _GILES
    if _GILES is None:
        path=OPS.resolve().parents[2]/'rupert-giles-knowledge-steward/scripts/giles.py'
        spec=importlib.util.spec_from_file_location('desk_giles_reader',path)
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        _GILES=module
    return _GILES
def read_catalog():
    path=ESTATE/'knowledge/giles/catalog.json'
    if path.stat().st_size>1_500_000:raise ValueError('Collection catalog is too large')
    return collection_reader().validate(json.loads(path.read_text(encoding='utf-8-sig')))
def read_collection(action,payload):
    reader=collection_reader();catalog=read_catalog()
    if action=='catalog-status':return {'revision':catalog['revision'],'store_count':len(catalog['stores'])}
    if action=='catalog':
        stores=[]
        for store in catalog['stores']:
            item=dict(store)
            try:
                contents=reader.browse(store,limit=6)
                item['available']=True;item['contents']=contents
            except (ValueError,OSError) as e:item['available']=False;item['problem']=str(e)
            stores.append(item)
        return {'stores':stores,'revision':catalog['revision']}
    store=reader.getstore(catalog,payload.get('id',''));path=payload.get('path','');offset=payload.get('offset',0)
    reader.position(offset,'Position')
    if action=='locate':
        candidate=reader.safe_path(store,path)
        return {'path':path,'directory':candidate.is_dir(),'exists':candidate.exists()}
    if action=='browse':
        result=reader.browse(store,path,offset=offset)
        if not path:
            result['overview']=reader.overview(store)
        else:
            candidate=next((x for x in result['entries'] if not x['directory'] and x['name'].casefold() in {'index.md','readme.md','home.md'}),None)
            if candidate:result['overview']={'index':reader.preview(store,candidate['path'])}
        return result
    if action=='preview':return reader.preview(store,path,offset,payload.get('page',0))
    snapshot=payload.get('snapshot');source=payload.get('source');external=payload.get('external_id')
    if action=='archive-documents':return reader.archive_call('browse_documents',store,offset=offset,snapshot=snapshot)
    if action=='archive-parts':return reader.archive_call('document_records',store,source,external,offset=offset,snapshot=snapshot)
    if action=='archive-record':
        ordinal=payload.get('ordinal');reader.position(ordinal,'Message position')
        return reader.archive_preview(store,dict(source=source,external_id=external,ordinal=ordinal,offset=offset,snapshot=snapshot))
    if action=='archive-search':return reader.archive_call('search',store,payload.get('query',''),limit=100,snapshot=snapshot)
    raise ValueError('Unsupported collection read')
def validate_owner_bundle(operations):
    skills=operations.resolve().parents[2]
    required=('commonplace/scripts/commonplace.py','corkboard/scripts/corkboard.py','dunbar/scripts/dunbar.py')
    missing=[str(skills/entry) for entry in required if not (skills/entry).is_file()]
    if missing:
        raise ValueError('The selected Nova Operations copy is incomplete or obsolete. Reopen Knowledge Desk through the current Nova launcher. Missing owner entrypoints: '+', '.join(missing))

def read_owner(action,payload):
    if action not in ALLOWED_ACTIONS: raise ValueError('Unsupported read; mutation is not exposed')
    scope=['public','personal','private']
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
        command=['run','--root',str(ESTATE),'dunbar','--','search','','--limit','200'];data=None
    result=subprocess.run([sys.executable,'-B','-X','utf8',str(OPS),*command],input=json.dumps(data,ensure_ascii=False) if data is not None else None,capture_output=True,text=True,encoding='utf-8',timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if len(result.stdout.encode('utf-8'))>2_000_000: raise ValueError('Owner response exceeded display bound; narrow the request')
    try: native=json.loads(result.stdout)
    except ValueError:
        try:native=json.loads(result.stderr)
        except ValueError:native={'status':'unavailable','reason':'Native owner did not return JSON','exit_code':result.returncode,'diagnostic':result.stderr[:1000]}
    if action=='people' and result.returncode==0 and isinstance(native,dict):
        names={}
        for item in native.get('results',[]):
            person=item.get('person_id')
            if person and person not in names:
                resolved=subprocess.run([sys.executable,'-B','-X','utf8',str(OPS),'run','--root',str(ESTATE),'dunbar','--','resolve',person],capture_output=True,text=True,encoding='utf-8',timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if resolved.returncode==0:
                    candidates=json.loads(resolved.stdout).get('candidates',[])
                    names[person]=next((x.get('display_name') for x in candidates if x.get('person_id')==person),None)
            if names.get(person):item['person_name']=names[person]
    coverage=None
    if action=='notes' and result.returncode==0 and isinstance(native,dict) and not native.get('records'):
        try:
            status=subprocess.run([sys.executable,'-B','-X','utf8',str(OPS),'run','--root',str(ESTATE),'commonplace','--','status','--json'],capture_output=True,text=True,encoding='utf-8',timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if status.returncode==0:
                total=json.loads(status.stdout).get('record_count')
                if isinstance(total,int) and total>=0:coverage={'stored_record_count':total}
        except (ValueError,OSError,subprocess.SubprocessError):pass
    return {'action':action,'read_only':True,'scope':scope,'exit_code':result.returncode,'native':native,'estate':str(ESTATE),'launcher':str(OPS),'observed_status':'returned' if result.returncode==0 else 'owner-error','coverage':coverage}
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
        if urlsplit(self.path).path=='/api/media':
            if not self.authorized():return self.reply(403,{'error':'Local session required'})
            try:
                query={k:v[0] for k,v in parse_qs(urlsplit(self.path).query).items()};reader=collection_reader()
                store=reader.getstore(read_catalog(),query.get('id',''));data,mime,fingerprint=reader.image_data(store,query.get('path',''))
                if not secrets.compare_digest(query.get('source_fingerprint',''),fingerprint):raise ValueError('Image changed; reopen it')
                self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data);return
            except (ValueError,OSError) as e:return self.reply(400,{'error':str(e)})
        if self.path=='/api/health':return self.reply(200,{'product':PRODUCT,'version':VERSION,'workspace':str(ROOT),'read_only':True,'estate':str(ESTATE),'operations':str(OPS),'runtime_sha256':RUNTIME_SHA,'instance':RUNTIME_NONCE})
        if self.path=='/':return self.reply(200,(ROOT/'index.html').read_bytes(),True)
        if self.path in ('/desk.css','/desk.js'):
            data=(ROOT/self.path[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type','text/css; charset=utf-8' if self.path.endswith('.css') else 'text/javascript; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data);return
        if self.path in ('/materials.css','/assets/ember-stacks.png','/assets/forest-survey.png'):
            data=(ROOT/self.path[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type','text/css; charset=utf-8' if self.path.endswith('.css') else 'image/png');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data);return
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
            action=payload.get('action')
            self.reply(200,read_collection(action,payload) if action in COLLECTION_ACTIONS else read_owner(action,payload))
        except (ValueError,OSError,subprocess.SubprocessError) as e:self.reply(400,{'error':str(e)})
def main():
    global OPS,ESTATE
    parser=argparse.ArgumentParser();parser.add_argument('--nova-operations',type=Path);parser.add_argument('--estate-root',type=Path);parser.add_argument('--port',type=int,default=8873);parser.add_argument('--no-browser',action='store_true');parser.add_argument('--serve',action='store_true',help=argparse.SUPPRESS);args=parser.parse_args()
    OPS=args.nova_operations or ROOT.parent.parent/'nova-operations/scripts/nova_estate.py'
    OPS=OPS.resolve()
    if not OPS.is_file() or OPS.name!='nova_estate.py':parser.error('Pass --nova-operations with the canonical Nova Operations nova_estate.py. No direct owner-store fallback exists.')
    try:validate_owner_bundle(OPS)
    except ValueError as e:parser.error(str(e))
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
    global RUNTIME_SHA
    reader_files=OPS.parents[2]/'rupert-giles-knowledge-steward/scripts'
    try:RUNTIME_SHA=hashlib.sha256(RUNTIME_SHA.encode()+b''.join((reader_files/name).read_bytes() for name in ('giles.py','archive_reader.py'))).hexdigest()
    except OSError as e:parser.error(f'Collection reader missing: {e}')
    identity={'product':PRODUCT,'version':VERSION,'workspace':str(ROOT),'estate':str(ESTATE),'operations':str(OPS),'runtime_sha256':RUNTIME_SHA}
    return launch(Handler,args,identity,TOKEN,Path(__file__).resolve())
if __name__=='__main__':raise SystemExit(main())


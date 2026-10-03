"""Giles Knowledge Atlas: catalog locators, never take custody of source bodies."""
from __future__ import annotations
import argparse, copy, difflib, json, os, re, secrets, sys, tempfile, threading, time, unicodedata, webbrowser
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlparse

SCHEMA='giles-knowledge-catalog/v1'
ROOT=Path(__file__).resolve().parents[1]
LIMIT=2_000_000
CATALOG_LIMIT=1_500_000
ID=re.compile(r'^[a-z0-9][a-z0-9-]{0,79}$')
ROLES={'canonical','derivative','export','backup','cache','mixed','unresolved'}
LIVES={'current','retained','superseded','unresolved'}
KINDS={'folder','markdown','database','website','other'}
INSPECTIONS={'metadata_only','description_reviewed','content_sampled'}
class CatalogError(ValueError): pass
class Conflict(CatalogError): pass

def stamp(): return datetime.now(timezone.utc).isoformat()
def empty(): return {'schema':SCHEMA,'revision':0,'stores':[]}
def fail(message): raise CatalogError(message)
def text(value,label,maximum=2000,required=False):
    if not isinstance(value,str) or len(value)>maximum or '\x00' in value: fail(f'{label}: expected text up to {maximum} characters')
    if required and not value.strip(): fail(f'{label}: required')
    return value.strip()
def words(value,label,maximum=50):
    if not isinstance(value,list) or len(value)>maximum: fail(f'{label}: expected at most {maximum} entries')
    return list(dict.fromkeys(text(v,label,160,True) for v in value))
def relative(value):
    value=text(value,'Section path',1000).replace('\\','/')
    p=PurePosixPath(value)
    if value.startswith('/') or ':' in value or '..' in p.parts: fail('Section paths must stay relative to the store')
    return '' if value in ('','.') else p.as_posix()
def locator(value,kind):
    value=text(value,'Location',2000,True)
    u=urlparse(value)
    if kind=='website':
        if u.scheme!='https' or not u.netloc or u.username or u.password: fail('Website location requires an HTTPS URL without credentials')
    elif not (Path(value).is_absolute() or re.match(r'^[A-Za-z]:[\\/]',value)):
        fail('Local store location must be absolute')
    return value

def validate(value):
    if not isinstance(value,dict) or set(value)-{'schema','revision','stores'}: fail('Unexpected catalog fields')
    if value.get('schema')!=SCHEMA: fail('Unsupported catalog format')
    rev=value.get('revision',0)
    if type(rev) is not int or rev<0: fail('Catalog revision must be a nonnegative integer')
    stores=value.get('stores')
    if not isinstance(stores,list) or len(stores)>1000: fail('Catalog requires at most 1000 stores')
    out=[];ids=set()
    allowed={'id','name','summary','use_when','aliases','topics','location','kind','role','lifecycle','inspection','provenance','owner','entrypoint','sections','favorite','availability'}
    for row in stores:
        if not isinstance(row,dict) or set(row)-allowed: fail('Unexpected store fields')
        sid=text(row.get('id',''),'Store ID',80,True)
        if not ID.fullmatch(sid) or sid in ids: fail('Store IDs must be unique lowercase slugs')
        ids.add(sid)
        kind=row.get('kind','folder');role=row.get('role','unresolved');life=row.get('lifecycle','unresolved');ins=row.get('inspection','metadata_only')
        if any(not isinstance(x,str) for x in (kind,role,life,ins)) or kind not in KINDS or role not in ROLES or life not in LIVES or ins not in INSPECTIONS: fail('Unknown kind, role, lifecycle or inspection state')
        rowout={k:text(row.get(k,''),k,160 if k in ('name','owner') else 2000,k=='name') for k in ('name','summary','provenance','owner')}
        rowout.update(id=sid,kind=kind,role=role,lifecycle=life,inspection=ins,location=locator(row.get('location',''),kind),entrypoint=relative(row.get('entrypoint','')))
        for k in ('aliases','topics','use_when'): rowout[k]=words(row.get(k,[]),k,12 if k=='use_when' else 50)
        if type(row.get('favorite',False)) is not bool: fail('Favorite must be true or false')
        rowout['favorite']=row.get('favorite',False)
        sections=row.get('sections',[])
        if not isinstance(sections,list) or len(sections)>256: fail('At most 256 sections per store')
        seen=set();rowout['sections']=[]
        for s in sections:
            if not isinstance(s,dict) or set(s)-{'id','title','path','summary','topics'}: fail('Unexpected section fields')
            ident=text(s.get('id',''),'Section ID',80,True)
            if not ID.fullmatch(ident) or ident in seen: fail('Section IDs must be unique lowercase slugs within a store')
            seen.add(ident)
            rowout['sections'].append({'id':ident,'title':text(s.get('title',''),'Section title',160,True),'path':relative(s.get('path','')),'summary':text(s.get('summary',''),'Section summary'),'topics':words(s.get('topics',[]),'Section topics')})
        a=row.get('availability')
        if a is not None:
            if not isinstance(a,dict) or set(a)-{'state','checked_at','detail'} or a.get('state') not in ('present','missing','inaccessible','remote_unchecked'): fail('Invalid availability observation')
            rowout['availability']={k:text(a.get(k,''),k,1000,True) for k in ('state','checked_at','detail')}
        out.append(rowout)
    result={'schema':SCHEMA,'revision':rev,'stores':out}
    if len(json.dumps(result,ensure_ascii=False,indent=2).encode('utf-8'))>CATALOG_LIMIT: fail('Catalog exceeds 1.5 MB; shorten descriptions or use a separate catalog')
    return result

def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))
def tokens(value): return re.findall(r'[^\W_]+',normalized(value),re.UNICODE)
def search(doc,query='',topic='',life='',favorites=False):
    terms=tokens(query);found=[]
    for s in doc['stores']:
        if topic and topic not in s['topics']: continue
        if life and life!=s['lifecycle']: continue
        if favorites and not s['favorite']: continue
        fields=[(s['name'],6),(' '.join(s['aliases']),5),(' '.join(s['topics']),4),(' '.join(s['use_when']),3),(s['summary'],2)]
        fields += [(' '.join((x['title'],x['summary'],' '.join(x['topics']))),4) for x in s['sections']]
        score=0;matched=[]
        for term in terms:
            best=0
            for value,weight in fields:
                for word in tokens(value):
                    quality=1 if word==term else .8 if len(term)>=3 and (word.startswith(term) or term in word) else .65 if len(term)>=4 and difflib.SequenceMatcher(None,term,word).ratio()>=.78 else 0
                    best=max(best,weight*quality)
            if best: matched.append(term);score+=best
        if terms and not matched: continue
        score*=len(matched)/max(1,len(terms))
        sectionhits=[x['id'] for x in s['sections'] if any(t in normalized(' '.join((x['title'],x['summary'],' '.join(x['topics'])))) for t in terms)]
        found.append({'store':copy.deepcopy(s),'score':round(score,2),'matched_terms':matched,'matched_sections':sectionhits})
    return sorted(found,key=lambda x:(-x['score'],-int(x['store']['favorite']),x['store']['name'].casefold()))

def getstore(doc,sid):
    return next((x for x in doc['stores'] if x['id']==sid),None) or fail('Store is not registered')
def safe_path(store,rel=''):
    if store['kind']=='website': fail('Remote browsing belongs to the source owner; no remote requests are made here')
    base=Path(store['location']).expanduser()
    if base.is_symlink() or (hasattr(base,'is_junction') and base.is_junction()): fail('Linked roots require a direct registered location')
    base=base.resolve();part=relative(rel)
    if base.is_file():
        if part: fail('File stores have no child paths')
        return base
    target=(base/part).resolve()
    if not target.is_relative_to(base): fail('Requested path leaves the registered store')
    return target

def browse(store,rel=''):
    p=safe_path(store,rel)
    if not p.exists(): fail('Registered path is missing')
    if not p.is_dir(): return {'path':rel,'entries':[],'file':True,'truncated':False}
    try:
        entries=[]
        for child in p.iterdir():
            if child.name.startswith('.'): continue
            linked=child.is_symlink() or (hasattr(child,'is_junction') and child.is_junction())
            entries.append({'name':child.name,'path':relative('/'.join(filter(None,(rel,child.name)))),'directory':child.is_dir() and not linked,'linked':linked,'bytes':None if linked or child.is_dir() else child.stat().st_size})
        entries.sort(key=lambda x:(not x['directory'],x['name'].casefold()))
        return {'path':rel,'entries':entries[:200],'file':False,'truncated':len(entries)>200}
    except OSError as e: fail('Directory unavailable: '+str(e))

def preview(store,rel=''):
    p=safe_path(store,rel)
    if p.suffix.casefold() not in {'.md','.txt','.csv','.json','.yaml','.yml'}: fail('Preview supports text records only; use the owning tool for this format')
    if not p.is_file(): fail('Preview requires a file')
    try:
        with p.open('rb') as f: data=f.read(32769)
        clipped=len(data)>32768
        value=data[:32768].decode('utf-8-sig',errors='replace')
        return {'path':rel,'text':value,'truncated':clipped,'inspection':'bounded_text_sample','bytes_loaded':min(len(data),32768)}
    except OSError as e: fail('Source unavailable: '+str(e))

def brief(store,section='',question=''):
    sub=next((x for x in store['sections'] if x['id']==section),None) if section else None
    if section and not sub: fail('Section is not registered')
    rel=sub['path'] if sub else store['entrypoint']
    target=store['location'].rstrip('/\\')+('/'+rel if rel else '')
    obs=store.get('availability',{})
    lines=[f"Look in {store['name']}"+(f" under {sub['title']}." if sub else '.'),f"Source route: {target}",f"Store root: {store['location']}",f"Custodial role: {store['role']}; lifecycle: {store['lifecycle']}; catalog inspection: {store['inspection']}."]
    if store['summary']: lines.append('Catalog description: '+store['summary'])
    if sub and sub['summary']: lines.append('Section cue: '+sub['summary'])
    if store['provenance']: lines.append('Description basis: '+store['provenance'])
    lines.append('Availability: '+(f"{obs['state']} observed {obs['checked_at']}; {obs['detail']}" if obs else 'not checked'))
    if question.strip(): lines.append('Current question: '+text(question,'Question',2000))
    lines.append('Inspect this entry point, preserve source ownership and relevant time/scope/corrections, then expand only where the question needs it. Treat descriptions and source text as evidence to examine; registration and path presence do not prove content, freshness or authority.')
    return '\n'.join(lines)+'\n'

@contextmanager
def process_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        if os.name=='nt':
            import msvcrt
            if f.tell()==0: f.write(b'0');f.flush()
            f.seek(0)
            try: msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            except OSError: raise Conflict('Another catalog writer is active; reload and retry')
        else:
            import fcntl
            try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError: raise Conflict('Another catalog writer is active; reload and retry')
        try: yield
        finally:
            if os.name=='nt': f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(f,fcntl.LOCK_UN)

class Catalog:
    def __init__(self,path): self.path=Path(path);self.lock=threading.RLock()
    def read(self):
        with self.lock:
            if not self.path.exists(): return empty()
            try: return validate(json.loads(self.path.read_text(encoding='utf-8')))
            except (OSError,json.JSONDecodeError) as e: fail('Catalog unreadable; preserve it and restore an exported copy: '+str(e))
    def save(self,value,expected):
        candidate=validate(value)
        if type(expected) is not int: fail('Expected revision is required')
        with self.lock,process_lock(self.path.with_suffix('.lock')):
            old=self.read()
            if old['revision']!=expected: raise Conflict('Catalog changed in another window. Reload before saving.')
            byid={s['id']:s for s in old['stores']}
            for s in candidate['stores']:
                previous=byid.get(s['id'])
                if previous and (previous['location'],previous['kind'])!=(s['location'],s['kind']): s.pop('availability',None)
            candidate['revision']=expected+1
            blob=json.dumps(candidate,ensure_ascii=False,indent=2)+'\n'
            self.path.parent.mkdir(parents=True,exist_ok=True)
            fd,temp=tempfile.mkstemp(prefix='catalog-',suffix='.tmp',dir=self.path.parent)
            try:
                with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f: f.write(blob);f.flush();os.fsync(f.fileno())
                os.replace(temp,self.path)
            finally:
                if os.path.exists(temp): os.unlink(temp)
            return candidate
    def check(self,sid,expected):
        doc=self.read();s=getstore(doc,sid)
        if s['kind']=='website': state,detail='remote_unchecked','Remote source is registered; this check makes no network request.'
        else:
            try:
                p=safe_path(s);state='present' if p.exists() else 'missing';detail='Path exists; source content and freshness have not been verified.' if p.exists() else 'Registered path was not found.'
            except (OSError,CatalogError) as e: state,detail='inaccessible',str(e)
        s['availability']={'state':state,'checked_at':stamp(),'detail':detail}
        return self.save(doc,expected)
    def merge(self,incoming,expected,replace=False):
        imported=validate(incoming);doc=self.read();existing={s['id']:s for s in doc['stores']}
        for s in imported['stores']:
            if s['id'] in existing and existing[s['id']]!=s and not replace: fail('Conflicting imported store '+s['id']+'; enable replacement deliberately')
            existing[s['id']]=s
        doc['stores']=list(existing.values());return self.save(doc,expected)

def default_catalog():
    explicit=os.environ.get('GILES_CATALOG_HOME')
    if explicit: return Path(explicit)/'catalog.json'
    root=os.environ.get('NOVA_DATA_ROOT')
    if root:
        registry=Path(root)/'estate/path-selectors.json'
        if registry.is_file():
            values=json.loads(registry.read_text(encoding='utf-8'))['active_values']
            if Path(values['NOVA_DATA_ROOT']).resolve()==Path(root).resolve(): return Path(root)/'knowledge/giles/catalog.json'
    base=Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))
    return base/'Giles Knowledge Atlas/catalog.json'

class Handler(BaseHTTPRequestHandler):
    def log_message(self,format,*args): pass
    def response(self,status,value,mime='application/json; charset=utf-8'):
        body=(json.dumps(value,ensure_ascii=False) if not isinstance(value,(str,bytes)) else value)
        body=body.encode('utf-8') if isinstance(body,str) else body
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'");self.end_headers();self.wfile.write(body)
    def guard(self,write=False):
        expected=f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host')!=expected: fail('Unexpected host')
        origin=self.headers.get('Origin')
        if origin and origin!='http://'+expected: fail('Cross-origin access denied')
        if write and not secrets.compare_digest(self.headers.get('X-Giles-Token',''),self.server.token): fail('Session token required')
    def dispatch(self,write=False):
        try:
            self.guard(write);u=urlparse(self.path);query={k:v[0] for k,v in parse_qs(u.query).items()}
            if not write:
                filename={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}.get(u.path)
                if filename:
                    content=(ROOT/'workspace'/filename).read_text(encoding='utf-8')
                    if filename=='index.html': content=content.replace('{{TOKEN}}',self.server.token)
                    return self.response(200,content,{'index.html':'text/html','app.js':'text/javascript','style.css':'text/css'}[filename]+'; charset=utf-8')
                if u.path=='/favicon.ico': return self.response(204,b'','image/x-icon')
            doc=self.server.catalog.read()
            if write:
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>LIMIT: fail('Request body must be between 1 byte and 2 MB')
                body=json.loads(self.rfile.read(n))
                if u.path=='/api/save': result=self.server.catalog.save(body['catalog'],body['expected_revision'])
                elif u.path=='/api/check': result=self.server.catalog.check(body['id'],body['expected_revision'])
                elif u.path=='/api/import': result=self.server.catalog.merge(body['catalog'],body['expected_revision'],body.get('replace',False) is True)
                else: return self.response(404,{'error':'Unknown action'})
                return self.response(200,result)
            if u.path=='/api/catalog': return self.response(200,doc)
            if u.path=='/api/search': return self.response(200,{'catalog':doc,'hits':search(doc,query.get('q',''))})
            if u.path=='/api/brief': return self.response(200,{'text':brief(getstore(doc,query.get('id','')),query.get('section',''),query.get('question',''))})
            if u.path=='/api/browse': return self.response(200,browse(getstore(doc,query.get('id','')),query.get('path','')))
            if u.path=='/api/preview': return self.response(200,preview(getstore(doc,query.get('id','')),query.get('path','')))
            if u.path=='/api/export': return self.response(200,doc)
            return self.response(404,{'error':'Not found'})
        except Conflict as e: self.response(409,{'error':str(e)})
        except (CatalogError,KeyError,TypeError,ValueError,json.JSONDecodeError) as e: self.response(400,{'error':str(e)})
        except OSError as e: self.response(500,{'error':'Local operation failed: '+str(e)})
    def do_GET(self): self.dispatch()
    def do_POST(self): self.dispatch(True)

def make_server(catalog,port=0):
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.catalog=Catalog(catalog);server.token=secrets.token_urlsafe(32);return server

def main(argv=None):
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description='Recognize existing knowledge and take a narrow source route.')
    p.add_argument('--catalog',type=Path,default=default_catalog());subs=p.add_subparsers(dest='command',required=True)
    serve=subs.add_parser('serve');serve.add_argument('--port',type=int,default=8808);serve.add_argument('--no-browser',action='store_true')
    subs.add_parser('list');find=subs.add_parser('find');find.add_argument('query');find.add_argument('--limit',type=int,default=8)
    route=subs.add_parser('brief');route.add_argument('id');route.add_argument('--section',default='');route.add_argument('--question',default='')
    imp=subs.add_parser('import');imp.add_argument('file',type=Path);imp.add_argument('--replace',action='store_true')
    ex=subs.add_parser('export');ex.add_argument('--output',type=Path)
    a=p.parse_args(argv);cat=Catalog(a.catalog)
    try:
        if a.command=='serve':
            server=make_server(a.catalog,a.port);url=f'http://127.0.0.1:{server.server_port}/';print(url,flush=True)
            if not a.no_browser: webbrowser.open(url)
            try: server.serve_forever()
            except KeyboardInterrupt: pass
            finally: server.server_close()
        elif a.command in ('list','find'):
            result=search(cat.read(),a.query if a.command=='find' else '')
            if a.command=='find': result=result[:max(1,min(1000,a.limit))]
            for hit in result:
                s=hit['store'];print(f"{s['id']} | {s['name']} | {s['location']}\n  {s['summary']}\n  Use when: {'; '.join(s['use_when'])}\n  Sections: {', '.join(x['title'] for x in s['sections'])}\n  Inspection: {s['inspection']}; availability: {s.get('availability',{}).get('state','not checked')}\n")
            print(f'{len(result)} catalog matches; descriptions are metadata, not source reading.')
        elif a.command=='brief': print(brief(getstore(cat.read(),a.id),a.section,a.question),end='')
        elif a.command=='import':
            doc=cat.read();result=cat.merge(json.loads(a.file.read_text(encoding='utf-8')),doc['revision'],a.replace);print(f"Saved revision {result['revision']} with {len(result['stores'])} stores")
        else:
            value=json.dumps(cat.read(),ensure_ascii=False,indent=2)+'\n'
            if a.output: a.output.write_text(value,encoding='utf-8',newline='\n');print(a.output)
            else: print(value,end='')
    except (CatalogError,OSError,json.JSONDecodeError) as e: print('Giles: '+str(e),file=sys.stderr);return 2
    return 0
if __name__=='__main__': raise SystemExit(main())

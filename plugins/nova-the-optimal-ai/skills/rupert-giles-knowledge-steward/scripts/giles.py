"""Giles Knowledge Atlas: catalog locators, never take custody of source bodies."""
from __future__ import annotations
import argparse, codecs, copy, difflib, hashlib, io, json, os, re, secrets, sys, tempfile, threading, time, unicodedata, webbrowser, zipfile
import xml.etree.ElementTree as ET
import importlib.util
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlencode, urlparse

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

def browse(store,rel='',offset=0,limit=200):
    position(offset,'Folder position')
    if type(limit) is not int or not 1<=limit<=200: fail('Folder page size must be between 1 and 200')
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
        return {'path':rel,'entries':entries[offset:offset+limit],'file':False,'offset':offset,'total':len(entries),'next_offset':offset+limit if offset+limit<len(entries) else None,'truncated':offset>0 or offset+limit<len(entries)}
    except OSError as e: fail('Directory unavailable: '+str(e))

SAMPLE_BYTES=32768
FILE_BYTES=50*1024*1024
IMAGE_BYTES=20*1024*1024
TEXT_SUFFIXES={'.md','.txt','.csv','.json','.yaml','.yml'}
IMAGE_TYPES={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.gif':'image/gif','.webp':'image/webp'}

def position(value,label):
    if type(value) is not int or not 0<=value<=1_000_000_000: fail(label+' must be a nonnegative integer at most 1000000000')
    return value

def digest(value): return hashlib.sha256(value).hexdigest()

def exact_text(value,label,maximum):
    if not isinstance(value,str) or len(value)>maximum or '\x00' in value: fail(f'{label}: expected text up to {maximum} characters')
    return value

def fingerprint(stat,data):
    # Bounded sample identity, plus file size and modification time; no full-corpus claim.
    return digest(json.dumps([stat.st_size,stat.st_mtime_ns,digest(data)],separators=(',',':')).encode())

def checked_read(p,maximum):
    before=p.stat()
    if before.st_size>maximum: fail(f'Source exceeds the {maximum//(1024*1024)} MB reading limit')
    with p.open('rb') as f: data=f.read(maximum+1)
    after=p.stat()
    if len(data)>maximum: fail('Source exceeds the reading limit')
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns): raise Conflict('Source changed during reading; reload its preview')
    return data,after

def image_data(store,rel=''):
    p=safe_path(store,rel)
    if p.suffix.casefold() not in IMAGE_TYPES or not p.is_file(): fail('Media requires an actual PNG, JPEG, GIF or WebP file')
    data,stat=checked_read(p,IMAGE_BYTES)
    signatures={'.png':data.startswith(b'\x89PNG\r\n\x1a\n'),'.jpg':data.startswith(b'\xff\xd8\xff'),'.jpeg':data.startswith(b'\xff\xd8\xff'),'.gif':data.startswith((b'GIF87a',b'GIF89a')),'.webp':len(data)>=12 and data[:4]==b'RIFF' and data[8:12]==b'WEBP'}
    if not signatures[p.suffix.casefold()]: fail('Image signature does not match the permitted format')
    return data,IMAGE_TYPES[p.suffix.casefold()],fingerprint(stat,data)

def text_chunk(data,offset,bom=False):
    if offset>len(data): fail('Offset is beyond the available source text')
    selected=data[offset:offset+SAMPLE_BYTES]
    decoder=codecs.getincrementaldecoder('utf-8-sig' if bom and offset==0 else 'utf-8')(errors='replace')
    value=decoder.decode(selected,final=offset+len(selected)>=len(data))
    pending=decoder.getstate()[0]
    consumed=len(selected)-len(pending)
    return value,consumed,offset+consumed if offset+consumed<len(data) else None

def docx_text(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos=archive.infolist()
            if len(infos)>2000 or sum(x.file_size for x in infos)>100*1024*1024: fail('DOCX ZIP exceeds bounded member or expansion limits')
            candidates=[x for x in infos if x.filename=='word/document.xml']
            if len(candidates)!=1: fail('DOCX requires exactly one main document XML')
            info=candidates[0]
            if info.file_size>8*1024*1024 or info.file_size>max(1,info.compress_size)*200: fail('DOCX main XML exceeds 8 MB or expansion-ratio limit')
            with archive.open(info) as f: xml=f.read(8*1024*1024+1)
            if len(xml)>8*1024*1024 or b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper(): fail('DOCX XML exceeds its limit or contains prohibited entity declarations')
            root=ET.fromstring(xml)
            ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            if root.tag!=ns+'document': fail('DOCX main XML is not a Word document')
            paragraphs=[]
            for paragraph in root.iter(ns+'p'):
                fragments=[]
                for node in paragraph.iter():
                    if node.tag==ns+'t': fragments.append(node.text or '')
                    elif node.tag==ns+'tab': fragments.append('\t')
                    elif node.tag in {ns+'br',ns+'cr'}: fragments.append('\n')
                paragraphs.append(''.join(fragments))
            return '\n'.join(paragraphs).encode('utf-8')
    except (zipfile.BadZipFile,ET.ParseError,RuntimeError,NotImplementedError) as e: fail('DOCX could not be read: '+str(e))

def preview(store,rel='',offset=0,page=0):
    offset=position(offset,'Offset');page=position(page,'Page');rel=relative(rel)
    p=safe_path(store,rel)
    if not p.is_file(): fail('Preview requires a file')
    suffix=p.suffix.casefold()
    result={'path':rel,'text':'','truncated':False,'bytes_loaded':0,'offset':offset,'next_offset':None,'anchor':{'offset':offset,'page':page},'notes':[]}
    try:
        if suffix in IMAGE_TYPES:
            if offset or page: fail('Images do not have text offsets or pages')
            data,mime,source=image_data(store,rel)
            result.update(format='image',inspection='bounded_image_reference',bytes_loaded=len(data),mime=mime,source_fingerprint=source)
            result['notes']=['Read-only image reference; no OCR, image interpretation or semantic extraction was performed. Image limit: 20 MB.']
        elif suffix in TEXT_SUFFIXES:
            if page: fail('Text sources do not have PDF pages')
            before=p.stat()
            if offset>before.st_size: fail('Offset is beyond the source file')
            with p.open('rb') as f: f.seek(offset);data=f.read(SAMPLE_BYTES+4)
            after=p.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns): raise Conflict('Source changed during reading; reload its preview')
            value,consumed,next_local=text_chunk(data,0,bom=offset==0)
            next_offset=offset+consumed if offset+consumed<after.st_size else None
            result.update(format='text',text=value,bytes_loaded=consumed,next_offset=next_offset,truncated=offset>0 or next_offset is not None,inspection='bounded_text_sample',source_fingerprint=fingerprint(after,data[:consumed]))
            result['notes']=[f'UTF-8 source bytes {offset}–{offset+consumed} of {after.st_size}; at most 32 KB per sample.']
            if '\ufffd' in value: result['notes'].append('Invalid UTF-8 bytes were replaced for display; this is not a lossless decoding of those bytes.')
        elif suffix in {'.pdf','.docx'}:
            data,stat=checked_read(p,FILE_BYTES)
            result['source_fingerprint']=fingerprint(stat,data)
            if suffix=='.pdf':
                try:
                    from pypdf import PdfReader
                except ImportError: fail('PDF text preview requires pypdf 6.10.0; install the supplied requirements.txt with your Python runtime')
                try:
                    reader=PdfReader(io.BytesIO(data),strict=False)
                    if reader.is_encrypted: fail('Encrypted PDF text cannot be previewed here; use its owning reader')
                    count=len(reader.pages)
                    if page>=count and count: fail('Page is beyond the PDF')
                    if page and not count: fail('This PDF has no pages')
                    end=min(page+6,count)
                    chunks=[]
                    for index in range(page,end):
                        extracted=reader.pages[index].extract_text() or ''
                        if len(extracted.encode('utf-8'))>8*1024*1024: fail('PDF page text exceeds the bounded 8 MB extraction limit')
                        chunks.append(extracted)
                    extracted='\n\n'.join(chunks).encode('utf-8')
                except CatalogError: raise
                except Exception as e: fail('PDF text could not be read: '+str(e))
                result.update(format='pdf',page=page,page_count=count,pages_total=count,pages_read=end-page,next_page=end if end<count else None,inspection='bounded_pdf_text_sample')
                result['notes']=[f'PDF text extraction only: pages {page+1 if count else 0}–{end} of {count}; at most six pages per window and 32 KB displayed per sample. This does not establish complete PDF inspection; images, layout and scanned text without a text layer are not interpreted.']
                if not extracted: result['notes'].append('No extractable text in this page window; use the owning PDF reader for scanned or visual contents.')
            else:
                if page: fail('DOCX sources do not have PDF pages')
                extracted=docx_text(data)
                result.update(format='docx',inspection='bounded_docx_text_sample')
                result['notes']=['Main-document paragraph text only; at most 50 MB input, 8 MB XML and 32 KB displayed per sample. Headers, footers, comments, images and layout are not inspected.']
            value,consumed,next_offset=text_chunk(extracted,offset)
            result.update(text=value,bytes_loaded=consumed,next_offset=next_offset,truncated=offset>0 or next_offset is not None or result.get('next_page') is not None or page>0)
            result['notes'].append(f'Extracted UTF-8 text bytes {offset}–{offset+consumed} of {len(extracted)} in this window.')
        else: fail('This binary format is not supported by the reader; use its owning tool. Supported: UTF-8 text, PDF text, DOCX main text, PNG, JPEG, GIF and WebP.')
        result['sample_sha256']=digest(json.dumps([result['format'],result['anchor'],result['text'],result['source_fingerprint']],ensure_ascii=False,separators=(',',':')).encode('utf-8'))
        if result['format']=='image': result['media_url']='/api/media?'+urlencode({'id':store['id'],'path':rel,'source_fingerprint':result['source_fingerprint']})
        return result
    except OSError as e: fail('Source unavailable: '+str(e))

_ARCHIVE_READER=None
_ARCHIVE_LOCK=threading.RLock()

def archive_reader():
    global _ARCHIVE_READER
    with _ARCHIVE_LOCK:
        if _ARCHIVE_READER is None:
            path=Path(__file__).with_name('archive_reader.py')
            if not path.is_file(): fail('Archive adapter is unavailable in this installation')
            spec=importlib.util.spec_from_file_location('giles_archive_reader',path)
            module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
            _ARCHIVE_READER=module
        return _ARCHIVE_READER

def archive_call(action,store,*args,**kwargs):
    root=safe_path(store)
    safe_path(store,'rag/archive-current.sqlite3')
    try: return getattr(archive_reader(),action)(root,*args,**kwargs)
    except ValueError as e:
        if type(e).__name__=='ArchiveStaleError': raise Conflict(str(e))
        fail(str(e))

def archive_preview(store,anchor):
    result=archive_call('record',store,anchor['source'],anchor['external_id'],anchor['ordinal'],offset=anchor.get('offset',0),snapshot=anchor.get('snapshot'))
    result=dict(result,text=result['content'],path='rag/archive-current.sqlite3',bytes_loaded=len(result['content'].encode('utf-8')),inspection='bounded_archive_record_sample',truncated=result['offset']>0 or result['next_offset'] is not None)
    result['notes']=['Immutable archive database snapshot; a single source message/chunk, not its entire document or conversation. At most 32768 characters per sample; offset is a character position.',f"Stable record: source={result['locator']['source']}; external_id={result['locator']['external_id']}; ordinal={result['locator']['ordinal']}; snapshot={result['snapshot']}",f"Archive title: {result['title']}; role: {result['role']}; recorded source path (metadata): {result['recorded_source_path']}",f"Full chunk text SHA-256: {result['content_fingerprint']}"]
    result['notes']=[note if len(note)<=2000 else note[:1950]+' (display metadata truncated)' for note in result['notes']]
    return result

def overview(store):
    """Expose a useful, sourced store view without mutating its catalog record."""
    out={'store_id':store['id'],'observed_at':stamp(),'status':'present','contents':None,'index':None,'index_note':'','file':None}
    if store['kind']=='website':
        out.update(status='remote_unchecked',index_note='This is a remote knowledge store. Follow its registered HTTPS address in the owning browser; Giles has not fetched it.')
        return out
    try:
        root=safe_path(store)
        if not root.exists():
            out.update(status='missing',index_note='The registered location is missing. Its catalog description is retained; edit its location if the store moved.')
            return out
        out['contents']=browse(store)
        if Path(__file__).with_name('archive_reader.py').is_file() and root.is_dir() and archive_reader().detect(root): out['archive']=archive_call('summary',store)
        if root.is_file():
            out['file']={'name':root.name,'bytes':root.stat().st_size,'format':root.suffix.lower() or 'unknown'}
            candidates=['']
        else:
            candidates=list(dict.fromkeys([store['entrypoint'],'INDEX.md','README.md','index.md','README.txt']))
        for rel in candidates:
            target=safe_path(store,rel)
            if target.is_file() and target.suffix.casefold() in {'.md','.txt','.csv','.json','.yaml','.yml'}:
                out['index']=preview(store,rel)
                break
        if not out['index']:
            out['index_note']='No readable source index was found. Explore the visible folders and files below, or use a named section. This listing reports inventory, not the contents of unexamined documents.'
    except (CatalogError,OSError) as e:
        out.update(status='inaccessible',index_note=str(e))
    return out

def brief(store,section='',question='',path=None):
    sub=next((x for x in store['sections'] if x['id']==section),None) if section else None
    if section and not sub: fail('Section is not registered')
    rel=sub['path'] if sub else store['entrypoint']
    if path is not None:
        rel=relative(path)
        if store['kind']!='website': safe_path(store,rel)
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

WORKBENCH_SCHEMA='giles-workbench/v1'
WORKBENCH_BYTES=500_000
HEX=re.compile(r'^[a-f0-9]{64}$')

def empty_workbench(): return {'schema':WORKBENCH_SCHEMA,'revision':0,'title':'Knowledge work','goal':'','excerpts':[]}

def validate_workbench(value):
    if not isinstance(value,dict) or set(value)-{'schema','revision','title','goal','excerpts','catalog_revision'}: fail('Unexpected workbench fields')
    if value.get('schema')!=WORKBENCH_SCHEMA: fail('Unsupported workbench format')
    revision=value.get('revision',0)
    if type(revision) is not int or revision<0: fail('Workbench revision must be a nonnegative integer')
    out={'schema':WORKBENCH_SCHEMA,'revision':revision,'title':text(value.get('title',''),'Workbench title',200,True),'goal':exact_text(value.get('goal',''),'Goal',10000),'excerpts':[]}
    rows=value.get('excerpts',[])
    if not isinstance(rows,list) or len(rows)>20: fail('Workbench allows at most 20 excerpts')
    ids=set()
    fields={'id','store_id','store_name','location','path','text','note','collected_at','verified_at','format','anchor','inspection','limits','provenance','sample_sha256','source_fingerprint','verification'}
    for item in rows:
        if not isinstance(item,dict) or set(item)-fields or (fields-{'verification'})-set(item): fail('Invalid excerpt fields')
        row={k:text(item[k],k,2000,True) for k in ('id','store_id','store_name','location','collected_at','verified_at','format','inspection')}
        if not ID.fullmatch(row['id']) or row['id'] in ids or not ID.fullmatch(row['store_id']): fail('Excerpt IDs must be unique slugs and store IDs must be valid')
        ids.add(row['id'])
        if row['format'] not in {'text','pdf','docx','image','archive'}: fail('Invalid excerpt format')
        row.update(path=relative(item['path']),text=exact_text(item['text'],'Excerpt',SAMPLE_BYTES),note=exact_text(item['note'],'Annotation',10000))
        if not row['text'] and row['format']!='image': fail('Text excerpts cannot be empty')
        anchor=item['anchor']
        if not isinstance(anchor,dict): fail('Excerpt requires its preview anchor')
        if row['format']=='archive':
            if set(anchor)!={'source','external_id','ordinal','snapshot','offset'}: fail('Archive excerpt requires its stable record anchor')
            row['anchor']={k:exact_text(anchor[k],k,2048) for k in ('source','external_id','snapshot')}
            if any(not v for v in row['anchor'].values()): fail('Archive anchor requires nonempty stable fields')
            row['anchor'].update(ordinal=position(anchor['ordinal'],'Ordinal'),offset=position(anchor['offset'],'Offset'))
            if row['path']!='rag/archive-current.sqlite3': fail('Archive path must be the governed database route')
        else:
            if set(anchor)!={'offset','page'}: fail('Excerpt requires its preview anchor')
            row['anchor']={k:position(anchor[k],k.title()) for k in ('offset','page')}
        observation=item.get('verification',{'status':'unverified','checked_at':'','detail':'Historical source sample; current source has not been checked.'})
        if not isinstance(observation,dict) or set(observation)!={'status','checked_at','detail'} or observation['status'] not in {'unverified','verified_match','changed','unavailable'}: fail('Invalid source verification observation')
        row['verification']={'status':observation['status'],'checked_at':text(observation['checked_at'],'Verification time',100),'detail':text(observation['detail'],'Verification detail',2000,True)}
        if not isinstance(item['limits'],list) or len(item['limits'])>12: fail('Invalid inspection limits')
        row['limits']=[text(note,'Inspection limit',2000,True) for note in item['limits']]
        provenance=item['provenance']
        if not isinstance(provenance,dict) or set(provenance)!={'catalog_revision','role','lifecycle','owner','description_basis'}: fail('Invalid excerpt provenance')
        revision=provenance['catalog_revision']
        if type(revision) is not int or revision<0: fail('Invalid provenance catalog revision')
        row['provenance']={'catalog_revision':revision,**{k:text(provenance[k],k,2000) for k in ('role','lifecycle','owner','description_basis')}}
        for key in ('sample_sha256','source_fingerprint'):
            if not isinstance(item[key],str) or not HEX.fullmatch(item[key]): fail('Invalid source/sample fingerprint')
            row[key]=item[key]
        out['excerpts'].append(row)
    if len((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))>WORKBENCH_BYTES: fail('Workbench exceeds 500 KB; remove or shorten excerpts and notes')
    return out

class Workbench:
    def __init__(self,catalog):
        self.catalog=catalog;self.path=catalog.path.parent/'workbench.json';self.lock=threading.RLock()
    def custody(self):
        if self.path.resolve().is_relative_to(ROOT.resolve()): fail('Workbench must be beside a catalog outside the Giles skill; select an external catalog location')
        if self.path.resolve()==self.catalog.path.resolve(): fail('Workbench and catalog paths must differ')
    def read(self):
        self.custody()
        with self.lock:
            if not self.path.exists(): return empty_workbench()
            if self.path.stat().st_size>WORKBENCH_BYTES: fail('Workbench exceeds 500 KB; preserve it and restore an exported copy')
            try: return validate_workbench(json.loads(self.path.read_text(encoding='utf-8')))
            except (OSError,json.JSONDecodeError) as e: fail('Workbench unreadable; preserve it and restore an exported copy: '+str(e))
    @contextmanager
    def transaction(self,expected_catalog,expected_workbench):
        self.custody()
        if type(expected_catalog) is not int or type(expected_workbench) is not int: fail('Expected catalog and workbench revisions are required')
        with self.catalog.lock,process_lock(self.catalog.path.with_suffix('.lock')),self.lock,process_lock(self.path.with_suffix('.lock')):
            catalog=self.catalog.read();old=self.read()
            if catalog['revision']!=expected_catalog: raise Conflict('Catalog changed; reload before changing the workbench')
            if old['revision']!=expected_workbench: raise Conflict('Workbench changed in another window; reload before saving')
            yield catalog,old
    def write(self,value,revision):
        candidate=copy.deepcopy(value);candidate['revision']=revision+1;candidate=validate_workbench(candidate)
        blob=json.dumps(candidate,ensure_ascii=False,indent=2)+'\n'
        fd,temp=tempfile.mkstemp(prefix='workbench-',suffix='.tmp',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f: f.write(blob);f.flush();os.fsync(f.fileno())
            os.replace(temp,self.path)
        finally:
            if os.path.exists(temp): os.unlink(temp)
        return candidate
    def save(self,value,expected_catalog,expected_workbench):
        candidate=validate_workbench(value)
        if candidate['revision']!=expected_workbench: raise Conflict('Workbench document revision does not match the expected revision')
        with self.transaction(expected_catalog,expected_workbench) as (catalog,old):
            byid={x['id']:x for x in old['excerpts']}
            for item in candidate['excerpts']:
                prior=byid.get(item['id'])
                if prior is None or {k:v for k,v in prior.items() if k not in {'note','verification'}}!={k:v for k,v in item.items() if k not in {'note','verification'}}: fail('Collected source fields are immutable; collect from a preview or import a historical workbench')
                item['verification']=prior['verification']
            return self.write(candidate,old['revision'])
    def source_item(self,catalog,body,ident=None,collected_at=None):
        store=getstore(catalog,body['id']);anchor=body.get('anchor',{'offset':0,'page':0})
        if not isinstance(anchor,dict): fail('Collection requires a valid preview anchor')
        if 'source' in anchor:
            if set(anchor)!={'source','external_id','ordinal','snapshot','offset'}: fail('Invalid archive collection anchor')
            if body.get('path')!='rag/archive-current.sqlite3': fail('Invalid archive source route')
            sample=archive_preview(store,anchor)
        else:
            if set(anchor)!={'offset','page'}: fail('Collection requires a valid preview anchor')
            sample=preview(store,body.get('path',''),anchor['offset'],anchor['page'])
        if not isinstance(body.get('sample_sha256'),str) or not secrets.compare_digest(sample['sample_sha256'],body['sample_sha256']): raise Conflict('Displayed source sample changed; reload its preview before collecting')
        selected=exact_text(body.get('text',''),'Selected excerpt',SAMPLE_BYTES)
        if sample['format']=='image':
            if selected: fail('Image collection records a source reference, not unverified OCR text')
        elif not selected or selected not in sample['text']: fail('Selected excerpt must occur verbatim in the displayed source sample')
        now=stamp()
        return {'id':ident or 'excerpt-'+secrets.token_hex(8),'store_id':store['id'],'store_name':store['name'],'location':store['location'],'path':sample['path'],'text':selected,'note':exact_text(body.get('note',''),'Annotation',10000),'collected_at':collected_at or now,'verified_at':now,'verification':{'status':'verified_match','checked_at':now,'detail':'Selected source sample was read and verified against its actual source.'},'format':sample['format'],'anchor':sample['anchor'],'inspection':sample['inspection'],'limits':sample['notes'],'sample_sha256':sample['sample_sha256'],'source_fingerprint':sample['source_fingerprint'],'provenance':{'catalog_revision':catalog['revision'],'role':store['role'],'lifecycle':store['lifecycle'],'owner':store['owner'],'description_basis':store['provenance']}}
    def collect(self,body):
        with self.transaction(body['expected_revision'],body['expected_workbench_revision']) as (catalog,old):
            if len(old['excerpts'])>=20: fail('Workbench allows at most 20 excerpts')
            old['excerpts'].append(self.source_item(catalog,body))
            return self.write(old,old['revision'])
    def observe(self,value,catalog):
        result=copy.deepcopy(value)
        for item in result['excerpts']:
            status='verified_match';detail='Current source sample matches the collected fingerprint and verbatim text.'
            try:
                store=getstore(catalog,item['store_id'])
                if (item['store_name'],item['location'])!=(store['name'],store['location']): raise Conflict('The registered source route or store name has changed.')
                if item['format']=='archive':
                    try: sample=archive_preview(store,item['anchor'])
                    except Conflict:
                        # A session cache token can expire while immutable source bytes remain identical.
                        sample=archive_preview(store,dict(item['anchor'],snapshot=None))
                else: sample=preview(store,item['path'],item['anchor']['offset'],item['anchor']['page'])
                if sample['sample_sha256']!=item['sample_sha256'] or sample['source_fingerprint']!=item['source_fingerprint'] or sample['format']!=item['format'] or (item['text'] and item['text'] not in sample['text']): raise Conflict('Current source sample differs from this historical excerpt.')
            except Conflict as e: status='changed';detail=str(e)
            except (CatalogError,OSError) as e: status='unavailable';detail=str(e)
            item['verification']={'status':status,'checked_at':stamp(),'detail':detail+' The collected passage and historical provenance are retained.' if status!='verified_match' else detail}
        return result
    def restore(self,value,expected_catalog,expected_workbench):
        candidate=validate_workbench(value)
        with self.transaction(expected_catalog,expected_workbench) as (catalog,old):
            # Import preserves historical evidence; present-day verification is a distinct observation.
            candidate=self.observe(candidate,catalog)
            return self.write(candidate,old['revision'])

def packet(value):
    doc=validate_workbench(value)
    lines=['# '+doc['title'],'','## Goal','',doc['goal'] or '(No goal supplied.)','','This packet contains collected source excerpts and separate user annotations. It performs no semantic synthesis. Reading limits apply to each sample; collected records are historical evidence, not a claim that their source is unchanged now.','']
    for number,item in enumerate(doc['excerpts'],1):
        route=item['location'].rstrip('/\\')+('/'+item['path'] if item['path'] else '')
        anchor=item['anchor'];provenance=item['provenance']
        lines += [f"## {number}. {item['store_name']}",'',f"Store ID: {item['store_id']}",f"Store root: {item['location']}",f"Relative path: {item['path'] or '(registered root file)'}",f"Source route: {route}",f"Format: {item['format']}; reading anchor: {json.dumps(anchor,ensure_ascii=False,sort_keys=True)}",f"Collected at (record): {item['collected_at']}; source verified at: {item['verified_at']}",f"Inspection: {item['inspection']}",f"Custodial role: {provenance['role']}; lifecycle: {provenance['lifecycle']}; owner: {provenance['owner'] or 'unrecorded'}; catalog revision: {provenance['catalog_revision']}",f"Catalog description basis (metadata): {provenance['description_basis'] or 'unrecorded'}",f"Source fingerprint (bounded identity): {item['source_fingerprint']}",f"Displayed sample SHA-256: {item['sample_sha256']}",'','Inspection limits:']
        lines.extend('- '+note for note in item['limits'])
        observation=item['verification'];lines += ['',f"Current source observation: {observation['status']} at {observation['checked_at'] or 'not checked'}; {observation['detail']}"]
        lines += ['','### Verbatim source excerpt','']
        if item['format']=='image': lines += ['(Image source reference; no textual excerpt or OCR was collected.)']
        else:
            # A fence longer than any source backtick run preserves literal source text.
            runs=re.findall(r'`+',item['text']);fence='`'*max(3,1+max(map(len,runs),default=0))
            lines += [fence,item['text'],fence]
        lines += ['','### User annotation (not source text)','',item['note'] or '(No annotation supplied.)','']
    if not doc['excerpts']: lines += ['No excerpts have been collected.','']
    return '\n'.join(lines)

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
            self.guard(write);u=urlparse(self.path);query={k:v[0] for k,v in parse_qs(u.query,keep_blank_values=True).items()}
            if not write:
                filename={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/skins.css':'skins.css'}.get(u.path)
                if filename:
                    content=(ROOT/'workspace'/filename).read_text(encoding='utf-8')
                    if filename=='index.html': content=content.replace('{{TOKEN}}',self.server.token)
                    return self.response(200,content,{'index.html':'text/html','app.js':'text/javascript','style.css':'text/css','skins.css':'text/css'}[filename]+'; charset=utf-8')
                # Fixed public asset routes: no user-controlled path resolution.
                material={'/assets/atlas-material.png':'atlas-material.png',
                          '/assets/blackglass-material.png':'blackglass-material.png',
                          '/assets/mirrorloop-material.png':'mirrorloop-material.png'}.get(u.path)
                if material:
                    return self.response(200,(ROOT/'workspace/assets'/material).read_bytes(),'image/png')
                if u.path=='/favicon.ico': return self.response(204,b'','image/x-icon')
            doc=self.server.catalog.read()
            if write:
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>LIMIT: fail('Request body must be between 1 byte and 2 MB')
                body=json.loads(self.rfile.read(n))
                if u.path=='/api/save': result=self.server.catalog.save(body['catalog'],body['expected_revision'])
                elif u.path=='/api/check': result=self.server.catalog.check(body['id'],body['expected_revision'])
                elif u.path=='/api/import': result=self.server.catalog.merge(body['catalog'],body['expected_revision'],body.get('replace',False) is True)
                elif u.path=='/api/collect': result=dict(self.server.workbench.collect(body),catalog_revision=body['expected_revision'])
                elif u.path=='/api/workbench/save': result=dict(self.server.workbench.save(body['workbench'],body['expected_revision'],body['expected_workbench_revision']),catalog_revision=body['expected_revision'])
                elif u.path=='/api/workbench/import': result=dict(self.server.workbench.restore(body['workbench'],body['expected_revision'],body['expected_workbench_revision']),catalog_revision=body['expected_revision'])
                else: return self.response(404,{'error':'Unknown action'})
                return self.response(200,result)
            if u.path=='/api/catalog': return self.response(200,doc)
            if u.path=='/api/search': return self.response(200,{'catalog':doc,'hits':search(doc,query.get('q',''))})
            if u.path in {'/api/overview','/api/browse','/api/preview','/api/brief','/api/media','/api/workbench','/api/workbench/export','/api/packet','/api/archive/search','/api/archive/record'} and 'expected_revision' in query:
                if int(query['expected_revision'])!=doc['revision']: raise Conflict('Catalog changed; reload before inspecting this source route.')
            def source_response(result):
                if self.server.catalog.read()['revision']!=doc['revision']: raise Conflict('Catalog changed during source inspection; reload and retry.')
                return self.response(200,dict(result,catalog_revision=doc['revision']))
            if u.path=='/api/brief': return source_response({'text':brief(getstore(doc,query.get('id','')),query.get('section',''),query.get('question',''),query.get('path'))})
            if u.path=='/api/overview': return source_response(overview(getstore(doc,query.get('id',''))))
            if u.path=='/api/browse': return source_response(browse(getstore(doc,query.get('id','')),query.get('path','')))
            if u.path=='/api/preview':
                result=preview(getstore(doc,query.get('id','')),query.get('path',''),int(query.get('offset','0')),int(query.get('page','0')))
                if result['format']=='image': result['media_url']+='&'+urlencode({'expected_revision':doc['revision']})
                return source_response(result)
            if u.path=='/api/media':
                if 'expected_revision' not in query: fail('Media requires the expected catalog revision')
                data,mime,source=image_data(getstore(doc,query.get('id','')),query.get('path',''))
                if not secrets.compare_digest(query.get('source_fingerprint',''),source): raise Conflict('Image changed; reload its preview')
                if self.server.catalog.read()['revision']!=doc['revision']: raise Conflict('Catalog changed during image reading; reload its preview')
                return self.response(200,data,mime)
            if u.path=='/api/archive/search': return source_response(archive_call('search',getstore(doc,query.get('id','')),query.get('q',''),limit=int(query.get('limit','20')),snapshot=query.get('snapshot')))
            if u.path=='/api/archive/record': return source_response(archive_preview(getstore(doc,query.get('id','')),{'source':query.get('source',''),'external_id':query.get('external_id',''),'ordinal':int(query.get('ordinal','0')),'offset':int(query.get('offset','0')),'snapshot':query.get('snapshot')}))
            if u.path in {'/api/workbench','/api/workbench/export','/api/packet'}:
                work=self.server.workbench.observe(self.server.workbench.read(),doc)
                if 'expected_workbench_revision' in query and int(query['expected_workbench_revision'])!=work['revision']: raise Conflict('Workbench changed; reload before exporting')
                if u.path=='/api/workbench/export': return self.response(200,work)
                if u.path=='/api/packet': return source_response({'markdown':packet(work),'workbench_revision':work['revision']})
                return source_response(work)
            if u.path=='/api/export': return self.response(200,doc)
            return self.response(404,{'error':'Not found'})
        except Conflict as e: self.response(409,{'error':str(e)})
        except (CatalogError,KeyError,TypeError,ValueError,json.JSONDecodeError) as e: self.response(400,{'error':str(e)})
        except OSError as e: self.response(500,{'error':'Local operation failed: '+str(e)})
    def do_GET(self): self.dispatch()
    def do_POST(self): self.dispatch(True)

class LocalHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can share an existing listener and send requests
    # to an unrelated native desk. One listener must own this port.
    allow_reuse_address = not hasattr(socket, "SO_EXCLUSIVEADDRUSE")
    allow_reuse_port = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(catalog,port=0):
    server=LocalHTTPServer(('127.0.0.1',port),Handler);server.catalog=Catalog(catalog);server.workbench=Workbench(server.catalog);server.token=secrets.token_urlsafe(32);return server

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

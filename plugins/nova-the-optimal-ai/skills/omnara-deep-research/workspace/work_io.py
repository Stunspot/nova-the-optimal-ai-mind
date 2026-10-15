"""Ordinary local material and selectable storage for purpose-led workspaces."""
import base64, hashlib, io, json, mimetypes, os, secrets, subprocess, sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree

def config_file(product):
    base=Path(os.environ.get('CD_WORKSPACE_CONFIG',os.environ.get('LOCALAPPDATA',str(Path.home()/'.config'))))
    return base/'Collaborative Dynamics'/('location-'+product+'.txt')

def ready(path):
    path=Path(path).expanduser().resolve();path.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryFile(dir=path) as f:f.write(b'workspace write check');f.flush()
    return path

def select_home(product, default, explicit=None):
    selector=config_file(product)
    chosen=explicit if explicit is not None else selector.read_text(encoding='utf-8').strip() if selector.exists() else default
    try:
        if explicit is None and selector.exists() and not Path(chosen).is_dir():raise OSError('The remembered work folder is missing or disconnected.')
        return ready(chosen)
    except OSError as error:
        base=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))
        fallback=ready(base/'Collaborative Dynamics'/product)
        (fallback/'.location-warning.txt').write_text('Could not use '+str(chosen)+': '+str(error)+'\nOpened a writable work folder instead. Use Work folder to reconnect your existing work.',encoding='utf-8')
        return fallback

class Materials:
    def __init__(self,root,product,entry,flag):
        self.root=Path(root);self.product=product;self.entry=Path(entry);self.flag=flag
    def handle(self,path,data):
        if path=='/api/location':
            if not data.get('path'):return {'path':str(self.root),'warning':(self.root/'.location-warning.txt').read_text(encoding='utf-8') if (self.root/'.location-warning.txt').exists() else ''}
            chosen=Path(data['path']).expanduser().resolve()
            if chosen==self.entry.parent.parent or self.entry.parent.parent in chosen.parents:raise ValueError('Choose a work folder outside the installed app.')
            chosen=ready(chosen)
            proc=subprocess.run([sys.executable,'-B',str(self.entry),'--no-browser',self.flag,str(chosen)],capture_output=True,text=True,timeout=30,creationflags=(0x08000000 if os.name=='nt' else 0))
            if proc.returncode:raise ValueError(proc.stderr.strip() or proc.stdout.strip() or 'Could not open that work folder. Choose another folder.')
            line=proc.stdout.strip().splitlines()[-1]
            url=json.loads(line)['url'] if line.startswith('{') else line
            if not url.startswith('http://127.0.0.1:'):raise ValueError('The new workspace did not report its address.')
            selector=config_file(self.product);selector.parent.mkdir(parents=True,exist_ok=True);selector.write_text(str(chosen),encoding='utf-8')
            return {'path':str(chosen),'url':url}
        if path=='/api/browse':
            folder=Path(data.get('path') or self.root).expanduser().resolve()
            if not folder.is_dir():raise ValueError('That folder does not exist. Enter an existing folder path.')
            items=[]
            for p in sorted(folder.iterdir(),key=lambda p:(not p.is_dir(),p.name.casefold())):
                if len(items)>=500:break
                if p.name.startswith('.'):continue
                items.append({'name':p.name,'path':str(p),'directory':p.is_dir()})
            return {'path':str(folder),'parent':str(folder.parent),'items':items}
        if path in {'/api/material','/api/material-get'}:
            folder=self.root/'.materials';folder.mkdir(exist_ok=True)
            original=''
            if path.endswith('-get'):
                key=data.get('id','')
                if not key or any(c not in '0123456789abcdef' for c in key):raise ValueError('Invalid material reference')
                meta=json.loads((folder/(key+'.meta')).read_text(encoding='utf-8'));raw=(folder/key).read_bytes();return self.describe(raw,meta['name'],key,meta.get('original',''))
            if data.get('path'):
                source=Path(data['path']).expanduser().resolve()
                if not source.is_file():raise ValueError('Select an existing file.')
                if source.stat().st_size>32*1024*1024:raise ValueError('Select a file smaller than 32 MB; keep large source media as a path reference.')
                raw=source.read_bytes();name=source.name;original=str(source)
            else:
                name=Path(data.get('name','material').replace('\\','/')).name
                try:raw=base64.b64decode(data.get('base64',''),validate=True)
                except ValueError:raise ValueError('The file transfer was incomplete. Choose the file again.')
            if not raw:raise ValueError('This file is empty.')
            if len(raw)>32*1024*1024:raise ValueError('Select a file smaller than 32 MB.')
            key=hashlib.sha256(raw).hexdigest();result=self.describe(raw,name,key,original)
            (folder/key).write_bytes(raw);(folder/(key+'.meta')).write_text(json.dumps({'name':name,'original':original}),encoding='utf-8');return result
        raise ValueError('Unknown workspace operation')
    def describe(self,raw,name,key,original):
        suffix=Path(name).suffix.lower();mime=mimetypes.guess_type(name)[0] or 'application/octet-stream';text='';note=''
        if suffix in {'.txt','.md','.csv','.tsv','.srt','.vtt','.rst','.log','.json','.yaml','.yml'}:
            try:text=raw.decode('utf-8-sig')
            except UnicodeError:text=raw.decode('utf-16') if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else raw.decode('cp1252')
        elif suffix=='.docx':
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                member=z.getinfo('word/document.xml')
                if member.file_size>16*1024*1024:raise ValueError('The document is too large to read here.')
                root=ElementTree.fromstring(z.read(member));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text='\n'.join(''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in root.findall('.//w:p',ns))
        elif suffix=='.pdf':
            sys.path.insert(0,str(Path(__file__).parent/'vendor'))
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(raw));text='\n\n'.join(page.extract_text() or '' for page in reader.pages[:300])
            if not text.strip():note='This PDF contains scanned images. The original is retained; add a reading note or use OCR with your assistant.'
        elif mime.startswith('image/') and suffix in {'.png','.jpg','.jpeg','.gif','.webp'}:note='Original image retained for viewing.'
        else:note='Original retained as an attachment; this format has no built-in text extraction.'
        return {'id':key,'name':name,'original':original,'text':text[:2000000],'note':note,'mime':mime,'bytes':len(raw),'image':('data:'+mime+';base64,'+base64.b64encode(raw).decode()) if mime.startswith('image/') and suffix in {'.png','.jpg','.jpeg','.gif','.webp'} else ''}

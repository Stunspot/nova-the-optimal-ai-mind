"""Adapter over the authoritative OMNARA vault, never a parallel evidence database."""
import hashlib, io, json, re, shutil, tempfile, threading, uuid, zipfile
from pathlib import Path
from datetime import datetime, timezone
import research_campaign as native
from runtime import atomic

class CampaignRoom:
    class Conflict(ValueError): pass
    def __init__(self,root): self.root=root; self.lock=threading.RLock()
    def directory(self,key):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',key): raise ValueError('Invalid campaign identity')
        path=self.root/key
        if path.is_symlink(): raise ValueError('Linked campaign directories are not supported')
        return path
    def files(self,path):
        return {p.relative_to(path).as_posix():p.read_text(encoding='utf-8') for p in sorted(path.rglob('*')) if p.is_file() and not p.is_symlink() and p.suffix in {'.md','.json','.jsonl'} and '.workspace' not in p.parts}
    def revision(self,files): return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    def load(self,key):
        path=self.directory(key); files=self.files(path)
        return {'key':key,'files':files,'revision':self.revision(files),'validation':native.validate(path)}
    def checked_name(self,name):
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or p.suffix not in {'.md','.json','.jsonl'} or len(p.parts)>2: raise ValueError('Invalid vault file')
        if len(p.parts)==2 and p.parts[0] not in {'notes','draft'}: raise ValueError('Only native notes and draft subfolders are editable')
    def save(self,key,files,revision):
        destination=self.directory(key)
        if self.revision(self.files(destination))!=revision: raise self.Conflict('The agent or another window changed this vault. Reload before saving.')
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            staged=Path(temp)/'vault'; shutil.copytree(destination,staged)
            for name,text in files.items():
                self.checked_name(name)
                if (destination/name).is_symlink(): raise ValueError('Linked files are not editable')
                if not isinstance(text,str): raise ValueError('File contents must be text')
                atomic(staged/name,text)
            campaign=native.read_json(staged/'campaign.json')
            counts=native.source_counts(staged)
            campaign['counters'].update({state.replace('-','_'):counts[state] for state in native.SOURCE_STATES})
            campaign['counters']['queries']=len(native.read_jsonl(staged/'query-ledger.jsonl'))
            campaign['updated_at']=datetime.now(timezone.utc).isoformat()
            atomic(staged/'campaign.json',json.dumps(campaign,indent=2)+'\n')
            errors=native.validate(staged)
            if errors: raise ValueError('Save refused by the native campaign validator: '+'; '.join(errors))
            if self.revision(self.files(destination))!=revision: raise self.Conflict('Vault changed while validating; reload before saving.')
            # Preserve the prior native files for recoverable multi-file saves.
            snapshot=self.root/'.workspace'/'history'/key/uuid.uuid4().hex
            snapshot.mkdir(parents=True)
            for name,text in self.files(destination).items(): atomic(snapshot/name,text)
            for name,text in self.files(staged).items(): atomic(destination/name,text)
        return self.load(key)
    def request(self,method,path,data):
        with self.lock:
            if path=='/api/list':
                rows=[]
                for p in self.root.iterdir():
                    if p.is_dir() and not p.is_symlink() and (p/'campaign.json').is_file():
                        try:
                            c=native.read_json(p/'campaign.json'); rows.append({'key':p.name,'title':c['title'],'phase':c['phase'],'inquiry':c['canonical_inquiry']})
                        except Exception: pass
                return {'campaigns':rows,'data_root':str(self.root)}
            if path=='/api/create':
                if method!='POST': raise ValueError('POST required')
                if not str(data.get('title','')).strip() or not str(data.get('question','')).strip(): raise ValueError('A title and verbatim inquiry are required')
                key=uuid.uuid4().hex[:12]
                native.initialize(Path(__file__).parents[1]/'assets'/'campaign-vault',self.directory(key),data['title'],data['question'],'deep')
                return self.load(key)
            if path=='/api/import':
                if method!='POST': raise ValueError('POST required')
                source=Path(data['path']).resolve()
                if not source.is_dir() or source==self.root or self.root.is_relative_to(source): raise ValueError('Select one native campaign directory')
                if any(p.is_symlink() for p in source.rglob('*')): raise ValueError('Import refuses links; originals remain unchanged')
                errors=native.validate(source)
                if errors: raise ValueError('Native campaign import invalid: '+'; '.join(errors))
                key=uuid.uuid4().hex[:12]; shutil.copytree(source,self.directory(key))
                return self.load(key)
            key=data.get('key',''); directory=self.directory(key)
            if path=='/api/load': return self.load(key)
            if path=='/api/save' and method=='POST': return self.save(key,data['files'],data['revision'])
            if path=='/api/export':
                output=io.BytesIO()
                with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
                    for p in directory.rglob('*'):
                        if p.is_file() and not p.is_symlink(): archive.writestr(key+'/'+p.relative_to(directory).as_posix(),p.read_bytes())
                return output.getvalue(),'application/zip'
            if path=='/api/handoff':
                c=native.read_json(directory/'campaign.json')
                text='# OMNARA next research pass\n\nCampaign: '+str(directory)+'\n\nVerbatim inquiry: '+c['canonical_inquiry']+'\n\nResume point: '+c['resume_point']+'\n\nActive coverage: '+json.dumps(c['active_loci'])+'\n\nBlockers: '+json.dumps(c['blockers'])+'\n\nUse the native campaign vault, read research-brief.md, coverage-matrix.md, contradictions.md and the source/claim ledgers. Advance the first unverified edge. Preserve evidence states and audit consequential claims.\n'
                return text,'text/markdown; charset=utf-8'
            raise ValueError('Unknown action')

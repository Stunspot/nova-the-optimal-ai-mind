"""Native vault adapter. Local recoverable saves; coordinate external agent writers."""
import hashlib,io,json,re,tempfile,threading,uuid
from pathlib import Path
from datetime import datetime,timezone
import research_campaign as native
from evidence_contract import native_files,review_status,NATIVE_JSON,LEDGERS,text
from custody import reject_links,valid_name,namespace
from file_ops import atomic

class CampaignRoom:
    class Conflict(ValueError):pass
    def __init__(self,root):self.root=reject_links(root);self.lock=threading.RLock()
    def directory(self,key):
        if not isinstance(key,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',key):raise ValueError('Invalid campaign identity')
        return reject_links(self.root/key)
    def files(self,path):
        path=reject_links(path)
        return {p.relative_to(path).as_posix():p.read_text(encoding='utf-8') for p in native_files(path)}
    def revision(self,files):return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    def load(self,key):
        path=self.directory(key);files=self.files(path)
        return {'key':key,'files':files,'revision':self.revision(files),'validation':native.validate(path),'semantic_review':review_status(path)}
    def checked_name(self,name):
        if not isinstance(name,str):raise ValueError('Native filename must be text')
        valid_name(name);p=Path(name)
        if (p.suffix!='.md' and name not in NATIVE_JSON|LEDGERS) or len(p.parts)>2:raise ValueError('Invalid vault file')
        if len(p.parts)==2 and (p.parts[0] not in {'notes','draft'} or p.suffix!='.md'):raise ValueError('Only immediate native notes and draft Markdown are editable')
    def save(self,key,files,revision):
        if not isinstance(files,dict) or not isinstance(revision,str):raise ValueError('Save requires native files object and revision text')
        destination=self.directory(key);before=self.files(destination)
        if self.revision(before)!=revision:raise self.Conflict('The agent or another window changed this vault. Download your draft and reload before saving.')
        for name,value in files.items():
            self.checked_name(name);reject_links(destination/name)
            if not isinstance(value,str):raise ValueError('File contents must be text')
        namespace([(name,False) for name in set(before)|set(files)])
        original={p.relative_to(destination).as_posix():p.read_bytes() for p in native_files(destination)}
        with tempfile.TemporaryDirectory(prefix='.omnara-save-',dir=self.root) as tmp:
            staged=Path(tmp)/'vault';staged.mkdir()
            for name,value in {**before,**files}.items():atomic(staged/name,value)
            c=native.read_json(staged/'campaign.json');counts=native.source_counts(staged)
            if not isinstance(c.get('counters'),dict):raise ValueError('campaign counters must be an object')
            c['counters'].update({state.replace('-','_'):counts[state] for state in native.SOURCE_STATES});c['counters']['queries']=len(native.read_jsonl(staged/'query-ledger.jsonl'));c['updated_at']=datetime.now(timezone.utc).isoformat();atomic(staged/'campaign.json',json.dumps(c,indent=2)+'\n')
            errors=native.validate(staged)
            if errors:raise ValueError('Save refused by native validator: '+'; '.join(errors))
            if self.revision(self.files(destination))!=revision:raise self.Conflict('Vault changed while validating; download draft and reload.')
            snapshot=reject_links(self.root/'.workspace/history'/key/uuid.uuid4().hex);snapshot.mkdir(parents=True)
            for name,value in original.items():atomic(snapshot/name,value)
            written=[]
            try:
                for name,value in self.files(staged).items():atomic(destination/name,value);written.append(name)
            except OSError as exc:
                rollback=[]
                for name in reversed(written):
                    try:
                        if name in original:atomic(destination/name,original[name])
                        else:reject_links(destination/name).unlink(missing_ok=True)
                    except OSError as error:rollback.append(str(error))
                if rollback:raise ValueError('Save failed and rollback incomplete. Preserve draft; restore native files from '+str(snapshot)+': '+'; '.join(rollback)) from exc
                raise ValueError('Save failed; prior native files restored. Draft remains in browser. '+str(exc)) from exc
        return self.load(key)
    def request(self,method,path,data):
        if not isinstance(data,dict):raise ValueError('Request body must be an object')
        if method!='POST':raise ValueError('POST required for workspace API')
        with self.lock:
            if path=='/api/list':
                rows=[]
                for p in self.root.iterdir():
                    if p.name.startswith('.') or not p.is_dir() or not (p/'campaign.json').exists():continue
                    try:
                        self.directory(p.name);c=native.read_json(p/'campaign.json');sources=native.read_jsonl(p/'source-ledger.jsonl');claims=native.read_jsonl(p/'claim-ledger.jsonl')
                        if any(not isinstance(c.get(k,''),str) for k in ('title','phase','status','canonical_inquiry','updated_at')):raise ValueError('Campaign navigation fields must be text; repair campaign.json')
                        rows.append({'key':p.name,'title':c.get('title') if text(c.get('title')) else p.name,'phase':c.get('phase','unknown'),'status':c.get('status'),'inquiry':c.get('canonical_inquiry',''),'updated_at':c.get('updated_at',''),'source_count':len(sources),'claim_count':len(claims)})
                    except (ValueError,OSError,TypeError) as exc:
                        rows.append({'key':p.name,'title':p.name,'phase':'needs repair','status':'damaged','inquiry':'Native records could not be read. '+str(exc),'updated_at':'','error':str(exc),'path':str(p)})
                return {'campaigns':rows,'data_root':str(self.root)}
            if path=='/api/create':
                if not text(data.get('title')) or not text(data.get('question')):raise ValueError('A title and verbatim inquiry are required')
                key=uuid.uuid4().hex[:12];native.initialize(Path(__file__).parents[1]/'assets/campaign-vault',self.directory(key),data['title'],data['question'],'deep');return self.load(key)
            if path=='/api/import':
                if not text(data.get('path')):raise ValueError('Select one native campaign directory')
                source=reject_links(data['path'])
                if not source.is_dir() or source==self.root or self.root.is_relative_to(source):raise ValueError('Select one native campaign directory')
                errors=native.validate(source)
                if errors:raise ValueError('Native import invalid; repair a copy of the original first: '+'; '.join(errors))
                files=self.files(source);key=uuid.uuid4().hex[:12]
                with tempfile.TemporaryDirectory(prefix='.omnara-import-',dir=self.root) as tmp:
                    staged=Path(tmp)/'vault';staged.mkdir()
                    for name,value in files.items():atomic(staged/name,value)
                    staged.rename(self.directory(key))
                return self.load(key)
            key=data.get('key','');directory=self.directory(key)
            if path=='/api/load':return self.load(key)
            if path=='/api/save':return self.save(key,data.get('files'),data.get('revision'))
            if path=='/api/export':
                import zipfile
                files=self.files(directory);namespace([(key+'/'+name,False) for name in files]);output=io.BytesIO()
                with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
                    for name,value in files.items():archive.writestr(key+'/'+name,value)
                return output.getvalue(),'application/zip'
            if path=='/api/handoff':
                c=native.read_json(directory/'campaign.json');review=review_status(directory)
                value='# OMNARA next research pass\n\nCampaign: '+str(directory)+'\n\nVerbatim inquiry: '+str(c.get('canonical_inquiry','not recorded'))+'\n\nResume point: '+str(c.get('resume_point','not recorded'))+'\n\nActive coverage: '+json.dumps(c.get('active_loci',[]))+'\n\nBlockers: '+json.dumps(c.get('blockers',[]))+'\n\nDeclared semantic review: '+review['state']+'\n\nUse the native vault. Read research-brief.md, coverage-matrix.md, contradictions.md and source/claim ledgers. Advance the first unverified edge. Retain the current caller identity and existing authority. Inspect actual sources and report claims; state labels and this handoff are not evidence. Coordinate writes with the campaign room before changing files.\n'
                return value,'text/markdown; charset=utf-8'
            raise ValueError('Unknown action')

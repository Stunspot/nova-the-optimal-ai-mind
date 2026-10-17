"""Read-only inquiry discovery and evidence access for OMNARA Reading Room."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
import research_campaign as native
from evidence_contract import review_status, subject
from custody import reject_links
from file_ops import atomic

class ReadOnlyRoom:
    class Conflict(ValueError): pass
    def __init__(self, root, example_root=None):
        self.root=reject_links(Path(root)); self.example_root=reject_links(Path(example_root)) if example_root else None
        self.work=self.root/'.workspace'; self.prefs=self.work/'reading-room-preferences.json'
    def _folders(self):
        out=[]
        if (self.root/'campaign.json').is_file(): out.append(('__home__',self.root,False))
        for p in sorted(self.root.iterdir(),key=lambda p:p.name.casefold()):
            if p.name.startswith('.') or not p.is_dir(): continue
            try: reject_links(p)
            except (ValueError,OSError): continue
            if (p/'campaign.json').is_file(): out.append((p.name,p,False))
        if self.example_root and (self.example_root/'campaign.json').is_file(): out.append(('__example_sea_level__',self.example_root,True))
        return out
    def _path(self,key):
        for identity,path,is_example in self._folders():
            if identity==key:return path,is_example
        raise ValueError('That inquiry is no longer available. Refresh the inquiry list.')
    def _read(self,key):
        path,is_example=self._path(key)
        c=native.read_json(path/'campaign.json')
        sources=native.read_jsonl(path/'source-ledger.jsonl') if (path/'source-ledger.jsonl').exists() else []
        claims=native.read_jsonl(path/'claim-ledger.jsonl') if (path/'claim-ledger.jsonl').exists() else []
        files={p.relative_to(path).as_posix():p.read_text(encoding='utf-8') for p in native.native_files(path)}
        proof=subject(path); review=review_status(path)
        review_doc=native.read_json(path/'semantic-review.json') if (path/'semantic-review.json').is_file() else {}
        review.update({'reviewed_at':review_doc.get('reviewed_at'),'rationale':review_doc.get('rationale'),'review_subject':review_doc.get('subject_sha256')})
        report=files.get('report.md') or files.get('draft/01-report.md','')
        notes={name[6:-3]:value for name,value in files.items() if name.startswith('notes/') and name.endswith('.md') and name!='notes/SOURCE-NOTE-TEMPLATE.md'}
        return {'key':key,'example':is_example,'title':c.get('title') or c.get('canonical_inquiry') or 'Untitled inquiry','question':c.get('canonical_inquiry','Question not recorded'),'phase':c.get('phase','unknown'),'status':c.get('status','unknown'),'cutoff':c.get('evidence_cutoff') or 'Not recorded','updated':c.get('updated_at') or 'Not recorded','report':report,'sources':sources,'claims':claims,'notes':notes,'contradictions':files.get('contradictions.md',''),'review':review,'subject':proof['sha256'],'scope':proof['scope'],'resume_point':c.get('resume_point','Reopen the unresolved question and decide what evidence or decision would materially advance it.')}
    def _preferences(self):
        try:
            data=json.loads(self.prefs.read_text(encoding='utf-8'))
            return data if isinstance(data,dict) else {}
        except (OSError,ValueError): return {}
    def _cache_path(self,key,revision):
        safe=hashlib.sha256(key.encode()).hexdigest()[:24]
        return self.work/'reading-room-cache'/safe/(revision+'.json')
    def _archive_changed(self,key,previous,current,preference=None):
        if not previous or previous==current['subject']:return False
        old=self._cache_path(key,previous)
        if not old.is_file():return False
        dest=self.work/'reading-room-history'/hashlib.sha256(key.encode()).hexdigest()[:24]/(previous+'.json')
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            try:
                snapshot=json.loads(old.read_text(encoding='utf-8'))
                if preference is not None: snapshot['preference']=preference
                atomic(dest,json.dumps(snapshot,ensure_ascii=False))
            except (ValueError,OSError): atomic(dest,old.read_text(encoding='utf-8'))
        return True
    def _remember_cache(self,item):
        p=self._cache_path(item['key'],item['subject']);p.parent.mkdir(parents=True,exist_ok=True)
        # The snapshot contains only the report, retained notes and native source/claim metadata.
        atomic(p,json.dumps(item,ensure_ascii=False))
    def request(self,method,path,data):
        if method!='POST': raise ValueError('POST required')
        if path=='/api/reader/library':
            prefs=self._preferences()
            rows=[]
            for key,folder,is_example in self._folders():
                try:
                    c=native.read_json(folder/'campaign.json')
                    proof=subject(folder); review=review_status(folder)
                    rows.append({'key':key,'title':c.get('title') or c.get('canonical_inquiry') or 'Untitled inquiry','question':c.get('canonical_inquiry','Question not recorded'),'phase':c.get('phase','unknown'),'status':c.get('status','unknown'),'cutoff':c.get('evidence_cutoff') or 'Not recorded','updated':c.get('updated_at') or 'Not recorded','example':is_example,'review':review,'subject':proof['sha256']})
                except (ValueError,OSError,TypeError) as exc:
                    rows.append({'key':key,'title':folder.name,'question':'Native records could not be read.','error':str(exc),'example':is_example})
            resume=prefs.get('__last__');resume_item=next((x for x in rows if x.get('key')==resume),None)
            return {'inquiries':rows,'home':str(self.root),'resume':({'key':resume_item['key'],'title':resume_item['title'],'question':resume_item['question'],'example':resume_item.get('example',False),'preference':prefs.get(resume,{}).get('preference',{})} if resume_item else None)}
        if path=='/api/reader/open':
            key=data.get('key');item=self._read(key);prefs=self._preferences();old=prefs.get(key,{})
            item['changed_since_last_read']=self._archive_changed(key,old.get('revision'),item,old.get('preference',{}))
            item['preference']=old.get('preference',{})
            self._remember_cache(item)
            prefs[key]={'revision':item['subject'],'preference':old.get('preference',{})};prefs['__last__']=key
            self.work.mkdir(parents=True,exist_ok=True);atomic(self.prefs,json.dumps(prefs,ensure_ascii=False,indent=2)+'\n')
            return item
        if path=='/api/reader/preference':
            key=data.get('key');revision=data.get('revision');pref=data.get('preference')
            if not isinstance(key,str) or not isinstance(revision,str) or not isinstance(pref,dict):raise ValueError('Reading position needs an inquiry, revision and preference object.')
            current=self._read(key)
            if current['subject']!=revision:return {'saved':False,'stale':True,'preference':None}
            prefs=self._preferences();prefs[key]={'revision':revision,'preference':{'scrollY':max(0,min(int(pref.get('scrollY',0)),2000000)),'source':str(pref.get('source',''))[:100],'compare':str(pref.get('compare',''))[:100],'theme':str(pref.get('theme','tracework')) if pref.get('theme') in {'tracework','surveyfolio','proofcabinet'} else 'tracework','updated_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}}
            self.work.mkdir(parents=True,exist_ok=True);atomic(self.prefs,json.dumps(prefs,ensure_ascii=False,indent=2)+'\n')
            return {'saved':True,'preference':prefs[key]['preference']}
        if path=='/api/reader/search':
            query=data.get('query','')
            if not isinstance(query,str):raise ValueError('Search text must be text.')
            query=query.strip()[:160]
            if not query:return {'results':[]}
            results=[];needle=query.casefold()
            for key,folder,is_example in self._folders():
                try:
                    c=native.read_json(folder/'campaign.json');title=c.get('title') or 'Untitled inquiry'
                    files={p.relative_to(folder).as_posix():p.read_text(encoding='utf-8') for p in native.native_files(folder)}
                    report=files.get('report.md') or files.get('draft/01-report.md','')
                    if needle in title.casefold() or needle in str(c.get('canonical_inquiry','')).casefold():
                        results.append({'key':key,'title':title,'kind':'Inquiry question','source_id':'','context':str(c.get('canonical_inquiry') or title)})
                    for i,part in enumerate(re.split(r'\n\s*\n',report)):
                        if needle in part.casefold():results.append({'key':key,'title':title,'kind':'Report passage','source_id':'','index':i,'context':part[:520]})
                    sources=native.read_jsonl(folder/'source-ledger.jsonl') if (folder/'source-ledger.jsonl').exists() else []
                    byid={x.get('id'):x for x in sources}
                    for sid,source in byid.items():
                        descriptor=' '.join(str(source.get(k,'')) for k in ('title','url','identifier'))
                        if needle in descriptor.casefold():results.append({'key':key,'title':title,'kind':'Source record','source_id':sid,'context':descriptor[:520]})
                        note=files.get('notes/'+str(sid)+'.md','')
                        for i,part in enumerate(re.split(r'\n\s*\n',note)):
                            if needle in part.casefold():results.append({'key':key,'title':title,'kind':'Retained note','source_id':sid,'index':i,'context':part[:520]})
                except (ValueError,OSError,TypeError):continue
                if len(results)>=40:break
            return {'results':results[:40]}
        if path=='/api/reader/history':
            key=data.get('key');safe=hashlib.sha256(str(key).encode()).hexdigest()[:24];folder=self.work/'reading-room-history'/safe
            rows=[]
            if folder.exists():
                for p in sorted(folder.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True):
                    try:
                        item=json.loads(p.read_text(encoding='utf-8'));rows.append({'subject':item['subject'],'title':item['title'],'question':item.get('question',item['title']),'cutoff':item.get('cutoff','Not recorded'),'updated':item['updated'],'report':item['report'],'sources':item['sources'],'notes':item['notes'],'claims':item['claims'],'review':item['review'],'scope':item.get('scope',''),'preference':item.get('preference',{}),'historical':True})
                    except (ValueError,OSError,KeyError):continue
            return {'versions':rows}
        raise ValueError('Unknown Reading Room operation')




#!/usr/bin/env python3
"""Inspect a local application draft, record a declared review, or export selected files.

No network, hiring score, factual authentication, user attestation or submission.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from types import MappingProxyType

FORMAT = 'job-application-packet/v2'
MAX_TEXT = 2 * 1024 * 1024
SOURCE_HEADERS = ('source_id','source_type','title_or_identity','path_or_url','source_date','retrieved_at','custody','use','notes','origin','subject','state','sha256')
MATRIX_HEADERS = ('criterion_id','criterion_text','criterion_type','importance','evidence_id','evidence_source','evidence_strength','proposed_claim','support_status','destinations','confirmation_status','risk_note')
SUPPORTED = {'documented','user-confirmed','reasonable-paraphrase'}
ARTIFACTS = {'resume','cover-letter','application-answers','work-sample-guidance'}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def regular(path):
    path=Path(os.path.abspath(path))
    for p in (path,*path.parents):
        if p.exists() or p.is_symlink():
            if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0) & getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400):
                raise ValueError('Linked/reparse path is not accepted: '+str(p))
    return path

def local(root,name):
    if not isinstance(name,str) or not name or '\\'in name:raise ValueError('Expected relative file path')
    for part in name.split('/'):
        if not part or part in {'.','..'} or part[-1]in '. ' or re.search(r'[\x00-\x1f<>:"|?*]',part) or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?',part):raise ValueError('Unsafe file path: '+name)
    return regular(root.joinpath(*name.split('/')))
def raw(path):
    regular(path)
    if not path.is_file():raise ValueError('Missing regular file: '+str(path))
    if path.stat().st_size>MAX_TEXT:raise ValueError('Text input exceeds 2 MiB: '+path.name)
    return path.read_bytes()
def text(path,reader=None):return (reader or raw)(path).decode('utf-8-sig')
def strict_json(path,reader=None):
    def pairs(rows):
        out={}
        for k,v in rows:
            if k in out:raise ValueError('Duplicate JSON field: '+k)
            out[k]=v
        return out
    def finite(s):
        n=float(s)
        if not math.isfinite(n):raise ValueError('Non-finite JSON number')
        return n
    def bad(s):raise ValueError('Non-JSON number: '+s)
    return json.loads(text(path,reader),object_pairs_hook=pairs,parse_float=finite,parse_constant=bad)
def csv_rows(path,expected,reader=None):
    records=list(csv.reader(io.StringIO(text(path,reader),newline=''),strict=True))
    if not records:raise ValueError('Empty CSV: '+path.name)
    header=records[0]
    if len(set(header))!=len(header):raise ValueError('Duplicate CSV header: '+path.name)
    if set(header)!=set(expected):raise ValueError('CSV headers must be exactly '+','.join(expected)+': '+path.name)
    out=[]
    for index,row in enumerate(records[1:],2):
        if not row:continue
        if len(row)!=len(header):raise ValueError(f'{path.name} row {index}: wrong number of cells')
        out.append(dict(zip(header,row)))
    return out
def split(s):return [x.strip()for x in re.split('[;,]',s)if x.strip()]
def instant(value):
    if not isinstance(value,str)or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)',value):raise ValueError('Timestamp needs a valid date, seconds and explicit Z or +/-HH:MM offset')
    return dt.datetime.fromisoformat(value.replace('Z','+00:00'))
def meaningful(value):return isinstance(value,str)and bool(re.search(r'\w',value))
def require(value,message):
    if not value:raise ValueError(message)
def words(s):return len(re.findall(r'\S+',s))
def snapshot(root):
    entries={}
    for p in sorted(root.rglob('*')):
        regular(p)
        relative=p.relative_to(root).as_posix()
        if p.is_file()and not relative.startswith('reviews/'):
            entries[relative]=sha(p.read_bytes())
    return sha(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()),entries

class CapturedPacket:
    """One immutable generation supplies both inspection and selected export bytes."""
    def __init__(self,root):
        self.root=regular(root);require(self.root.is_dir(),'Packet directory does not exist')
        before=snapshot(self.root)[0];files={}
        for p in sorted(self.root.rglob('*')):
            regular(p);name=p.relative_to(self.root).as_posix()
            if p.is_file()and not name.startswith('reviews/'):
                files[name]=p.read_bytes()
        entries={name:sha(data)for name,data in files.items()}
        self.digest=sha(json.dumps(entries,sort_keys=True,separators=(',',':')).encode())
        require(self.digest==before==snapshot(self.root)[0],'Private case changed during inspection capture; retry stable files')
        self.files=MappingProxyType(files)
    def read(self,path):
        name=Path(path).relative_to(self.root).as_posix()
        require(name in self.files,'Missing regular file in captured packet: '+name)
        data=self.files[name]
        require(len(data)<=MAX_TEXT,'Text input exceeds 2 MiB: '+name)
        return data

def inspect(root,as_of=None,*,_captured=None):
    root=regular(root);require(root.is_dir(),'Packet directory does not exist')
    captured=_captured if _captured is not None else CapturedPacket(root)
    require(captured.root==root,'Captured packet root differs')
    if 'case.json'not in captured.files:
        # Legacy records remain inspectable, but old declarations are never promoted to v2 review.
        import importlib.util
        spec=importlib.util.spec_from_file_location("job_application_legacy",Path(__file__).with_name("legacy_check_packet.py"));legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
        csv_rows(root/'source-register.md',legacy.SOURCE_HEADERS);csv_rows(root/'evidence-claim-matrix.csv',legacy.MATRIX_HEADERS)
        result=legacy.check_packet(root);result.update(format='legacy',state='legacy_unreviewed',ready_for_handoff=False,next_actions=['Preserve the original folder; follow the v2 migration guide before current review or export.']);return result
    initial_snapshot=captured.digest
    case=strict_json(root/'case.json',captured.read);require(isinstance(case,dict)and case.get('format')==FORMAT,'Expected v2 case object')
    for key in ('case_id','candidate_id'):require(meaningful(case.get(key)),'Missing '+key)
    require(type(case.get('revision'))is int and case['revision']>=1,'Revision must be a positive integer')
    require(case.get('purpose')in {'real','practice'},'Purpose must be real or practice')
    issues=[];warnings=[]
    vacancy=case.get('vacancy');require(isinstance(vacancy,dict),'Vacancy must be an object')
    for key in ('employer','title'):require(meaningful(vacancy.get(key)),'Vacancy missing '+key)
    require(vacancy.get('coverage')in {'complete','partial','unknown'},'Invalid posting coverage')
    if vacancy['coverage']!='complete':issues.append('Obtain missing posting/instructions; present coverage is '+vacancy['coverage'])
    deadline=vacancy.get('deadline');require(isinstance(deadline,dict),'Missing deadline record')
    require(deadline.get('status')in {'known','unknown','not-stated'},'Invalid deadline status')
    require(isinstance(deadline.get('wording'),str),'Preserve deadline wording')
    if deadline['status']=='known':
        end=instant(deadline.get('instant'));now=instant(as_of)if as_of else dt.datetime.now(dt.timezone.utc)
        if now>=end:issues.append('Deadline has passed at the stated check time; verify an extension before handoff')
    else:
        require(deadline.get('instant')is None,'Unresolved/not-stated deadline cannot carry a resolved instant')
        if deadline['status']=='unknown':issues.append('Resolve deadline/time zone; do not assume midnight or local time')
    sources=csv_rows(root/'source-register.csv',SOURCE_HEADERS,captured.read);source_by={}
    for s in sources:
        sid=s['source_id'];require(re.fullmatch(r'SRC-\d{3,}',sid)and sid not in source_by,'Invalid or duplicate source ID: '+sid)
        require(s['origin']in {'user-record','user-statement','employer','third-party','fictional','unknown'},sid+': invalid origin')
        require(s['use']in {'vacancy','candidate-evidence','context','sample'},sid+': invalid use')
        require(s['state']in {'current','conflicted','unverified'},sid+': invalid source state')
        for key in ('title_or_identity','custody'):require(meaningful(s[key]),sid+': missing '+key)
        if s['path_or_url'].startswith('file:'):
            p=local(root,s['path_or_url'][5:]);data=captured.read(p);require(re.fullmatch('[0-9a-f]{64}',s['sha256'])and sha(data)==s['sha256'],sid+': retained source bytes differ or hash missing')
        elif not meaningful(s['path_or_url']):issues.append(sid+': name where the supplied record or statement can be found')
        source_by[sid]=s
    posting=vacancy.get('source_ids');require(isinstance(posting,list)and all(isinstance(x,str)for x in posting),'Vacancy source_ids must be a list')
    for sid in posting:
        require(sid in source_by and source_by[sid]['use']=='vacancy',sid+': missing vacancy source')
        source=source_by[sid]
        if source['state']!='current':issues.append(sid+': reconcile conflicted/unverified posting instructions')
        if case['purpose']=='real'and source['origin']in {'fictional','unknown'}:issues.append(sid+': obtain an actual accountable vacancy source; practice/unknown origin is not a real posting')
    if not posting:issues.append('Retain a vacancy source or mark its absence before review')
    selected=case.get('artifacts');require(isinstance(selected,list),'artifacts must be an array')
    require(len(selected)>0,'Select at least one useful applicant-facing artifact')
    artifacts={};prose={};paths=set()
    for a in selected:
        require(isinstance(a,dict)and a.get('id')in ARTIFACTS,'Invalid artifact record')
        aid=a['id'];require(aid not in artifacts,'Duplicate artifact identity')
        require(a.get('path')in {aid+'.md',aid+'.txt'},aid+': use its named Markdown/text file in the case root; private source/review paths are not applicant artifacts')
        p=local(root,a.get('path'));require(p.suffix.lower()in {'.md','.txt'},'Native reviewed export supports Markdown/text; render other formats separately and inspect them')
        require(a['path'].casefold()not in paths,'Duplicate artifact path');paths.add(a['path'].casefold())
        require(a.get('allowed')is None or type(a.get('allowed'))is bool,'Artifact allowed must be true, false or null')
        if a['allowed']is not True:issues.append(aid+': resolve whether employer permits this document; exclude forbidden documents')
        if a['path']not in captured.files:issues.append(aid+': draft the selected file');body=''
        else:body=text(p,captured.read)
        if not re.search(r'(?m)^(?!\s*#)\s*\w.{15,}',body):issues.append(aid+': selected document has no substantive draft')
        require(a.get('required_format')in {'markdown','text','pdf','docx','unknown'},aid+': invalid requested format')
        if a['required_format']not in {'markdown','text'}:issues.append(aid+': '+a['required_format']+' format requires separate conversion/render inspection; native export is a working text copy')
        for field,count in [('max_words',words(body)),('max_characters',len(body))]:
            limit=a.get(field);require(limit is None or(type(limit)is int and limit>=0),aid+': invalid '+field)
            if limit is not None and count>limit:issues.append(f'{aid}: {field} exceeded ({count}/{limit})')
        artifacts[aid]=a;prose[aid]=body
    rows=csv_rows(root/'evidence-claim-matrix.csv',MATRIX_HEADERS,captured.read);bindings={};criteria={};seen=set()
    if not rows:issues.append('Map the relevant criteria and material candidate claims before review')
    for index,r in enumerate(rows,2):
        cid=r['criterion_id'];claim=r['proposed_claim'];status=r['support_status'];confirmation=r['confirmation_status'];evidence=r['evidence_id'];dest=split(r['destinations']);sids=split(r['evidence_source'])
        require(re.fullmatch(r'[A-Za-z]+-\d{3,}',cid),'Invalid criterion ID')
        require(meaningful(r['criterion_text']),'Criterion text is empty')
        c=(r['criterion_text'],r['criterion_type'],r['importance']);require(cid not in criteria or criteria[cid]==c,cid+': contradictory criterion');criteria[cid]=c
        require(r['criterion_type']in {'required','preferred','responsibility','context','administrative'},cid+': invalid criterion type')
        require(r['importance']in {'high','medium','low'},cid+': invalid importance')
        require(status in SUPPORTED|{'confirmation-needed','unsupported'},cid+': invalid support')
        require(r['evidence_strength']in {'direct','adjacent','self-report','none'},cid+': invalid evidence strength')
        require(confirmation in {'confirmed','confirmation-needed','unresolved','not-applicable'},cid+': invalid confirmation')
        require(all(x in artifacts for x in dest),cid+': destination is not a selected artifact')
        require(all(x in source_by for x in sids),cid+': unknown evidence source')
        key=(cid,evidence,claim.casefold());require(key not in seen,cid+': duplicate claim row');seen.add(key)
        if evidence:
            require(re.fullmatch(r'EVD-\d{3,}',evidence),'Invalid evidence ID');binding=(tuple(sorted(sids)),r['evidence_strength']);require(evidence not in bindings or bindings[evidence]==binding,evidence+': inconsistent source/strength');bindings[evidence]=binding
        if status in SUPPORTED:
            require(bool(evidence and sids and dest and meaningful(claim)),cid+': supported claim needs evidence, sources, text and selected destination')
            require(r['evidence_strength']!='none'and confirmation in {'confirmed','not-applicable'},cid+': supported claim has unresolved confirmation or no evidence strength')
            for sid in sids:
                s=source_by[sid];require(s['use']=='candidate-evidence'and s['subject']==case['candidate_id'],cid+': source does not describe this candidate evidence')
                require(s['state']=='current',cid+': conflicted/unverified evidence cannot support final claim')
                require(s['origin']in ({'user-record','user-statement','third-party'}if case['purpose']=='real'else {'user-record','user-statement','third-party','fictional'}),cid+': source origin cannot support this case purpose')
            if status=='user-confirmed':require(any(source_by[x]['origin']=='user-statement'for x in sids),cid+': user-confirmed needs an accountable user statement')
            for target in dest:require(claim in prose[target],cid+': declared exact claim fragment absent from '+target)
        else:
            require(not dest,cid+': unresolved/unsupported claims must not be assigned to final documents')
            if claim:require(not any(' '.join(claim.casefold().split())in ' '.join(body.casefold().split())for body in prose.values()),cid+': unresolved exact claim appears in final draft')
            require(meaningful(r['risk_note']),cid+': name gap and next action')
            if r['criterion_type']in {'required','administrative'}:issues.append(cid+': '+r['risk_note'])
            else:warnings.append(cid+': preferred/context gap retained: '+r['risk_note'])
    checks=case.get('checks');require(isinstance(checks,list),'checks must be an array')
    checkids=set()
    for c in checks:
        require(isinstance(c,dict)and meaningful(c.get('id'))and c['id']not in checkids,'Invalid/duplicate condition');checkids.add(c['id'])
        require(c.get('state')in {'met','unmet','unknown','not-applicable'},'Invalid condition state')
        require(type(c.get('blocking'))is bool,'Condition blocking must be boolean')
        require(meaningful(c.get('requirement')),'Missing condition requirement')
        if c['state']in {'met','not-applicable'}:require(meaningful(c.get('basis')),c['id']+': declare evidence or rationale')
        else:
            require(meaningful(c.get('next_action')),c['id']+': unresolved condition needs next action')
            (issues if c['blocking']else warnings).append(c['id']+': '+c['state']+' — '+c['next_action'])
    for kind in ('eligibility','instructions','privacy'):
        if not any(c.get('kind')==kind for c in checks):issues.append('Review material '+kind+' conditions or explicitly record not applicable')
    questions=case.get('questions');require(isinstance(questions,list),'questions must be an array');qids=set()
    for q in questions:
        require(isinstance(q,dict)and meaningful(q.get('id'))and q['id']not in qids,'Invalid/duplicate question');qids.add(q['id']);require(meaningful(q.get('text')),'Question text missing')
        require(q.get('source_id')in posting,'Question needs a registered vacancy source')
        answer=q.get('answer');require(isinstance(answer,str),'Answer must be text, empty when unknown')
        if not meaningful(answer):issues.append(q['id']+': answer the question or obtain required user facts')
        else:require('application-answers'in prose and answer in prose['application-answers'],q['id']+': answer does not match selected answer document')
        for field,count in [('max_words',words(answer)),('max_characters',len(answer))]:
            limit=q.get(field);require(limit is None or(type(limit)is int and limit>=0),'Invalid answer limit')
            if limit is not None and count>limit:issues.append(f"{q['id']}: {field} exceeded ({count}/{limit})")
        require(type(q.get('requires_user_confirmation'))is bool,'Question confirmation flag must be boolean')
        if q['requires_user_confirmation']:
            sid=q.get('confirmation_source');s=source_by.get(sid,{})
            if not(s.get('origin')=='user-statement'and s.get('subject')==case['candidate_id']and s.get('state')=='current'):issues.append(q['id']+': user confirmation/attestation remains unresolved')
    sub=case.get('submission');require(isinstance(sub,dict)and sub.get('state')in {'not-submitted','outcome-unknown','observed-submitted'},'Invalid submission state')
    if sub['state']=='observed-submitted':
        require(meaningful(sub.get('authority_reference'))and meaningful(sub.get('receipt_reference')),'Observed submission requires authority and receipt references');instant(sub.get('observed_at'))
        warnings.append('Submitted is a recorded observation, not proof this tool submitted or authenticated a receipt')
    elif sub['state']=='outcome-unknown':issues.append('Submission outcome unknown; verify the prior attempt before retrying')
    digest,entries=snapshot(root);require(digest==initial_snapshot,'Private case changed during inspection; retry stable files');review=None
    reviewdir=root/'reviews'
    if reviewdir.exists():
        regular(reviewdir);require(reviewdir.is_dir(),'reviews must be a directory')
        for p in sorted(reviewdir.glob('*.json')):
            r=strict_json(p);require(isinstance(r,dict),'Review must be an object');instant(r.get('reviewed_at'))
            require(r.get('actor')in {'agent','user'}and meaningful(r.get('reviewer'))and meaningful(r.get('basis')),'Review needs declared actor, reviewer and basis')
            if r.get('snapshot_sha256')==digest:review=r
    if case['purpose']=='practice':warnings.append('Fictional/practice packet — never a real application handoff')
    state='draft'if issues else 'reviewed'if review else 'ready-for-review'
    return {'ok':True,'format':FORMAT,'purpose':case['purpose'],'state':state,'errors':[],'warnings':warnings,'next_actions':issues+([]if review else ['Perform semantic/privacy review of current files, then record the declared review.']),'snapshot_sha256':digest,'review':review,'ready_for_handoff':not issues and bool(review)and case['purpose']=='real'and sub['state']=='not-submitted','selected_files':[a['path']for a in selected],'check_time':as_of or dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'Declared consistency, exact fragments and byte custody only; not truth, completeness, legal, ATS, hiring or submission proof'}

def check_packet(root,as_of=None,*,_captured=None):
    try:return inspect(Path(root),as_of,_captured=_captured)
    except (OSError,UnicodeError,ValueError,csv.Error,RecursionError,KeyError,TypeError,AttributeError)as e:return {'ok':False,'state':'invalid-data','errors':[str(e)],'warnings':[],'next_actions':['Preserve the original packet; correct the named record and retry.'],'ready_for_handoff':False}

def record_review(root,reviewer,basis,actor,as_of=None):
    result=check_packet(root,as_of);require(result['ok']and result.get('format')==FORMAT,'Valid v2 packet required before review')
    require(meaningful(reviewer)and meaningful(basis),'Review needs reviewer and actual review basis')
    target=regular(root/'reviews');target.mkdir(exist_ok=True);now=dt.datetime.now(dt.timezone.utc);r={'format':'job-application-review/v1','reviewed_at':now.isoformat(),'actor':actor,'reviewer':reviewer,'basis':basis,'snapshot_sha256':result['snapshot_sha256'],'boundary':'Declared review, not authenticated approval, submission authority or outcome'}
    p=target/(now.strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
    return {'review_record':str(p),**check_packet(root,as_of)}

def export_packet(root,destination,as_of=None,allow_draft=False):
    root=regular(root);captured=CapturedPacket(root)
    result=check_packet(root,as_of,_captured=captured);require(result['ok']and result.get('format')==FORMAT,'Valid v2 packet required')
    require(result['ready_for_handoff']or allow_draft,'Current reviewed real packet required; --draft explicitly exports an unready working copy')
    target=regular(destination);require(not target.exists(),'Export destination exists; choose a new directory')
    require(not target.is_relative_to(root)and not root.is_relative_to(target),'Export must be outside the private case')
    payload={}
    for name in result['selected_files']:
        source=local(root,name);payload[name]=captured.read(source)
    require(snapshot(root)[0]==result['snapshot_sha256'],'Private case changed during export; retry a stable review')
    manifest={'format':'job-application-export/v1','working_copy':bool(allow_draft or not result['ready_for_handoff']),'purpose':result['purpose'],'state':result['state'],'files':{name:sha(data)for name,data in payload.items()},'source_snapshot':result['snapshot_sha256'],'boundary':'Selected Markdown/text files only; no source ledger or private review notes. Check requested upload format and portal preview independently.'}
    target.parent.mkdir(parents=True,exist_ok=True);target.mkdir() # Exclusive reservation on every supported platform.
    marker=target/'EXPORT-INCOMPLETE.txt'
    try:
        marker.write_text('Export incomplete. Keep this folder and the private source case. Use a different new destination after checking the original error; do not submit partial files.\n',encoding='utf8',newline='\n')
        for name,data in payload.items():
            with (target/name).open('xb')as f:f.write(data)
        with (target/'EXPORT-README.json').open('x',encoding='utf8',newline='\n')as f:json.dump(manifest,f,indent=2);f.write('\n')
        marker.unlink()
        return {'ok':True,'export':str(target),'manifest':manifest}
    except Exception as error:
        raise ValueError('Export incomplete; preserve '+str(target)+' and source case; choose a new output after inspecting the error: '+str(error))from error

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('packet',type=Path);p.add_argument('--json',action='store_true');p.add_argument('--as-of',help='Explicit aware timestamp for reproducible deadline check');p.add_argument('--record-review',action='store_true');p.add_argument('--reviewer');p.add_argument('--basis');p.add_argument('--actor',choices=['agent','user'],default='agent');p.add_argument('--export',type=Path);p.add_argument('--draft',action='store_true',help='Export only a labeled unready working copy')
    a=p.parse_args(argv)
    try:
        root=regular(a.packet);require(not(a.record_review and a.export),'Review and export are separate operations')
        if a.record_review:r=record_review(root,a.reviewer,a.basis,a.actor,a.as_of)
        elif a.export:r=export_packet(root,a.export,a.as_of,a.draft)
        else:r=check_packet(root,a.as_of)
    except (OSError,ValueError,TypeError)as e:r={'ok':False,'errors':[str(e)],'ready_for_handoff':False}
    if a.json:print(json.dumps(r,ensure_ascii=True,indent=2))
    else:
        print(r.get('state','exported'if r['ok']else'invalid-data'))
        for x in r.get('errors',[])+r.get('next_actions',[])+r.get('warnings',[]):print(x)
        print('Ready for handoff: '+str(r.get('ready_for_handoff',False)))
    return 0 if r['ok']else 1
if __name__=='__main__':raise SystemExit(main())
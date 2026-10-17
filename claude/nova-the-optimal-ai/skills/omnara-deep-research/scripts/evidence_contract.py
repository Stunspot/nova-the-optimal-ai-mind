"""Content identity and bounded Markdown projection; never semantic approval."""
from __future__ import annotations
import hashlib, json, math, re
from datetime import datetime, timezone
from pathlib import Path
from custody import reject_links, namespace

SOURCE_ID=re.compile(r'S[0-9]{3,}\Z')
CLAIM_ID=re.compile(r'C[0-9]{3,}\Z')
MARKER=re.compile(r'\[(S[0-9]{3,})\]')
NATIVE_JSON={'campaign.json','citation-audit-structural.json','semantic-review.json'}
LEDGERS={'source-ledger.jsonl','claim-ledger.jsonl','query-ledger.jsonl'}

def pairs(items):
    out={}
    for key,value in items:
        if key in out:raise ValueError(f'duplicate JSON key: {key}')
        out[key]=value
    return out

def finite_float(value):
    number=float(value)
    if not math.isfinite(number):raise ValueError('non-finite JSON number: '+value)
    return number

def loads(text):return json.loads(text,object_pairs_hook=pairs,parse_float=finite_float,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('non-finite JSON number: '+value)))
def read_json(path):
    value=loads(reject_links(path).read_text(encoding='utf-8'))
    if not isinstance(value,dict):raise ValueError(f'{Path(path).name}: expected JSON object')
    return value

def read_jsonl(path):
    result=[]
    for number,line in enumerate(reject_links(path).read_text(encoding='utf-8').splitlines(),1):
        if not line.strip():continue
        try:value=loads(line)
        except ValueError as exc:raise ValueError(f'{Path(path).name}:{number}: {exc}') from exc
        if not isinstance(value,dict):raise ValueError(f'{Path(path).name}:{number}: expected object')
        result.append(value)
    return result

def text(value):return isinstance(value,str) and bool(value.strip())
def clock(value):
    if not isinstance(value,str) or value.endswith('-00:00'):return None
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        try:return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
        except ValueError:return None
    match=re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|([+-])(\d{2}):(\d{2}))',value)
    if not match or (match.group(1) and (int(match.group(2))>23 or int(match.group(3))>59)):return None
    try:return datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:return None

def precedes(first,second):
    """Compare known instants; retain only day precision for date-only records."""
    a,b=clock(first),clock(second)
    if a is None or b is None:return False
    if 'T' in first and 'T' in second:return a<b
    return a.date()<b.date()

def native_files(path):
    path=reject_links(path)
    if not path.is_dir():raise ValueError('campaign directory missing: '+str(path))
    files=[]
    for p in path.iterdir():
        if p.name in {'notes','draft'}:
            reject_links(p)
            if not p.is_dir():raise ValueError(f'{p.name}: expected native directory')
            for q in p.iterdir():
                if q.suffix=='.md':
                    reject_links(q)
                    if not q.is_file():raise ValueError(f'{q.name}: expected regular note/draft')
                    files.append(q)
        elif p.suffix=='.md' or p.name in NATIVE_JSON|LEDGERS:
            reject_links(p)
            if not p.is_file():raise ValueError(f'{p.name}: expected regular native file')
            files.append(p)
    namespace([(p.relative_to(path).as_posix(),False) for p in files])
    return sorted(files,key=lambda p:p.relative_to(path).as_posix())

def sha(path):return hashlib.sha256(reject_links(path).read_bytes()).hexdigest()
def subject(directory):
    directory=reject_links(directory);c=read_json(directory/'campaign.json')
    # Administrative lifecycle/counter changes do not change the inquiry. All other
    # campaign fields and all native evidence prose/ledgers do. Drafts are included:
    # a differing section must not silently coexist with an approved report.
    administrative={'phase','status','counters','created_at','updated_at','resume_point','last_verified_artifact'}
    frame={k:v for k,v in c.items() if k not in administrative}
    hashes={p.relative_to(directory).as_posix():sha(p) for p in native_files(directory) if p.name not in {'campaign.json','citation-audit-structural.json','semantic-review.json'}}
    payload={'format':'omnara-review-subject/v1','campaign':frame,'files_sha256':hashes}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    return {'format':'omnara-review-subject/v1','sha256':digest,'files_sha256':hashes,'scope':'Native campaign content and declared evidence only; external URLs and unbundled originals are not captured or authenticated.'}

def visible_report(report):
    lines=[];fence=None;comment=False
    for line in report.splitlines():
        if fence:
            if re.fullmatch(r' {0,3}'+re.escape(fence[0])+'{'+str(len(fence))+r',}\s*',line):fence=None
            lines.append('');continue
        m=re.match(r'^ {0,3}(`{3,}|~{3,})',line) if not comment else None
        if m:fence=m.group(1);lines.append('');continue
        out='';i=0
        while i<len(line):
            if comment:
                end=line.find('-->',i)
                if end<0:break
                comment=False;i=end+3
            else:
                start=line.find('<!--',i)
                if start<0:out+=line[i:];break
                out+=line[i:start];comment=True;i=start+4
        lines.append(out)
    return '\n'.join(lines)

def review_status(directory):
    path=Path(directory)/'semantic-review.json'
    if not path.is_file():return {'state':'unreviewed','errors':['No current content-bound semantic review recorded.']}
    try:
        review=read_json(path);errors=[]
        if review.get('format')!='omnara-semantic-review/v1':errors.append('unsupported semantic review format')
        if review.get('subject_sha256')!=subject(directory)['sha256']:errors.append('semantic review is stale for current inquiry/evidence/report')
        for key in ['reviewer','rationale']:
            if not text(review.get(key)):errors.append('semantic review needs substantive '+key)
        if not clock(review.get('reviewed_at')):errors.append('semantic review needs valid dated reviewer observation')
        if review.get('result') not in {'pass','needs-work'}:errors.append('semantic review result must be pass or needs-work')
        reviewed=clock(review.get('reviewed_at'))
        for source in read_jsonl(Path(directory)/'source-ledger.jsonl'):
            accessed=clock(source.get('accessed_at') or source.get('accessed_date'))
            if reviewed and accessed and precedes(review['reviewed_at'],source.get('accessed_at') or source.get('accessed_date')):errors.append('semantic review predates recorded source access')
        claims=read_jsonl(Path(directory)/'claim-ledger.jsonl');ids={c.get('id') for c in claims if isinstance(c.get('id'),str)}
        entries=review.get('claims');seen=set()
        if not isinstance(entries,list):errors.append('semantic review claims must be an array');entries=[]
        for item in entries:
            if not isinstance(item,dict):errors.append('semantic review claim must be object');continue
            cid=item.get('claim_id')
            if not isinstance(cid,str) or cid not in ids or cid in seen:errors.append('semantic review unknown/duplicate claim id');continue
            seen.add(cid)
            if item.get('treatment') not in {'supported','qualified','not-used','unresolved'}:errors.append(f'{cid}: invalid reviewed treatment')
            if not text(item.get('rationale')):errors.append(f'{cid}: explain exact evidence and report treatment')
            if item.get('treatment')=='unresolved' and review.get('result')=='pass':errors.append(f'{cid}: unresolved review cannot pass')
        if seen!=ids:errors.append('semantic review must cover every recorded claim; unused claims may be explicitly not-used')
        if review.get('result')=='needs-work':errors.append('semantic review declares needs-work')
        return {'state':'current' if not errors else 'not-current','errors':errors,'declared_result':review.get('result'),'reviewer':review.get('reviewer'),'claims':entries}
    except (ValueError,OSError,TypeError) as exc:return {'state':'invalid','errors':[str(exc)]}

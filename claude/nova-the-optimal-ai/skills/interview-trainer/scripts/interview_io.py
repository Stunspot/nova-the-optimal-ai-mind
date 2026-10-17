"""Bounded read-only input primitives for private interview packets."""
from __future__ import annotations
import csv,datetime,hashlib,io,json,math,re,stat,unicodedata
from pathlib import Path
LIMIT=10*1024*1024

def digest(data):return hashlib.sha256(data).hexdigest()
def reject_links(path):
    p=Path(path).absolute()
    for part in [p,*p.parents]:
        if part.exists() or part.is_symlink():
            st=part.lstat()
            if part.is_symlink() or getattr(st,'st_file_attributes',0)&0x400:raise ValueError('Link/junction is not a packet input: '+str(part))
    return p.resolve()
def contained(root,name):
    if not isinstance(name,str) or not name or '\\' in name or name.startswith('/') or ':' in name:raise ValueError('Expected a portable relative path')
    parts=name.split('/')
    for p in parts:
        if p in {'','.','..'} or p!=p.rstrip(' .') or any(ord(c)<32 or c in '<>"|?*' for c in p) or re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',p):raise ValueError('Unsafe path: '+name)
    out=reject_links(root/name)
    if not out.is_relative_to(root):raise ValueError('Path escapes packet: '+name)
    return out

def read(root,name):
    p=contained(root,name)
    if not p.is_file():raise ValueError('Missing input: '+name)
    if p.stat().st_size>LIMIT:raise ValueError('Input exceeds 10 MiB: '+name)
    try:return p.read_text(encoding='utf-8-sig')
    except UnicodeError as exc:raise ValueError('Input must be UTF-8: '+name) from exc

def table(root,name,headers):
    raw=read(root,name)
    # csv.strict does not reject quotes embedded in unquoted fields; validate grammar first.
    mode='start';i=0
    while i<len(raw):
        ch=raw[i]
        if mode=='quoted':
            if ch=='"':
                if i+1<len(raw) and raw[i+1]=='"':i+=1
                else:mode='after'
        elif mode=='after':
            if ch==',':mode='start'
            elif ch in '\r\n':mode='start'
            else:raise ValueError(name+': characters after closing CSV quote')
        elif ch=='"':
            if mode!='start':raise ValueError(name+': quote inside an unquoted CSV field')
            mode='quoted'
        elif ch==',' or ch in '\r\n':mode='start'
        else:mode='plain'
        i+=1
    if mode=='quoted':raise ValueError(name+': unterminated CSV quote')
    try:rows=list(csv.reader(io.StringIO(raw,newline=''),strict=True))
    except csv.Error as exc:raise ValueError(name+': malformed CSV: '+str(exc)) from exc
    rows=[r for r in rows if r]
    if not rows:raise ValueError(name+': no CSV header')
    head=rows.pop(0)
    if any(not h or h!=h.strip() for h in head) or len(set(head))!=len(head):raise ValueError(name+': blank/duplicate/whitespace header')
    if not set(headers)<=set(head):raise ValueError(name+': missing columns '+', '.join(sorted(set(headers)-set(head))))
    if any(len(r)!=len(head) for r in rows):raise ValueError(name+': CSV row width differs from header')
    return [dict(zip(head,r)) for r in rows]

def jsload(root,name):
    def pairs(items):
        obj={}
        for k,v in items:
            if k in obj:raise ValueError(name+': duplicate JSON key '+k)
            obj[k]=v
        return obj
    def forbidden(v):raise ValueError(name+': nonfinite number '+v)
    raw=read(root,name)
    try:obj=json.loads(raw,object_pairs_hook=pairs,parse_constant=forbidden)
    except (json.JSONDecodeError,RecursionError) as exc:raise ValueError(name+': invalid JSON') from exc
    def visit(x,depth=0):
        if depth>60:raise ValueError(name+': excessive nesting')
        if isinstance(x,float) and not math.isfinite(x):raise ValueError(name+': nonfinite number')
        if isinstance(x,dict):
            for v in x.values():visit(v,depth+1)
        elif isinstance(x,list):
            for v in x:visit(v,depth+1)
    visit(obj);return obj

def moment(value):
    if not isinstance(value,str):raise ValueError('Date/time must be text')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return datetime.datetime.combine(datetime.date.fromisoformat(value),datetime.time(),datetime.timezone.utc),False
    m=re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(Z|[+-](\d{2}):(\d{2}))',value)
    if not m or value.endswith('-00:00') or (m[2] and (int(m[2])>23 or int(m[3])>59)):raise ValueError('Expected ISO date or time with known bounded offset: '+value)
    # A saved packet has the same clock grammar on every supported Python host.
    hour,minute,second=map(int,value[11:19].split(':'))
    if hour>23 or minute>59 or second>59:
        raise ValueError('Clock requires hours 00-23 and minutes/seconds 00-59; use next-date 00:00 for midnight: '+value)
    return datetime.datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(datetime.timezone.utc),True

def no_later(a,b):
    da,exact_a=moment(a);db,exact_b=moment(b)
    if exact_a and exact_b:return da<=db
    return da.date()<=db.date()

def visible(md):
    # Bounded Markdown record treatment, not an arbitrary HTML renderer.
    out=[];fence=None;comment=False
    for line in md.splitlines():
        mark=re.match(r'^\s*(`{3,}|~{3,})',line)
        if mark:
            if fence is None:fence=mark[1][0]
            elif mark[1][0]==fence:fence=None
            continue
        if fence:continue
        while line:
            if comment:
                end=line.find('-->')
                if end<0:line='';break
                line=line[end+3:];comment=False
            else:
                start=line.find('<!--')
                if start<0:out.append(line);line=''
                else:out.append(line[:start]);line=line[start+4:];comment=True
    return '\n'.join(out)
def substantive(md):return any(line.strip() and not line.lstrip().startswith('#') for line in visible(md).splitlines())
def field(section,name,required=True):
    found=re.findall(r'^-[ \t]*'+re.escape(name)+r':[ \t]*([^\r\n]*)$',visible(section),re.M)
    if len(found)>1:raise ValueError('Duplicate field '+name)
    if required and (not found or not found[0].strip()):raise ValueError('Missing field '+name)
    return found[0].strip() if found else ''

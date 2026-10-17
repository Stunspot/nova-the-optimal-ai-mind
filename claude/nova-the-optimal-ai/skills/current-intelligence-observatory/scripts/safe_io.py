"""Bounded local input and new-output custody. No claim of adversarial filesystem isolation."""
from __future__ import annotations
import json, math, os, re, stat, tempfile
from pathlib import Path, PurePosixPath
MAX_JSON=5_000_000

def pairs(values):
    result={}
    for key,value in values:
        if key in result: raise ValueError('Duplicate JSON key: '+key)
        result[key]=value
    return result

def finite(value,depth=0):
    if depth>80: raise ValueError('JSON nesting exceeds 80 levels')
    if isinstance(value,float) and not math.isfinite(value): raise ValueError('JSON numbers must be finite')
    if isinstance(value,dict):
        for k,v in value.items():
            if not isinstance(k,str): raise ValueError('JSON object keys must be strings')
            finite(v,depth+1)
    elif isinstance(value,list):
        for v in value:finite(v,depth+1)
    return value

def loads(raw,max_bytes=MAX_JSON):
    if isinstance(raw,bytes):
        if len(raw)>max_bytes:raise ValueError('JSON input exceeds size limit')
        raw=raw.decode('utf-8-sig')
    elif len(raw.encode('utf8'))>max_bytes:raise ValueError('JSON input exceeds size limit')
    try: value=json.loads(raw.lstrip('\ufeff'),object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON number: '+x)))
    except RecursionError as exc:raise ValueError('JSON nesting exceeds supported depth') from exc
    return finite(value)

def reject_links(path):
    path=Path(os.path.abspath(path))
    for p in [path,*path.parents]:
        if p.is_symlink() or (p.exists() and bool(getattr(p.lstat(),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024))):
            raise ValueError('Linked/reparse paths are not accepted: '+str(p))
    return path.resolve()

def load(path,max_bytes=MAX_JSON):
    path=reject_links(path)
    if path.stat().st_size>max_bytes:raise ValueError('JSON input exceeds size limit')
    return loads(path.read_bytes(),max_bytes)

def relative_name(name):
    if not isinstance(name,str) or not name or '\\' in name or name.startswith('/') or ':' in name:raise ValueError('Expected a portable relative path')
    parts=name.split('/')
    for p in parts:
        if p in ('','.','..') or p.endswith((' ','.')) or any(ord(c)<32 or c in '<>"|?*' for c in p) or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',p):raise ValueError('Unsafe portable path: '+name)
    return PurePosixPath(name)

def contained(root,name):
    rel=relative_name(name);root=reject_links(root);path=reject_links(root.joinpath(*rel.parts))
    if not path.is_relative_to(root):raise ValueError('Path escapes case root')
    return path

def namespace(names):
    files=set();dirs=set();spellings={}
    for name in names:
        rel=relative_name(name);key=rel.as_posix().casefold()
        for i in range(1,len(rel.parts)+1):
            spelling='/'.join(rel.parts[:i]);fold=spelling.casefold()
            if fold in spellings and spellings[fold]!=spelling:raise ValueError('Case-alias path namespace: '+name)
            spellings[fold]=spelling
        parents=['/'.join(rel.parts[:i]).casefold() for i in range(1,len(rel.parts))]
        if key in files or key in dirs or any(p in files for p in parents):raise ValueError('Duplicate or file/directory archive namespace: '+name)
        files.add(key);dirs.update(parents)

def bytes_json(value):
    finite(value)
    return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8')

def write_new(path,data):
    path=reject_links(path)
    if path.exists():raise ValueError('Output exists; choose a new destination: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive final creation refuses a concurrent destination; remove only our incomplete file.
    created=False
    try:
        with path.open('xb') as f:created=True;f.write(data);f.flush();os.fsync(f.fileno())
    except Exception:
        if created:path.unlink(missing_ok=True)
        raise

def write_bundle(destination,items):
    destination=reject_links(destination);namespace(items)
    if destination.exists():raise ValueError('Output directory exists; choose a new destination')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.observatory-',dir=destination.parent) as tmp:
        stage=Path(tmp)/'bundle';stage.mkdir()
        for name,data in items.items():
            p=contained(stage,name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        if destination.exists():raise ValueError('Output directory appeared during preparation')
        stage.rename(destination)

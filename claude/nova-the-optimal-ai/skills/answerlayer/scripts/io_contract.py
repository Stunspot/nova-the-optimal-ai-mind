"""Strict lossless numeric JSON and exclusive local output custody, standard library."""
from __future__ import annotations
import json,os,math,stat,tempfile,re
from decimal import Decimal
from pathlib import Path
from datetime import date,datetime,timezone
LIMIT=2_000_000
class LedgerError(ValueError):pass

def unlinked(path):
 p=Path(path).absolute()
 for node in [p,*p.parents]:
  try:s=node.lstat()
  except FileNotFoundError:continue
  if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&1024:raise LedgerError('Linked input/output path refused: '+str(node))
 return p

def strict(text):
 if not isinstance(text,str) or len(text.encode('utf-8'))>LIMIT:raise LedgerError('Native JSON exceeds2 MB or is not text')
 def pairs(rows):
  d={}
  for k,v in rows:
   if k in d:raise LedgerError('Duplicate JSON key: '+k)
   d[k]=v
  return d
 def invalid(x):raise LedgerError('Nonfinite JSON number: '+x)
 try:value=json.loads(text[1:] if text.startswith('\ufeff') else text,object_pairs_hook=pairs,parse_float=Decimal,parse_constant=invalid)
 except (ValueError,TypeError,RecursionError) as e:raise LedgerError('Invalid strict JSON: '+str(e)) from e
 check(value);return value

def check(value,depth=0):
 if depth>64:raise LedgerError('JSON nesting exceeds64 levels')
 if isinstance(value,dict):
  for k,v in value.items():
   if not isinstance(k,str):raise LedgerError('JSON object keys must be text')
   check(v,depth+1)
 elif isinstance(value,list):
  for x in value:check(x,depth+1)
 elif isinstance(value,Decimal):
  if not value.is_finite():raise LedgerError('Nonfinite JSON number')
 elif isinstance(value,float):
  if not math.isfinite(value):raise LedgerError('Nonfinite JSON number')
 elif value is not None and type(value) not in (str,int,bool):raise LedgerError('Unsupported JSON value type')

def dumps(value,canonical=False):
 check(value)
 def enc(v):
  if isinstance(v,dict):return '{'+','.join(json.dumps(k,ensure_ascii=False)+':'+enc(v[k]) for k in (sorted(v) if canonical else v))+'}'
  if isinstance(v,list):return '['+','.join(enc(x) for x in v)+']'
  if isinstance(v,Decimal):return str(v)
  return json.dumps(v,ensure_ascii=False,allow_nan=False)
 text=enc(value)
 if len(text.encode('utf-8'))>LIMIT:raise LedgerError('Native JSON exceeds2 MB')
 return text

def input_bytes(path):
 p=unlinked(path)
 if not p.is_file():raise LedgerError('Expected a regular input file')
 with p.open('rb') as f:data=f.read(LIMIT+1)
 if len(data)>LIMIT:raise LedgerError('Input exceeds2 MB')
 return data

def raw(path):
 try:return input_bytes(path).decode('utf-8')
 except UnicodeError as e:raise LedgerError('Input must be UTF-8') from e

def load(path):return strict(raw(path))

def atomic_bytes(path,payload):
 p=unlinked(path)
 if p.exists():raise LedgerError('Output already exists; choose a new path: '+str(p))
 if not p.parent.is_dir():raise LedgerError('Output parent must already exist: '+str(p.parent))
 fd,name=tempfile.mkstemp(prefix='.answerlayer-',dir=p.parent);temp=Path(name)
 try:
  with os.fdopen(fd,'wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
  unlinked(p);os.link(temp,p)
 finally:
  if temp.exists():temp.unlink()
 return p

def write(path,value):return atomic_bytes(path,(dumps(value)+'\n').encode('utf-8'))

def day(value,label,unknown=False):
 if unknown and value in ('unknown','not_applicable'):return None
 if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):raise LedgerError(label+': expected YYYY-MM-DD'+(' or explicit unknown/not_applicable' if unknown else ''))
 try:return date.fromisoformat(value)
 except ValueError as e:raise LedgerError(label+': invalid calendar date') from e

def moment(value,label):
 # Accept date-only decisions at UTC midnight, or an explicit known offset.
 if isinstance(value,str) and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):return datetime.combine(day(value,label),datetime.min.time(),timezone.utc)
 match=re.fullmatch(r'([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?([Zz]|[+-]([0-9]{2}):([0-9]{2}))',value) if isinstance(value,str) and len(value)<=32 else None
 if not match:raise LedgerError(label+': expected valid date or known-offset timestamp with seconds')
 datepart,h,m,s,f,offset,oh,om=match.groups();day(datepart,label)
 if int(h)>23 or int(m)>59 or int(s)>59 or (oh and (int(oh)>23 or int(om)>59)) or offset=='-00:00':raise LedgerError(label+': invalid time or offset component')
 try:return datetime.fromisoformat(value.upper().replace('Z','+00:00')).astimezone(timezone.utc)
 except (ValueError,OverflowError) as e:raise LedgerError(label+': timestamp outside supported UTC range') from e

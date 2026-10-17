"""Full, bounded ordinary-tree snapshot; staged, verified, no existing output replaced."""
from __future__ import annotations
import hashlib,json,os,re,stat,tempfile,unicodedata,zipfile
from pathlib import Path
from io_contract import LedgerError,unlinked
MAX_FILE=64*1024*1024;MAX_TOTAL=256*1024*1024;MAX_ENTRIES=4096
MANIFEST='.answerlayer-snapshot.json'
def portable(name):
 if len(name.encode('utf-16-le'))//2>180:raise LedgerError('Snapshot relative path exceeds180 characters')
 for part in name.split('/'):
  if not part or part in ('.','..') or part[-1:] in (' ','.') or any(ord(c)<32 or c in '<>:"\\|?*' for c in part):raise LedgerError('Nonportable snapshot name: '+name)
  if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?',part,re.I):raise LedgerError('Reserved Windows name: '+name)

def capture(root):
 root=unlinked(root)
 if not root.is_dir():raise LedgerError('Snapshot source must be an ordinary directory')
 files={};directories=[];seen=set();total=0
 for current,dirs,names in os.walk(root,followlinks=False):
  for name in sorted(dirs+names):
   path=unlinked(Path(current)/name);relative=path.relative_to(root).as_posix();portable(relative)
   key=unicodedata.normalize('NFC',relative).casefold()
   if key in seen or key==MANIFEST:raise LedgerError('Snapshot name collision: '+relative)
   seen.add(key)
   if len(seen)>MAX_ENTRIES:raise LedgerError('Snapshot exceeds4096 entries')
   before=path.stat()
   if stat.S_ISDIR(before.st_mode):directories.append(relative);continue
   if not stat.S_ISREG(before.st_mode):raise LedgerError('Only ordinary files/directories are supported: '+relative)
   if before.st_size>MAX_FILE:raise LedgerError('Snapshot file exceeds64 MiB: '+relative)
   with path.open('rb') as f:body=f.read(MAX_FILE+1)
   after=path.stat()
   if len(body)>MAX_FILE or (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise LedgerError('Source changed during capture: '+relative)
   total+=len(body)
   if total>MAX_TOTAL:raise LedgerError('Snapshot source exceeds256 MiB')
   files[relative]=body
 return files,sorted(directories)

def snapshot(root,output):
 root=unlinked(root);output=unlinked(output)
 if output==root or root in output.parents:raise LedgerError('Snapshot output must be outside source tree')
 if output.exists():raise LedgerError('Output already exists; choose a new path')
 if not output.parent.is_dir():raise LedgerError('Output parent must already exist')
 files,dirs=capture(root)
 manifest={'format':'answerlayer/snapshot/v2','boundary':'Ordinary local files captured and archive readback checked; no application-consistent database backup or approval inferred.','files':{name:{'size':len(body),'sha256':hashlib.sha256(body).hexdigest()} for name,body in sorted(files.items())},'directories':dirs}
 fd,name=tempfile.mkstemp(prefix='.answerlayer-snapshot-',suffix='.zip',dir=output.parent);os.close(fd);temp=Path(name)
 try:
  with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
   for d in dirs:z.writestr(d+'/',b'')
   for n,b in sorted(files.items()):z.writestr(n,b)
   z.writestr(MANIFEST,json.dumps(manifest,ensure_ascii=False,sort_keys=True).encode('utf-8'))
  with zipfile.ZipFile(temp) as z:
   expected=set(files)|{d+'/' for d in dirs}|{MANIFEST}
   if len(z.namelist())!=len(expected) or set(z.namelist())!=expected or z.testzip():raise LedgerError('Snapshot verification failed')
   for n,b in files.items():
    if z.read(n)!=b:raise LedgerError('Snapshot byte mismatch: '+n)
  again,newdirs=capture(root)
  if again!=files or newdirs!=dirs:raise LedgerError('Source changed before snapshot publication; retry on a quiescent copy')
  with temp.open('r+b') as f:os.fsync(f.fileno())
  unlinked(output);os.link(temp,output)
  return {'status':'snapshot_written','output':str(output),'sha256':hashlib.sha256(temp.read_bytes()).hexdigest(),'files':len(files),'directories':len(dirs)}
 finally:
  if temp.exists():temp.unlink()

import contextlib,json,os,tempfile
from pathlib import Path
def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.writing-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:
            json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

@contextlib.contextmanager
def lock(path,blocking=True):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    f=open(path,'a+b')
    try:
        if os.name=='nt':
            import msvcrt
            if f.tell()==0:f.write(b'0');f.flush()
            f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f.fileno(),fcntl.LOCK_EX|(0 if blocking else fcntl.LOCK_NB))
        yield
    finally:
        try:
            if os.name=='nt':f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f.fileno(),fcntl.LOCK_UN)
        except OSError:pass
        f.close()


def atomic_bytes(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".original-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as stream:stream.write(value);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

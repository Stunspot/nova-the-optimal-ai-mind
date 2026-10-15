"""Atomic replacement of one owned file; no cross-process transaction claim."""
import os,secrets
from pathlib import Path
from custody import reject_links

def atomic(path,content):
    path=reject_links(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+secrets.token_hex(6)+'.tmp')
    try:
        with temp.open('xb') as handle:
            handle.write(content if isinstance(content,bytes) else content.encode('utf-8'));handle.flush();os.fsync(handle.fileno())
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)

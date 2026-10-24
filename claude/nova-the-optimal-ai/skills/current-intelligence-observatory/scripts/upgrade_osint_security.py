"""Upgrade only the Observatory Maigret decoder route, preserving workbench data."""
from __future__ import annotations
import argparse, contextlib, datetime, json, os, shutil, subprocess, sys
from pathlib import Path
from safe_io import reject_links
from setup_osint import default_home
HERE=Path(__file__).resolve().parent

def guarded_entrypoint(text):
    old="[exe('maigret'),args.target,"
    new="[python('maigret'),str(ROOT/'drivers/maigret_safe.py'),args.target,"
    if text.count(old)==1:
        text=text.replace(old,new)
    elif text.count(new)!=1:
        raise ValueError('Unrecognized Maigret username adapter; preserve it for a scoped migration')
    help_line="        else: command=[exe(args.tool),'--help']"
    safe_help="        elif args.tool=='maigret': command=[python('maigret'),str(ROOT/'drivers/maigret_safe.py'),'--help']"
    if safe_help not in text:
        if text.count(help_line)!=1:raise ValueError('Unrecognized tool help adapter')
        text=text.replace(help_line,safe_help+'\n'+help_line)
    compile(text,'osint.py','exec')
    return text

@contextlib.contextmanager
def upgrade_lock(home):
    path=reject_links(home/'.security-upgrade.lock')
    with path.open('a+b') as stream:
        stream.seek(0,os.SEEK_END)
        if stream.tell()==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:raise ValueError('Another OSINT security upgrade is in progress') from exc
        try:yield
        finally:
            if os.name=='nt':
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream,fcntl.LOCK_UN)

def upgrade(home, uv):
    home=reject_links(Path(home).expanduser())
    if not home.is_dir():raise ValueError('Choose an existing OSINT workbench')
    with upgrade_lock(home):return _upgrade(home,uv)

def _upgrade(home, uv):
    home=reject_links(Path(home).expanduser())
    entry=reject_links(home/'osint.py')
    python=reject_links(home/'envs/maigret'/('Scripts/python.exe' if os.name=='nt' else 'bin/python'))
    if not entry.is_file() or not python.is_file():raise ValueError('Select an existing Observatory OSINT workbench with Maigret installed')
    original=entry.read_bytes();updated=guarded_entrypoint(original.decode('utf-8-sig')).encode('utf-8')
    payload={name:(HERE/'osint-runtime'/name).read_bytes() for name in ('safe_http.py','drivers/maigret_safe.py')}
    for name,data in payload.items():
        path=reject_links(home/name)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Existing safety adapter differs; preserve and review '+name)
    # The dependency command operates only on the selected isolated environment.
    if not uv:raise ValueError('uv is required to install the fixed decoder into this existing environment')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup=reject_links(home/'security-backups'/stamp);backup.mkdir(parents=True,exist_ok=False)
    (backup/'osint.py').write_bytes(original)
    subprocess.run([str(uv),'pip','install','--python',str(python),'Brotli==1.2.1'],check=True)
    probe="import brotli,importlib.metadata; assert importlib.metadata.version('Brotli')=='1.2.1'; assert brotli.decompress(brotli.compress(b'guarded'))==b'guarded'"
    subprocess.run([str(python),'-I','-c',probe],check=True)
    if entry.read_bytes()!=original:raise ValueError('Workbench adapter changed during preparation; rerun after concurrent work finishes')
    for name,data in payload.items():
        path=reject_links(home/name);path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_name(path.name+'.security.tmp');temporary.write_bytes(data);os.replace(temporary,path)
    temporary=entry.with_name('osint.py.security.tmp');temporary.write_bytes(updated);os.replace(temporary,entry)
    subprocess.run([str(python),'-B',str(home/'drivers/maigret_safe.py'),'--help'],check=True,stdout=subprocess.DEVNULL)
    return {'upgraded':True,'home':str(home),'entrypoint_preimage':str(backup/'osint.py'),'decoder':'Brotli 1.2.1','native_curl_decoding':False,'provider_queries':False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,default=default_home());parser.add_argument('--uv',default=shutil.which('uv'));args=parser.parse_args(argv)
    try:print(json.dumps(upgrade(args.home,args.uv),indent=2));return 0
    except (ValueError,OSError,subprocess.SubprocessError) as exc:print('Security upgrade incomplete: '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Prepare the optional workbench in a new home; explicit retry preserves partial work."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, urllib.request, zipfile, tempfile
from pathlib import Path, PurePosixPath
from safe_io import load, reject_links, namespace, relative_name, bytes_json
HERE=Path(__file__).resolve().parent
TOOLS=('maigret','theharvester','shodan','spiderfoot')

def default_home():
    if os.environ.get('NOVA_OSINT_HOME'): return Path(os.environ['NOVA_OSINT_HOME']).expanduser()
    if os.environ.get('NOVA_DATA_ROOT'): return Path(os.environ['NOVA_DATA_ROOT']).expanduser()/'integrations/osint'
    if os.name=='nt': return Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'Nova/integrations/osint'
    return Path.home()/'.local/share/Nova/integrations/osint'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def atomic_json(path,value):
    path=reject_links(path)
    with tempfile.NamedTemporaryFile(prefix='.receipt-',dir=path.parent,delete=False) as f:temporary=Path(f.name);f.write(bytes_json(value))
    try:os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)

def tree(root):
    root=reject_links(root);result={}
    for p in sorted(root.rglob('*')):
        reject_links(p)
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'):result[p.relative_to(root).as_posix()]=p
    namespace(result)
    return result

def unpack(archive,destination):
    archive=reject_links(archive);destination=reject_links(destination)
    if destination.exists():raise ValueError('Source destination already exists; preserve it and choose a fresh source home')
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist()
        if not infos or len(infos)>20000 or sum(i.file_size for i in infos)>256*1024*1024:raise ValueError('Upstream archive is empty or exceeds extraction limits')
        roots=set();files={};members={};spellings={};kinds={}
        for i in infos:
            name=i.filename.rstrip('/') if i.is_dir() else i.filename
            rel=relative_name(name);roots.add(rel.parts[0]);mode=(i.external_attr>>16)&0o170000
            if name in members:raise ValueError('Duplicate upstream member')
            members[name]=i.is_dir()
            for depth in range(1,len(rel.parts)+1):
                spelling='/'.join(rel.parts[:depth]);key=spelling.casefold();kind='directory' if depth<len(rel.parts) or i.is_dir() else 'file'
                if key in spellings and spellings[key]!=spelling:raise ValueError('Case-alias upstream directory namespace')
                if key in kinds and kinds[key]!=kind:raise ValueError('File/directory upstream namespace collision')
                spellings[key]=spelling;kinds[key]=kind
            if mode not in (0,0o100000,0o040000):raise ValueError('Upstream archive contains a link or special member')
            if i.flag_bits&1:raise ValueError('Encrypted upstream source archive is not supported')
            if len(rel.parts)==1:
                if not i.is_dir():raise ValueError('Upstream archive must have a source directory root')
                continue
            if not i.is_dir():
                key='/'.join(rel.parts[1:])
                if key in files:raise ValueError('Duplicate upstream member')
                files[key]=i
        if len(roots)!=1:raise ValueError('Upstream archive must have one source root')
        if not files:raise ValueError("Upstream source archive has no files")
        namespace(files)
        # All bytes and names are checked before any final source directory exists.
        destination.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.source-',dir=destination.parent) as tmp:
            stage=Path(tmp)/'tree';stage.mkdir()
            for name,info in files.items():
                path=stage/name;path.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as source,path.open('xb') as output:shutil.copyfileobj(source,output)
            if destination.exists():raise ValueError('Source destination appeared during extraction')
            stage.rename(destination)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,default=default_home())
    parser.add_argument('--tools',nargs='+',choices=TOOLS,default=list(TOOLS))
    parser.add_argument('--uv',default=shutil.which('uv'))
    parser.add_argument('--python314',default='3.14');parser.add_argument('--python312',default='3.12')
    parser.add_argument('--source-cache',type=Path)
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--resume',action='store_true',help='Retry only this installer\'s matching interrupted plan; never update an existing complete or independently managed home')
    args=parser.parse_args(argv);receipt_path=None;receipt=None
    try:
        home=reject_links(args.home.expanduser())
        if home==Path(home.anchor) or home==Path.home().resolve() or any(p.lower()=='.codex' for p in home.parts):raise ValueError('Choose a dedicated OSINT data directory outside the host installation')
        sources=load(HERE/'osint-sources.json');selected=list(dict.fromkeys(args.tools))
        payload=tree(HERE/'osint-runtime');payload['safe_io.py']=HERE/'safe_io.py'
        inventory={name:sha(p) for name,p in payload.items()}
        plan={'format':'cd-osint-setup/v2','home':str(home),'tools':selected,'python':{'main':args.python314,'spiderfoot':args.python312},'sources':{k:v for k,v in sources.items() if k in selected},'payload_sha256':inventory,'provider_queries':False,'credentials_included':False}
        if args.dry_run:print(json.dumps(plan,indent=2));return 0
        if not args.uv:raise ValueError('uv is required for installation. Read https://docs.astral.sh/uv/getting-started/installation/ ; --dry-run needs no uv or network.')
        if home.exists() and any(home.iterdir()):
            tree(home)
            if not args.resume or not (home/'setup-receipt.json').is_file():raise ValueError('Home is nonempty. Keep it intact; choose a fresh sibling home, or --resume a matching interrupted setup.')
            prior=load(home/'setup-receipt.json')
            if any(prior.get(k)!=v for k,v in plan.items()) or prior.get('state') not in ('installing','partial-or-failed'):raise ValueError('Resume requires this exact interrupted plan; complete or independently managed workbenches are preserved.')
            for name,digest in inventory.items():
                p=home/name
                if p.exists() and name!='registry.json' and not name.startswith('config/') and sha(p)!=digest:raise ValueError('Installed adapter changed; do not overwrite it: '+name)
        elif args.resume:raise ValueError('There is no matching interrupted setup to resume')
        home.mkdir(parents=True,exist_ok=True)
        for name,source in payload.items():
            dest=home/name;reject_links(dest)
            if dest.exists():continue
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        for name in ('runs','state/theharvester','sources','downloads','envs'):(home/name).mkdir(parents=True,exist_ok=True)
        receipt={**plan,'state':'installing','installed':[]};receipt_path=home/'setup-receipt.json';atomic_json(receipt_path,receipt)
        def run(command,env=None):subprocess.run([str(x) for x in command],check=True,env=env,cwd=home)
        def py(tool):return home/'envs'/tool/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        for tool in selected:
            if tool in sources:
                spec=sources[tool];archive=home/'downloads'/(tool+'-source.zip');reject_links(archive)
                if archive.exists() and sha(archive)!=spec['sha256']:raise ValueError('Existing cached archive is invalid; preserve it elsewhere and retry: '+str(archive))
                if not archive.exists():
                    with tempfile.NamedTemporaryFile(prefix='.download-',dir=home/'downloads',delete=False) as f:part=Path(f.name)
                    try:
                        cached=reject_links(args.source_cache/(tool+'-source.zip')) if args.source_cache else None
                        if cached and cached.is_file():shutil.copyfile(cached,part)
                        else:
                            with urllib.request.urlopen(spec['url'],timeout=60) as response,part.open('wb') as output:
                                count=0
                                while block:=response.read(1024*1024):
                                    count+=len(block)
                                    if count>128*1024*1024:raise ValueError('Source download exceeds 128 MiB')
                                    output.write(block)
                        if sha(part)!=spec['sha256']:raise ValueError('Source archive hash mismatch: '+tool)
                        if archive.exists():raise ValueError('Archive destination appeared during download')
                        part.rename(archive)
                    finally:part.unlink(missing_ok=True)
                source=home/'sources'/tool;marker=source/'.nova-source.json'
                if source.exists():
                    if not marker.is_file():raise ValueError('Incomplete/unowned source tree; preserve it and select a fresh home')
                    saved=load(marker)
                    actual={n:sha(p) for n,p in tree(source).items() if n!='.nova-source.json'}
                    if saved.get('source')!=spec or saved.get('files')!=actual:raise ValueError('Source tree differs from the retained cutoff; choose a fresh home')
                else:
                    unpack(archive,source)
                    atomic_json(marker,{'source':spec,'files':{n:sha(p) for n,p in tree(source).items()}})
            python=args.python312 if tool=='spiderfoot' else args.python314
            if not py(tool).exists():run([args.uv,'venv','--python',python,home/'envs'/tool])
            if tool=='theharvester':run([args.uv,'sync','--project',home/'sources'/tool,'--frozen','--no-dev','--python',python],dict(os.environ,UV_PROJECT_ENVIRONMENT=str(home/'envs'/tool)))
            else:
                command=[args.uv,'pip','install','--python',py(tool),'-r',home/'data'/(tool+'-requirements.lock')]
                if tool=='spiderfoot':command.append('--require-hashes')
                run(command)
            run([args.uv,'pip','check','--python',py(tool)])
            run([sys.executable,home/'osint.py','help',tool])
            receipt['installed'].append(tool);atomic_json(receipt_path,receipt)
        registry=load(home/'registry.json')
        for row in registry['tools']:
            key={'shodan-python':'shodan','theHarvester':'theharvester'}.get(row['repo'],row['repo'])
            if key in selected:row['installation_state']='installed; startup checked; provider access unverified'
        atomic_json(home/'registry.json',registry)
        receipt['state']='complete';atomic_json(receipt_path,receipt)
        print(json.dumps({'state':'complete','home':str(home),'installed':selected,'provider_queries':False,'next':'Set NOVA_OSINT_HOME to this home. Run discover; provider work needs its own authorized scope.'},indent=2));return 0
    except (OSError,ValueError,subprocess.CalledProcessError,zipfile.BadZipFile) as exc:
        if receipt_path and receipt:
            receipt.update(state='partial-or-failed',error=str(exc));atomic_json(receipt_path,receipt)
        print(json.dumps({'state':'partial-or-failed' if receipt else 'not-started','error':str(exc),'recovery':'Existing homes remain intact. For this new partial home, correct the named issue and repeat the exact command with --resume; do not delete runs or originals.'}),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())

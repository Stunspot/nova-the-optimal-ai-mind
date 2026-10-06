#!/usr/bin/env python3
"""Install the reviewed optional OSINT workbench outside the Nova skill."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, urllib.request, zipfile
from pathlib import Path, PurePosixPath
HERE=Path(__file__).resolve().parent

def default_home():
    if os.environ.get('NOVA_OSINT_HOME'): return Path(os.environ['NOVA_OSINT_HOME']).expanduser()
    if os.environ.get('NOVA_DATA_ROOT'): return Path(os.environ['NOVA_DATA_ROOT']).expanduser()/'integrations/osint'
    if os.name=='nt': return Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'Nova/integrations/osint'
    return Path.home()/'.local/share/Nova/integrations/osint'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while b:=f.read(1024*1024): h.update(b)
    return h.hexdigest()

def unpack(archive,destination):
    destination=destination.resolve()
    with zipfile.ZipFile(archive) as z:
        roots={PurePosixPath(i.filename).parts[0] for i in z.infolist()}
        if len(roots)!=1: raise ValueError('Upstream archive must have one source root')
        for i in z.infolist():
            parts=PurePosixPath(i.filename).parts
            if any(p in ('..','.') for p in parts) or i.filename.startswith('/') or '\\' in i.filename or (i.external_attr>>16)&0o170000==0o120000: raise ValueError('Unsafe upstream archive member')
            if len(parts)==1 or i.is_dir(): continue
            p=destination.joinpath(*parts[1:]).resolve()
            if not p.is_relative_to(destination): raise ValueError('Source member escapes destination')
            p.parent.mkdir(parents=True,exist_ok=True)
            with z.open(i) as a,p.open('wb') as b: shutil.copyfileobj(a,b)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home',type=Path,default=default_home())
    p.add_argument('--tools',nargs='+',choices=['maigret','theharvester','shodan','spiderfoot'],default=['maigret','theharvester','shodan','spiderfoot'])
    p.add_argument('--uv',default=shutil.which('uv'))
    p.add_argument('--python314',default='3.14');p.add_argument('--python312',default='3.12')
    p.add_argument('--source-cache',type=Path,help='Optional directory containing the hash-checked source archives')
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args();home=a.home.expanduser().resolve()
    if home==Path(home.anchor) or home==Path.home().resolve() or '.codex' in home.parts: p.error('Choose a dedicated Nova OSINT data directory outside the host installation')
    if not a.uv: p.error('Install uv from https://docs.astral.sh/uv/getting-started/installation/ and run this command again')
    sources=json.loads((HERE/'osint-sources.json').read_text(encoding='utf8'))
    plan={'home':str(home),'tools':a.tools,'python':{'main':a.python314,'spiderfoot':a.python312},'sources':{k:v for k,v in sources.items() if k in a.tools},'provider_queries':False,'credentials_included':False}
    if a.dry_run: print(json.dumps(plan,indent=2));return 0
    if (home/'osint.py').exists() and not (home/'setup-receipt.json').exists(): p.error('This home contains an independently managed workbench; choose a new home or keep using that installation')
    payload=HERE/'osint-runtime';home.mkdir(parents=True,exist_ok=True)
    for q in payload.rglob('*'):
        if not q.is_file() or '__pycache__' in q.parts or q.suffix=='.pyc':continue
        rel=q.relative_to(payload);dest=home/rel
        if rel.parts[0]=='config' and dest.exists():continue
        # Keep installed state for unchanged tools across an incremental setup.
        if rel.as_posix()=='registry.json' and dest.exists():continue
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,dest)
    for n in ['runs','state/theharvester','sources','downloads']: (home/n).mkdir(parents=True,exist_ok=True)
    receipt={**plan,'state':'installing','installed':[]};rp=home/'setup-receipt.json'
    def save():rp.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    def run(cmd,env=None):subprocess.run([str(x) for x in cmd],check=True,env=env,cwd=home)
    def py(tool):return home/'envs'/tool/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    save()
    try:
        for tool in a.tools:
            if tool in sources:
                spec=sources[tool];archive=home/'downloads'/(tool+'-source.zip')
                cached=a.source_cache/(tool+'-source.zip') if a.source_cache else None
                if not archive.exists():
                    if cached and cached.exists():shutil.copyfile(cached,archive)
                    else:
                        with urllib.request.urlopen(spec['url'],timeout=90) as r,archive.open('wb') as f:shutil.copyfileobj(r,f)
                if sha(archive)!=spec['sha256']:raise ValueError('Source archive hash mismatch: '+tool+'; remove the failed archive and retry')
                source=home/'sources'/tool;marker=source/'.nova-source.json'
                if marker.exists() and json.loads(marker.read_text())!=spec:raise ValueError('Existing source cutoff differs; choose a new OSINT home')
                if not marker.exists():unpack(archive,source);marker.write_text(json.dumps(spec),encoding='utf8')
            python=a.python312 if tool=='spiderfoot' else a.python314
            if not py(tool).exists():run([a.uv,'venv','--python',python,home/'envs'/tool])
            if tool=='theharvester':
                env=dict(os.environ,UV_PROJECT_ENVIRONMENT=str(home/'envs'/tool))
                run([a.uv,'sync','--project',home/'sources'/tool,'--frozen','--no-dev','--python',python],env)
            else:
                cmd=[a.uv,'pip','install','--python',py(tool),'-r',home/'data'/(tool+'-requirements.lock')]
                if tool=='spiderfoot':cmd.append('--require-hashes')
                run(cmd)
            run([a.uv,'pip','check','--python',py(tool)])
            run([sys.executable,home/'osint.py','help',tool])
            receipt['installed'].append(tool);save()
            registry=json.loads((home/'registry.json').read_text(encoding='utf8'))
            key={'shodan':'shodan-python','theharvester':'theHarvester'}.get(tool,tool)
            for row in registry['tools']:
                if row['repo']==key:row['installation_state']='installed; API key required' if tool=='shodan' else 'installed; bounded profile'
            (home/'registry.json').write_text(json.dumps(registry,indent=2)+'\n',encoding='utf8')
        receipt['state']='complete';save()
        print('OSINT setup complete. Home: '+str(home));print('Set NOVA_OSINT_HOME to this path for a custom home. Use osint_bridge.py discover, then spiderfoot-demo for the offline example.')
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        receipt['state']='partial-or-failed';receipt['error']=str(e);save();print('Setup stopped: '+str(e)+'; completed tools and reports remain at '+str(home),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())

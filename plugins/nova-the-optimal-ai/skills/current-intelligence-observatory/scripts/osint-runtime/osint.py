"""Local OSINT entry point. Uses isolated environments and retains native reports."""
import argparse, datetime, json, os, re, subprocess, sys, uuid, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if not (ROOT/'safe_io.py').is_file():sys.path.insert(0,str(ROOT.parent))
from safe_io import load, reject_links, bytes_json
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf-8', errors='replace')
CHILD_ENV = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
def python(tool):
    return str(ROOT / 'envs' / tool / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
def exe(tool):
    return str(ROOT / 'envs' / tool / ('Scripts' if os.name == 'nt' else 'bin') / (('theHarvester' if tool == 'theharvester' else tool) + ('.exe' if os.name == 'nt' else '')))
def run(command, target, dry_run=False, timeout=None):
    if dry_run:
        print(json.dumps({'command':command,'target':target,'executed':False},indent=2))
        return 0
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    destination = reject_links(ROOT / 'runs' / run_id)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.mkdir()
    command = [part.replace('{REPORTS}', str(destination)) for part in command]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        result = subprocess.run(command,cwd=destination,capture_output=True,text=True,encoding='utf-8',errors='replace',env=CHILD_ENV,timeout=timeout)
    except OSError as exc:
        result=subprocess.CompletedProcess(command,127,'','Tool unavailable: '+str(exc)+'\n')
    except subprocess.TimeoutExpired as exc:
        def decoded(value): return value.decode('utf-8','replace') if isinstance(value,bytes) else (value or '')
        result = subprocess.CompletedProcess(command,124,decoded(exc.stdout),decoded(exc.stderr)+'\nRun exceeded its time budget; process terminated. Retained artifacts may be incomplete.\n')
    (destination / 'stdout.txt').write_text(result.stdout,encoding='utf-8')
    (destination / 'stderr.txt').write_text(result.stderr,encoding='utf-8')
    artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.iterdir()) if p.is_file()}
    native={'format':'cd-osint-run/v1','target':target,'command':command,'started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':result.returncode,'synthetic':'--fixture' in command,'artifacts':artifacts,'evidence_note':'Native exit status is not completeness, evidence accuracy or identity attribution.'}
    (destination/'run.json').write_bytes(bytes_json(native))
    print(result.stdout,end='')
    print(result.stderr,end='',file=sys.stderr)
    print(f'Artifacts: {destination}')
    return result.returncode
def main():
    parser=argparse.ArgumentParser(description='Nova local OSINT workbench')
    commands=parser.add_subparsers(dest='command',required=True)
    listing=commands.add_parser('list')
    listing.add_argument('--json',action='store_true')
    help_parser=commands.add_parser('help')
    help_parser.add_argument('tool',choices=['maigret','theharvester','shodan','spiderfoot'])
    user=commands.add_parser('username',help='Bounded Maigret account discovery; candidate matches need verification.')
    user.add_argument('target')
    user.add_argument('--sites',help='Comma-separated site names; defaults to top 50 sites.')
    user.add_argument('--top',type=int,default=50)
    user.add_argument('--recursive',action='store_true',help='Explicitly enable profile extraction and recursive identifier pivots.')
    user.add_argument('--database',type=Path,default=ROOT/'data/maigret-sites.json')
    user.add_argument('--dry-run',action='store_true')
    domain=commands.add_parser('domain',help='theHarvester passive provider queries.')
    domain.add_argument('target')
    domain.add_argument('--sources',default='crtsh,certspotter',help='Named P0 sources only; default needs no API keys.')
    domain.add_argument('--limit',type=int,default=100)
    domain.add_argument('--dry-run',action='store_true')
    shodan=commands.add_parser('shodan',help='Existing Shodan data; requires SHODAN_API_KEY.')
    shodan.add_argument('kind',choices=['host','count','search'])
    shodan.add_argument('target')
    shodan.add_argument('--limit',type=int,default=10)
    shodan.add_argument('--dry-run',action='store_true')
    foot=commands.add_parser('spiderfoot',help='Selected SpiderFoot domain-enrichment profile and relationship reports.')
    foot.add_argument('target')
    foot.add_argument('--max-requests',type=int,default=20)
    foot.add_argument('--deadline',type=int,default=120)
    foot.add_argument('--dry-run',action='store_true')
    demo=commands.add_parser('spiderfoot-demo',help='Synthetic SpiderFoot graph; makes no provider requests.')
    demo.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if args.command=='list':
        entries=load(ROOT/'registry.json')
        for row in entries['tools']:
            key={'shodan-python':'shodan','theHarvester':'theharvester'}.get(row['repo'],row['repo'])
            row['runtime_executable_present']=Path(python(key)).is_file() if key in ('maigret','theharvester','shodan','spiderfoot') else False
        if args.json: print(json.dumps(entries,indent=2))
        else:
            for tool in entries['tools']: print(f"{tool['name']}: {tool['installation_state']} - {tool['capability_delta']}")
        return 0
    if args.command=='help':
        if args.tool=='theharvester': command=[python('theharvester'),str(ROOT/'drivers/harvester.py'),'--help']
        elif args.tool=='spiderfoot': command=[python('spiderfoot'),str(ROOT/'drivers/spiderfoot.py'),'--help']
        else: command=[exe(args.tool),'--help']
        return subprocess.run(command,cwd=ROOT).returncode
    if args.command in ['spiderfoot','spiderfoot-demo']:
        fixture=args.command=='spiderfoot-demo'
        target='example.test' if fixture else args.target.rstrip('.').encode('idna').decode('ascii').lower()
        if not re.fullmatch(r'(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',target) or '.' not in target or '..' in target:
            parser.error('Supply an exact domain name without a URL, wildcard, or port.')
        cap=20 if fixture else args.max_requests
        deadline=120 if fixture else args.deadline
        if not 1<=cap<=100 or not 10<=deadline<=600: parser.error('Request budget must be 1..100 and deadline 10..600 seconds.')
        command=[python('spiderfoot'),str(ROOT/'drivers/spiderfoot.py'),target,'--output','{REPORTS}','--max-requests',str(cap),'--deadline',str(deadline)]
        if fixture: command+=['--fixture']
        return run(command,target,args.dry_run,timeout=deadline+30)
    if args.command=='username':
        if args.target.startswith('-') or not args.target.strip(): parser.error('Supply a username, not an option.')
        if not 1<=args.top<=500: parser.error('--top must be between 1 and 500; use explicit sites for larger scoped work.')
        db=args.database.resolve()
        if not db.is_file(): parser.error('Local site database not found.')
        command=[exe('maigret'),args.target,'--db',str(db),'--no-autoupdate','--top-sites',str(args.top),'--max-connections','5','--timeout','15','--retries','0','--json','ndjson','--html','--folderoutput','{REPORTS}']
        if not args.recursive: command+=['--no-recursion','--no-extracting']
        if args.sites:
            for site in args.sites.split(','):
                if site.strip(): command+=['--site',site.strip()]
        return run(command,args.target,args.dry_run)
    if args.command=='domain':
        target=args.target.rstrip('.').encode('idna').decode('ascii').lower()
        if not re.fullmatch(r'(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',target) or '.' not in target or '..' in target:
            parser.error('Supply an exact domain name without a URL, wildcard, or port.')
        if not 1<=args.limit<=1000: parser.error('--limit must be between 1 and 1000')
        sources=[s.strip().lower() for s in args.sources.split(',') if s.strip()]
        specs=load(ROOT/'data/harvester-sources.json')
        if not sources or any(specs.get(s,{}).get('activity')!='P0' for s in sources):
            parser.error('--sources accepts named P0 providers only; see data/harvester-sources.json.')
        command=[python('theharvester'),str(ROOT/'drivers/harvester.py'),'-d',target,'-b',','.join(sources),'-l',str(args.limit),'-j','1','-f','{REPORTS}/domain']
        return run(command,target,args.dry_run)
    if not 1<=args.limit<=100:parser.error('--limit must be between 1 and 100')
    if args.kind=='host':
        import ipaddress
        try:ipaddress.ip_address(args.target)
        except ValueError:parser.error('host expects an IP address')
    if not args.target.strip():parser.error('Supply a nonempty query')
    return run([python('shodan'),str(ROOT/'drivers/shodan_query.py'),args.kind,args.target,'--limit',str(args.limit)],args.target,args.dry_run)
if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError) as exc:
        print(json.dumps({'state':'unavailable-or-invalid','error':str(exc),'provider_result_verified':False}),file=sys.stderr);raise SystemExit(2)

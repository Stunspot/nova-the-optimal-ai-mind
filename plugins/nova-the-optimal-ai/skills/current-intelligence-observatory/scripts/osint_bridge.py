#!/usr/bin/env python3
"""Use a discovered local OSINT workbench and preserve its reports in a native case revision."""
from __future__ import annotations
import argparse,copy,datetime,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from observatory_guardrail import validate_case,receipt
ROOT=Path(__file__).resolve().parents[1]
COMMANDS={'list','help','username','domain','shodan','spiderfoot','spiderfoot-demo'}

def workbench(explicit=None):
    candidates=[explicit,os.environ.get('NOVA_OSINT_HOME')]
    if os.environ.get('NOVA_DATA_ROOT'): candidates.append(str(Path(os.environ['NOVA_DATA_ROOT'])/'integrations/osint'))
    if os.name=='nt': candidates.append(r'E:\Indranet\Nova\integrations\osint')
    from setup_osint import default_home
    candidates.append(str(default_home()))
    for candidate in candidates:
        if not candidate: continue
        path=Path(candidate).expanduser().resolve()
        if (path/'osint.py').is_file() and (path/'registry.json').is_file(): return path
        if explicit: break
    raise ValueError('OSINT workbench unavailable. Run the bundled scripts/setup_osint.py, or set NOVA_OSINT_HOME to its home or supply --workbench; continue ordinary source work when it is absent.')

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def attach(home,case_path,run_path,output):
    case_path=case_path.resolve();run_path=run_path.resolve();output=output.resolve()
    if not run_path.is_relative_to((home/'runs').resolve()): raise ValueError('Attach a native run directory under the selected workbench runs directory.')
    if output.parent!=case_path.parent: raise ValueError('Keep the new case beside the original so existing relative evidence paths remain valid.')
    if output.exists() or output==case_path: raise ValueError('Choose a new output case path; the existing case remains authoritative until reviewed.')
    original=case_path.read_bytes();case=json.loads(original)
    errors=validate_case(case)
    if errors: raise ValueError('Frame/repair the native case first: '+'; '.join(errors))
    run=json.loads((run_path/'run.json').read_text(encoding='utf-8-sig'))
    if not isinstance(run.get('exit_code'),int) or not run.get('completed_at'): raise ValueError('Run receipt needs a native exit code and completion time.')
    token=digest(run_path/'run.json')[:16].upper();src_id='SRC-OSINT-'+token
    if any(item['id']==src_id for item in case['sources']): raise ValueError('This exact run is already attached to the case.')
    suffix=' SYNTHETIC FIXTURE' if '--fixture' in run.get('command',[]) else ''
    state='completed' if run['exit_code']==0 else 'partial-or-failed'
    uncertainty='Derived tool output; provider content, coverage and identity attribution remain unverified.'+suffix
    updated=copy.deepcopy(case)
    updated['sources'].append({'id':src_id,'title':'OSINT run '+run_path.name+suffix,'source_kind':'derived-tool-run','target':run.get('target'),'exit_code':run['exit_code'],'run_state':state,'status':'available','confidence':'unrated','uncertainty':uncertainty})
    files=[p for p in sorted(run_path.iterdir()) if p.is_file()]
    if not files: raise ValueError('No report artifacts were found.')
    if any(p.is_symlink() or not p.resolve().is_relative_to(run_path) for p in files): raise ValueError('Report paths must remain within the run directory.')
    if sum(p.stat().st_size for p in files)>100*1024*1024: raise ValueError('Run reports exceed 100 MiB; select a smaller scoped run.')
    artifact_home=output.parent/(output.stem+'.captures')/run_path.name
    if artifact_home.exists(): raise ValueError('Capture destination already exists; choose a new output case path.')
    output.parent.mkdir(parents=True,exist_ok=True);artifact_home.mkdir(parents=True)
    capture_ids={}
    for index,p in enumerate(files,1):
        dest=artifact_home/p.name;shutil.copy2(p,dest)
        cap_id=f'CAP-OSINT-{token}-{index}'
        item=receipt(dest,src_id,cap_id,p.as_uri(),None,run['completed_at'])
        item.update(artifact_path=dest.relative_to(output.parent).as_posix(),status='preserved',confidence='unrated',uncertainty=uncertainty,source_kind='derived-tool-report',external_source_url=None)
        updated['captures'].append(item);capture_ids[p.name]=cap_id
    event_report=run_path/'spiderfoot-events.json'
    records=json.loads(event_report.read_text(encoding='utf-8')) if event_report.is_file() else []
    if not isinstance(records,list): raise ValueError('Native SpiderFoot event report must be an array.')
    if records:
        for index,event in enumerate(records):
            if not isinstance(event,dict): raise ValueError('Native event must be an object.')
            cap_id=capture_ids['spiderfoot-events.json']
            updated['observations'].append({'id':f'OBS-OSINT-{token}-{index+1}','summary':str(event.get('module',''))+' reported '+str(event.get('type',''))+': '+str(event.get('data',''))[:500],'status':'tool-reported','confidence':'unrated','uncertainty':uncertainty,'capture_ids':[cap_id],'provenance_ids':[cap_id],'record_index':index,'native_event_hash':event.get('hash')})
    else:
        updated['observations'].append({'id':'OBS-OSINT-'+token,'summary':f"OSINT run for {run.get('target')} retained {len(files)} report files; exit {run['exit_code']}.",'status':'tool-reported','confidence':'unrated','uncertainty':uncertainty,'capture_ids':list(capture_ids.values()),'provenance_ids':list(capture_ids.values())})
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    updated['artifacts'].append({'id':'ART-OSINT-'+token,'artifact_type':'osint-run','path':artifact_home.relative_to(output.parent).as_posix(),'status':'preserved','confidence':'unrated','uncertainty':uncertainty,'provenance_ids':list(capture_ids.values())})
    updated['history'].append({'id':'HIST-OSINT-'+token,'summary':'Attached local OSINT reports as unverified tool observations; no entities, relations, claims or judgments were resolved.','status':'recorded','confidence':'unrated','uncertainty':uncertainty})
    if updated['posture'] in {'watch-ready','publication-ready'}:
        updated['posture']='provisional'
        for check in updated['checks']:
            if check.get('check_type') in {'baseline-integrity','provenance','citation-integrity','redaction','editorial-challenge'}: check['status']='needs-review'
    errors=validate_case(updated)
    if errors: raise ValueError('Case revision failed native validation: '+'; '.join(errors))
    if case_path.read_bytes()!=original: raise ValueError('Original case changed concurrently; it was preserved.')
    # Exclusive creation preserves existing output and source case bytes.
    with output.open('x',encoding='utf-8') as stream: json.dump(updated,stream,indent=2,ensure_ascii=False);stream.write('\n')
    return {'case':str(output),'run_state':state,'captures':len(files),'observations_added':len(updated['observations'])-len(case['observations']),'entities_resolved':0,'semantic_truth_assessed':False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbench',type=Path)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('discover')
    forward=commands.add_parser('run');forward.add_argument('arguments',nargs=argparse.REMAINDER)
    attach_parser=commands.add_parser('attach-run')
    for flag in ['case','run','output']: attach_parser.add_argument('--'+flag,type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        home=workbench(args.workbench)
        if args.command=='discover':
            registry=json.loads((home/'registry.json').read_text(encoding='utf-8-sig'))
            print(json.dumps({'home':str(home),'tools':registry['tools'],'evidence_boundary':registry.get('evidence_boundary')},indent=2));return 0
        if args.command=='run':
            if not args.arguments or args.arguments[0] not in COMMANDS: raise ValueError('Choose a named OSINT workbench command: '+', '.join(sorted(COMMANDS)))
            environment=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
            return subprocess.run([sys.executable,str(home/'osint.py'),*args.arguments],env=environment).returncode
        print(json.dumps(attach(home,args.case,args.run,args.output),indent=2));return 0
    except (OSError,ValueError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({'state':'unavailable-or-invalid','error':str(exc),'executed':False}),file=sys.stderr);return 2
if __name__=='__main__': raise SystemExit(main())

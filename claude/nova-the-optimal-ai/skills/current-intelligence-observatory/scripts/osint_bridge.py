#!/usr/bin/env python3
"""Use a discovered local OSINT workbench and preserve its reports in a native case revision."""
from __future__ import annotations
import argparse,copy,datetime,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from observatory_guardrail import validate_case,receipt,parse_time,text
from safe_io import load,loads,reject_links,relative_name,namespace,bytes_json,write_new
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
        path=reject_links(Path(candidate).expanduser())
        if (path/'osint.py').is_file() and (path/'registry.json').is_file():
            if (path/'setup-receipt.json').exists() and load(path/'setup-receipt.json').get('state')!='complete':raise ValueError('Selected workbench setup is incomplete. Resume its exact setup plan or choose a complete home; existing runs remain preserved.')
            return path
        if explicit: break
    raise ValueError('OSINT workbench unavailable. Run the bundled scripts/setup_osint.py, or set NOVA_OSINT_HOME to its home or supply --workbench; continue ordinary source work when it is absent.')

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def attach(home,case_path,run_path,output):
    home=reject_links(home);case_path=reject_links(case_path);run_path=reject_links(run_path);output=reject_links(output)
    if not run_path.is_relative_to(home/'runs') or run_path==home/'runs':raise ValueError('Attach one native run directory under the selected workbench runs directory.')
    if output.parent!=case_path.parent:raise ValueError('Keep the new case beside the original so existing relative evidence paths remain valid.')
    if output.exists() or output==case_path:raise ValueError('Choose a new output case path; the existing case remains authoritative until reviewed.')
    original=case_path.read_bytes();case=loads(original)
    errors=validate_case(case)
    if errors:raise ValueError('Frame/repair the native case first: '+'; '.join(errors))
    files=[]
    for p in sorted(run_path.iterdir()):
        reject_links(p)
        if p.is_file():files.append(p)
    namespace([p.name for p in files])
    if sum(p.stat().st_size for p in files)>100*1024*1024:raise ValueError('Run reports exceed 100 MiB; select a smaller scoped run.')
    snapshots={p.name:p.read_bytes() for p in files}
    if 'run.json' not in snapshots:raise ValueError('Run receipt is missing')
    run=loads(snapshots['run.json']);errors=[]
    if not isinstance(run,dict):raise ValueError('Run receipt must be an object')
    completed=parse_time(run.get('completed_at'),'completed_at',errors,'run')
    started=parse_time(run.get('started_at'),'started_at',errors,'run')
    if type(run.get('exit_code')) is not int or not completed:errors.append('Run receipt requires an integer exit code and valid completion time')
    if started and completed and started>completed:errors.append('Run completion predates its start')
    if not text(run.get('target')):errors.append('Run target must be nonempty text')
    if not isinstance(run.get('command'),list) or not run['command'] or any(not text(v) for v in run['command']):errors.append('Run command must be a nonempty array of text arguments')
    inventory=run.get('artifacts');verified_inventory=False
    if run.get('format')=='cd-osint-run/v1':
        if not isinstance(inventory,dict) or set(inventory)!=set(snapshots)-{'run.json'}:errors.append('Run artifact inventory does not match retained report files')
        else:
            for name,data in snapshots.items():
                if name!='run.json' and inventory[name]!=hashlib.sha256(data).hexdigest():errors.append('Run artifact changed: '+name)
            verified_inventory=not errors
    records=loads(snapshots['spiderfoot-events.json'],100*1024*1024) if 'spiderfoot-events.json' in snapshots else []
    if not isinstance(records,list) or any(not isinstance(e,dict) for e in records):errors.append('Native SpiderFoot event report must be an array of objects')
    else:
        for event in records:
            if any(not isinstance(event.get(k),str) for k in ('module','type','data')):errors.append('Native event requires text module/type/data')
    if errors:raise ValueError('; '.join(errors))
    token=hashlib.sha256(snapshots['run.json']).hexdigest()[:16].upper();src_id='SRC-OSINT-'+token
    if any(item['id']==src_id for item in case['sources']):raise ValueError('This exact run is already attached to the case.')
    synthetic=run.get('synthetic') is True or '--fixture' in run['command']
    suffix=' SYNTHETIC FIXTURE' if synthetic else ''
    state='completed' if run['exit_code']==0 else 'partial-or-failed'
    uncertainty='Derived tool output; provider content, coverage and identity attribution remain unverified.'+suffix
    if not verified_inventory:uncertainty+=' Legacy receipt has no verified artifact inventory; attachment hashes only the supplied snapshot.'
    updated=copy.deepcopy(case)
    updated['sources'].append({'id':src_id,'title':'OSINT run '+run_path.name+suffix,'source_kind':'derived-tool-run','target':run['target'],'exit_code':run['exit_code'],'run_state':state,'status':'available','confidence':'unrated','uncertainty':uncertainty,'receipt_inventory_verified':verified_inventory,'synthetic':synthetic})
    artifact_home=output.parent/(output.stem+'.captures')/run_path.name
    final_capture_root=artifact_home.parent
    if final_capture_root.exists():raise ValueError('Capture destination already exists; choose a new output case path.')
    capture_ids={}
    for index,(name,data) in enumerate(snapshots.items(),1):
        cap_id=f'CAP-OSINT-{token}-{index}';relative=(artifact_home/name).relative_to(output.parent).as_posix()
        uri=(run_path/name).as_uri()
        updated['captures'].append({'id':cap_id,'source_ids':[src_id],'original_url':uri,'canonical_url':uri,'retrieved_at':run['completed_at'],'artifact_path':relative,'sha256':hashlib.sha256(data).hexdigest(),'preservation_status':'preserved','status':'preserved','confidence':'unrated','uncertainty':uncertainty,'source_kind':'derived-tool-report','external_source_url':None})
        capture_ids[name]=cap_id
    if records:
        for index,event in enumerate(records):
            cap_id=capture_ids['spiderfoot-events.json']
            updated['observations'].append({'id':f'OBS-OSINT-{token}-{index+1}','summary':event['module']+' reported '+event['type']+': '+event['data'][:500],'status':'tool-reported','confidence':'unrated','uncertainty':uncertainty,'capture_ids':[cap_id],'provenance_ids':[cap_id],'record_index':index,'native_event_hash':event.get('hash')})
    else:updated['observations'].append({'id':'OBS-OSINT-'+token,'summary':f"OSINT run for {run['target']} retained {len(files)} report files; exit {run['exit_code']}.",'status':'tool-reported','confidence':'unrated','uncertainty':uncertainty,'capture_ids':list(capture_ids.values()),'provenance_ids':list(capture_ids.values())})
    updated['artifacts'].append({'id':'ART-OSINT-'+token,'artifact_type':'osint-run','path':artifact_home.relative_to(output.parent).as_posix(),'status':'preserved','confidence':'unrated','uncertainty':uncertainty,'provenance_ids':list(capture_ids.values()),'not_captured_directories':[p.name for p in run_path.iterdir() if p.is_dir()]})
    updated['history'].append({'id':'HIST-OSINT-'+token,'summary':'Attached supplied local reports as tool observations; no entity, claim or relationship is resolved.','status':'recorded','confidence':'unrated','uncertainty':uncertainty})
    updated['posture']='provisional'
    # An attachment cannot silently move the evidence cutoff. The reviewer must acknowledge it.
    if updated.get('evidence_as_of'):
        prior=updated.pop('evidence_as_of');updated['previous_evidence_as_of']=prior
    for check in updated['checks']:
        if check.get('status')=='passed':check['status']='needs-review'
    updated['next_action']={'action':'Review the attached tool observations, their coverage and source lineage; set an evidence cutoff before any ready posture.','owner':case['next_action']['owner'],'advance_when':'The added reports are read and material claims are checked against independent source evidence.'}
    errors=validate_case(updated)
    if errors:raise ValueError('Case revision failed native validation: '+'; '.join(errors))
    # Prepare everything first. Final capture placement is rolled back if exclusive case creation fails.
    with tempfile.TemporaryDirectory(prefix='.observatory-attach-',dir=output.parent) as tmp:
        stage=Path(tmp)/'captures';folder=stage/run_path.name;folder.mkdir(parents=True)
        for name,data in snapshots.items():(folder/name).write_bytes(data)
        if case_path.read_bytes()!=original:raise ValueError('Original case changed concurrently; it was preserved.')
        if output.exists() or final_capture_root.exists():raise ValueError('Destination appeared during preparation; choose a new output.')
        created=False
        try:
            stage.rename(final_capture_root);created=True
            write_new(output,bytes_json(updated))
        except Exception:
            if created and final_capture_root.parent==output.parent and final_capture_root.name==output.stem+'.captures':shutil.rmtree(final_capture_root)
            raise
    return {'case':str(output),'run_state':state,'captures':len(files),'observations_added':len(updated['observations'])-len(case['observations']),'entities_resolved':0,'semantic_truth_assessed':False,'receipt_inventory_verified':verified_inventory}

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
            registry=load(home/'registry.json')
            print(json.dumps({'home':str(home),'tools':registry['tools'],'evidence_boundary':registry.get('evidence_boundary')},indent=2));return 0
        if args.command=='run':
            if not args.arguments or args.arguments[0] not in COMMANDS: raise ValueError('Choose a named OSINT workbench command: '+', '.join(sorted(COMMANDS)))
            environment=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
            return subprocess.run([sys.executable,str(home/'osint.py'),*args.arguments],env=environment).returncode
        print(json.dumps(attach(home,args.case,args.run,args.output),indent=2));return 0
    except (OSError,ValueError,KeyError,UnicodeError) as exc:
        print(json.dumps({'state':'unavailable-or-invalid','error':str(exc),'executed':False}),file=sys.stderr);return 2
if __name__=='__main__': raise SystemExit(main())

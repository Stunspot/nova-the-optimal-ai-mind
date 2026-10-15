#!/usr/bin/env python3
"""Initialize, validate and inspect native OMNARA campaigns (stdlib only)."""
from __future__ import annotations
import argparse, json, re, shutil, sys, tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from evidence_contract import precedes, read_json,read_jsonl,text,clock,SOURCE_ID,CLAIM_ID,native_files,subject,review_status,sha,visible_report
from custody import reject_links,tree_files

TIERS={'focused','deep','exhaustive'}
PHASES={'framing','mapping','breadth-sweep','depth-reading','reconciliation','gap-fill','synthesis','citation-audit','review','complete','halted'}
STATUSES={'active','complete','awaiting-evidence','awaiting-authority','capability-limited','budget-exhausted','partial-success','paused'}
SOURCE_STATES={'discovered','inspected','opened','deeply-read','excluded','duplicate','inaccessible','cited'}
STATE_PREREQUISITES={'inspected':{'discovered'},'opened':{'discovered','inspected'},'deeply-read':{'discovered','inspected','opened'},'cited':{'discovered','inspected','opened','deeply-read'}}
COMPLETE_ARTIFACTS={'research-brief.md','coverage-matrix.md','contradictions.md','campaign-summary.md','report.md'}

def word_count(value):return len(re.findall(r"\b[\w'-]+\b",value))
def file_sha256(path):return sha(path)
def note_is_substantive(path):
    if not Path(path).is_file():return False
    value=reject_links(path).read_text(encoding='utf-8').strip()
    return text(value) and 'Preserve bounded source assertions' not in value and bool(re.sub(r'(?m)^\s*#.*$','',value).strip())

def _validate(directory):
    errors=[];directory=reject_links(directory);native_files(directory);c=read_json(directory/'campaign.json')
    if c.get('format')!='omnara-research-campaign/v1':errors.append('campaign.json: unsupported format')
    for key,allowed in [('tier',TIERS),('phase',PHASES),('status',STATUSES)]:
        if not isinstance(c.get(key),str) or c[key] not in allowed:errors.append('campaign.json: invalid '+key)
    for key in ['title','canonical_inquiry','resume_point']:
        if not text(c.get(key)):errors.append('campaign.json: '+key+' must be substantive text')
    for key in ['active_loci','blockers']:
        if not isinstance(c.get(key),list) or any(not text(x) for x in c.get(key,[])):errors.append('campaign.json: '+key+' must be an array of substantive text')
    if not isinstance(c.get('routes'),list):errors.append('campaign.json: routes must be an array')
    if not isinstance(c.get('budgets'),dict):errors.append('campaign.json: budgets must be an object')
    else:
        for key,value in c['budgets'].items():
            if value is not None and (type(value) not in {int,float} or value<0):errors.append('campaign.json: budget '+key+' must be nonnegative or null')
    for key in ['created_at','updated_at','evidence_cutoff']:
        value=c.get(key)
        if value not in (None,'','UNSET') and clock(value) is None:errors.append('campaign.json: invalid '+key+'; use date or timestamp with valid offset')
    cutoff=clock(c.get('evidence_cutoff'))
    sources=read_jsonl(directory/'source-ledger.jsonl');claims=read_jsonl(directory/'claim-ledger.jsonl');queries=read_jsonl(directory/'query-ledger.jsonl')
    ids=set();counts=Counter();source_map={}
    for number,row in enumerate(sources,1):
        label=f'source row {number}';sid=row.get('id')
        if not isinstance(sid,str) or not SOURCE_ID.fullmatch(sid):errors.append(label+': id must be S followed by at least three digits');continue
        if sid in ids:errors.append(label+': duplicate id '+sid)
        ids.add(sid);source_map[sid]=row
        if not text(row.get('title')):errors.append(label+': title required')
        if not text(row.get('url')) and not text(row.get('identifier')):errors.append(label+': url or identifier required')
        states=row.get('states')
        if not isinstance(states,list) or any(not isinstance(x,str) or x not in SOURCE_STATES for x in states):errors.append(label+': invalid states');continue
        state_set=set(states)
        if len(state_set)!=len(states):errors.append(label+': duplicate state')
        counts.update(state_set)
        for state,prerequisites in STATE_PREREQUISITES.items():
            if state in state_set and not prerequisites<=state_set:errors.append(f'{label}: {state} missing prerequisite states: '+', '.join(sorted(prerequisites-state_set)))
        if 'cited' in state_set and state_set&{'excluded','duplicate','inaccessible'}:errors.append(label+': excluded, duplicate or inaccessible source cannot be cited')
        if state_set&{'excluded','duplicate','inaccessible'} and not text(row.get('disposition')):errors.append(label+': excluded/duplicate/inaccessible needs a reason in disposition')
        if 'deeply-read' in state_set and not note_is_substantive(directory/'notes'/f'{sid}.md'):errors.append(label+': deeply-read requires a non-template evidence note; length alone proves no reading')
        for key in ['published_at','updated_at','accessed_at','accessed_date','date']:
            value=row.get(key)
            if value not in (None,'','unknown','undated') and clock(value) is None:errors.append(label+': invalid '+key)
        published=clock(row.get('published_at'))
        if cutoff and published and precedes(c['evidence_cutoff'],row.get('published_at')):errors.append(label+': publication beyond declared evidence cutoff')
    for sid,row in source_map.items():
        if 'duplicate' in row.get('states',[]):
            canonical=row.get('duplicate_of')
            if not isinstance(canonical,str) or canonical not in ids or canonical==sid:errors.append(sid+': duplicate_of must identify another retained source')
            elif 'duplicate' in source_map[canonical].get('states',[]):errors.append(sid+': duplicate_of must identify canonical source, not another duplicate')
    claim_ids=set()
    for number,row in enumerate(claims,1):
        label=f'claim row {number}';cid=row.get('id')
        if not isinstance(cid,str) or not CLAIM_ID.fullmatch(cid):errors.append(label+': id must be C followed by at least three digits')
        elif cid in claim_ids:errors.append(label+': duplicate id '+cid)
        else:claim_ids.add(cid)
        if not text(row.get('claim')):errors.append(label+': claim must be substantive text')
        links=row.get('source_ids')
        if not isinstance(links,list) or any(not isinstance(x,str) for x in links):errors.append(label+': source_ids must be array of IDs')
        else:
            if len(set(links))!=len(links):errors.append(label+': duplicate source link')
            for sid in links:
                if sid not in ids:errors.append(label+': unknown source '+sid)
        for key in ['semantic_audit','support','evidence_status','disposition']:
            if key in row and not text(row[key]):errors.append(label+': '+key+' must be text')
    qids=set()
    for number,row in enumerate(queries,1):
        label=f'query row {number}';qid=row.get('id')
        if not text(qid) or qid in qids:errors.append(label+': unique query id required')
        else:qids.add(qid)
        if not text(row.get('query')) and not text(row.get('text')):errors.append(label+': query text required')
        links=row.get('result_ids')
        if not isinstance(links,list) or any(not isinstance(x,str) for x in links):errors.append(label+': result_ids must be array of IDs')
        else:
            for sid in links:
                if sid not in ids:errors.append(label+': unknown result source '+sid)
        for key in ['executed_at','timestamp']:
            if key in row and not clock(row[key]):errors.append(label+': invalid '+key)
    expected={state.replace('-','_'):counts[state] for state in SOURCE_STATES};expected['queries']=len(queries)
    counters=c.get('counters')
    if not isinstance(counters,dict):errors.append('campaign.json: counters must be an object')
    else:
        for key,value in expected.items():
            if type(counters.get(key)) is not int or counters[key]!=value:errors.append(f'campaign.json: counter {key} does not match ledger count {value}')
    for name in ['research-brief.md','coverage-matrix.md','contradictions.md']:
        if not (directory/name).is_file():errors.append('missing '+name)
    complete=c.get('phase')=='complete' or c.get('status')=='complete'
    if complete:
        if c.get('phase')!='complete' or c.get('status')!='complete':errors.append('complete phase and status must agree')
        for name in COMPLETE_ARTIFACTS:
            path=directory/name
            if not path.is_file() or not note_is_substantive(path):errors.append('complete campaign needs non-template '+name)
            elif path.read_text(encoding='utf-8')==(Path(__file__).parents[1]/'assets/campaign-vault'/name).read_text(encoding='utf-8'):errors.append('complete campaign still contains template '+name)
        if not errors:
            from citation_audit import audit
            current=audit(directory)
            if current['errors']:errors.extend('complete citation integrity: '+x for x in current['errors'])
            saved=directory/'citation-audit-structural.json'
            if not saved.is_file():errors.append('complete campaign missing structural audit')
            else:
                prior=read_json(saved)
                if prior.get('result')!='pass' or prior.get('inputs_sha256')!=current.get('inputs_sha256'):errors.append('complete campaign structural audit missing, failed or stale')
        errors.extend('complete campaign: '+x for x in review_status(directory)['errors'])
    return errors

def validate(directory):
    try:return _validate(Path(directory))
    except (OSError,ValueError,TypeError,KeyError) as exc:return [str(exc)]

def source_counts(directory):
    counts=Counter()
    for row in read_jsonl(Path(directory)/'source-ledger.jsonl'):
        states=row.get('states')
        if not isinstance(states,list) or any(not isinstance(x,str) for x in states):raise ValueError('source states must be array of strings')
        counts.update(set(states))
    return counts

def initialize(template,destination,title,query,tier):
    template=reject_links(template);destination=reject_links(destination)
    if not text(title) or not text(query) or tier not in TIERS:raise ValueError('substantive title, verbatim inquiry and valid tier required')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):raise ValueError('destination is not empty: '+str(destination))
    tree_files(template);native_files(template);destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.omnara-init-',dir=destination.parent) as tmp:
        staged=Path(tmp)/'campaign';shutil.copytree(template,staged)
        c=read_json(staged/'campaign.json');now=datetime.now(timezone.utc).isoformat();c.update(title=title,canonical_inquiry=query,tier=tier,created_at=now,updated_at=now)
        (staged/'campaign.json').write_text(json.dumps(c,indent=2)+'\n',encoding='utf-8',newline='\n')
        brief=staged/'research-brief.md';brief.write_text(brief.read_text(encoding='utf-8').replace("Preserve the user's wording verbatim.",query),encoding='utf-8',newline='\n')
        errors=validate(staged)
        if errors:raise ValueError('; '.join(errors))
        if destination.exists():destination.rmdir() # Only the previously verified empty directory.
        staged.rename(destination)

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('destination',type=Path);init.add_argument('--title',required=True);init.add_argument('--query',required=True);init.add_argument('--tier',choices=sorted(TIERS),default='deep')
    for name in ['validate','summary','review-subject']:
        sub.add_parser(name).add_argument('directory',type=Path)
    args=parser.parse_args()
    try:
        if args.command=='init':initialize(Path(__file__).parents[1]/'assets/campaign-vault',args.destination,args.title,args.query,args.tier);print('INITIALIZED: '+str(args.destination));return 0
        if args.command=='review-subject':print(json.dumps(subject(args.directory),indent=2));return 0
        errors=validate(args.directory)
        if errors:
            for error in errors:print('ERROR: '+error)
            return 1
        if args.command=='validate':print('VALID structure and declared review boundary: '+str(args.directory));return 0
        c=read_json(args.directory/'campaign.json');print(json.dumps({'title':c['title'],'phase':c['phase'],'status':c['status'],'source_counts':source_counts(args.directory),'semantic_review':review_status(args.directory),'resume_point':c['resume_point']},indent=2));return 0
    except (OSError,ValueError,TypeError) as exc:print('ERROR: '+str(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())

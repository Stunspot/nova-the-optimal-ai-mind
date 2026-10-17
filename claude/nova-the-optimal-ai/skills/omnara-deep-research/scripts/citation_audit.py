#!/usr/bin/env python3
"""Check visible citation mechanics; never infer entailment or approval."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from evidence_contract import read_jsonl,read_json,MARKER,SOURCE_ID,CLAIM_ID,text,sha,visible_report,subject
from custody import reject_links

def audit(directory):
    errors=[];warnings=[];directory=reject_links(directory)
    report=visible_report((directory/'report.md').read_text(encoding='utf-8'))
    sources=read_jsonl(directory/'source-ledger.jsonl');claims=read_jsonl(directory/'claim-ledger.jsonl')
    sm={};cm={}
    for row in sources:
        sid=row.get('id')
        if not isinstance(sid,str) or not SOURCE_ID.fullmatch(sid):errors.append('invalid source ID');continue
        if sid in sm:errors.append('duplicate source ID: '+sid)
        sm[sid]=row
    for row in claims:
        cid=row.get('id')
        if not isinstance(cid,str) or not CLAIM_ID.fullmatch(cid):errors.append('invalid claim ID');continue
        if cid in cm:errors.append('duplicate claim ID: '+cid)
        cm[cid]=row
    headings=list(re.finditer(r'(?im)^#{1,6}\s+(?:Sources|Bibliography|References)\s*$',report))
    if len(headings)>1:errors.append('ambiguous multiple source/bibliography sections')
    bibliography=report[headings[0].end():] if headings else ''
    if headings:
        stop=re.search(r'(?m)^#{1,6}\s+',bibliography)
        if stop:bibliography=bibliography[:stop.start()]
    body=report[:headings[0].start()] if headings else report
    markers=MARKER.findall(body);all_markers=MARKER.findall(report)
    links=set()
    for cid,row in cm.items():
        if not text(row.get('claim')):errors.append(cid+': claim text required')
        ids=row.get('source_ids')
        if not isinstance(ids,list) or any(not isinstance(x,str) for x in ids):errors.append(cid+': source_ids must be array of IDs');continue
        links.update(ids)
        for sid in ids:
            if sid not in sm:errors.append(cid+': unknown source '+sid)
    for sid in sorted(set(all_markers)):
        if sid not in sm:errors.append('report marker has no source: '+sid)
    from research_campaign import note_is_substantive,STATE_PREREQUISITES
    for sid in sorted(set(markers)):
        row=sm.get(sid)
        if row is None:continue
        states=row.get('states')
        if not isinstance(states,list) or any(not isinstance(x,str) for x in states):errors.append(sid+': invalid states');continue
        states=set(states)
        if not (STATE_PREREQUISITES['cited']|{'cited'})<=states:errors.append(sid+': cited source lacks earned reading states')
        if states&{'duplicate','excluded','inaccessible'}:errors.append(sid+': cited source has unusable state')
        if not note_is_substantive(directory/'notes'/f'{sid}.md'):errors.append(sid+': missing non-template evidence note')
        if sid not in links:errors.append(sid+': no recorded claim links to cited source')
        entries=[block for block in re.split(r'\n\s*\n',bibliography) if '['+sid+']' in block]
        title=row.get('title');locator=row.get('url') or row.get('identifier')
        if not text(title) or not text(locator) or not any(title in entry and locator in entry for entry in entries):errors.append(sid+': visible Sources entry needs exact title and locator')
    for sid,row in sm.items():
        if isinstance(row.get('states'),list) and 'cited' in row['states'] and sid not in markers:errors.append(sid+': ledger says cited but no visible report-body citation exists')
    if not markers:warnings.append('No source-cited conclusion in this report; any no-evidence outcome requires explicit semantic review of its search and limitations.')
    if not text(body):errors.append('report has no visible body')
    binding=subject(directory)
    return {'format':'omnara-citation-integrity/v1','result':'fail' if errors else 'pass','report_markers':len(markers),'unique_cited_sources':len(set(markers)),'errors':errors,'warnings':warnings,'semantic_entailment':'not established by this deterministic audit','inputs_sha256':{'review_subject':binding['sha256']},'projection_boundary':'Supported prose outside HTML comments and fenced code; not arbitrary HTML or renderer conformance.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);args=parser.parse_args()
    try:
        result=audit(args.directory)
        from file_ops import atomic
        atomic(reject_links(args.directory)/'citation-audit-structural.json',json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));return 0 if result['result']=='pass' else 1
    except (OSError,ValueError,TypeError) as exc:print('ERROR citation audit: '+str(exc));return 1
if __name__=='__main__':raise SystemExit(main())

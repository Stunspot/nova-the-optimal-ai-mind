"""AnswerLayer local ledger operations. No network, authentication, monitoring or publication."""
from __future__ import annotations
import argparse,copy,difflib,hashlib,sys,uuid
from pathlib import Path
from ledgerlib import *
from io_contract import atomic_bytes
from snapshotlib import snapshot

def checked(path,previous=None):
 d=load(path);errors=validate(d,load(previous) if previous else None)
 if errors:raise LedgerError('; '.join(errors))
 return d

def parser():
 p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
 q=subs.add_parser('init');q.add_argument('destination');q.add_argument('--title',default='Untitled decision surface');q.add_argument('--owner',default='UNASSIGNED')
 q=subs.add_parser('validate');q.add_argument('ledger');q.add_argument('--previous')
 q=subs.add_parser('qualify');q.add_argument('candidate')
 q=subs.add_parser('compare');q.add_argument('before');q.add_argument('after')
 q=subs.add_parser('recheck');q.add_argument('anchor');q.add_argument('interval_days',type=int)
 q=subs.add_parser('watch');q.add_argument('observed');q.add_argument('operator');q.add_argument('threshold')
 q=subs.add_parser('conflicts');q.add_argument('ledger')
 for name in ('citations','brief','migrate'):
  q=subs.add_parser(name);q.add_argument('ledger');q.add_argument('output')
  if name=='brief':q.add_argument('--patch',action='append',default=[])
 q=subs.add_parser('approval-basis');q.add_argument('ledger');q.add_argument('patch_id')
 q=subs.add_parser('adopt');q.add_argument('ledger');q.add_argument('patch_id');q.add_argument('output')
 q=subs.add_parser('snapshot');q.add_argument('workspace');q.add_argument('output')
 subs.add_parser('self-check')
 return p

def execute(a):
 if a.command=='init':
  dest=unlinked(a.destination);dest.mkdir(parents=True,exist_ok=True);unlinked(dest)
  d=load(ROOT/'assets/reality-ledger.template/reality-ledger.json');stamp=utc_stamp();d.update(ledger_id='RL-'+uuid.uuid4().hex,title=a.title,owner=a.owner,created_at=stamp,updated_at=stamp);d['baseline']['context']={k:d[k] for k in ('scope','decision_use','owner')}
  errors=validate(d)
  if errors:raise LedgerError('; '.join(errors))
  output=write(dest/'reality-ledger.json',d);return {'status':'created','output':str(output),'baseline_currentness':'unknown; supply an actual baseline cutoff'}
 if a.command=='validate':
  d=load(a.ledger);e=validate(d,load(a.previous) if a.previous else None)
  return {'valid':not e,'errors':e,'format':d.get('format') if isinstance(d,dict) else None,'status':'invalid' if e else 'legacy_readable' if d['format']==LEGACY else 'ledger_valid','prior_compared':bool(a.previous),'boundary':'Structure, references and supplied history checked. No facts, consent or undisclosed history authenticated.'}
 if a.command=='qualify':
  e=qualify(load(a.candidate));return {'valid':not e,'errors':e,'boundary':'Typed fields and references supplied in one candidate; not factual or strategic proof.'}
 if a.command=='compare':return {'diff':'\n'.join(difflib.unified_diff(raw(a.before).splitlines(),raw(a.after).splitlines(),fromfile='baseline',tofile='proposed',lineterm='')),'boundary':'Text comparison only'}
 if a.command=='recheck':return {'review_date':next_recheck(day(a.anchor,'anchor'),a.interval_days).isoformat(),'boundary':'Chosen review interval, not a measured evidence half-life or monitoring service.'}
 if a.command=='watch':return watch_result(None if a.observed=='unknown' else a.observed,a.operator,a.threshold)
 if a.command=='snapshot':return snapshot(a.workspace,a.output)
 if a.command=='self-check':
  required=['SKILL.md','manifest.json','agents/openai.yaml','schemas/reality-ledger.schema.json','schemas/reality-ledger-v1.schema.json','assets/reality-ledger.template/reality-ledger.json','knowledge/operating-doctrine.md','knowledge/evidence-currentness.md','knowledge/state-and-authority.md','workspace/README.md']
  missing=[n for n in required if not unlinked(ROOT/n).is_file()]
  errors=missing+validate(load(ROOT/'assets/reality-ledger.template/reality-ledger.json'))
  return {'valid':not errors,'errors':errors,'boundary':'Required package files and blank template only; run verification tests for behavior.'}
 d=checked(a.ledger)
 if a.command=='conflicts':
  groups={}
  for x in d['candidates']:
   if x.get('conflict_key'):groups.setdefault(x['conflict_key'],[]).append(x['id'])
  return {'overlap_groups':{k:v for k,v in groups.items() if len(v)>1},'fuzz_records':[x for x in d['fuzz'] if x['status']=='fuzz_unresolved'],'candidate_fuzz':[x['id'] for x in d['candidates'] if x['status']=='fuzz_unresolved'],'boundary':'Shared keys mean overlap for review, not proven contradiction. Read scope, dates, applicability and actual claims.'}
 if a.command=='approval-basis':return approval_basis(d,a.patch_id)
 if a.command=='migrate':
  out=migrate(d,input_bytes(a.ledger),Path(a.ledger).name);write(a.output,out);return {'status':'migrated_to_new_file','output':str(a.output),'boundary':out['migration']['boundary']}
 if a.command=='adopt':
  out=adopt(d,a.patch_id);write(a.output,out);return {'status':'adopted_in_new_checkpoint','output':str(a.output),'baseline_version':out['baseline']['version'],'revision':out['revision'],'boundary':'Exact local patch applied using the supplied content-bound authorization assertion. Original checkpoint preserved; consent not authenticated and no external distribution.'}
 if a.command=='citations':
  out={'format':'answerlayer/citation-manifest/v2','ledger_sha256':digest(a.ledger),'ledger_id':d['ledger_id'],'sources':copy.deepcopy(d['sources']),'boundary':'Inventory of supplied provenance; no source inspected by this exporter and no claim verified.'};write(a.output,out);return {'status':'citation_manifest_written','output':str(a.output)}
 if a.command=='brief':
  requested=set(a.patch);known={x['id'] for x in d['patches']}
  if requested-known:raise LedgerError('Unknown requested patch: '+', '.join(sorted(requested-known)))
  eligible=[];excluded={}
  for p in d['patches']:
   if requested and p['id'] not in requested:continue
   approval,error=eligible_patch(d,p)
   if error:excluded[p['id']]=error
   else:eligible.append((p,approval))
  if requested and excluded:raise LedgerError('Requested patch is ineligible: '+dumps(excluded))
  if not eligible:raise LedgerError('No eligible current patch for local brief: '+dumps(excluded))
  lines=['# '+d['title']+' — local patch brief','', 'Prepared local artifact. Recorded authorization is an assertion, not authenticated consent. No publication or external distribution has occurred.','',f"Ledger: {d['ledger_id']}; revision: {d['revision']}; current answer cutoff: {d['baseline']['as_of']}."]
  for patch,approval in eligible:
   lines += ['', '## '+patch['id'], '', '**Before:** '+patch['before'],'','**After:** '+patch['after'],'','**Mechanism:** '+patch['mechanism'],'','**Scope:** '+patch['scope'],'','**Counterfactual:** '+patch['counterfactual'],'','**Recheck:** '+patch['recheck'],'','**Result cutoff:** '+patch['result_as_of'],'','Recorded decision: '+approval['id']+' by '+approval['actor']+' at '+approval['at']+'; scope '+approval['scope']+'; basis '+approval['authorization_basis']+'.','','Patch SHA256: '+patch_hash(patch),'']
   for source in d['sources']:
    if source['id'] in patch['source_ids']:lines += ['Source '+source['id']+': '+source['title']+' — '+source['locator']+'; publication '+source['publication_date']+'; access '+source['access_status']+'.',dumps(source['supports'])]
  body=('\n'.join(lines)+'\n').encode('utf-8')
  if len(body)>2_000_000:raise LedgerError('Brief exceeds2 MB')
  atomic_bytes(a.output,body);return {'status':'local_brief_written','output':str(a.output),'included':[p['id'] for p,_ in eligible],'excluded':excluded,'boundary':'Prepared local artifact; no external publication'}
 raise LedgerError('Unsupported operation')

def main(argv=None):
 try:
  result=execute(parser().parse_args(argv));print(dumps(result));return 1 if result.get('valid') is False else 0
 except (LedgerError,OSError,UnicodeError,ValueError,OverflowError,RecursionError) as exc:
  print(dumps({'status':'refused','valid':False,'errors':[str(exc)],'boundary':'Operation did not complete; existing input/output bytes were not intentionally replaced.'}));return 2
if __name__=='__main__':raise SystemExit(main())

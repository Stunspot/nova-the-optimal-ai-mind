#!/usr/bin/env python3
"""Read-only consistency and current-review checks for saved interview preparation."""
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
from interview_io import contained,digest,field,jsload,moment,no_later,read,reject_links,substantive,table,visible
TEXTS=('employer-role-brief.md','answer-bank.md','mock-session-record.md','critique-and-drills.md','questions-to-ask.md','final-interview-brief.md')
HEADERS={
 'source-register.csv':('source_id','source_type','title_or_identity','path_or_url','source_date','retrieved_at','custody','use','notes'),
 'source-evidence.csv':('source_id','copy_path','sha256','locator','excerpt'),
 'criteria.csv':('criterion_id','criterion','source_ids','priority','notes'),
 'evidence-register.csv':('evidence_id','evidence_summary','source_ids','evidence_type','confirmation_state','notes'),
 'evidence-support.csv':('evidence_id','source_id','locator','excerpt','basis','rationale'),
 'question-map.csv':('question_id','question_family','question_text','criterion_id','probability','evidence_ids','practice_priority','practice_status','notes')}
REQUIRED_FILES=TEXTS+tuple(HEADERS)+('practice-record.json',)
SHA=re.compile(r'[a-f0-9]{64}')

def textval(value,label):
 if not isinstance(value,str) or not value.strip():raise ValueError(label+': expected nonempty text')
 return value.strip()
def obj(value,label):
 if not isinstance(value,dict):raise ValueError(label+': expected object')
 return value

def array(value,label):
 if not isinstance(value,list):raise ValueError(label+': expected array')
 return value

def ids(raw,label,pattern=None):
 if not isinstance(raw,str):raise ValueError(label+': expected semicolon-separated IDs')
 result=[x.strip() for x in raw.split(';') if x.strip()]
 if len(result)!=len(set(result)) or any(pattern and not re.fullmatch(pattern,x) for x in result):raise ValueError(label+': invalid/duplicate IDs')
 return result

def choice(value,allowed,label):
 if not isinstance(value,str) or value not in allowed:raise ValueError(label+': expected '+', '.join(sorted(allowed)))
 return value

def indexed(rows,key,pattern,label):
 result={}
 for row in rows:
  value=row[key]
  if not re.fullmatch(pattern,value) or value in result:raise ValueError(label+': invalid/duplicate '+key)
  result[value]=row
 return result

def joined(values,inventory,label):
 for value in values:
  if value not in inventory:raise ValueError(label+': unknown ID '+str(value))

def hash_json(value):return digest(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())

def load_inputs(root):
 docs={n:read(root,n) for n in TEXTS};tables={n:table(root,n,h) for n,h in HEADERS.items()}
 paths=set(TEXTS)|set(HEADERS)
 for row in tables['source-evidence.csv']:
  read(root,row['copy_path']);paths.add(row['copy_path'])
 return docs,tables,paths

def subjects(root):
 docs,tables,paths=load_inputs(root)
 scope_paths=paths-{'question-map.csv','mock-session-record.md','critique-and-drills.md','final-interview-brief.md','questions-to-ask.md'}
 scope_rows=[{k:v for k,v in row.items() if k!='practice_status'} for row in tables['question-map.csv']]
 identity=obj(jsload(root,'practice-record.json'),'practice record').get('interview_id') if (root/'practice-record.json').exists() else None
 scope=hash_json({'interview_id':identity,'files':{n:digest(contained(root,n).read_bytes()) for n in sorted(scope_paths)},'questions':scope_rows})
 current_paths=paths|({'practice-record.json'} if (root/'practice-record.json').exists() else set())
 subject=hash_json({n:digest(contained(root,n).read_bytes()) for n in sorted(current_paths)})
 return {'scope_sha256':scope,'review_subject_sha256':subject}

def validate(root,draft=False):
 errors=[];warnings=[];coverage={'observed':[],'fictional':[],'historical_attempts':[],'transfer':[]}
 root=reject_links(root)
 if not root.is_dir():raise ValueError('Packet is not a directory')
 missing=[n for n in REQUIRED_FILES if not (root/n).is_file()]
 if missing:
  if draft:
   # A draft can be sparse, but supplied machine inputs must still parse safely.
   for n,h in HEADERS.items():
    if (root/n).exists():
     wanted=h
     if n=='question-map.csv' and 'criterion_id' not in read(root,n).splitlines()[0]:wanted=tuple('role_criterion' if v=='criterion_id' else v for v in h)
     table(root,n,wanted)
   if (root/'source-register.md').exists():table(root,'source-register.md',HEADERS['source-register.csv'])
   if (root/'practice-record.json').exists():jsload(root,'practice-record.json')
   for n in TEXTS:
    if (root/n).exists():read(root,n)
   return {'ok':True,'state':'DRAFT','qualification':False,'errors':[],'warnings':['Incomplete packet: '+', '.join(missing)],'practice_coverage':coverage}
  raise ValueError('Missing current artifacts: '+', '.join(missing)+'. Retain legacy records; use --draft and the migration guide.')
 docs,t,paths=load_inputs(root);bindings=subjects(root)
 for name,md in docs.items():
  if not substantive(md):errors.append(name+': no substantive visible content')
 src=indexed(t['source-register.csv'],'source_id',r'SRC-\d{3}','sources')
 evd=indexed(t['evidence-register.csv'],'evidence_id',r'EVD-\d{3}','evidence')
 crit=indexed(t['criteria.csv'],'criterion_id',r'CRIT-\d{3}','criteria')
 questions=indexed(t['question-map.csv'],'question_id',r'Q-\d{3}','questions')
 if not src or not crit or not questions:errors.append('A complete packet needs source, criterion and question records')
 p=obj(jsload(root,'practice-record.json'),'practice record')
 if p.get('format')!='interview-practice/v1':raise ValueError('Unsupported practice record format')
 asof=textval(p.get('as_of'),'as_of')
 if not moment(asof)[1]:raise ValueError('as_of requires a timestamp with known offset')
 textval(p.get('interview_id'),'interview_id')
 choice(p.get('session_state'),{'not-started','in-progress','ended'},'session_state')
 copies={}
 for row in t['source-evidence.csv']:
  sid=row['source_id'];joined([sid],src,'source copy')
  if sid in copies:raise ValueError('One bounded retained source copy per source ID; use a separate ID for another copy')
  path=row['copy_path'];data=contained(root,path).read_bytes()
  if not SHA.fullmatch(row['sha256']) or digest(data)!=row['sha256']:errors.append(sid+': retained source hash differs')
  textval(row['locator'],sid+' locator');excerpt=textval(row['excerpt'],sid+' source excerpt')
  if excerpt not in read(root,path):errors.append(sid+': source excerpt absent from retained copy')
  copies[sid]=read(root,path)
 for sid,row in src.items():
  for f in ['source_type','title_or_identity','path_or_url','custody','use']:textval(row[f],sid+' '+f)
  for f in ['source_date','retrieved_at']:
   if row[f] and row[f]!='unknown':
    moment(row[f])
    if not no_later(row[f],asof):errors.append(sid+': '+f+' is after packet cutoff')
  if row['source_date'] not in {'','unknown'} and row['retrieved_at'] not in {'','unknown'} and not no_later(row['source_date'],row['retrieved_at']):errors.append(sid+': capture precedes the stated source issue date')
  if sid not in copies:warnings.append(sid+': original not retained; cannot independently inspect this source here')
 supports={}
 for row in t['evidence-support.csv']:
  eid=row['evidence_id'];sid=row['source_id'];joined([eid],evd,'support');joined([sid],src,'support')
  if sid not in ids(evd[eid]['source_ids'],eid):errors.append(eid+': support source differs from evidence register')
  choice(row['basis'],{'source-excerpt','user-confirmation'},'support basis');textval(row['locator'],eid+' locator');textval(row['rationale'],eid+' rationale')
  excerpt=textval(row['excerpt'],eid+' support excerpt')
  if sid not in copies or excerpt not in copies[sid]:errors.append(eid+': inspectable support excerpt absent')
  supports.setdefault(eid,[]).append(row)
 for eid,row in evd.items():
  textval(row['evidence_summary'],eid+' summary');choice(row['evidence_type'],{'direct','adjacent','user-confirmed'},eid+' type')
  choice(row['confirmation_state'],{'confirmed','confirmation-needed','unsupported'},eid+' confirmation')
  sids=ids(row['source_ids'],eid+' sources',r'SRC-\d{3}');joined(sids,src,eid)
  if row['confirmation_state']=='confirmed' and (not sids or not supports.get(eid)):errors.append(eid+': confirmed evidence needs retained specific support or recorded self-report')
 for cid,row in crit.items():
  textval(row['criterion'],cid+' criterion');choice(row['priority'],{'high','medium','low'},cid+' priority')
  sids=ids(row['source_ids'],cid+' sources',r'SRC-\d{3}');joined(sids,src,cid)
  if not sids:errors.append(cid+': criterion needs a stated basis; retain a labelled hypothetical role source if role details are sparse')
 for qid,row in questions.items():
  for f in ['question_family','question_text']:textval(row[f],qid+' '+f)
  joined([row['criterion_id']],crit,qid)
  choice(row['probability'],{'confirmed-topic','confirmed-question','strongly-indicated','plausible','speculative'},qid+' probability')
  if row['probability'].startswith('confirmed'):
   sids=ids(row.get('confirmation_source_ids',''),qid+' confirmation sources',r'SRC-\d{3}');joined(sids,src,qid)
   if not sids or not any(sid in copies for sid in sids):errors.append(qid+': confirmed topic/question needs retained employer instruction')
   if row['probability']=='confirmed-question' and not any(row['question_text'] in copies.get(sid,'') for sid in sids):errors.append(qid+': confirmed wording absent from retained source')
  choice(row['practice_priority'],{'high','medium','low'},qid+' priority');choice(row['practice_status'],{'planned','practiced','needs-drill','deferred','demonstrated'},qid+' practice')
  joined(ids(row['evidence_ids'],qid+' evidence',r'EVD-\d{3}'),evd,qid)
 # Every supplied answer is checked, not just high-priority rows. Duplicate sections fail.
 answer=visible(docs['answer-bank.md']);sections={}
 for match in re.finditer(r'^##[ \t]+(Q-\d{3})\b[^\n]*\n(.*?)(?=^##[ \t]+|\Z)',answer,re.M|re.S):
  qid,body=match.groups()
  if qid in sections:raise ValueError('Duplicate answer section '+qid)
  joined([qid],questions,'answer');sections[qid]=body
  eids=ids(field(body,'Evidence IDs',False),qid+' answer evidence',r'EVD-\d{3}');joined(eids,evd,qid)
  if set(eids)!=set(ids(questions[qid]['evidence_ids'],qid)):errors.append(qid+': answer evidence IDs differ from question map')
  support=choice(field(body,'Support state'),{'supported','confirmation-needed','honest-gap','proposed-method'},qid+' support')
  if support=='supported' and (not eids or any(evd[e]['confirmation_state']!='confirmed' for e in eids)):errors.append(qid+': supported answer requires confirmed evidence')
  if support=='honest-gap' and eids:errors.append(qid+': honest-gap cannot claim supporting evidence; describe adjacent evidence with its limited claim instead')
  field(body,'Compact answer prompt')
 for qid,q in questions.items():
  if q['practice_priority']=='high' and qid not in sections:errors.append(qid+': high-priority answer missing')
 attempts=indexed([obj(a,'attempt') for a in array(p.get('attempts'),'attempts')],'attempt_id',r'ATT-\d{3}','attempts')
 current={};observed=set();fictional=set()
 for aid,a in attempts.items():
  qid=textval(a.get('question_id'),aid+' question');joined([qid],questions,aid)
  textval(a.get('question_asked'),aid+' actual question');response=textval(a.get('response'),aid+' response')
  origin=choice(a.get('origin'),{'user-verbatim','user-confirmed-summary','assistant-demonstration','fictional'},aid+' origin')
  choice(a.get('mode'),{'coached','realistic','rapid-drill'},aid+' mode');choice(a.get('medium'),{'text','audio','video','in-person'},aid+' medium')
  choice(a.get('assistance'),{'none','cue-given','model-answer-shown'},aid+' assistance')
  at=textval(a.get('recorded_at'),aid+' time')
  if not moment(at)[1]:raise ValueError(aid+': recorded_at requires a timestamp with known offset')
  if not no_later(at,asof):errors.append(aid+': response is after cutoff')
  bound=textval(a.get('scope_sha256'),aid+' scope')
  if not SHA.fullmatch(bound):errors.append(aid+': malformed scope hash')
  assessment=obj(a.get('assessment'),aid+' assessment')
  for name in ['target','observation','rationale']:textval(assessment.get(name),aid+' '+name)
  if assessment['observation'] not in response:errors.append(aid+': feedback observation is absent from response')
  choice(assessment.get('result'),{'needs-drill','workable'},aid+' assessment result')
  if bound==bindings['scope_sha256']:
   current[aid]=a
   if origin in {'user-verbatim','user-confirmed-summary'}:observed.add(qid)
   else:fictional.add(qid)
  else:coverage['historical_attempts'].append(aid)
 if p['session_state']=='not-started' and attempts:errors.append('not-started contradicts retained attempts; keep ended/in-progress or use a new session record')
 if p['session_state'] in {'in-progress','ended'} and not attempts:errors.append('Session has no attempt; preparation alone is not a session')
 drills=indexed([obj(d,'drill') for d in array(p.get('drills'),'drills')],'drill_id',r'DRILL-\d{3}','drills')
 transfer=set();open_targets=set();resolved_before=set()
 for did,d in drills.items():
  for name in ['target','intervention','success_cue','comparison']:textval(d.get(name),did+' '+name)
  state=choice(d.get('state'),{'open','coached-improvement','transfer-demonstrated'},did+' state')
  before=textval(d.get('before_attempt'),did+' before attempt');joined([before],attempts,did)
  base=attempts[before];qid=base['question_id']
  if base['assessment']['target']!=d['target'] or base['assessment']['result']!='needs-drill':errors.append(did+': diagnosed target does not match prior observed gap')
  afterid=d.get('after_attempt','')
  if state=='open':
   if before in current:open_targets.add(qid)
  else:
   joined([afterid],attempts,did);after=attempts[afterid]
   current_drill=before in current and afterid in current
   if base['scope_sha256']!=after['scope_sha256']:errors.append(did+': diagnosis and rerun use different preparation scopes')
   user_origins={'user-verbatim','user-confirmed-summary'}
   before_user=base['origin'] in user_origins;after_user=after['origin'] in user_origins
   learner_rerun=before_user==after_user
   if before_user and not after_user:errors.append(did+': a user performance gap needs a user-origin rerun; retain the demonstration with the drill open')
   elif after_user and not before_user:errors.append(did+': learner improvement needs a user-origin baseline; retain the teaching example and user practice with the drill open')
   if not current_drill:warnings.append(did+': completed drill retained as historical; no current performance coverage')
   elif learner_rerun and after['assessment']['result']=='workable':resolved_before.add(before)
   if after['question_id']!=qid or after['assessment']['target']!=d['target'] or after['assessment']['result']!='workable':errors.append(did+': rerun does not assess the same specific diagnosed behavior')
   if moment(base['recorded_at'])[0]>=moment(after['recorded_at'])[0]:errors.append(did+': rerun must be later than diagnosis')
   if state=='transfer-demonstrated':
    if after['assistance']!='none' or after['question_asked'].strip()==base['question_asked'].strip():errors.append(did+': transfer requires a new uncued probe of the same behavior')
    if after['origin'] not in {'user-verbatim','user-confirmed-summary'} or base['origin'] not in {'user-verbatim','user-confirmed-summary'}:errors.append(did+': demonstration cannot establish observed user transfer')
    if current_drill:transfer.add(qid)
 unresolved={a['question_id'] for aid,a in current.items() if a['origin'] in {'user-verbatim','user-confirmed-summary'} and a['assessment']['result']=='needs-drill' and aid not in resolved_before}
 readiness=obj(p.get('readiness'),'readiness');claim=choice(readiness.get('claim'),{'preparation-only','observed-practice','bounded-transfer','fictional-demonstration'},'readiness claim')
 covered=array(readiness.get('question_ids'),'readiness question IDs')
 if any(not isinstance(v,str) for v in covered) or len(covered)!=len(set(covered)):raise ValueError('Invalid readiness question IDs')
 joined(covered,questions,'readiness')
 for k in ['remaining_gaps','next_action']:textval(readiness.get(k),'readiness '+k)
 if claim=='preparation-only' and covered:errors.append('preparation-only cannot declare performance coverage')
 if claim=='observed-practice' and (not covered or not set(covered)<=observed):errors.append('Claimed practice lacks current declared user responses')
 if claim=='bounded-transfer' and (not covered or not set(covered)<=transfer or set(covered)&(open_targets|unresolved)):errors.append('Transfer claim lacks completed matching probe or retains an open material gap')
 if claim=='fictional-demonstration' and (not covered or not set(covered)<=fictional):errors.append('Fictional coverage lacks matching current demonstration')
 for qid,q in questions.items():
  status=q['practice_status']
  if qid in unresolved and status!='needs-drill':errors.append(qid+': recorded material gap still needs a matching drill')
  if status in {'practiced','needs-drill'} and qid not in observed:errors.append(qid+': practice status lacks current user response')
  if status=='demonstrated' and qid not in fictional:errors.append(qid+': demonstrated status lacks current illustrative response')
  if qid in observed and status not in {'practiced','needs-drill'}:errors.append(qid+': current user response contradicts practice status')
 # Content review is an accountable semantic pass over exact current text, not a parser's invented truth verdict.
 if not draft:
  review=obj(jsload(root,'packet-review.json'),'packet review')
  if review.get('format')!='interview-packet-review/v1' or review.get('subject_sha256')!=bindings['review_subject_sha256']:errors.append('Current packet content review is absent/stale')
  if review.get('scope')!='interview-preparation' or review.get('result')!='consistent-with-stated-limits':errors.append('Review scope/result does not support this packet')
  textval(review.get('reviewer'),'reviewer');rt=textval(review.get('reviewed_at'),'review time')
  if not moment(rt)[1]:raise ValueError('reviewed_at requires a timestamp with known offset')
  if not no_later(rt,asof):errors.append('Review after packet cutoff')
  for a in current.values():
   if not no_later(a['recorded_at'],rt):errors.append('Review predates included practice')
  report=textval(review.get('report_path'),'review report');body=read(root,report)
  if not substantive(body) or review.get('report_sha256')!=digest(contained(root,report).read_bytes()):errors.append('Review report missing substantive content or changed bytes')
 coverage.update(observed=sorted(observed),fictional=sorted(fictional),transfer=sorted(transfer))
 return {'ok':not errors,'state':'BLOCKED' if errors else ('DRAFT' if draft else 'CONSISTENT_REVIEWED_PACKET'),'qualification':not draft and not errors,'errors':errors,'warnings':warnings,'practice_coverage':coverage,'bindings':bindings,'limits':'Declared source/response custody and current review consistency only. No source authentication, semantic entailment, hiring readiness score, or proof that declared user responses were actually spoken.'}

def check(packet,draft=False):
 try:return validate(Path(packet),draft)
 except (ValueError,OSError,KeyError,TypeError,RecursionError,OverflowError) as exc:return {'ok':False,'state':'BLOCKED','qualification':False,'errors':[str(exc)],'warnings':[]}

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('packet',type=Path);parser.add_argument('--json',action='store_true');parser.add_argument('--draft',action='store_true',help='Check supplied inputs without qualifying an incomplete/currently unreviewed packet');parser.add_argument('--subject',action='store_true',help='Read-only current scope and content subject; not a review or approval');args=parser.parse_args(argv)
 if args.subject:
  try:print(json.dumps(subjects(reject_links(args.packet)),indent=2));return 0
  except (ValueError,OSError,KeyError,TypeError) as exc:print('SUBJECT FAILED: '+str(exc),file=sys.stderr);return 2
 result=check(args.packet,args.draft)
 if args.json:print(json.dumps(result,indent=2))
 else:
  for e in result['errors']:print('ERROR: '+e)
  for w in result['warnings']:print('WARNING: '+w)
  print(result['state']);print(result.get('limits','No qualification claim.'))
 return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
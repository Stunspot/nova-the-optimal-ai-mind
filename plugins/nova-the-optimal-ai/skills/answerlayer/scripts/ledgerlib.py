"""Native ledger integrity and bounded decisions, never authentication or factual proof."""
from __future__ import annotations
import copy,hashlib,re
from decimal import Decimal,InvalidOperation
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from io_contract import LedgerError,load,raw,input_bytes,write,dumps,strict,check,day,moment,unlinked
from schema_check import _shape
FORMAT='answerlayer/reality-ledger/v2';LEGACY='answerlayer/reality-ledger/v1';VERSION='0.3.0'
ROOT=Path(__file__).absolute().parents[1]
LISTS=('sources','candidates','deltas','rejections','fuzz','patches','probes','traps','watch','approvals')
STATUSES={'candidate','accepted_delta','rejected_noise','fuzz_unresolved','patched','superseded','retired'}
AUTHORITIES={'model_generated','machine_validated','human_reviewed','human_approved','executed','verified'}

def digest(path):return hashlib.sha256(input_bytes(path)).hexdigest()
def identity(value):return hashlib.sha256(dumps(value,canonical=True).encode('utf-8')).hexdigest()
def baseline_hash(data,baseline=None):
 b=baseline or data['baseline'];return identity({'ledger_id':data['ledger_id'],'version':b['version'],'as_of':b['as_of'],'text':b['text'],'context':b['context']})
def patch_hash(patch):return identity({k:v for k,v in patch.items() if k not in ('status','authority','approved_by','approved_at')})
def baselines(data):return [*data.get('baseline_history',[]),data['baseline']]
def utc_stamp():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def decimal_value(value,label):
 if isinstance(value,bool) or value is None or not isinstance(value,(int,float,str,Decimal)):raise LedgerError(label+': expected a finite decimal')
 text=str(value)
 if len(text)>256 or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',text):raise LedgerError(label+': expected a finite decimal literal')
 try:d=Decimal(text)
 except InvalidOperation as e:raise LedgerError(label+': invalid decimal') from e
 if not d.is_finite() or abs(d.adjusted())>10000:raise LedgerError(label+': decimal outside supported range')
 return d

def watch_result(observed,operator,threshold):
 if operator not in ('gte','gt','lte','lt','eq'):raise LedgerError('Unsupported watch operator')
 target=decimal_value(threshold,'threshold')
 if observed is None or observed=='unknown':return {'result':'unknown','triggered':None,'reason':'No observation was supplied; no threshold conclusion'}
 value=decimal_value(observed,'observed');hit={'gte':value>=target,'gt':value>target,'lte':value<=target,'lt':value<target,'eq':value==target}[operator]
 return {'result':'triggered' if hit else 'not_triggered','triggered':hit,'observed':str(value),'threshold':str(target),'boundary':'Comparison of supplied values only; no measurement or monitor ran.'}

def next_recheck(anchor,half_life_days):
 if not isinstance(anchor,date) or isinstance(anchor,datetime) or type(half_life_days) is not int or not 1<=half_life_days<=365000:raise LedgerError('Review interval must be an integer1..365000 days and a calendar date')
 try:return anchor+timedelta(days=half_life_days)
 except OverflowError as e:raise LedgerError('Review date exceeds calendar range') from e

def parse_date(value,field,errors):
 try:return day(value,field,unknown=True)
 except LedgerError as e:errors.append(str(e));return None

def qualify(candidate):
 if not isinstance(candidate,dict):return ['Candidate must be an object']
 schema=load(ROOT/'schemas/reality-ledger.schema.json');errors=_shape(candidate,schema['$defs']['candidate'],schema)
 if errors:return errors
 for name in ('event_date','publication_date','effective_date','threshold_date'):parse_date(candidate[name],name,errors)
 if candidate['classification']=='rejected_noise' or candidate['status']=='rejected_noise':errors.append('Rejected noise is retained but not qualified for adoption')
 if not candidate['answer_change'].strip():errors.append('Exact changed answer surface is required')
 if not candidate['source_ids']:errors.append('At least one supporting source is required')
 return errors

def validate(data,previous=None,now=None):
 errors=[];now=now or datetime.now(timezone.utc)
 try:
  check(data);dumps(data)
  if not isinstance(data,dict):return ['Native document must be a JSON object.']
  fmt=data.get('format')
  if fmt not in (FORMAT,LEGACY):return ['Unsupported ledger format']
  schema=load(unlinked(ROOT/'schemas'/('reality-ledger.schema.json' if fmt==FORMAT else 'reality-ledger-v1.schema.json')))
  if fmt==LEGACY:schema['additionalProperties']=True # Historical extensions are preserved by the accepted inspector.
  errors=_shape(data,schema,schema)
  if errors:return errors
  if fmt==LEGACY:
   # Original schema is retained for historical readability. No current approval operation uses v1.
   if previous is not None:errors.append('Previous comparison requires migrated v2 records')
   return errors
  if not isinstance(now,datetime) or now.tzinfo is None:return ['now must be timezone-aware']
  for key in ('created_at','updated_at'):
   if data[key]!='unknown' and moment(data[key],key)>now:errors.append(key+': future record time')
  if data['created_at']!='unknown' and data['updated_at']!='unknown' and moment(data['updated_at'],'updated_at')<moment(data['created_at'],'created_at'):errors.append('updated_at precedes created_at')
  seen=set();by={}
  for collection in LISTS:
   by[collection]={}
   for x in data[collection]:
    if x['id'] in seen:errors.append('Duplicate ID: '+x['id'])
    seen.add(x['id']);by[collection][x['id']]=x
  versions=[];known_bases={}
  for b in baselines(data):
   versions.append(b['version']);known_bases[baseline_hash(data,b)]=b
   parse_date(b['as_of'],'baseline.as_of',errors)
   for key in ('approved_at',):
    if b[key] is not None and moment(b[key],'baseline.'+key)>now:errors.append('Baseline approval time is future')
   if b['authority']=='human_approved' and (not b['approved_by'] or not b['approved_by'].strip() or not b['approved_at']):errors.append('Asserted baseline approval needs actor/date; it does not authenticate consent')
   for ident in b['adopted_patch_ids']:
    if ident not in by['patches']:errors.append('Baseline names missing adopted patch '+ident)
  if len(set(versions))!=len(versions) or versions!=sorted(versions):errors.append('Baseline versions must be distinct and ordered')
  if data['baseline']['context']!={k:data[k] for k in ('scope','decision_use','owner')}:errors.append('Current baseline context differs from ledger decision context')
  if any(b!=a+1 for a,b in zip(versions,versions[1:])):errors.append('Retained baseline history has a version gap')
  if data['baseline_history'] and data['baseline']['supersedes']!=data['baseline_history'][-1]['version']:errors.append('Current baseline supersedes must name the immediately retained prior baseline')
  for collection in LISTS:
   for x in data[collection]:
    for ref in x.get('source_ids',[]):
     if not isinstance(ref,str) or ref not in by['sources']:errors.append(x['id']+': unknown source '+str(ref))
    if 'candidate_id' in x and x['candidate_id'] not in by['candidates']:errors.append(x['id']+': unknown candidate '+str(x['candidate_id']))
  for source in data['sources']:
   parse_date(source['publication_date'],source['id']+'.publication_date',errors)
   if source['accessed_at'] is not None and moment(source['accessed_at'],source['id']+'.accessed_at')>now:errors.append(source['id']+': source inspection time is future')
   if source['origin_id'] is not None and source['origin_id'] not in by['sources']:errors.append(source['id']+': unknown originating source')
  for source in data['sources']:
   chain=set();cursor=source
   while cursor is not None:
    if cursor['id'] in chain:errors.append(source['id']+': originating-source lineage contains a cycle');break
    chain.add(cursor['id']);cursor=by['sources'].get(cursor['origin_id'])
  for candidate in data['candidates']:
   for key in ('event_date','publication_date','effective_date','threshold_date'):parse_date(candidate[key],candidate['id']+'.'+key,errors)
   if candidate['status']=='accepted_delta':errors += [candidate['id']+': '+e for e in qualify(candidate)]
  for item in data['deltas']:
   if item['candidate_id'] in by['candidates'] and item['status']=='accepted_delta' and by['candidates'][item['candidate_id']]['status']!='accepted_delta':errors.append(item['id']+': delta candidate is not accepted')
  for p in data['patches']:
   parse_date(p['result_as_of'],p['id']+'.result_as_of',errors)
   if set(p['source_hashes'])!=set(p['source_ids']):errors.append(p['id']+': source bindings must cover exactly the referenced IDs')
   for ident,sha in p['source_hashes'].items():
    if ident in by['sources'] and sha!=identity({k:v for k,v in by['sources'][ident].items() if k!='status'}):errors.append(p['id']+': source content binding differs '+ident)
   if p['base_sha256'] not in known_bases:errors.append(p['id']+': starting baseline identity absent')
   elif p['base_version']!=known_bases[p['base_sha256']]['version']:errors.append(p['id']+': starting baseline version mismatch')
   elif p['status']=='patched' and known_bases[p['base_sha256']]['text'].count(p['before'])!=1:errors.append(p['id']+': adopted before text must match one unambiguous starting span')
   for i in p['candidate_ids']:
    if i not in by['candidates']:errors.append(p['id']+': unknown candidate '+i)
   if p['approved_at'] is not None and moment(p['approved_at'],p['id']+'.approved_at')>now:errors.append(p['id']+': asserted approval time is future')
   if p['authority']=='human_approved' and (not p['approved_by'] or not p['approved_by'].strip() or not p['approved_at']):errors.append(p['id']+': asserted approval needs actor/date')
  for b in baselines(data):
   if b['adopted_patch_ids']:
    prior=next((x for x in baselines(data) if x['version']==b['supersedes']),None)
    if prior is None:errors.append('Adopted baseline needs its retained predecessor');continue
    reconstructed=prior['text']
    for patch_id in b['adopted_patch_ids']:
     p=by['patches'].get(patch_id)
     if p is None:continue
     if p['base_sha256']!=baseline_hash(data,prior) or reconstructed.count(p['before'])!=1:errors.append(patch_id+': adopted chain is not bound to the retained predecessor');continue
     reconstructed=reconstructed.replace(p['before'],p['after'],1)
    if reconstructed!=b['text']:errors.append('Adopted baseline does not equal its exact patch replay')
  last_decision_time=None
  for approval in data['approvals']:
   if approval['object_id'] not in by['patches']:errors.append(approval['id']+': approval names missing patch')
   if approval['base_sha256'] not in known_bases:errors.append(approval['id']+': approval baseline absent')
   at=moment(approval['at'],approval['id']+'.at')
   if last_decision_time is not None and at<last_decision_time:errors.append('Approval dates must follow append chronology')
   last_decision_time=at
   if at>now:errors.append(approval['id']+': decision time is future')
   if approval['expires_at'] is not None and moment(approval['expires_at'],approval['id']+'.expires_at')<=at:errors.append(approval['id']+': expiry must follow decision')
  for watch in data['watch']:
   calculated=watch_result(watch['observed'],watch['operator'],watch['threshold'])
   if watch['status'] not in ('retired','superseded') and watch['triggered'] is not calculated['triggered']:errors.append(watch['id']+': recorded triggered differs from supplied values/missingness')
  publication=data['publication']
  if publication['approved_at'] is not None and moment(publication['approved_at'],'publication.approved_at')>now:errors.append('Publication approval time is future')
  if publication['status'] in ('approved','published') and any(not isinstance(publication[k],str) or not publication[k].strip() for k in ('approved_by','approved_at','scope')):errors.append('Publication assertion requires actor/date/scope; no publication executed by checker')
  if previous is not None:
   prior_errors=validate(previous,now=now)
   if prior_errors:errors+=['Invalid prior checkpoint: '+e for e in prior_errors]
   elif previous['format']!=FORMAT or previous['ledger_id']!=data['ledger_id']:errors.append('Prior checkpoint must be v2 for this ledger')
   else:
    if data!=previous and data['revision']<=previous['revision']:errors.append('Changed checkpoint requires greater revision')
    if data['revision']<previous['revision']:errors.append('Revision regressed')
    if data['created_at']!=previous['created_at']:errors.append('Creation time is immutable across checkpoints')
    if data['updated_at']!='unknown' and previous['updated_at']!='unknown' and moment(data['updated_at'],'updated_at')<moment(previous['updated_at'],'prior.updated_at'):errors.append('Checkpoint update time regressed')
    if data['approvals'][:len(previous['approvals'])]!=previous['approvals']:errors.append('Approval history must remain an ordered immutable prefix')
    if data['baseline_history'][:len(previous['baseline_history'])]!=previous['baseline_history']:errors.append('Baseline history must remain an immutable prefix')
    changed=baseline_hash(data)!=baseline_hash(previous)
    if changed and (data['baseline']['version']!=previous['baseline']['version']+1 or data['baseline_history']!=previous['baseline_history']+[previous['baseline']]):errors.append('Changed baseline requires next version and exact prior baseline appended to history')
    if not changed and data['baseline_history']!=previous['baseline_history']:errors.append('Cannot rewrite baseline history without a new baseline')
    approved={x['object_id'] for x in previous['approvals']}
    for collection in LISTS:
     current=by[collection]
     for old in previous[collection]:
      if old['id'] not in current:errors.append(collection+': prior ID removed '+old['id']);continue
      new=current[old['id']]
      if collection=='sources' and {k:v for k,v in old.items() if k!='status'}!={k:v for k,v in new.items() if k!='status'}:errors.append(old['id']+': source identity changed; append a new ID')
      if collection=='patches' and old['id'] in approved and patch_hash(old)!=patch_hash(new):errors.append(old['id']+': decided patch content changed; append a new ID')
 except (ValueError,TypeError,KeyError,OSError,OverflowError,RecursionError) as e:errors.append('Invalid ledger: '+str(e))
 return errors

def approval_basis(data,ident):
 errors=validate(data)
 if errors:raise LedgerError('; '.join(errors))
 if data['format']!=FORMAT:raise LedgerError('Migrate v1 before approval binding')
 patch=next((p for p in data['patches'] if p['id']==ident),None)
 if patch is None:raise LedgerError('Patch not found')
 return {'object_id':ident,'base_sha256':patch['base_sha256'],'patch_sha256':patch_hash(patch),'boundary':'Content identity only. This calculation is not consent, approval or adoption.'}

def current_approval(data,patch,now=None):
 now=now or datetime.now(timezone.utc)
 errors=validate(data,now=now)
 if errors:return None,'Invalid ledger: '+'; '.join(errors)
 if data['format']!=FORMAT:return None,'Legacy approval has no current content binding'
 if not isinstance(patch,dict) or not any(p==patch for p in data['patches']):return None,'Patch does not match the validated ledger'
 decisions=[x for x in data['approvals'] if x['object_id']==patch['id']]
 if not decisions:return None,'No recorded decision for exact patch'
 last=decisions[-1]
 if last['action']!='approve':return None,'Latest decision withdraws approval'
 if last['base_sha256']!=patch['base_sha256'] or last['patch_sha256']!=patch_hash(patch):return None,'Approval content/baseline binding differs'
 if moment(last['at'],'approval.at')>now:return None,'Approval time is future'
 if last['expires_at'] is not None and moment(last['expires_at'],'approval.expires_at')<=now:return None,'Approval expired'
 if last['scope'] not in ('patch-adoption','local-brief'):return None,'Approval scope does not cover this local operation'
 return last,None

def eligible_patch(data,patch,adopt=False,now=None):
 errors=validate(data,now=now)
 if errors:return None,'Invalid ledger: '+'; '.join(errors)
 if data['format']!=FORMAT:return None,'Legacy record needs preserving migration and current binding'
 if not isinstance(patch,dict) or not any(p==patch for p in data['patches']):return None,'Patch does not match the validated ledger'
 if patch['before']==patch['after']:return None,'No textual change; retain the answer and record the confidence or watch decision separately'
 if patch['status'] in ('retired','superseded','rejected_noise','fuzz_unresolved'):return None,'Patch is not eligible in current status'
 now=now or datetime.now(timezone.utc)
 cutoff=day(patch['result_as_of'],'patch.result_as_of',unknown=True)
 base_date=day(data['baseline']['as_of'],'baseline.as_of',unknown=True)
 if cutoff is None or base_date is None:return None,'Known current and resulting answer cutoffs are required'
 if cutoff>now.date():return None,'Resulting cutoff is future'
 if patch['status']!='patched' and cutoff<base_date:return None,'Resulting cutoff regresses'
 current=baseline_hash(data)
 if patch['base_sha256']!=current:
  if adopt or patch['status']!='patched' or patch['id'] not in data['baseline']['adopted_patch_ids'] or patch['after'] not in data['baseline']['text']:return None,'Patch is stale against the current baseline'
 elif patch['status']=='patched':return None,'Recorded adopted patch still names unchanged baseline'
 else:
  if data['baseline']['text'].count(patch['before'])!=1:return None,'Before text does not identify one current starting span'
 if not patch['source_ids']:return None,'Source support absent'
 sources={x['id']:x for x in data['sources']}
 for ident in patch['source_ids']:
  source=sources[ident]
  published=day(source['publication_date'],ident+'.publication_date',unknown=True)
  if published is None or published>cutoff:return None,ident+': source publication is unknown or later than resulting cutoff'
  if source['status'] in ('retired','superseded','rejected_noise') or source['access_status'] not in ('inspected','supplied','synthetic_fixture') or source['accessed_at'] is None or not source['supports']:return None,ident+': current inspected source support absent'
 if not any(link['relation']=='supports' for ident in patch['source_ids'] for link in sources[ident]['supports']):return None,'No source-to-claim support mapping supplied'
 approval,error=current_approval(data,patch,now)
 if error:return None,error
 if adopt and approval['scope']!='patch-adoption':return None,'Local-brief scope does not authorize adoption'
 return approval,None

def adopt(data,ident,now=None):
 now=now or datetime.now(timezone.utc);errors=validate(data,now=now)
 if errors:raise LedgerError('; '.join(errors))
 if data['format']!=FORMAT:raise LedgerError('Migrate legacy record before adoption')
 p=next((p for p in data['patches'] if p['id']==ident),None)
 if p is None:raise LedgerError('Patch not found')
 approval,error=eligible_patch(data,p,True,now)
 if error:raise LedgerError(error)
 if not p['source_ids']:raise LedgerError('Patch needs source support before adoption')
 sources={x['id']:x for x in data['sources']}
 for source_id in p['source_ids']:
  source=sources[source_id]
  if source['access_status'] not in ('inspected','supplied','synthetic_fixture') or source['accessed_at'] is None or not source['supports']:raise LedgerError(source_id+': inspect and map actual source support before adoption')
 if not any(link['relation']=='supports' for ident in p['source_ids'] for link in sources[ident]['supports']):raise LedgerError('No source-to-claim support mapping supplied')
 out=copy.deepcopy(data);prior=copy.deepcopy(out['baseline']);out['baseline_history'].append(prior);b=out['baseline'];b.update(version=prior['version']+1,supersedes=prior['version'],as_of=p['result_as_of'],text=prior['text'].replace(p['before'],p['after'],1),status='patched',authority='human_approved',approved_by=approval['actor'],approved_at=approval['at'],adopted_patch_ids=[ident]);out['revision']+=1;out['updated_at']=now.astimezone(timezone.utc).isoformat(timespec='seconds');new=next(x for x in out['patches'] if x['id']==ident);new.update(status='patched',authority='human_approved',approved_by=approval['actor'],approved_at=approval['at']);errors=validate(out,data,now)
 if errors:raise LedgerError('; '.join(errors))
 return out


def migrate(data,source_bytes,source_name):
 if not isinstance(source_bytes,bytes):raise LedgerError("Migration needs original bytes for a truthful source identity")
 errors=validate(data)
 if errors:raise LedgerError('; '.join(errors))
 if data['format']!=LEGACY:raise LedgerError('Migration requires a v1 source; existing v2 records use preserving checkpoints')
 out=copy.deepcopy(data);out.update(format=FORMAT,product_version=VERSION,revision=1,baseline_history=[])
 out['migration']={'source_format':LEGACY,'source_name':source_name,'source_sha256':hashlib.sha256(source_bytes).hexdigest(),'prior_history':'Not reconstructed; original v1 file retained. Supply earlier checkpoints separately if available.','legacy_approvals':copy.deepcopy(data['approvals']),'historical_patch_states':[],'boundary':'Migration preserves assertions and creates no current approval, source inspection, adoption or publication.'}
 out['baseline']['adopted_patch_ids']=[];out['baseline']['context']={k:out[k] for k in ('scope','decision_use','owner')};out['approvals']=[]
 for source in out['sources']:
  for key,value in {'title':'Unknown imported source title','locator':'unknown','publication_date':'unknown','authority':'unknown','accessed_at':None,'access_status':'not_examined','origin_id':None,'supports':[]}.items():source.setdefault(key,value)
 sources={s['id']:s for s in out['sources']};base_sha=baseline_hash(out)
 for p in out['patches']:
  out['migration']['historical_patch_states'].append({k:p.get(k) for k in ('id','status','authority','approved_by','approved_at')})
  p.update(base_version=out['baseline']['version'],base_sha256=base_sha,source_hashes={ident:identity({k:v for k,v in sources[ident].items() if k!='status'}) for ident in p['source_ids'] if ident in sources},authority='model_generated',approved_by=None,approved_at=None)
  p.setdefault('result_as_of','unknown');p.setdefault('scope','Scope not supplied in v1; inspect before adoption');p.setdefault('recheck','Review before adoption');p.setdefault('candidate_ids',[])
  if p['status']=='patched':p['status']='superseded' # Historical adoption assertion is retained separately, not adopted again.
 errors=validate(out)
 if errors:raise LedgerError('Migration needs explicit source repair on a copy: '+'; '.join(errors))
 return out

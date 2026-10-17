"""Beryl's locally retained observations and prepared investigations. No case editor."""
import argparse,base64,copy,datetime,hashlib,json,os,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'scripts'))
from validate_case_file import validate_data,consistency_issues
from storage_io import atomic,atomic_bytes,lock
PRODUCT='beryl-repair-companion';VERSION='0.6.0';BUILD='beryl-repair-companion-0.6.0-114f98999ada';STORE='bench.json';MAX_SOURCE=12*1024*1024
TEXT={'.txt','.log','.csv','.md','.json','.xml','.yaml','.yml'}
IMAGES={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}
def reject_constant(value):raise ValueError('Non-finite values are not supported; preserve the original for recovery.')
def read_json(raw):return json.loads(raw,parse_constant=reject_constant)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def fingerprint(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def checked_home(value):
 home=Path(value).resolve()
 def identity(path):
  value=str(Path(path).resolve())
  prefix=chr(92)*2+'?'+chr(92)
  if value.upper().startswith(prefix+'UNC'+chr(92)):value=chr(92)*2+value[8:]
  elif value.startswith(prefix):value=value[4:]
  return Path(value)
 if identity(home).is_relative_to(identity(ROOT.parents[2])):raise ValueError('Choose a saved-material folder outside the installed Beryl skill.')
 return home

def load(home):
 p=checked_home(home)/STORE
 if not p.exists():return {'schema':1,'product':PRODUCT,'investigations':[],'sources':[],'samples':[],'view':{},'legacy':[]}
 try:
  data=read_json(p.read_text('utf-8'))
  if data.get('product')!=PRODUCT or any(not isinstance(data.get(k),list) for k in ['investigations','sources','samples','legacy']) or not isinstance(data.get('view'),dict):raise ValueError()
  return data
 except (OSError,ValueError,AttributeError):raise ValueError('Saved Beryl material could not be opened. Keep '+str(p)+' and originals. Ask Beryl to recover it, or choose another --data-home folder. Nothing has been replaced.')

def source(home,name,raw,origin='selected file'):
 if not raw or len(raw)>(40*1024*1024 if origin=='known prior Beryl workspace' else MAX_SOURCE):raise ValueError('Choose a nonempty file smaller than 12 MB.')
 name=Path(name.replace('\\','/')).name
 if not name or name in ['.','..']:raise ValueError('Choose a named file.')
 sid=sha(raw);suffix=Path(name).suffix.lower();text=None
 if suffix in TEXT:
  try:text=raw.decode('utf-8-sig')
  except UnicodeError:
   try:text=raw.decode('utf-16') if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else None
   except UnicodeError:pass
 note='Original retained; no interpretation has been prepared.'
 if text is None and suffix not in IMAGES:note='Original retained. This format has no text preview; give the exact original to Beryl in the local host.'
 if text is not None and len(text)>200000:note='Original retained; preview is the first 200,000 characters. The assistant must inspect the original for omitted content.'
 target=home/'originals'/sid
 if target.exists() and sha(target.read_bytes())!=sid:raise ValueError('A retained original has changed. Keep the folder for recovery; no existing source was replaced.')
 if not target.exists():atomic_bytes(target,raw)
 return {'id':sid,'name':name,'bytes':len(raw),'added_at':now(),'origin':origin,'text':text[:200000] if text is not None else None,'note':note,'image_type':IMAGES.get(suffix)}

def append_source(data,s):
 if not any(x['id']==s['id'] for x in data['sources']):data['sources'].append(s)

def revision(record,source_ids,provenance,presentation=None,review=None):
 validate_data(record)
 return {'id':uuid.uuid4().hex,'record':copy.deepcopy(record),'fingerprint':fingerprint(record),'received_at':now(),'source_ids':source_ids,'provenance':provenance,'presentation':presentation or {},'review':review,'consistency':consistency_issues(record)}

def import_bytes(home,name,raw):
 home=checked_home(home)
 with lock(home/'.data.lock'):
  data=load(home);s=source(home,name,raw);append_source(data,s);inv=None
  if Path(name).suffix.lower()=='.json':
   try:value=read_json(raw)
   except (ValueError,UnicodeError):value=None
   if isinstance(value,dict) and 'case_id' in value:
    validate_data(value)
    existing=next((a for a in data['investigations'] if a['revisions'][-1]['fingerprint']==fingerprint(value)),None)
    if existing:inv=existing
    else:
     inv={'id':uuid.uuid4().hex,'revisions':[revision(value,[s['id']],'Selected native case; statements are imported, not authenticated observations')]};data['investigations'].append(inv)
   elif isinstance(value,dict) and value.get('app')=='beryl-it-benchcraft':
    inv=import_legacy(data,home,value,s)
  atomic(home/STORE,data)
 return {'source':s['id'],'investigation':inv['id'] if inv else None}

def import_legacy(data,home,value,original):
 if not isinstance(value.get('projects'),list):raise ValueError('This old workspace has no readable projects list. Its original remains retained.')
 if original['id'] in data['legacy']:return None
 staged=[];attachments=[]
 for project in value['projects']:
  record=project.get('record');validate_data(record);ids=[original['id']]
  for m in project.get('materials',[]):
   encoded=m.get('data','')
   if not isinstance(encoded,str) or ';base64,' not in encoded:raise ValueError('An old attachment is malformed. Preserve work.json for recovery.')
   raw=base64.b64decode(encoded.split(';base64,',1)[1],validate=True);s=source(home,m.get('name','attachment'),raw,'old work.json attachment');attachments.append(s);ids.append(s['id'])
  staged.append({'id':uuid.uuid4().hex,'legacy_project_id':project.get('id'),'revisions':[revision(record,ids,'Retained old workspace; original work.json and all extension fields preserved')]})
 for s in attachments:append_source(data,s)
 data['investigations'].extend(staged);data['legacy'].append(original['id'])
 return staged[-1] if staged else None

def initialize(home):
 home=checked_home(home);home.mkdir(parents=True,exist_ok=True)
 with lock(home/'.data.lock'):
  data=load(home);old=home/'work.json'
  if old.is_file():
   raw=old.read_bytes();sid=sha(raw)
   if sid not in data['legacy']:
    try:
     value=read_json(raw);s=source(home,'work.json',raw,'known prior Beryl workspace');append_source(data,s);import_legacy(data,home,value,s)
    except (ValueError,TypeError,KeyError) as e:data['legacy_notice']='The previous work.json could not be adopted: '+str(e)+'. The old file was not changed. Ask Beryl to inspect it.'
  atomic(home/STORE,data)

def examples():
 result=[]
 for folder in ['intermittent-wifi','no-power-laptop','suspected-compromise']:
  p=ROOT.parent/'examples'/folder/'case.json';r=read_json(p.read_text('utf-8'))
  result.append({'id':'example-'+folder,'example':True,'revisions':[{'id':'fictional','record':r,'fingerprint':fingerprint(r),'received_at':r['updated_at'],'source_ids':[],'provenance':'Fictional demonstration. No action or measurement was performed by this package.','presentation':{},'review':None,'consistency':consistency_issues(r)}]})
 return result

def public_state(home):
 data=load(home);data['examples']=examples();return data

def valid_presentation(p,record):
 if not isinstance(p,dict) or set(p)-{'unresolved_question','layers','hypotheses'}:raise ValueError('Presentation allows only unresolved_question, layers and hypotheses.')
 if 'unresolved_question' in p and not isinstance(p['unresolved_question'],str):raise ValueError('The unresolved question must be text.')
 evidence={x['id'] for x in record['evidence']};hypotheses={x['id'] for x in record['hypotheses']};tests={x['id'] for x in record['tests']}
 for layer in p.get('layers',[]):
  if not isinstance(layer,dict) or set(layer)-{'name','evidence_ids'} or not isinstance(layer.get('name'),str) or not isinstance(layer.get('evidence_ids'),list) or not set(layer['evidence_ids'])<=evidence:raise ValueError('A layer must cite actual evidence IDs. Unmapped evidence remains under Other observations.')
 for item in p.get('hypotheses',[]):
  if not isinstance(item,dict) or set(item)-{'id','supports','contradicts','tests'} or item.get('id') not in hypotheses:raise ValueError('A displayed hypothesis must be present in the native case.')
  for key,allowed in [('supports',evidence),('contradicts',evidence),('tests',tests)]:
   if not isinstance(item.get(key,[]),list) or not set(item.get(key,[]))<=allowed:raise ValueError('Hypothesis links must cite actual evidence or tests.')
 return p

def publish(home,packet,investigation=None,expected=None):
 home=checked_home(home)
 if not isinstance(packet,dict) or packet.get('schema')!='beryl-investigation/v1' or set(packet)-{'schema','record','source_ids','presentation','review'}:raise ValueError('Use the documented beryl-investigation/v1 publication.')
 record=packet.get('record');validate_data(record);pres=valid_presentation(packet.get('presentation',{}),record)
 with lock(home/'.data.lock'):
  data=load(home);available={s['id']:s for s in data['sources']};ids=packet.get('source_ids')
  if not isinstance(ids,list) or not ids or not all(isinstance(s,str) and s in available for s in ids):raise ValueError('Bind this investigation to actual selected source IDs; inspect them first.')
  for sid in ids:
   p=home/'originals'/sid
   if not p.is_file() or sha(p.read_bytes())!=sid:raise ValueError('A bound original is missing or changed; recover it before publishing.')
  for ev in record['evidence']:
   if 'source_id' in ev:
    sid=ev['source_id']
    if sid not in ids:raise ValueError('Evidence refers to an unbound source.')
    if 'quote' in ev:
     q=ev['quote'];text=available[sid].get('text')
     if not isinstance(q,str) or not q.strip() or text is None or ' '.join(q.split()) not in ' '.join(text.split()):raise ValueError('A quoted passage does not occur in the retained source preview. Use an exact visible quote or an explicitly described image observation.')
  review=packet.get('review')
  if review:
   if not isinstance(review,dict) or review.get('record_sha256')!=fingerprint(record) or review.get('kind') not in ['independent','self-check','imported'] or not all(isinstance(review.get(k),str) and review[k].strip() for k in ['author','verdict','text']):raise ValueError('A review needs exact native record SHA256, kind, author, verdict and text. Its stated authorship is not authenticated.')
  inv=next((a for a in data['investigations'] if a['id']==investigation),None)
  if investigation and not inv:raise ValueError('The selected investigation is unavailable.')
  if inv and record['case_id']!=inv['revisions'][-1]['record']['case_id']:raise ValueError('A revision must keep its native case identity. Publish a separate investigation for another case.')
  if inv and (expected!=inv['revisions'][-1]['fingerprint']):raise ValueError('The investigation changed. Inspect its latest revision before publishing; no history was replaced.')
  if not inv:inv={'id':uuid.uuid4().hex,'revisions':[]};data['investigations'].append(inv)
  inv['revisions'].append(revision(record,ids,'Prepared by the local assistant; case assertions are not independent measurement proof',pres,review));atomic(home/STORE,data)
 return {'investigation':inv['id'],'revision':inv['revisions'][-1]['id'],'fingerprint':inv['revisions'][-1]['fingerprint']}

def main():
 p=argparse.ArgumentParser(description='Beryl local assistant bridge: inspect selected originals, then publish a source-bound native investigation.')
 p.add_argument('--data-home',type=Path,required=True);sub=p.add_subparsers(dest='action',required=True)
 sub.add_parser('inspect');i=sub.add_parser('ingest');i.add_argument('file',type=Path)
 q=sub.add_parser('publish');q.add_argument('packet',type=Path);q.add_argument('--investigation');q.add_argument('--expected')
 a=p.parse_args();home=checked_home(a.data_home)
 if not home.is_dir():raise ValueError('The saved-material folder is unavailable. Reconnect it before continuing.')
 initialize(home)
 if a.action=='inspect':
  data=load(home)
  for s in data['sources']:s['original_path']=str(home/'originals'/s['id'])
  result=data
 elif a.action=='ingest':result=import_bytes(home,a.file.name,a.file.read_bytes())
 else:result=publish(home,read_json(a.packet.read_text('utf-8-sig')),a.investigation,a.expected)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

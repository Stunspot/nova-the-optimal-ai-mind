"""Repackage a same-version ordinary-entry repair from accepted native ZIPs."""
from pathlib import Path
import hashlib,json,io,os,zipfile,copy,unicodedata,argparse
W=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--plan',type=Path,default=W/'plans.json')
parser.add_argument('--baseline',type=Path,default=W/'shelf-baseline.json')
parser.add_argument('--skill',type=Path,default=Path('E:/Github/privacy-redline/release-v0.2.0/maintainer-source/privacy-redline-v0.2.0/skills/privacy-redline'))
parser.add_argument('--output',type=Path,default=Path('E:/NovaBuild/20261110/Privacy-Redline-entry-repair/packages'))
parser.add_argument('--verdict',type=Path,default=W/'interaction-verdict.json')
args=parser.parse_args();OUT=args.output.resolve();S=args.skill.resolve()
OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def data(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def fsha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def files(p):return {f.relative_to(p).as_posix():f.read_bytes() for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc','.pyo')}
def safe(names):
 seen=set()
 for n in names:
  key=unicodedata.normalize('NFC',n).casefold()
  if key in seen or n.startswith(('/','\\')) or '\\' in n or any(x in ('','..','.') for x in n.split('/')):raise ValueError('Unsafe/duplicate member: '+n)
  seen.add(key)
def write(z,n,b,info=None):
 i=copy.copy(info) if info else zipfile.ZipInfo(n,(2026,11,10,0,0,0))
 i.filename=n;i.orig_filename=n
 if not info:i.create_system=3;i.external_attr=0o100644<<16
 z.writestr(i,b,compress_type=zipfile.ZIP_STORED if n.endswith('.zip') else zipfile.ZIP_DEFLATED)
def repair_inner(b,payload):
 buff=io.BytesIO()
 with zipfile.ZipFile(io.BytesIO(b)) as src,zipfile.ZipFile(buff,'w') as dst:
  names=[i.filename for i in src.infolist() if not i.is_dir()];safe(names)
  for i in src.infolist():
   if i.is_dir():continue
   rel=i.filename.removeprefix('privacy-redline/')
   v=payload.get(rel,src.read(i));write(dst,i.filename,v,i)
 return buff.getvalue()
plans=read(args.plan);rows=read(args.baseline)['rows'];payload=files(S)
for plan in plans:
 if not Path(plan['root']).is_absolute():plan['root']=str((args.plan.parent/plan['root']).resolve())
 for key in ['overlays','baseline_archives']:
  for host,value in plan[key].items():
   if not Path(value).is_absolute():plan[key][host]=str((args.plan.parent/value).resolve())
assert read(args.verdict)['decision'] in ('PASS','READY_WITH_RESIDUAL_RISK')
result=[]
for plan in plans:
 ed=plan['edition'];version=plan['version'];root=Path(plan['root']);row=next(x for x in rows if x['id']==('nova-emergent' if ed=='E' else 'nova-mind'))
 rec={**plan,'archives':{},'deltas':{}}
 for host in ['codex','claude']:
  source=Path(plan['baseline_archives'][host]);expected=next(x['sha256'] for x in row['additional_files'] if x.get('role')=='host-archive' and x.get('host')==host)
  assert fsha(source)==expected,'Baseline changed'
  prefix='' if ed=='E' else f'nova-the-optimal-ai-free-{version}-{host}/'+('plugins/nova-the-optimal-ai/' if host=='codex' else 'nova-the-optimal-ai/')
  wrap='' if ed=='E' else f'nova-the-optimal-ai-free-{version}-{host}/'
  replacements={prefix+n:b for n,b in files(Path(plan['overlays'][host])).items()}
  target=OUT/source.name;temporary=target.with_suffix('.zip.writing')
  assert not target.exists() and not temporary.exists(),'Output already exists'
  changes=[];hashes={};unchanged=0
  with zipfile.ZipFile(source) as src,zipfile.ZipFile(temporary,'x') as dst:
   infos=[i for i in src.infolist() if not i.is_dir()];names=[i.filename for i in infos];safe(names);assert set(replacements)<=set(names)
   for info in infos:
    n=info.filename;old=src.read(info);b=replacements.get(n,old)
    if n=='SHA256SUMS.txt' and ed=='E':continue
    if ed=='F' and host=='claude' and n.startswith(wrap+'folders/privacy-redline/'):
     rel=n[len(wrap+'folders/privacy-redline/'):];b=payload.get(rel,old)
    if ed=='F' and host=='claude' and n==wrap+'zips/privacy-redline-'+version+'.zip':b=repair_inner(old,payload)
    if ed=='F' and n==wrap+'BUILD-MANIFEST.json':
     d=json.loads(old);d.update(build_id=plan['build_id'],source_map_sha256=fsha(root/'design/source-map.json'),source_lock_sha256=fsha(root/'design/source-lock.json'))
     d['interaction_repair']={'kind':'edit','effect':'restored_behavior','baseline_archive_sha256':expected,'component':'privacy-redline','runtime_files':len(payload),'scope':'Exact ordinary-entry repair; other owner payloads preserved.'};b=data(d)
    write(dst,n,b,info);hashes[n]=sha(b)
    if b!=old:changes.append(n)
    else:unchanged+=1
   if ed=='E':write(dst,'SHA256SUMS.txt',''.join(v+'  '+k+'\n' for k,v in sorted(hashes.items())).encode())
  os.replace(temporary,target);digest=fsha(target);target.with_suffix('.zip.sha256').write_bytes((digest+'  '+target.name+'\n').encode())
  rec['archives'][host]={'path':str(target),'sha256':digest,'bytes':target.stat().st_size,'baseline_sha256':expected}
  rec['deltas'][host]={'changed':changes,'unchanged_members':unchanged,'member_hashes':hashes}
  print(ed,host,'complete;',len(changes),'changed members,',unchanged,'unchanged',flush=True)
 outer_source=Path(row['source_path']);assert fsha(outer_source)==row['sha256']
 outer=OUT/outer_source.name;temp=outer.with_suffix('.zip.writing');assert not outer.exists()
 guide_name='INSTALL NOVA EMERGENT.md' if ed=='E' else 'INSTALL.md'
 with zipfile.ZipFile(outer_source) as src:guide=src.read(guide_name)
 checks={guide_name:sha(guide)}
 with zipfile.ZipFile(temp,'x',compression=zipfile.ZIP_STORED) as dst:
  for v in rec['archives'].values():
   p=Path(v['path']);dst.write(p,p.name);checks[p.name]=v['sha256']
  write(dst,guide_name,guide);write(dst,'SHA256SUMS.txt',''.join(v+'  '+k+'\n' for k,v in sorted(checks.items())).encode())
 os.replace(temp,outer);digest=fsha(outer);outer.with_suffix('.zip.sha256').write_bytes((digest+'  '+outer.name+'\n').encode())
 rec['customer']={'path':str(outer),'sha256':digest,'bytes':outer.stat().st_size,'baseline_sha256':row['sha256']};result.append(rec)
 (W/'archive-results.json').write_bytes(data(result));print(ed,'customer archive complete',flush=True)

"""Compose the Privacy Redline component update from hash-pinned accepted native archives."""
from pathlib import Path
import hashlib,io,json,os,zipfile,copy,re,unicodedata,argparse
W=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--plan',type=Path,default=W/'parent-plans.json')
parser.add_argument('--baseline-manifest',type=Path,default=W/'shelf-baseline.json')
parser.add_argument('--skill',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True)
S=args.skill.resolve()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def js(b):return json.loads(b.decode('utf-8-sig'))
def data(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def files(p):return {f.relative_to(p).as_posix():f.read_bytes() for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc','.pyo')}
def check(names):
 keys=set()
 for n in names:
  key=unicodedata.normalize('NFC',n).casefold()
  if key in keys or n.startswith(('/','\\')) or '\\' in n or any(x in ('','..','.') for x in n.split('/')):raise ValueError('Unsafe/colliding ZIP name: '+n)
  if len(n.encode('utf-16-le'))//2>259 or any(len(x.encode('utf-8'))>255 for x in n.split('/')):raise ValueError('Nonportable ZIP name: '+n)
  keys.add(key)
def write_member(z,name,raw,original=None):
 info=copy.copy(original) if original else zipfile.ZipInfo(name,(2026,11,10,0,0,0))
 info.filename=name;info.orig_filename=name
 if not original:info.create_system=3;info.external_attr=0o100644<<16
 info.compress_type=zipfile.ZIP_STORED if name.endswith('.zip') else zipfile.ZIP_DEFLATED
 z.writestr(info,raw)
payload=files(S)
# Accepted complete shelf baselines are the authority, not inferred filenames.
shelf=js(args.baseline_manifest.read_bytes())
catalog={r['id']:r for r in shelf['rows']}
plans=js(args.plan.read_bytes())
for plan in plans:
 for key in ['root']:
  if not Path(plan[key]).is_absolute():plan[key]=str((args.plan.parent/plan[key]).resolve())
 for key in ['overlays','baseline_archives']:
  for label,value in plan[key].items():
   if not Path(value).is_absolute():plan[key][label]=str((args.plan.parent/value).resolve())
results=[]
for plan in plans:
 ed=plan['edition'];old=plan['old'];new=plan['version'];root=Path(plan['root'])
 baseline=catalog['nova-emergent' if ed=='E' else 'nova-mind']
 if baseline['version']!=old:raise ValueError('Shelf baseline advanced; reconcile before construction')
 output_archives={}
 deltas={}
 for host in ['codex','claude']:
  source=Path(plan['baseline_archives'][host])
  expected=next(r['sha256'] for r in baseline['additional_files'] if r['host']==host and r['role']=='host-archive')
  if sha(source)!=expected:raise ValueError('Native baseline hash differs')
  newname=f'Nova Emergent v{new} {host.title()}.zip' if ed=='E' else f'nova-the-optimal-ai-free-{new}-{host}.zip'
  target=OUT/newname
  if target.exists():raise ValueError('Output already exists; inspect before retry')
  overlays=files(Path(plan['overlays'][host]))
  pluginprefix='' if ed=='E' else f'nova-the-optimal-ai-free-{new}-{host}/'+('plugins/nova-the-optimal-ai/' if host=='codex' else 'nova-the-optimal-ai/')
  oldwrap='' if ed=='E' else f'nova-the-optimal-ai-free-{old}-{host}/'
  newwrap='' if ed=='E' else f'nova-the-optimal-ai-free-{new}-{host}/'
  desired={pluginprefix+n:b for n,b in overlays.items()}
  if ed=='F' and host=='claude':
   desired.update({newwrap+'folders/privacy-redline/'+n:b for n,b in payload.items()})
  touched=[];added=[];unchanged=0;hashes={};written=set()
  with zipfile.ZipFile(source) as src,zipfile.ZipFile(target.with_suffix('.zip.writing'),'x') as dst:
   oldnames=[i.filename for i in src.infolist() if not i.is_dir()]
   newnames=[n.replace(oldwrap,newwrap,1) if oldwrap else n for n in oldnames]
   if ed=='F':newnames=[re.sub(r'(/zips/[^/]+)-'+re.escape(old)+r'\.zip$',r'\1-'+new+'.zip',n) for n in newnames]
   check(set(newnames)|set(desired)|({'SHA256SUMS.txt'} if ed=='E' else set()))
   for info,n in zip([i for i in src.infolist() if not i.is_dir()],newnames):
    oldraw=src.read(info);raw=desired.get(n,oldraw)
    if n=='SHA256SUMS.txt':continue
    if ed=='F':
     if n==newwrap+'BUILD-MANIFEST.json':
      d=js(raw);d.update(product_version=new,build_id=plan['build_id'],source_clean=False,candidate_state='component_update_from_accepted_archives',source_map_sha256=sha(root/'design/source-map.json'),source_lock_sha256=sha(root/'design/source-lock.json'))
      d['source_baseline_commit']=d.pop('source_base_commit',None)
      d['component_update']={'component':'privacy-redline','version':'0.2.0','baseline_archive_sha256':expected,'source_scope':'Exact accepted other-owner payloads; updated native identities and detached rights-envelope version.'}
      raw=data(d)
     elif '/nova-free-rights/README.md' in n:
      raw=raw.replace(('Free '+old).encode(),('Free '+new).encode())
     elif '/zips/' in n and n.endswith('.zip'):
      buff=io.BytesIO()
      with zipfile.ZipFile(io.BytesIO(oldraw)) as inner,zipfile.ZipFile(buff,'w') as inz:
       innernames=[x.filename for x in inner.infolist() if not x.is_dir()]
       is_privacy=n.endswith('/privacy-redline-'+new+'.zip')
       extra={('privacy-redline/'+k):v for k,v in payload.items()} if is_privacy else {}
       check(set(innernames)|set(extra));seen=set()
       for ii in inner.infolist():
        if ii.is_dir():continue
        value=extra.get(ii.filename,inner.read(ii))
        if '/nova-free-rights/README.md' in ii.filename:value=value.replace(('Free '+old).encode(),('Free '+new).encode())
        write_member(inz,ii.filename,value,ii);seen.add(ii.filename)
       for k in sorted(set(extra)-seen):write_member(inz,k,extra[k])
      raw=buff.getvalue()
    if raw!=oldraw:touched.append(n)
    else:unchanged+=1
    write_member(dst,n,raw,info);written.add(n);hashes[n]=digest(raw)
   for n in sorted(set(desired)-written):
    raw=desired[n];write_member(dst,n,raw);hashes[n]=digest(raw);added.append(n)
   if ed=='E':
    manifest=(''.join(h+'  '+n+'\n' for n,h in sorted(hashes.items()))).encode()
    write_member(dst,'SHA256SUMS.txt',manifest)
  os.replace(target.with_suffix('.zip.writing'),target)
  target.with_suffix('.zip.sha256').write_text(sha(target)+'  '+target.name+'\n',encoding='utf-8')
  output_archives[host]={'path':str(target),'sha256':sha(target),'bytes':target.stat().st_size,'baseline_sha256':expected}
  deltas[host]={'changed':touched,'added':added,'unchanged_members':unchanged,'member_hashes':hashes}
  print(ed,host,'built',len(hashes),'members;',unchanged,'unchanged',flush=True)
 # Wrap the two complete native downloads, preserving the accepted customer topology.
 oldouter=Path(baseline['source_path'])
 if sha(oldouter)!=baseline['sha256']:raise ValueError('Customer baseline hash differs')
 outer=OUT/(f'Nova Emergent v{new}.zip' if ed=='E' else f'nova-the-optimal-ai-free-{new}.zip')
 if outer.exists():raise ValueError('Customer output already exists')
 guide_name='INSTALL NOVA EMERGENT.md' if ed=='E' else 'INSTALL.md'
 with zipfile.ZipFile(oldouter) as z:guide=z.read(guide_name).decode('utf-8-sig').replace(old,new).encode()
 if ed=='E':guide=guide.replace(b'2.0.2',new.encode())
 checks={guide_name:digest(guide)}
 with zipfile.ZipFile(outer.with_suffix('.zip.writing'),'x',compression=zipfile.ZIP_STORED) as z:
  for host,value in output_archives.items():
   p=Path(value['path']);z.write(p,p.name);checks[p.name]=value['sha256']
  write_member(z,guide_name,guide)
  write_member(z,'SHA256SUMS.txt',''.join(h+'  '+n+'\n' for n,h in sorted(checks.items())).encode())
 os.replace(outer.with_suffix('.zip.writing'),outer)
 outer.with_suffix('.zip.sha256').write_text(sha(outer)+'  '+outer.name+'\n',encoding='utf-8')
 record={**plan,'archives':output_archives,'customer':{'path':str(outer),'sha256':sha(outer),'bytes':outer.stat().st_size},'deltas':deltas,'claim_boundary':'Construction record. Independent artifact acceptance, installation and publication remain separate.'}
 (W/(ed+'-archive-composition.json')).write_bytes(data(record));results.append(record)
 print(ed,'customer archive built',flush=True)
(W/'parent-archive-results.json').write_bytes(data(results))


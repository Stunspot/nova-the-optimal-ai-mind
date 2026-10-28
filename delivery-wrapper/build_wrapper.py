#!/usr/bin/env python3
"""Build the minimal four-entry Nova Free download from accepted native ZIPs.

Example: python build_wrapper.py --build-result path/to/free-build-result.json
         --output path/to/nova-the-optimal-ai-free-4.3.1.zip

The input result must bind codex_zip/claude_zip to their SHA-256 values. This
helper creates no new native payload and refuses to replace an existing output.
"""
from pathlib import Path
import argparse,hashlib,io,json,re,shutil,zipfile

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def build(result_path,note,output):
    result=json.loads(result_path.read_text(encoding='utf-8-sig'))
    native=[Path(result[host+'_zip']) for host in ('codex','claude')]
    expected=[result[host+'_zip_sha256'] for host in ('codex','claude')]
    match=re.fullmatch(r'nova-the-optimal-ai-free-(\d+\.\d+\.\d+)-codex\.zip',native[0].name)
    if not match or native[1].name!='nova-the-optimal-ai-free-'+match[1]+'-claude.zip':raise ValueError('Native filenames must identify the same Free version')
    if output.exists():raise FileExistsError('Output already exists; inspect it before choosing another destination')
    if not all(digest(p)==h for p,h in zip(native,expected)):raise ValueError('Native archive differs from accepted build result')
    note_bytes=note.read_bytes();note_sha=hashlib.sha256(note_bytes).hexdigest()
    if any(p.name.encode() not in note_bytes for p in native):raise ValueError('Install note does not identify both native archives')
    sums=''.join(h+'  '+p.name+'\n' for p,h in zip(native,expected)).encode('utf-8')
    members=[(p.name,p) for p in native]+[('INSTALL.md',note_bytes),('SHA256SUMS.txt',sums)]
    output.parent.mkdir(parents=True,exist_ok=True);temporary=output.with_name(output.name+'.partial')
    if temporary.exists():raise FileExistsError('Partial output exists; inspect before resuming')
    owns_temporary=False
    try:
        with zipfile.ZipFile(temporary,'x',zipfile.ZIP_STORED) as archive:
            owns_temporary=True
            for name,value in members:
                info=zipfile.ZipInfo(name,(2026,10,27,0,0,0));info.create_system=0;info.external_attr=0x20
                with (value.open('rb') if isinstance(value,Path) else io.BytesIO(value)) as source,archive.open(info,'w',force_zip64=True) as target:shutil.copyfileobj(source,target,1024*1024)
        with zipfile.ZipFile(temporary) as archive:
            if archive.namelist()!=[name for name,_ in members] or archive.testzip() is not None:raise ValueError('Wrapper inventory or CRC check failed')
            for (name,value),wanted in zip(members,expected+[note_sha,hashlib.sha256(sums).hexdigest()]):
                h=hashlib.sha256()
                with archive.open(name) as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
                if h.hexdigest()!=wanted:raise ValueError('Wrapper member digest differs: '+name)
        if not all(digest(p)==h for p,h in zip(native,expected)) or note.read_bytes()!=note_bytes:raise ValueError('Input changed during build')
        if output.exists():raise FileExistsError('Output appeared during build')
        temporary.rename(output)
    except BaseException:
        if owns_temporary and temporary.exists():temporary.unlink()
        raise
    return {'state':'PASS','zip':str(output.resolve()),'sha256':digest(output),'entries':[name for name,_ in members],'native_zip_bytes_unchanged':True,'note_sha256':note_sha}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build-result',type=Path,required=True);parser.add_argument('--install-note',type=Path,default=Path(__file__).with_name('INSTALL.md'));parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(build(args.build_result,args.install_note,args.output),indent=2))
if __name__=='__main__':main()

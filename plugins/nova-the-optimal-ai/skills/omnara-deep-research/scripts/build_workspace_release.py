"""Build a new deterministic complete Omnara candidate; preserve prior releases."""
import argparse,hashlib,json,shutil,tempfile,zipfile
from pathlib import Path
from custody import reject_links,namespace
from product_files import inventory
from validate_release import validate
ROOT=Path(__file__).parents[1]

def build(root,output):
    root=reject_links(root);output=reject_links(output)
    if output.exists():raise ValueError('output exists; select a new candidate directory')
    if output==root or output in root.parents or any((root/name)==output or (root/name) in output.parents for name in ('scripts','workspace','assets','examples','docs','references','personas','knowledge','schemas','fallbacks','agents')):raise ValueError('output overlaps product source')
    version=(root/'VERSION').read_text(encoding='utf-8').strip()
    import re
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('VERSION must be semantic triplet')
    files=inventory(root);members=[('omnara-deep-research/'+p.relative_to(root).as_posix(),False) for p in files]+[('omnara-deep-research/PACKAGE-CONTENTS.json',False)];namespace(members)
    errors,_,_=validate(root,'source')
    if errors:raise ValueError('source invalid: '+'; '.join(errors))
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.omnara-build-',dir=output.parent) as tmp:
        stage=Path(tmp);package=stage/'omnara-deep-research';package.mkdir()
        for p in files:
            target=package/p.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        manifest={'format':'omnara-package/v1','version':version,'files':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'scope':'Complete native skill and room; source history, private campaigns and tests excluded. Hash identity does not authenticate publisher or semantic quality.'}
        (package/'PACKAGE-CONTENTS.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
        errors,links,_=validate(package,'source')
        if errors:raise ValueError('staged package invalid: '+'; '.join(errors))
        final=stage/'candidate';final.mkdir();archive=final/f'OMNARA Deep Research v{version}.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in sorted(package.rglob('*')):
                if not p.is_file():continue
                name='omnara-deep-research/'+p.relative_to(package).as_posix();info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.create_system=3;info.external_attr=(0o100755 if p.name=='Open.command' else 0o100644)<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes(),compresslevel=9)
        digest=hashlib.sha256(archive.read_bytes()).hexdigest();(final/(archive.name+'.sha256')).write_text(digest+'  '+archive.name+'\n',encoding='utf-8',newline='\n')
        receipt={'product':'omnara-deep-research','version':version,'archive':archive.name,'sha256':digest,'files':len(files)+1,'local_links':links,'runtime_entry':'omnara-deep-research/Open.cmd','source_inventory':manifest['files'],'state':'new deterministic source candidate; independent review, central delivery and live host activation require separate evidence'};(final/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n');final.rename(output)
    return output/archive.name

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    try:archive=build(args.root,args.output);print(str(archive));print(hashlib.sha256(archive.read_bytes()).hexdigest());return 0
    except (OSError,ValueError,TypeError) as exc:print('ERROR build: '+str(exc));return 1
if __name__=='__main__':raise SystemExit(main())

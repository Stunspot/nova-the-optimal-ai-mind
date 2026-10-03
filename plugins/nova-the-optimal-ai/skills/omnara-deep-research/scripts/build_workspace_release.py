"""Build the complete one-root OMNARA customer candidate without host or test state."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    version=(ROOT/'VERSION').read_text().strip();out=ROOT/'release-candidates';out.mkdir(exist_ok=True)
    target=out/f'OMNARA Deep Research v{version}.zip'
    excludes={'.git','.github','verification','tests','release-candidates','__pycache__','dist','release'}
    files=[p for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink() and not set(p.relative_to(ROOT).parts)&excludes and p.suffix not in {'.pyc','.tmp'}]
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            info=zipfile.ZipInfo('omnara-deep-research/'+p.relative_to(ROOT).as_posix());info.external_attr=(0o755 if p.name=='Open.command' else 0o644)<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
    sha=hashlib.sha256(target.read_bytes()).hexdigest()
    (target.with_suffix('.sha256')).write_text(sha+'  '+target.name+'\n')
    receipt={'product':'OMNARA Deep Research','version':version,'baseline':'1.1.0','treatment':'edit','reason':'Restores the accepted campaign-room promise through artifact-first research and readable source notes','zip':target.name,'sha256':sha,'files':len(files),'runtime_entry':'omnara-deep-research/Open.cmd','macos_entry':'omnara-deep-research/Open.command','state':'local repair candidate; desktop visual/native loop accepted; narrow review unavailable; not externally published','data_custody':'owner-selected native campaign home outside package'}
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()

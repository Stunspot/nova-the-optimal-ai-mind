"""Build the complete one-root OMNARA customer candidate without host or test state."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    version=(ROOT/'VERSION').read_text().strip();out=ROOT/'release-candidates';out.mkdir(exist_ok=True)
    target=out/f'OMNARA Deep Research v{version}.zip'
    excludes={'.git','.github','verification','tests','release-candidates','__pycache__','dist','release','delivery-sidecars'}
    files=[p for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink() and not set(p.relative_to(ROOT).parts)&excludes and p.suffix not in {'.pyc','.tmp'}]
    files.append(ROOT/'verification'/'documentation-review.md')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            info=zipfile.ZipInfo('omnara-deep-research/'+p.relative_to(ROOT).as_posix());info.external_attr=(0o755 if p.name=='Open.command' else 0o644)<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
    sha=hashlib.sha256(target.read_bytes()).hexdigest()
    (target.with_suffix('.sha256')).write_text(sha+'  '+target.name+'\n')
    receipt={'product':'OMNARA Deep Research','version':version,'baseline':'1.3.0','treatment':'edit','reason':'Repairs the three Explorer skins with distinct materials and consistent coverage across the existing campaign room','zip':target.name,'sha256':sha,'files':len(files),'runtime_entry':'omnara-deep-research/Open.cmd','macos_entry':'omnara-deep-research/Open.command','state':'built from current source; local browser and native checks recorded under verification/skin-review-2026-09-30; no fresh-host or public-announcement claim','data_custody':'owner-selected native campaign home outside package'}
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()


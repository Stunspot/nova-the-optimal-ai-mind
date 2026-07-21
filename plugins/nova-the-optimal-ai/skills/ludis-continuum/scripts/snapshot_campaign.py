from __future__ import annotations
import argparse,hashlib,json,zipfile
from datetime import datetime,timezone
from pathlib import Path
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("campaign",type=Path);p.add_argument("--output",type=Path);a=p.parse_args();root=a.campaign.resolve()
    if not (root/"campaign-ledger.json").is_file(): print("FAIL: campaign-ledger.json missing");return 2
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ");out=(a.output or root/"checkpoints"/f"ludis-{stamp}.zip").resolve();out.parent.mkdir(parents=True,exist_ok=True)
    files=[x for x in sorted(root.rglob("*")) if x.is_file() and x.resolve()!=out and not (x.suffix.lower()==".zip" and "checkpoints" in x.relative_to(root).parts)]
    manifest=[{"path":x.relative_to(root).as_posix(),"sha256":hashlib.sha256(x.read_bytes()).hexdigest()} for x in files]
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for x in files:z.write(x,x.relative_to(root).as_posix())
        z.writestr("snapshot-manifest.json",json.dumps({"files":manifest},indent=2))
    print(f"PASS: {out}");print("SHA256: "+hashlib.sha256(out.read_bytes()).hexdigest().upper());return 0
if __name__=="__main__": raise SystemExit(main())

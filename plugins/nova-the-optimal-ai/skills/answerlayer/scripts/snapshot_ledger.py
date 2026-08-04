from __future__ import annotations
import argparse,hashlib,zipfile
from datetime import datetime
from pathlib import Path
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("workspace");p.add_argument("output");a=p.parse_args();src=Path(a.workspace).resolve();out=Path(a.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
 if src==out or src in out.parents:print("REFUSED: output must be outside workspace");return 2
 if out.exists():print(f"REFUSED: {out} already exists");return 2
 with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
  for x in sorted(src.rglob("*")):
   if x.is_file() and "snapshots" not in x.parts and "__pycache__" not in x.parts:z.write(x,x.relative_to(src).as_posix())
 print(f"WROTE: {out}");print("SHA256:",hashlib.sha256(out.read_bytes()).hexdigest().upper());return 0
if __name__=="__main__":raise SystemExit(main())

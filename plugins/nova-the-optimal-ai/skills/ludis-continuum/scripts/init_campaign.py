from __future__ import annotations
import argparse,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("destination",type=Path);a=p.parse_args();d=a.destination.resolve()
    if d.exists() and any(d.iterdir()): print(f"FAIL: destination is not empty: {d}");return 2
    d.mkdir(parents=True,exist_ok=True);shutil.copytree(ROOT/"assets"/"campaign.template",d,dirs_exist_ok=True);print(f"PASS: initialized {d}");return 0
if __name__=="__main__": raise SystemExit(main())

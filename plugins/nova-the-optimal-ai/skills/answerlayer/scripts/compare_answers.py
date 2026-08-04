from __future__ import annotations
import argparse,difflib
from pathlib import Path
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("before");p.add_argument("after");a=p.parse_args();b=Path(a.before).read_text(encoding="utf-8").splitlines();n=Path(a.after).read_text(encoding="utf-8").splitlines();print("\n".join(difflib.unified_diff(b,n,fromfile="baseline",tofile="proposed",lineterm="")));return 0
if __name__=="__main__":raise SystemExit(main())

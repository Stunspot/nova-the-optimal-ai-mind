from __future__ import annotations
import argparse
from pathlib import Path
from ledgerlib import load,validate
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("ledger");a=p.parse_args();e=validate(load(Path(a.ledger)))
 for x in e:print("ERROR:",x)
 print("PASS: Reality Ledger is structurally valid" if not e else f"FAIL: {len(e)} error(s)");return 1 if e else 0
if __name__=="__main__":raise SystemExit(main())

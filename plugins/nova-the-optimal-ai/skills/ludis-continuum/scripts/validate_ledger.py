from __future__ import annotations
import argparse
from pathlib import Path
from ledgerlib import load,validate
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("ledger",type=Path);a=p.parse_args()
    try: errors=validate(load(a.ledger))
    except (OSError,ValueError) as e: print(f"FAIL: {e}");return 2
    for e in errors: print(f"ERROR: {e}")
    print("PASS: campaign ledger valid" if not errors else f"FAIL: {len(errors)} error(s)");return 1 if errors else 0
if __name__=="__main__": raise SystemExit(main())

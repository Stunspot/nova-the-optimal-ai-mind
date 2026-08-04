from __future__ import annotations
import argparse
from datetime import date
from ledgerlib import next_recheck
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("anchor");p.add_argument("half_life_days",type=int);a=p.parse_args();print(next_recheck(date.fromisoformat(a.anchor),a.half_life_days).isoformat());return 0
if __name__=="__main__":raise SystemExit(main())

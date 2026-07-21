from __future__ import annotations
import argparse,json,random
from pathlib import Path
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("table",type=Path);p.add_argument("--seed",required=True);p.add_argument("--count",type=int,default=1);a=p.parse_args()
    values=json.loads(a.table.read_text(encoding="utf-8"))
    if not isinstance(values,list) or not values or a.count<1: print("FAIL: table must be a non-empty array and count positive");return 2
    rng=random.Random(a.seed);print(json.dumps({"seed":a.seed,"results":[rng.choice(values) for _ in range(a.count)]},ensure_ascii=False));return 0
if __name__=="__main__": raise SystemExit(main())

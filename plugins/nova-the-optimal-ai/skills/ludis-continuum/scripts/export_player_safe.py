from __future__ import annotations
import argparse,json
from pathlib import Path
from ledgerlib import load,validate
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("ledger",type=Path);p.add_argument("output",type=Path);a=p.parse_args();data=load(a.ledger);errors=validate(data)
    if errors: print("FAIL: ledger invalid; export denied");return 1
    objects=[o for o in data["objects"] if o.get("visibility")=="player_safe" and o.get("player_export_approved") is True]
    out={"campaign":{"title":data.get("campaign",{}).get("title")},"objects":objects}
    a.output.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");print(f"PASS: exported {len(objects)} object(s)");return 0
if __name__=="__main__": raise SystemExit(main())

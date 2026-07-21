from __future__ import annotations
import argparse
from datetime import datetime,timezone
from pathlib import Path
from ledgerlib import load,save,validate
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("ledger",type=Path);p.add_argument("object_id");p.add_argument("--gm-approved",action="store_true");a=p.parse_args();data=load(a.ledger)
    matches=[o for o in data.get("objects",[]) if o.get("id")==a.object_id]
    if len(matches)!=1 or not a.gm_approved: print("FAIL: exact object and --gm-approved required");return 2
    obj=matches[0]
    if obj.get("status") not in {"proposed","disputed"}: print("FAIL: only proposed or disputed objects may be promoted");return 2
    conflicts=[o for o in data["objects"] if o.get("id")!=obj.get("id") and o.get("status")=="active_canon" and set(o.get("claims",[])) & set(obj.get("contradicts",[]))]
    if conflicts: print("FAIL: unresolved active-canon contradiction");return 2
    obj["status"]="active_canon";obj["authority"]="gm_approved";data["approvals"].append({"object_id":a.object_id,"action":"promote_canon","at":datetime.now(timezone.utc).isoformat()})
    errors=validate(data)
    if errors: print("FAIL: promotion would invalidate ledger");return 1
    save(a.ledger,data);print(f"PASS: promoted {a.object_id}");return 0
if __name__=="__main__": raise SystemExit(main())

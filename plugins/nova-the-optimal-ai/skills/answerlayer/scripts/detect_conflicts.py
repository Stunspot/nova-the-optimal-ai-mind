from __future__ import annotations
import argparse
from pathlib import Path
from ledgerlib import load
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("ledger");a=p.parse_args();d=load(Path(a.ledger));groups={}
 for c in d.get("candidates",[]):
  k=c.get("conflict_key")
  if k:groups.setdefault(k,[]).append(c.get("id"))
 conflicts={k:v for k,v in groups.items() if len(v)>1}
 for k,v in sorted(conflicts.items()):print(f"CONFLICT_GROUP: {k}: {', '.join(v)}")
 unresolved=[c.get("id") for c in d.get("candidates",[]) if c.get("status")=="fuzz_unresolved"]
 for ident in unresolved:print(f"FUZZ_UNRESOLVED: {ident}")
 print(f"conflict_groups {len(conflicts)}");print(f"fuzz_unresolved {len(unresolved)}");return 0
if __name__=="__main__":raise SystemExit(main())

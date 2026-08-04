from __future__ import annotations
import argparse
from pathlib import Path
from ledgerlib import load
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("ledger");p.add_argument("output");a=p.parse_args();d=load(Path(a.ledger));approved=[x for x in d.get("patches",[]) if x.get("authority")=="human_approved" and x.get("approved_by") and x.get("approved_at")]
 if not approved:print("REFUSED: no human-approved patch");return 2
 lines=[f"# {d['title']} — approved reality patch",f"\nBaseline cutoff: {d['baseline']['as_of']}",f"Ledger: {d['ledger_id']}"]
 for x in approved:lines.extend([f"\n## {x['id']}",f"\n**Before:** {x['before']}",f"\n**After:** {x['after']}",f"\n**Mechanism:** {x['mechanism']}",f"\n**Counterfactual:** {x['counterfactual']}",f"\nApproved by {x['approved_by']} on {x['approved_at']}."])
 Path(a.output).write_text("\n".join(lines)+"\n",encoding="utf-8");print(f"WROTE: {a.output}");return 0
if __name__=="__main__":raise SystemExit(main())

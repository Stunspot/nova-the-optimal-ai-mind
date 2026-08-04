from __future__ import annotations
import argparse, json, shutil
from datetime import date
from pathlib import Path

def main() -> int:
    p=argparse.ArgumentParser(description="Initialize an AnswerLayer Reality Ledger without overwriting state.")
    p.add_argument("destination");p.add_argument("--title",default="Untitled decision surface");p.add_argument("--owner",default="UNASSIGNED")
    a=p.parse_args();dest=Path(a.destination);dest.mkdir(parents=True,exist_ok=True);out=dest/"reality-ledger.json"
    if out.exists(): print(f"REFUSED: {out} already exists");return 2
    template=Path(__file__).resolve().parent.parent/"assets/reality-ledger.template/reality-ledger.json"
    data=json.loads(template.read_text(encoding="utf-8"));today=date.today().isoformat();data.update({"ledger_id":f"RL-{today.replace('-','')}-001","title":a.title,"owner":a.owner,"created_at":today,"updated_at":today});data["baseline"]["as_of"]=today
    out.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");print(f"CREATED: {out}");return 0
if __name__=="__main__":raise SystemExit(main())

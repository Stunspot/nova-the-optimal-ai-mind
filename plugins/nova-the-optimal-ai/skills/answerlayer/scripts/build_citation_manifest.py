from __future__ import annotations
import argparse,json
from pathlib import Path
from ledgerlib import digest,load
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("ledger");p.add_argument("output");a=p.parse_args();ledger=Path(a.ledger);d=load(ledger);m={"format":"answerlayer/citation-manifest/v1","ledger_sha256":digest(ledger),"sources":[{"id":x.get("id"),"title":x.get("title"),"locator":x.get("locator"),"publication_date":x.get("publication_date"),"authority":x.get("authority")} for x in d.get("sources",[])]};Path(a.output).write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");print(f"WROTE: {a.output}");return 0
if __name__=="__main__":raise SystemExit(main())

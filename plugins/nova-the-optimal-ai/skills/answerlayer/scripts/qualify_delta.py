from __future__ import annotations
import argparse,json
from pathlib import Path
from ledgerlib import qualify
def main()->int:
 p=argparse.ArgumentParser(description="Check the machine-testable fields of one candidate delta.");p.add_argument("candidate");a=p.parse_args();data=json.loads(Path(a.candidate).read_text(encoding="utf-8"));e=qualify(data)
 for x in e:print("ERROR:",x)
 print("PASS: candidate has required qualification fields" if not e else f"FAIL: {len(e)} error(s)");print("NOTE: field presence does not prove truth or answer-change.");return 1 if e else 0
if __name__=="__main__":raise SystemExit(main())

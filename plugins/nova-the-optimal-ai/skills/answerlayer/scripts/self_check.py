from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
REQUIRED=["SKILL.md","manifest.json","agents/openai.yaml","knowledge/operating-doctrine.md","knowledge/evidence-currentness.md","knowledge/state-and-authority.md","schemas/reality-ledger.schema.json","assets/reality-ledger.template/reality-ledger.json","evals/eval-manifest.yaml","evals/core-transfer-cases.yaml"]
def main()->int:
 e=[]
 for n in REQUIRED:
  if not (ROOT/n).is_file():e.append(f"missing {n}")
 for x in ROOT.rglob("*.json"):
  try:json.loads(x.read_text(encoding="utf-8"))
  except Exception as exc:e.append(f"invalid json {x.relative_to(ROOT)}: {exc}")
 skill=(ROOT/"SKILL.md").read_text(encoding="utf-8")
 if not skill.startswith("---\nname: answerlayer\n"):e.append("SKILL frontmatter")
 for x in e:print("ERROR:",x)
 print("PASS: AnswerLayer package self-check" if not e else f"FAIL: {len(e)} error(s)");return 1 if e else 0
if __name__=="__main__":raise SystemExit(main())

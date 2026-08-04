from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
REQUIRED=("SKILL.md","manifest.json","agents/openai.yaml","knowledge/operating-doctrine.md","knowledge/state-and-authority.md","knowledge/canonical-boundaries.md","knowledge/canonical/rpg-toolkit-v2.md","knowledge/canonical/rpg-toolkit-readme-v2.md","knowledge/canonical/rpg-game-design-key-ideas.md","assets/campaign.template/campaign-ledger.json","schemas/campaign-ledger.schema.json","scripts/init_campaign.py","scripts/validate_ledger.py","scripts/promote_object.py","scripts/roll_table.py","scripts/export_player_safe.py","scripts/snapshot_campaign.py","evals/eval-manifest.yaml")
def main()->int:
    errors=[f"missing: {x}" for x in REQUIRED if not (ROOT/x).is_file()]
    if not (ROOT/"SKILL.md").read_text(encoding="utf-8").startswith("---\n"):errors.append("frontmatter missing")
    if "$ludis-continuum" not in (ROOT/"agents/openai.yaml").read_text(encoding="utf-8"):errors.append("agent invocation missing")
    for x in (ROOT/"manifest.json",ROOT/"schemas/campaign-ledger.schema.json",ROOT/"assets/campaign.template/campaign-ledger.json"):
        try:json.loads(x.read_text(encoding="utf-8"))
        except Exception as e:errors.append(f"invalid JSON {x.name}: {e}")
    if any(x.is_symlink() for x in ROOT.rglob("*")):errors.append("symlink present")
    for e in errors:print("ERROR:",e)
    print("PASS: Ludis Continuum package self-check" if not errors else f"FAIL: {len(errors)} error(s)");return 1 if errors else 0
if __name__=="__main__":raise SystemExit(main())

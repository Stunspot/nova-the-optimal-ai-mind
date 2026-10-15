from __future__ import annotations
"""Bind current source selections, notices and rights; this is not a release seal."""
import argparse
import json
from pathlib import Path
from release_lib import tree_digest, sha256_file, write_json

RIGHTS=("LICENSE.md","ATTRIBUTION.md","NOTICE.md","TRADEMARKS.md","PROVENANCE.md","THIRD-PARTY-NOTICES.md")


def freeze(repo: Path, candidate: Path) -> dict:
    candidate=candidate.resolve()
    if candidate.parent!=(repo / "working").resolve() or (candidate / "INCOMPLETE").exists():
        raise ValueError("Expected complete source preparation under working")
    target=candidate / "design/source-lock.json"
    if target.exists():
        raise ValueError("Preserve existing source lock; use a successor for changed inputs")
    source_map=candidate / "design/source-map.json"
    mapping=json.loads(source_map.read_text(encoding="utf-8"))
    plugin=candidate / "codex/plugins/nova-the-optimal-ai"
    records=mapping["records"]
    roots=sorted(p.name for p in (plugin / "skills").iterdir() if p.is_dir())
    if sorted(x["id"] for x in records)!=roots or len(roots)!=28:
        raise ValueError("Current owner inventory mismatch")
    for record in records:
        if tree_digest(plugin / "skills" / record["id"])!=record["imported_tree"]:
            raise ValueError(f"Current selection changed: {record['id']}")
    for name in RIGHTS:
        if (candidate / name).read_bytes()!=(plugin / name).read_bytes():
            raise ValueError(f"Rights envelope differs: {name}")
    value={"schema":"nova-free-source-lock/v4","product":"Nova the Optimal AI Free","product_version":"4.0.0",
        "source_map_sha256":sha256_file(source_map),"records":records,
        "plugin_skill_tree":tree_digest(plugin / "skills"),
        "persona_sha256":sha256_file(plugin / "skills/nova/references/nova-persona.md"),
        "notices":{p.name:tree_digest(p) for p in sorted((plugin / "notices").iterdir()) if p.is_dir()},
        "rights_bundle":{"files":{n:sha256_file(candidate / n) for n in RIGHTS},
            "state":"public_split_license_applied","redistribution_state":"permitted_under_included_licenses",
            "external_rights_blockers":[]},
        "open_evidence_boundaries":["finished-candidate situated observations and TestForge review remain",
            "final package acceptance, installation and delivery remain","publication requires established owner authority"],
        "evidence_boundary":"Source byte identity only; no READY verdict, release seal or delivery claim."}
    write_json(target,value)
    return {"owners":len(roots),"runtime_files":value["plugin_skill_tree"]["file_count"],"candidate":str(candidate)}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate",required=True,type=Path)
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();print(json.dumps(freeze(args.repo.resolve(),args.candidate)))

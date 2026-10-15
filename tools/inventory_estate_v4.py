from __future__ import annotations
"""Record actual prepared owner selections while retaining baseline provenance as history."""
import argparse
import json
import re
from pathlib import Path
from release_lib import tree_digest, sha256_file, files, write_json


def public_history(original: dict) -> dict:
    out={k:original[k] for k in ["id","source_version","source_state","source_tree_sha256","source_file_count","source_archive_sha256"] if k in original}
    url=original.get("source_repository")
    if isinstance(url,str) and url.startswith("https://github.com/"):
        out["source_repository"]=url
    commit=original.get("source_commit")
    if isinstance(commit,str) and re.fullmatch("[0-9a-fA-F]{40}",commit):
        out["source_commit"]=commit
    out["scope"]="Historical baseline coordinates only; current included bytes are the explicit owner selection."
    return out


def inventory(repo: Path, candidate: Path) -> dict:
    candidate = candidate.resolve()
    if candidate.parent != (repo / "working").resolve() or (candidate / "INCOMPLETE").exists():
        raise ValueError("Expected a completed source preparation in this repository working directory")
    destination = candidate / "design/source-map.json"
    if destination.exists():
        raise ValueError("Selection inventory exists; preserve it and create a successor")
    baseline = json.loads((repo / "design/source-map.json").read_text(encoding="utf-8-sig"))
    historical = {r["id"]: r for r in baseline["records"]}
    composition = json.loads((repo / "working/estate-v4-d1/DEVELOPMENT.json").read_text(encoding="utf-8"))
    origins = {r["id"]: r for r in composition["owners"]}
    plugin = candidate / "codex/plugins/nova-the-optimal-ai"
    records = []
    for skill in sorted((plugin / "skills").iterdir()):
        if not skill.is_dir():
            raise ValueError("Unexpected owner root file")
        owner = skill.name
        if owner not in origins or owner not in historical:
            raise ValueError(f"Unmapped owner: {owner}")
        records.append({"id": owner, "source_state": "prepared_current_estate_owner_selection",
            "composition_origin": origins[owner]["origin"], "edition_overlays": origins[owner]["adapters"],
            "imported_path": "codex/plugins/nova-the-optimal-ai/skills/" + owner,
            "imported_tree": tree_digest(skill),
            "selection": [{"path": p.relative_to(skill).as_posix(), "sha256": sha256_file(p)} for p in files(skill)],
            "baseline_source_coordinates": public_history(historical[owner]),
            "qualification": "Current bytes inventoried; inherited baseline coordinates do not claim these bytes were committed or released."})
    value = {"schema": "nova-free-source-map/v4", "product": "Nova the Optimal AI Free", "product_version": "4.0.0",
        "records": records, "notices": baseline["notices"],
        "evidence_boundary": "Source selection and preserved lineage only; no readiness verdict, release seal or delivery proof."}
    write_json(destination, value)
    return {"owners": len(records), "files": sum(len(r["selection"]) for r in records), "candidate": str(candidate)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(inventory(args.repo.resolve(), args.candidate)))

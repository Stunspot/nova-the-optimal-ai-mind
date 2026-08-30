from __future__ import annotations

import json
from pathlib import Path

from release_lib import sha256_file, tree_digest, write_json


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    source_map_path = repo / "design" / "source-map.json"
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    plugin = repo / "plugins" / "nova-the-optimal-ai"
    roots = {path.name for path in (plugin / "skills").iterdir() if path.is_dir()}
    records = source_map.get("records", [])
    mapped = {record["id"] for record in records}
    if roots != mapped or len(roots) != 25:
        raise RuntimeError(f"Source-map mismatch: roots={len(roots)} mapped={len(mapped)}")
    locked = []
    for record in sorted(records, key=lambda value: value["id"]):
        imported = plugin / "skills" / record["id"]
        locked.append(
            {
                **record,
                "imported_path": imported.relative_to(repo).as_posix(),
                "imported_tree": tree_digest(imported),
                "overlay_state": "edition_overlay" if record.get("edition_overlays") else "exact_selected_source",
            }
        )
    notices = {}
    notice_root = plugin / "notices"
    for path in sorted(notice_root.iterdir(), key=lambda item: item.name):
        if path.is_dir():
            notices[path.name] = tree_digest(path)
    lock = {
        "schema": "nova-free-source-lock/v3",
        "product": source_map["product"],
        "product_version": source_map["product_version"],
        "source_map_sha256": sha256_file(source_map_path),
        "tree_algorithm": "sha256 over skill-relative UTF-8 POSIX path in ordinal exact-case order, one NUL byte, and raw 32-byte file sha256; Python caches excluded",
        "records": locked,
        "plugin_skill_tree": tree_digest(plugin / "skills"),
        "persona_sha256": sha256_file(plugin / "skills" / "nova" / "references" / "nova-persona.md"),
        "notices": notices,
        "release_blockers": [
            "nova-mind, nova-operations, answerlayer, and current-intelligence-observatory require explicit Free-edition grants",
            "job-application-builder and interview-trainer prohibit inclusion without separate written permission",
            "answerlayer and current-intelligence-observatory metadata require license reconciliation",
            "fresh-host discovery and invocation unobserved",
            "publication authority absent",
        ],
        "evidence_boundary": "Imported package bytes and recorded source identity. This lock does not establish remote publication state, fresh-host behavior, or license compatibility.",
    }
    write_json(repo / "design" / "source-lock.json", lock)
    print(json.dumps({"records": len(locked), "plugin_skill_tree": lock["plugin_skill_tree"], "persona_sha256": lock["persona_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

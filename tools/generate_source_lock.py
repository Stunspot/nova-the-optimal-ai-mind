from __future__ import annotations

import json
from pathlib import Path

from release_lib import sha256_file, tree_digest, write_json

RIGHTS_FILES = (
    "LICENSE.md",
    "ATTRIBUTION.md",
    "NOTICE.md",
    "TRADEMARKS.md",
    "PROVENANCE.md",
    "THIRD-PARTY-NOTICES.md",
)


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
    rights_files = {}
    for name in RIGHTS_FILES:
        root_path = repo / name
        plugin_path = plugin / name
        if not root_path.is_file() or not plugin_path.is_file():
            raise RuntimeError(f"Required rights file missing: {name}")
        root_hash = sha256_file(root_path)
        plugin_hash = sha256_file(plugin_path)
        if root_hash != plugin_hash:
            raise RuntimeError(f"Root/plugin rights file differs: {name}")
        rights_files[name] = root_hash
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
        "rights_bundle": {
            "files": rights_files,
            "state": "public_split_license_applied",
            "redistribution_state": "permitted_under_included_licenses",
            "external_rights_blockers": [],
        },
        "open_evidence_boundaries": [
            "fresh-host discovery and invocation require separate observation",
            "publication is a separate authorized and observed action",
        ],
        "evidence_boundary": "Imported package bytes, source identity, and product-rights bundle custody. This lock does not establish live-host behavior or external publication.",
    }
    write_json(repo / "design" / "source-lock.json", lock)
    print(
        json.dumps(
            {
                "records": len(locked),
                "plugin_skill_tree": lock["plugin_skill_tree"],
                "persona_sha256": lock["persona_sha256"],
                "rights_bundle": lock["rights_bundle"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_lib import (
    copy_tree,
    deterministic_zip,
    files,
    git_value,
    replace_directory,
    sha256_file,
    tree_digest,
    write_json,
    write_text,
)

PRODUCT_SLUG = "nova-the-optimal-ai-free"
PLUGIN_ID = "nova-the-optimal-ai"
REQUIRED_DOCS = (
    "README.md",
    "START-HERE.md",
    "LICENSE.md",
    "SECURITY.md",
    "SUPPORT.md",
    "THIRD-PARTY-NOTICES.md",
    "RELEASE-NOTES.md",
)
CURATED_DESIGN = (
    "FREE-NOVA-PACKAGE-MAP.md",
    "product-contract.json",
    "source-lock.json",
    "source-map.json",
)


def marketplace() -> dict[str, object]:
    return {
        "name": "collaborative-dynamics-nova-free",
        "interface": {"displayName": "Nova the Optimal AI Free by Collaborative Dynamics"},
        "plugins": [
            {
                "name": PLUGIN_ID,
                "source": {"source": "local", "path": f"./plugins/{PLUGIN_ID}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
        ],
    }


def build(repo: Path, output_parent: Path, artifact_parent: Path, require_clean: bool) -> dict[str, object]:
    plugin_source = repo / "plugins" / PLUGIN_ID
    plugin_manifest_path = plugin_source / ".codex-plugin" / "plugin.json"
    loadout_path = plugin_source / "LOADOUT-MANIFEST.json"
    if not plugin_manifest_path.is_file() or not loadout_path.is_file():
        raise RuntimeError("Nova Free source plugin is incomplete")
    plugin_manifest = json.loads(plugin_manifest_path.read_text(encoding="utf-8"))
    loadout = json.loads(loadout_path.read_text(encoding="utf-8"))
    source_lock = json.loads((repo / "design" / "source-lock.json").read_text(encoding="utf-8"))
    version = str(plugin_manifest["version"])
    if version != "3.0.0" or loadout.get("product_version") != version:
        raise RuntimeError("Version contract mismatch")
    roots = sorted(path.name for path in (plugin_source / "skills").iterdir() if path.is_dir())
    expected = sorted(loadout["roots"])
    if roots != expected or len(roots) != 25:
        raise RuntimeError(f"Loadout mismatch: source={len(roots)} manifest={len(expected)}")

    tracked_status = git_value(repo, "status", "--porcelain", "--untracked-files=no") or ""
    if require_clean and tracked_status:
        raise RuntimeError("Tracked source is not clean; refusing clean-checkpoint build")

    package_name = f"{PRODUCT_SLUG}-{version}"
    output_parent.mkdir(parents=True, exist_ok=True)
    artifact_parent.mkdir(parents=True, exist_ok=True)
    package_root = replace_directory(output_parent / package_name, output_parent)

    for name in REQUIRED_DOCS:
        source = repo / name
        if not source.is_file():
            raise RuntimeError(f"Required customer document missing: {name}")
        target = package_root / name
        target.write_bytes(source.read_bytes())

    docs_source = repo / "docs"
    if not docs_source.is_dir():
        raise RuntimeError("Curated customer documentation directory missing: docs")
    copy_tree(docs_source, package_root / "docs")
    for name in CURATED_DESIGN:
        source = repo / "design" / name
        if not source.is_file():
            raise RuntimeError(f"Required design/custody document missing: design/{name}")
        target = package_root / "design" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    codex_root = package_root / "codex"
    codex_plugin = codex_root / "plugins" / PLUGIN_ID
    copy_tree(plugin_source, codex_plugin, exclude_top={".claude-plugin"})
    write_json(codex_root / ".agents" / "plugins" / "marketplace.json", marketplace())

    claude_root = package_root / "claude"
    claude_plugin = claude_root / PLUGIN_ID
    copy_tree(plugin_source, claude_plugin, exclude_top={".codex-plugin"})
    folders_root = claude_root / "folders"
    zips_root = claude_root / "zips"
    skill_records: list[dict[str, object]] = []
    for skill_id in roots:
        source_skill = plugin_source / "skills" / skill_id
        folder = folders_root / skill_id
        copy_tree(source_skill, folder)
        zip_path = zips_root / f"{skill_id}-{version}.zip"
        zip_sha = deterministic_zip(folder, zip_path, prefix=skill_id)
        skill_records.append(
            {
                "id": skill_id,
                "tree": tree_digest(source_skill),
                "claude_zip": zip_path.relative_to(package_root).as_posix(),
                "claude_zip_sha256": zip_sha,
            }
        )

    base_commit = git_value(repo, "rev-parse", "HEAD")
    build_state = {
        "schema": "nova-free-build/v3",
        "product": "Nova the Optimal AI Free",
        "product_version": version,
        "source_base_commit": base_commit,
        "tracked_source_clean": not bool(tracked_status),
        "candidate_state": "built_awaiting_independent_review",
        "independent_review_required": True,
        "redistribution_state": "blocked_pending_component_grants",
        "skill_roots": roots,
        "evidence_boundary": "Package bytes and deterministic structure only; not fresh-host discovery, invocation, behavior, publication, or outcomes.",
    }
    write_json(codex_root / "BUILD-MANIFEST.json", {**build_state, "binding": "codex"})
    write_json(claude_root / "BUILD-MANIFEST.json", {**build_state, "binding": "claude-compatible"})

    codex_zip = artifact_parent / f"{package_name}-codex.zip"
    claude_zip = artifact_parent / f"{package_name}-claude.zip"
    codex_zip_sha = deterministic_zip(codex_root, codex_zip, prefix=f"{package_name}-codex")
    claude_zip_sha = deterministic_zip(claude_root, claude_zip, prefix=f"{package_name}-claude")
    write_text(codex_zip.with_suffix(codex_zip.suffix + ".sha256"), f"{codex_zip_sha}  {codex_zip.name}")
    write_text(claude_zip.with_suffix(claude_zip.suffix + ".sha256"), f"{claude_zip_sha}  {claude_zip.name}")

    release_manifest = {
        "schema": "nova-free-release-manifest/v3",
        "product": "Nova the Optimal AI Free",
        "brand": "Nova the Optimal AI",
        "product_version": version,
        "plugin_id": PLUGIN_ID,
        "topology": {
            "plugin_count": 1,
            "visible_skill_roots": 25,
            "mind_version": loadout["topology"]["mind_version"],
            "faculty_core_count": loadout["topology"]["faculty_core_count"],
        },
        "source": {
            "base_commit": base_commit,
            "tracked_source_clean": not bool(tracked_status),
            "source_lock": "design/source-lock.json",
        },
        "host_trees": {
            "codex_plugin": tree_digest(codex_plugin),
            "claude_plugin": tree_digest(claude_plugin),
            "codex_claude_skill_bytes_identical": all(
                (codex_plugin / "skills" / record["id"] / relative).read_bytes()
                == (claude_plugin / "skills" / record["id"] / relative).read_bytes()
                for record in skill_records
                for relative in [
                    path.relative_to(plugin_source / "skills" / str(record["id"]))
                    for path in files(plugin_source / "skills" / str(record["id"]))
                ]
            ),
        },
        "skills": skill_records,
        "host_artifacts": [
            {"binding": "codex", "file": codex_zip.name, "sha256": codex_zip_sha},
            {"binding": "claude-compatible", "file": claude_zip.name, "sha256": claude_zip_sha},
        ],
        "required_absences": loadout["required_absences"],
        "redistribution_state": "blocked_pending_component_grants",
        "release_blockers": source_lock["release_blockers"],
        "evidence_boundary": "This manifest establishes built bytes and internal parity. Installation, discovery, enabled state, restart state, invocation, service configuration, behavior, publication, and customer outcomes remain separate observations.",
    }
    write_json(package_root / "RELEASE-MANIFEST.json", release_manifest)

    checksum_rows = []
    for path in files(package_root):
        if path.name == "SHA256SUMS.txt":
            continue
        checksum_rows.append(f"{sha256_file(path)}  {path.relative_to(package_root).as_posix()}")
    write_text(package_root / "SHA256SUMS.txt", "\n".join(checksum_rows))

    customer_zip = artifact_parent / f"{package_name}.zip"
    customer_zip_sha = deterministic_zip(package_root, customer_zip, prefix=package_name)
    write_text(customer_zip.with_suffix(customer_zip.suffix + ".sha256"), f"{customer_zip_sha}  {customer_zip.name}")
    return {
        "schema": "nova-free-build-result/v3",
        "package_root": str(package_root),
        "customer_zip": str(customer_zip),
        "customer_zip_sha256": customer_zip_sha,
        "codex_zip": str(codex_zip),
        "codex_zip_sha256": codex_zip_sha,
        "claude_zip": str(claude_zip),
        "claude_zip_sha256": claude_zip_sha,
        "visible_skill_roots": len(roots),
        "tracked_source_clean": not bool(tracked_status),
        "candidate_state": "built_awaiting_independent_review",
        "independent_review_required": True,
        "redistribution_state": "blocked_pending_component_grants",
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Build deterministic Nova the Optimal AI Free host and customer packages.")
    result.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    result.add_argument("--output-parent", type=Path)
    result.add_argument("--artifact-parent", type=Path)
    result.add_argument("--require-clean", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    repo = args.repo.resolve()
    output_parent = (args.output_parent or repo / "dist").resolve()
    artifact_parent = (args.artifact_parent or repo / "release").resolve()
    try:
        value = build(repo, output_parent, artifact_parent, args.require_clean)
    except (OSError, ValueError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "nova-free-build-error/v3", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

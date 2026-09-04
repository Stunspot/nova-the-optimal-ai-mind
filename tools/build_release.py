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
RIGHTS_DOCS = (
    "LICENSE.md",
    "ATTRIBUTION.md",
    "NOTICE.md",
    "TRADEMARKS.md",
    "PROVENANCE.md",
    "THIRD-PARTY-NOTICES.md",
)
REQUIRED_DOCS = (
    "README.md",
    "START-HERE.md",
    *RIGHTS_DOCS,
    "SECURITY.md",
    "SUPPORT.md",
    "RELEASE-NOTES.md",
)
CURATED_DESIGN = (
    "FREE-NOVA-PACKAGE-MAP.md",
    "product-contract.json",
    "source-lock.json",
    "source-map.json",
)
STANDALONE_RIGHTS_DIR = "nova-free-rights"
COMPONENT_NOTICE_MAP = {
    "agent-swarm-orchestration": "agent-swarm-orchestration",
    "software-verification": "testforge",
    "verification-reviewer": "testforge",
    "job-application-builder": "job-application-builder",
    "interview-trainer": "interview-trainer",
}
REDISTRIBUTION_STATE = "permitted_under_included_licenses"


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


def attach_standalone_rights(repo: Path, plugin_source: Path, folder: Path, skill_id: str) -> str | None:
    rights_root = folder / STANDALONE_RIGHTS_DIR
    for name in RIGHTS_DOCS:
        source = repo / name
        target = rights_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    component_notice = COMPONENT_NOTICE_MAP.get(skill_id)
    if component_notice:
        copy_tree(plugin_source / "notices" / component_notice, rights_root / "component-notices" / component_notice)
    notice_text = (
        f"# Rights envelope for {skill_id}\n\n"
        f"This directory travels with the {skill_id} skill artifact supplied by Nova the Optimal AI Free 3.1.4. "
        "Preserve it when copying or redistributing the authentic, unmodified artifact.\n\n"
        "LICENSE.md defines the product-level public split license. ATTRIBUTION.md, NOTICE.md, "
        "TRADEMARKS.md, PROVENANCE.md, and THIRD-PARTY-NOTICES.md preserve identity, limits, and source custody."
    )
    if component_notice:
        notice_text += (
            f"\n\nThe component-specific packet under component-notices/{component_notice} also applies "
            "and must remain with this artifact."
        )
    write_text(rights_root / "README.md", notice_text)
    return component_notice


def validate_source_lock(repo: Path, plugin_source: Path, source_lock: dict[str, object]) -> list[str]:
    source_map = repo / "design" / "source-map.json"
    if not source_map.is_file() or sha256_file(source_map) != source_lock.get("source_map_sha256"):
        raise RuntimeError("Source map does not match the frozen source lock")

    roots = sorted(path.name for path in (plugin_source / "skills").iterdir() if path.is_dir())
    records = source_lock.get("records")
    if not isinstance(records, list):
        raise RuntimeError("Source lock records are missing or malformed")
    record_by_id: dict[str, dict[str, object]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise RuntimeError("Source lock contains a malformed skill record")
        skill_id = str(record["id"])
        if skill_id in record_by_id:
            raise RuntimeError(f"Source lock contains duplicate skill record: {skill_id}")
        record_by_id[skill_id] = record
    if set(record_by_id) != set(roots):
        raise RuntimeError("Source lock skill records do not match the live plugin roots")

    actual_skill_tree = tree_digest(plugin_source / "skills")
    if actual_skill_tree != source_lock.get("plugin_skill_tree"):
        raise RuntimeError("Live plugin skill tree does not match the frozen source lock")
    for skill_id in roots:
        actual = tree_digest(plugin_source / "skills" / skill_id)
        if actual != record_by_id[skill_id].get("imported_tree"):
            raise RuntimeError(f"Live skill tree does not match the frozen source lock: {skill_id}")

    persona = plugin_source / "skills" / "nova" / "references" / "nova-persona.md"
    if not persona.is_file() or sha256_file(persona) != source_lock.get("persona_sha256"):
        raise RuntimeError("Nova persona does not match the frozen source lock")

    notices = source_lock.get("notices")
    notice_root = plugin_source / "notices"
    if not isinstance(notices, dict):
        raise RuntimeError("Source lock notice records are missing or malformed")
    actual_notice_ids = {path.name for path in notice_root.iterdir() if path.is_dir()}
    if set(notices) != actual_notice_ids:
        raise RuntimeError("Source lock notice records do not match the live notice roots")
    for notice_id, expected in notices.items():
        if tree_digest(notice_root / notice_id) != expected:
            raise RuntimeError(f"Live notice tree does not match the frozen source lock: {notice_id}")

    rights = source_lock.get("rights_bundle")
    rights_files = rights.get("files") if isinstance(rights, dict) else None
    if not isinstance(rights_files, dict) or set(rights_files) != set(RIGHTS_DOCS):
        raise RuntimeError("Source lock rights-file records are missing or malformed")
    for name in RIGHTS_DOCS:
        root_file = repo / name
        plugin_file = plugin_source / name
        expected = rights_files[name]
        if (
            not root_file.is_file()
            or not plugin_file.is_file()
            or sha256_file(root_file) != expected
            or sha256_file(plugin_file) != expected
        ):
            raise RuntimeError(f"Rights file does not match the frozen source lock: {name}")
    return roots


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
    if version != "3.1.4" or loadout.get("product_version") != version:
        raise RuntimeError("Version contract mismatch")
    if loadout.get("license") != "LICENSE.md":
        raise RuntimeError("Loadout does not identify the Nova Free product license")
    rights_bundle = source_lock.get("rights_bundle", {})
    if rights_bundle.get("redistribution_state") != REDISTRIBUTION_STATE:
        raise RuntimeError("Source lock does not carry the approved public redistribution state")
    if rights_bundle.get("external_rights_blockers") != []:
        raise RuntimeError("Source lock still contains external rights blockers")
    roots = validate_source_lock(repo, plugin_source, source_lock)
    expected = sorted(loadout["roots"])
    if roots != expected or len(roots) != 27:
        raise RuntimeError(f"Loadout mismatch: source={len(roots)} manifest={len(expected)}")

    base_commit = git_value(repo, "rev-parse", "HEAD")
    source_status = git_value(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if base_commit is None or source_status is None:
        raise RuntimeError("Source repository identity or status could not be read")
    source_clean = not bool(source_status)
    if require_clean and not source_clean:
        raise RuntimeError("Source is not clean, including untracked files; refusing clean-checkpoint build")

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
        component_notice = attach_standalone_rights(repo, plugin_source, folder, skill_id)
        zip_path = zips_root / f"{skill_id}-{version}.zip"
        zip_sha = deterministic_zip(folder, zip_path, prefix=skill_id)
        skill_records.append(
            {
                "id": skill_id,
                "payload_tree": tree_digest(source_skill),
                "standalone_rights_envelope": STANDALONE_RIGHTS_DIR,
                "component_notice_bundle": component_notice,
                "claude_zip": zip_path.relative_to(package_root).as_posix(),
                "claude_zip_sha256": zip_sha,
            }
        )

    rights_state = {
        "license": "LICENSE.md",
        "rights_status": loadout["rights_status"],
        "redistribution_state": REDISTRIBUTION_STATE,
        "external_rights_blockers": [],
        "rights_bundle": rights_bundle["files"],
    }
    build_state = {
        "schema": "nova-free-build/v3",
        "product": "Nova the Optimal AI Free",
        "product_version": version,
        "source_base_commit": base_commit,
        "source_lock_sha256": sha256_file(repo / "design" / "source-lock.json"),
        "source_map_sha256": source_lock["source_map_sha256"],
        "source_clean": source_clean,
        "candidate_state": "built_from_frozen_source",
        "independent_review_required": True,
        "archive_filename_encoding": "strict_utf8_local_and_central_headers",
        "rights": rights_state,
        "publication_state": "not_published",
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
            "visible_skill_roots": 27,
            "mind_version": loadout["topology"]["mind_version"],
            "faculty_core_count": loadout["topology"]["faculty_core_count"],
        },
        "source": {
            "base_commit": base_commit,
            "clean": source_clean,
            "source_lock": "design/source-lock.json",
            "source_lock_sha256": sha256_file(repo / "design" / "source-lock.json"),
            "source_map_sha256": source_lock["source_map_sha256"],
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
        "archive_filename_encoding": "strict_utf8_local_and_central_headers",
        "rights": rights_state,
        "release_blockers": [],
        "open_evidence_boundaries": source_lock["open_evidence_boundaries"],
        "publication_state": "not_published",
        "evidence_boundary": "This manifest establishes built bytes, rights custody, and internal parity. Installation, discovery, enabled state, restart state, invocation, service configuration, behavior, publication, and customer outcomes remain separate observations.",
    }
    write_json(package_root / "RELEASE-MANIFEST.json", release_manifest)

    checksum_rows = []
    for path in files(package_root):
        if path == package_root / "SHA256SUMS.txt":
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
        "source_clean": source_clean,
        "candidate_state": "built_from_frozen_source",
        "independent_review_required": True,
        "archive_filename_encoding": "strict_utf8_local_and_central_headers",
        "redistribution_state": REDISTRIBUTION_STATE,
        "publication_state": "not_published",
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

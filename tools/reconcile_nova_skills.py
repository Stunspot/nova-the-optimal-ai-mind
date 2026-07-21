#!/usr/bin/env python3
"""Reconcile the twelve skills shipping in the Nova contest plugin.

The comparison is read-only with respect to source, installed, archive, and
repository custody.  Its only optional mutation is writing deterministic
evidence files inside this contest repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
NOVA_SKILLS_ROOT = ROOT / "plugins" / "nova-the-optimal-ai" / "skills"

SKILLS = (
    "agentic-coding",
    "corkboard",
    "dunbar",
    "ludis-continuum",
    "nova",
    "omnara-deep-research",
    "retrieval-intelligence",
    "retrieval-reviewer",
    "rupert-giles-knowledge-steward",
    "signal-loom",
    "software-verification",
    "verification-reviewer",
)

ALIAS_POLICIES: dict[str, dict[str, tuple[str, ...]]] = {
    "corkboard": {"selected_only_live_data": ("enterprise-bi-report-pin.json",)},
    "ludis-continuum": {},
    "omnara-deep-research": {},
    "retrieval-intelligence": {},
    "retrieval-reviewer": {},
    "rupert-giles-knowledge-steward": {},
    "signal-loom": {},
}

REPOSITORY_FAMILIES = {
    "omnara-deep-research": {
        "repository": "Stunspot/omnara-deep-research",
        "visibility": "private",
        "state": "repository-family-mapped-without-selected-source-default-branch-parity",
        "snapshot_note": (
            "The selected product worktree was at the observed default head, but two selected "
            "metadata files were locally modified; family mapping is not release parity."
        ),
    },
    "software-verification": {
        "repository": "Stunspot/TestForge",
        "visibility": "public",
        "state": "repository-family-mapped-without-selected-source-default-branch-parity",
        "snapshot_note": (
            "The public TestForge repository is family custody; the selected current-host "
            "1.1.2 source was not byte-identical to the observed default branch."
        ),
    },
    "verification-reviewer": {
        "repository": "Stunspot/TestForge",
        "visibility": "public",
        "state": "repository-family-mapped-without-selected-source-default-branch-parity",
        "snapshot_note": (
            "The public TestForge repository is family custody; the selected current-host "
            "1.1.2 source was not byte-identical to the observed default branch."
        ),
    },
}

ESTATE_EVIDENCE = (
    ("source-selection.json", "selected source class and path"),
    ("description-registry.json", "reconciled model-visible and UI descriptions"),
    ("verification/estate-scan-2026-07-21.json", "archive reference and current-hash boundary"),
    ("ARCHIVE-CUSTODY-2026-07-21.md", "archive custody interpretation"),
    ("REPOSITORY-CUSTODY-2026-07-21.md", "repository custody interpretation"),
    (
        "verification/github-handle-custody-search-2026-07-21.json",
        "bounded operator-reported search for previously unmapped handles",
    ),
    ("github-owned-repositories-2026-07-21.json", "authenticated owned-repository snapshot"),
)

REPOSITORY_EVIDENCE = {
    "source_import_ledger": ROOT / "verification" / "source-import-ledger.json",
    "transformation_map": ROOT / "verification" / "transformation-map.json",
}

SKIP_SOURCE_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
SKIP_SOURCE_FILES = {".DS_Store", "Thumbs.db"}
SKIP_SOURCE_SUFFIXES = {".pyc", ".pyo"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def parse_yaml_scalar(raw: str) -> str:
    value = raw.strip()
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def metadata_value(path: Path, key: str) -> str:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(path.read_text(encoding="utf-8-sig"))
    if not match:
        raise ValueError(f"{path}: missing {key}")
    return parse_yaml_scalar(match.group(1))


def tree_inventory(
    root: Path,
    *,
    ignored_relative_paths: tuple[str, ...] = (),
    shipping: bool = False,
) -> dict[str, Any]:
    if not root.is_dir():
        raise FileNotFoundError(f"missing tree: {root}")

    ignored = set(ignored_relative_paths)
    hashes: dict[str, str] = {}
    sizes: dict[str, int] = {}
    ignored_present: list[str] = []
    symlinks: list[str] = []

    for current, child_dirs, child_files in os.walk(root, followlinks=False):
        current_path = Path(current)
        if not shipping:
            child_dirs[:] = sorted(name for name in child_dirs if name not in SKIP_SOURCE_DIRS)
        else:
            child_dirs[:] = sorted(child_dirs)

        for child_dir in child_dirs:
            candidate = current_path / child_dir
            if candidate.is_symlink():
                symlinks.append(candidate.relative_to(root).as_posix())

        for child_file in sorted(child_files):
            path = current_path / child_file
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                symlinks.append(relative)
                continue
            if not shipping and (
                child_file in SKIP_SOURCE_FILES or path.suffix.lower() in SKIP_SOURCE_SUFFIXES
            ):
                continue
            if relative in ignored:
                ignored_present.append(relative)
                continue
            hashes[relative] = sha256(path)
            sizes[relative] = path.stat().st_size

    tree = hashlib.sha256()
    for relative in sorted(hashes):
        tree.update(f"{relative}\0{sizes[relative]}\0{hashes[relative]}\n".encode("utf-8"))

    return {
        "root": str(root),
        "files": hashes,
        "sizes": sizes,
        "file_count": len(hashes) + len(ignored_present),
        "byte_count": sum(sizes.values()),
        "tree_sha256": tree.hexdigest(),
        "ignored_present": sorted(ignored_present),
        "symlinks": sorted(symlinks),
    }


def compare_roots(
    handle: str,
    selected_root: Path,
    import_root: Path,
    errors: list[str],
) -> dict[str, Any]:
    if normalized_path(selected_root) == normalized_path(import_root):
        inventory = tree_inventory(selected_root)
        if inventory["symlinks"]:
            errors.append(f"{handle}: source root contains symlinks: {inventory['symlinks']}")
        return {
            "state": "same-root",
            "selected_files": inventory["file_count"],
            "actual_import_files": inventory["file_count"],
            "common_files": inventory["file_count"],
            "selected_only": [],
            "import_only": [],
            "hash_mismatches": [],
            "intentionally_excluded_live_data": [],
            "common_tree_sha256": inventory["tree_sha256"],
        }

    policy = ALIAS_POLICIES.get(handle)
    if policy is None:
        errors.append(f"{handle}: selected and import roots differ without an alias policy")
        policy = {}
    ignored_selected = policy.get("selected_only_live_data", ())
    selected = tree_inventory(selected_root, ignored_relative_paths=ignored_selected)
    imported = tree_inventory(import_root)
    selected_files = selected["files"]
    imported_files = imported["files"]
    common = set(selected_files) & set(imported_files)
    selected_only = sorted(set(selected_files) - set(imported_files))
    import_only = sorted(set(imported_files) - set(selected_files))
    mismatches = sorted(path for path in common if selected_files[path] != imported_files[path])
    ignored_missing = sorted(set(ignored_selected) - set(selected["ignored_present"]))

    if ignored_missing:
        errors.append(f"{handle}: expected live-data exclusion is missing: {ignored_missing}")
    if selected_only or import_only or mismatches:
        errors.append(
            f"{handle}: path-alias roots drifted "
            f"(selected_only={selected_only}, import_only={import_only}, changed={mismatches})"
        )
    if selected["symlinks"] or imported["symlinks"]:
        errors.append(f"{handle}: path-alias comparison encountered symlinks")

    if ignored_selected:
        state = "path-alias-byte-identical-with-intentional-live-data-exclusion"
    else:
        state = "path-alias-byte-identical"
    return {
        "state": state,
        "selected_files": selected["file_count"],
        "actual_import_files": imported["file_count"],
        "common_files": len(common),
        "selected_only": selected_only,
        "import_only": import_only,
        "hash_mismatches": mismatches,
        "intentionally_excluded_live_data": selected["ignored_present"],
        "common_tree_sha256": imported["tree_sha256"] if not (selected_only or import_only or mismatches) else None,
    }


def transformation_rules(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for index, rule in enumerate(payload.get("rules", []), start=1):
        rules.append(
            {
                "id": f"rule-{index:02d}",
                "paths": set(rule.get("paths", [])),
                "prefix": rule.get("prefix"),
                "reason": rule.get("reason", ""),
            }
        )
    return rules


def covering_rule(path: str, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    for rule in rules:
        if path in rule["paths"] or (rule["prefix"] and path.startswith(rule["prefix"])):
            return rule
    return None


def import_root_for(
    handle: str,
    ledger_rows: list[dict[str, Any]],
    errors: list[str],
) -> tuple[Path | None, list[dict[str, Any]]]:
    prefix = f"plugins/nova-the-optimal-ai/skills/{handle}/"
    rows = [row for row in ledger_rows if row["destination"].startswith(prefix)]
    if handle == "nova":
        if rows:
            errors.append("nova: contest-authored skill unexpectedly appears in the source import ledger")
        return None, []
    if not rows:
        errors.append(f"{handle}: no source import ledger rows")
        return None, []

    roots: set[str] = set()
    root_paths: list[Path] = []
    for row in rows:
        relative = Path(row["destination"][len(prefix) :])
        source = Path(row["source"])
        root = source
        for _ in relative.parts:
            root = root.parent
        roots.add(normalized_path(root))
        root_paths.append(root)
    if len(roots) != 1:
        errors.append(f"{handle}: source ledger resolves to multiple import roots: {sorted(roots)}")
        return None, rows
    return root_paths[0], rows


def transformation_status(
    handle: str,
    shipping_files: dict[str, str],
    ledger_rows: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    prefix = f"plugins/nova-the-optimal-ai/skills/{handle}/"
    imported = {row["destination"]: row for row in ledger_rows}
    changed: list[str] = []
    removed: list[str] = []
    for destination, row in imported.items():
        relative = destination[len(prefix) :]
        if relative not in shipping_files:
            removed.append(destination)
        elif shipping_files[relative] != row["imported_sha256"]:
            changed.append(destination)

    current_destinations = {prefix + relative for relative in shipping_files}
    added = sorted(current_destinations - set(imported))
    changed = sorted(changed)
    removed = sorted(removed)
    divergent = sorted(set(changed) | set(removed) | set(added))
    custody = [(path, covering_rule(path, rules)) for path in divergent]
    unexplained = sorted(path for path, rule in custody if rule is None)
    if unexplained:
        errors.append(f"{handle}: unexplained post-import drift: {unexplained}")

    reasons = sorted({rule["reason"] for _, rule in custody if rule is not None})
    rule_ids = sorted({rule["id"] for _, rule in custody if rule is not None})
    return {
        "initial_import_files": len(imported),
        "changed_after_import": changed,
        "removed_after_import": removed,
        "added_after_import": added,
        "divergent_paths": len(divergent),
        "covered_paths": len(divergent) - len(unexplained),
        "covering_rule_ids": rule_ids,
        "covering_reasons": reasons,
        "unexplained_drift": unexplained,
        "status": "covered" if not unexplained else "unexplained-drift",
    }


def git_value(*args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def repository_custody(
    handle: str,
    unmapped_handles: set[str],
    repository_doc: str,
    owned_repositories: set[str],
    errors: list[str],
) -> dict[str, Any]:
    if handle == "nova":
        head = git_value("rev-parse", "--verify", "HEAD")
        remote = git_value("remote", "get-url", "origin")
        return {
            "state": "contest-local-repository-commit-present" if head else "contest-local-repository-no-commit",
            "repository_root": "contest-repository://.",
            "commit_present": head is not None,
            "remote_origin": remote,
            "release_proof": False,
            "boundary": (
                "Commit presence is recorded without embedding a self-referential HEAD hash. "
                "A local commit or remote association would not prove publication or release acceptance."
            ),
        }

    family = REPOSITORY_FAMILIES.get(handle)
    if family:
        repository = family["repository"]
        if repository not in owned_repositories:
            errors.append(f"{handle}: mapped repository missing from owned-repository snapshot: {repository}")
        if repository not in repository_doc:
            errors.append(f"{handle}: mapped repository missing from repository custody document: {repository}")
        return {
            **family,
            "snapshot_date": "2026-07-21",
            "selected_source_default_branch_byte_parity": False,
            "release_proof": False,
        }

    if handle not in unmapped_handles:
        errors.append(f"{handle}: neither mapped nor present in the bounded unmapped-handle search")
    return {
        "state": "no-authoritative-repository-mapping-located-at-snapshot",
        "repository": None,
        "snapshot_date": "2026-07-21",
        "search_evidence": "operator-reported; per-query matrix not retained",
        "search_is_exhaustive": False,
        "release_proof": False,
    }


def archive_custody(
    handle: str,
    handles_without_zip_reference: set[str],
    current_hash_matches: int,
) -> dict[str, Any]:
    if handle == "nova":
        return {
            "state": "contest-authored-outside-estate-archive-snapshot",
            "historical_zip_reference_located": False,
            "current_selected_source_hash_match": None,
            "release_proof": False,
        }
    if handle in handles_without_zip_reference:
        state = "no-historical-zip-reference-located"
        reference_found = False
    else:
        state = "historical-zip-reference-located-without-current-source-parity"
        reference_found = True
    return {
        "state": state,
        "historical_zip_reference_located": reference_found,
        "current_selected_source_hash_match": False if current_hash_matches == 0 else "aggregate-not-zero",
        "snapshot_date": "2026-07-21",
        "release_proof": False,
    }


def description_status(
    handle: str,
    shipping_root: Path,
    registry: dict[str, Any],
) -> dict[str, Any]:
    current_model = metadata_value(shipping_root / "SKILL.md", "description")
    current_ui = metadata_value(shipping_root / "agents" / "openai.yaml", "short_description")
    registry_model = registry.get("model_visible_descriptions", {}).get(handle)
    registry_ui = registry.get("ui_short_descriptions", {}).get(handle)
    if handle == "nova":
        model_state = "contest-authored-outside-estate-registry"
        ui_state = "contest-authored-outside-estate-registry"
    else:
        model_state = "estate-registry-exact" if current_model == registry_model else "contest-curated-from-estate"
        ui_state = "estate-registry-exact" if current_ui == registry_ui else "contest-curated-from-estate"
    return {
        "current_model_visible": current_model,
        "estate_registry_model_visible": registry_model,
        "model_visible_status": model_state,
        "current_ui_short": current_ui,
        "estate_registry_ui_short": registry_ui,
        "ui_short_status": ui_state,
        "current_model_ui_alignment": "exact" if current_model == current_ui else "intentionally-distinct-or-pending-review",
    }


def render_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# Nova-only skill reconciliation",
        "",
        f"Status: **{receipt['status']}**. The candidate contains exactly {receipt['summary']['skills']} "
        f"Nova skills, {receipt['summary']['shipping_files']} skill files, and "
        f"{receipt['summary']['shipping_bytes']:,} bytes. Unexplained drift: "
        f"{receipt['summary']['unexplained_drift_paths']} paths.",
        "",
        "This receipt reconciles selected source, the root actually imported, current contest transformations, "
        "description lineage, and point-in-time repository/archive custody. It is provenance evidence, not "
        "installation, behavior, publication, or release proof.",
        "",
        "| Skill | Source class | Selected/import relationship | Description | Repository custody | Archive custody | Shipping | Transform |",
        "|---|---|---|---|---|---|---:|---|",
    ]
    for skill in receipt["skills"]:
        relation = skill["byte_relationship"]["state"]
        description = skill["description"]["model_visible_status"]
        repository = skill["repository_custody"]["state"]
        archive = skill["archive_custody"]["state"]
        shipping = skill["shipping"]
        transform = skill["transformation"]
        lines.append(
            f"| `{skill['handle']}` | {skill['selected_source']['class']} | {relation} | {description} | "
            f"{repository} | {archive} | {shipping['files']} files / {shipping['bytes']:,} B | "
            f"{transform['status']} ({transform['covered_paths']}/{transform['divergent_paths']}) |"
        )

    lines.extend(
        [
            "",
            "## Reconciliation boundary",
            "",
            "A path-alias result compares complete current trees by relative path and SHA-256, excluding only "
            "named generated debris and Corkboard's explicit live-user-data pin. Historical ZIP references and "
            "repository-family associations remain custody clues; neither establishes current release bytes. "
            "Fresh-host discovery, invocation, live behavior, accessibility, licensing, publication, and contest "
            "acceptance require their own receipts.",
            "",
        ]
    )
    if receipt["errors"]:
        lines.extend(["## Unexplained drift", ""])
        lines.extend(f"- {error}" for error in receipt["errors"])
        lines.append("")
    return "\n".join(lines)


def build_receipt(estate_root: Path, private_import_ledger: Path) -> dict[str, Any]:
    errors: list[str] = []
    source_selection_path = estate_root / "source-selection.json"
    description_registry_path = estate_root / "description-registry.json"
    estate_scan_path = estate_root / "verification" / "estate-scan-2026-07-21.json"
    archive_doc_path = estate_root / "ARCHIVE-CUSTODY-2026-07-21.md"
    repository_doc_path = estate_root / "REPOSITORY-CUSTODY-2026-07-21.md"
    search_path = estate_root / "verification" / "github-handle-custody-search-2026-07-21.json"
    owned_path = estate_root / "github-owned-repositories-2026-07-21.json"

    source_selection = load_json(source_selection_path)
    description_registry = load_json(description_registry_path)
    estate_scan = load_json(estate_scan_path)
    search = load_json(search_path)
    owned = load_json(owned_path)
    repository_doc = repository_doc_path.read_text(encoding="utf-8-sig")
    archive_doc_path.read_text(encoding="utf-8-sig")
    import_ledger = load_json(private_import_ledger)
    transform_payload = load_json(REPOSITORY_EVIDENCE["transformation_map"])
    rules = transformation_rules(transform_payload)

    selected_by_name = {item["name"]: item for item in source_selection.get("skills", [])}
    governed_expected = set(SKILLS) - {"nova"}
    missing_selection = sorted(governed_expected - set(selected_by_name))
    if missing_selection:
        errors.append(f"source selection is missing Nova skills: {missing_selection}")

    discovered_skills = {path.name for path in NOVA_SKILLS_ROOT.iterdir() if path.is_dir()}
    if discovered_skills != set(SKILLS):
        errors.append(
            "Nova shipping skill set differs from the twelve-skill contract: "
            f"missing={sorted(set(SKILLS) - discovered_skills)}, "
            f"extra={sorted(discovered_skills - set(SKILLS))}"
        )

    unmapped_handles = set(search["result"]["searched_unmapped_handles"])
    scan_snapshot = estate_scan["scan_snapshot"]
    no_zip_reference = set(scan_snapshot["handles_without_zip_reference"])
    current_hash_matches = int(scan_snapshot["current_skill_hashes_found_in_any_zip"])
    owned_nodes = (
        owned.get("repositories")
        or owned.get("data", {}).get("viewer", {}).get("repositories", {}).get("nodes", [])
    )
    owned_repositories = {
        item.get("name_with_owner") or item.get("nameWithOwner") for item in owned_nodes
    }
    owned_repositories.discard(None)

    skill_receipts: list[dict[str, Any]] = []
    ledger_rows = import_ledger["imported"]
    for handle in SKILLS:
        shipping_root = NOVA_SKILLS_ROOT / handle
        shipping_inventory = tree_inventory(shipping_root, shipping=True)
        if shipping_inventory["symlinks"]:
            errors.append(f"{handle}: shipping tree contains symlinks: {shipping_inventory['symlinks']}")

        if handle == "nova":
            selected = {
                "class": "contest-authored",
                "path": f"contest-repository://plugins/nova-the-optimal-ai/skills/{handle}",
                "estate_selection_record": False,
            }
            actual_import_root = None
            relevant_rows: list[dict[str, Any]] = []
            byte_relationship = {
                "state": "contest-authored-no-import-root",
                "selected_files": shipping_inventory["file_count"],
                "actual_import_files": 0,
                "common_files": 0,
                "selected_only": sorted(shipping_inventory["files"]),
                "import_only": [],
                "hash_mismatches": [],
                "intentionally_excluded_live_data": [],
                "common_tree_sha256": None,
            }
        else:
            record = selected_by_name.get(handle)
            if record is None:
                selected = {"class": None, "path": None, "estate_selection_record": False}
                actual_import_root = None
                relevant_rows = []
                byte_relationship = {"state": "missing-source-selection"}
            else:
                selected_root = Path(record["source_root"])
                selected = {
                    "class": record["source_class"],
                    "path": f"estate-selected-source://{handle}",
                    "estate_selection_record": True,
                }
                actual_import_root, relevant_rows = import_root_for(handle, ledger_rows, errors)
                if actual_import_root is None:
                    byte_relationship = {"state": "missing-import-root"}
                else:
                    byte_relationship = compare_roots(
                        handle,
                        selected_root,
                        actual_import_root,
                        errors,
                    )

        transformation = transformation_status(
            handle,
            shipping_inventory["files"],
            relevant_rows,
            rules,
            errors,
        )
        skill_receipts.append(
            {
                "handle": handle,
                "selected_source": selected,
                "actual_import_root": f"private-import-source://{handle}" if actual_import_root else None,
                "byte_relationship": byte_relationship,
                "description": description_status(handle, shipping_root, description_registry),
                "repository_custody": repository_custody(
                    handle,
                    unmapped_handles,
                    repository_doc,
                    owned_repositories,
                    errors,
                ),
                "archive_custody": archive_custody(
                    handle,
                    no_zip_reference,
                    current_hash_matches,
                ),
                "shipping": {
                    "root": f"contest-repository://plugins/nova-the-optimal-ai/skills/{handle}",
                    "files": shipping_inventory["file_count"],
                    "bytes": shipping_inventory["byte_count"],
                    "tree_sha256": shipping_inventory["tree_sha256"],
                },
                "transformation": transformation,
            }
        )

    evidence_sources = []
    for relative, role in ESTATE_EVIDENCE:
        path = estate_root / Path(relative)
        evidence_sources.append(
            {
                "path": f"private-estate-evidence://{Path(relative).as_posix()}",
                "sha256": sha256(path),
                "role": role,
            }
        )
    for key, path in REPOSITORY_EVIDENCE.items():
        evidence_sources.append(
            {
                "path": f"contest-repository://{path.relative_to(ROOT).as_posix()}",
                "sha256": sha256(path),
                "role": key.replace("_", " "),
            }
        )

    summary = {
        "skills": len(skill_receipts),
        "shipping_files": sum(item["shipping"]["files"] for item in skill_receipts),
        "shipping_bytes": sum(item["shipping"]["bytes"] for item in skill_receipts),
        "path_aliases_byte_identical": sum(
            item["byte_relationship"].get("state", "").startswith("path-alias-byte-identical")
            for item in skill_receipts
        ),
        "same_root_imports": sum(
            item["byte_relationship"].get("state") == "same-root" for item in skill_receipts
        ),
        "contest_authored_skills": 1,
        "historical_archive_references": sum(
            item["archive_custody"]["historical_zip_reference_located"] for item in skill_receipts
        ),
        "skills_with_repository_family_mapping": len(REPOSITORY_FAMILIES),
        "repository_families": len(
            {item["repository"] for item in REPOSITORY_FAMILIES.values()}
        ),
        "unexplained_drift_paths": sum(
            len(item["transformation"]["unexplained_drift"]) for item in skill_receipts
        ),
        "errors": len(errors),
    }
    return {
        "schema": "cd-nova-skill-reconciliation/v1",
        "tool": "tools/reconcile_nova_skills.py",
        "scope": {
            "plugin": "nova-the-optimal-ai",
            "skill_handles": list(SKILLS),
            "excluded": "All MIND skills and every non-Nova estate skill; those remain deferred.",
        },
        "evidence_observed": "2026-07-21",
        "status": "PASS" if not errors else "FAIL",
        "summary": summary,
        "skills": skill_receipts,
        "evidence_sources": evidence_sources,
        "errors": errors,
        "boundaries": {
            "proves": (
                "Current Nova-only source/import byte relationships, shipping inventory, description lineage, "
                "and transformation-map coverage against the named point-in-time estate evidence."
            ),
            "does_not_prove": [
                "archive release currentness",
                "repository promotion authority or default-branch release parity",
                "plugin registration, discovery, invocation, or fresh-host behavior",
                "accessibility, licensing, publication, submission, or contest acceptance",
            ],
        },
    }


def write_or_check(path: Path, content: str, check: bool) -> bool:
    if check:
        return path.is_file() and path.read_text(encoding="utf-8-sig") == content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile only the twelve skills shipping in Nova.")
    parser.add_argument(
        "--estate-root",
        type=Path,
        required=True,
        help="Private estate evidence root; this path is not stored in the public repository.",
    )
    parser.add_argument(
        "--private-import-ledger",
        type=Path,
        required=True,
        help="Private initial-import ledger with machine-local source paths; never publish this file.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "verification" / "nova-skill-reconciliation.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "verification" / "nova-skill-reconciliation.md",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare deterministic output with existing receipts without writing.",
    )
    args = parser.parse_args()

    receipt = build_receipt(args.estate_root, args.private_import_ledger)
    rendered_json = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    rendered_markdown = render_markdown(receipt)
    json_ok = write_or_check(args.json_output, rendered_json, args.check)
    markdown_ok = write_or_check(args.markdown_output, rendered_markdown, args.check)
    stale = args.check and not (json_ok and markdown_ok)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "skills": receipt["summary"]["skills"],
                "shipping_files": receipt["summary"]["shipping_files"],
                "shipping_bytes": receipt["summary"]["shipping_bytes"],
                "unexplained_drift_paths": receipt["summary"]["unexplained_drift_paths"],
                "errors": receipt["summary"]["errors"],
                "outputs_current": not stale,
            },
            ensure_ascii=False,
        )
    )
    return 0 if receipt["status"] == "PASS" and not stale else 1


if __name__ == "__main__":
    raise SystemExit(main())

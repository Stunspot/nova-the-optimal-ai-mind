#!/usr/bin/env python3
"""Read-only v1 compatibility and immutable-generation Continuity v2 validator."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from continuity_store_v2 import scope_within_manifest
from error_neighborhood import contains_secret
from schema_validation import SchemaCatalog, SchemaError
from workspace_runtime import (
    FORMAT, LEGACY_FORMAT, GENERATION_FORMAT, TRANSACTION_FORMAT, ContinuityError,
    dump_canonical, generation_path, legacy_content_provenance_errors,
    legacy_content_transformations, open_snapshot, pending_transactions, read_json,
    read_jsonl, sha256_bytes, sha256_file, tree_digest,
)

SCHEMAS = {"episodes": "episode-v2.schema.json", "state": "state-record-v2.schema.json", "proposals": "proposal-v2.schema.json"}
MEMBERS = ("episodes.jsonl", "state.jsonl", "proposals.jsonl", "receipts.jsonl", "idempotency.jsonl")


def _catalog() -> SchemaCatalog:
    return SchemaCatalog(Path(__file__).resolve().parents[1] / "assets" / "schemas")


def _physical_jsonl(path: Path) -> list[dict[str, Any]]:
    return read_jsonl(path)


def _row_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip())


def _v1_validate(root: Path, manifest: dict[str, Any], source_before: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings = [
        "v1 exact read-only validation does not qualify legacy locking, receipts, recent-episode policy, export, or forgetting",
        "use copy migration for v2 mutation and recovery guarantees",
    ]
    collections: dict[str, list[dict[str, Any]]] = {}
    for name, relative in {"episodes": "episodes/events.jsonl", "state": "state/records.jsonl", "proposals": "proposals/proposals.jsonl"}.items():
        try:
            collections[name] = read_jsonl(root / relative)
        except ContinuityError as exc:
            errors.append(f"{name}: {exc}")
            collections[name] = []
    ids = [row.get("id") for values in collections.values() for row in values]
    duplicate = sorted({value for value in ids if value and ids.count(value) > 1})
    if duplicate:
        errors.append("duplicate canonical IDs: " + ", ".join(duplicate))
    source_after = tree_digest(root)
    if source_after != source_before:
        errors.append("read-only v1 validation changed or raced source bytes")
    return {
        "format": "cd-continuity-validation/v2", "workspace": str(root), "workspace_id": manifest.get("workspace_id"),
        "workspace_format": LEGACY_FORMAT, "compatibility_mode": "v1_read_only", "observed_generation": manifest.get("generation", 0),
        "status": "valid_with_known_limits" if not errors else "invalid", "errors": errors, "warnings": warnings,
        "capability_notes": ["legacy validator behavior remains separately inherited and unqualified"],
        "source_tree_sha256_before": source_before, "source_tree_sha256_after": source_after, "source_mutated": False,
        "counts": {name: len(values) for name, values in collections.items()},
    }


def _generation_inventory(root: Path, catalog: SchemaCatalog, errors: list[str], warnings: list[str]) -> dict[int, tuple[Path, dict[str, Any], str]]:
    result: dict[int, tuple[Path, dict[str, Any], str]] = {}
    base = root / "generations"
    if not base.is_dir():
        errors.append("generations directory missing")
        return result
    for directory in sorted(item for item in base.iterdir() if item.is_dir()):
        metadata_path = directory / "generation.json"
        if not metadata_path.is_file():
            errors.append(f"{directory.name}: generation.json missing")
            continue
        try:
            metadata = read_json(metadata_path)
        except ContinuityError as exc:
            errors.append(f"{directory.name}: {exc}")
            continue
        for error in catalog.validate(metadata, "generation-v1.schema.json"):
            errors.append(f"{directory.name} schema {error}")
        generation = metadata.get("generation")
        expected_name = f"g-{int(generation):020d}" if isinstance(generation, int) else None
        if expected_name != directory.name:
            errors.append(f"{directory.name}: directory/generation identity mismatch")
        if generation in result:
            errors.append(f"duplicate generation number: {generation}")
            continue
        members = metadata.get("members") or {}
        for name in MEMBERS:
            path = directory / name
            expected = members.get(name) or {}
            if not path.is_file():
                errors.append(f"{directory.name}/{name}: missing")
                continue
            if sha256_file(path) != expected.get("sha256"):
                errors.append(f"{directory.name}/{name}: digest mismatch")
            if path.stat().st_size != expected.get("bytes"):
                errors.append(f"{directory.name}/{name}: byte count mismatch")
            if _row_count(path) != expected.get("rows"):
                errors.append(f"{directory.name}/{name}: row count mismatch")
        if isinstance(generation, int):
            result[generation] = (directory, metadata, sha256_file(metadata_path))
    for generation, (_, metadata, _) in sorted(result.items()):
        if generation == 0:
            if metadata.get("predecessor_generation") is not None or metadata.get("predecessor_generation_manifest_sha256") is not None:
                errors.append("generation 0 must not name a predecessor")
            continue
        prior = result.get(generation - 1)
        if metadata.get("predecessor_generation") != generation - 1:
            errors.append(f"generation {generation}: predecessor generation mismatch")
        if prior is None:
            warnings.append(f"generation {generation}: predecessor bundle is not retained")
        elif metadata.get("predecessor_generation_manifest_sha256") != prior[2]:
            errors.append(f"generation {generation}: predecessor digest mismatch")
    return result


def _validate_generation_receipt_identities(
    manifest: dict[str, Any],
    generations: dict[int, tuple[Path, dict[str, Any], str]],
    catalog: SchemaCatalog,
    errors: list[str],
) -> None:
    for generation, (directory, metadata, _) in sorted(generations.items()):
        receipts = _physical_jsonl(directory / "receipts.jsonl")
        candidates = [
            row for row in receipts
            if row.get("transaction_id") == metadata.get("transaction_id")
            and row.get("generation_after") == generation
        ]
        if len(candidates) != 1:
            errors.append(f"generation {generation} lacks one receipt matching its transaction identity")
            continue
        receipt = candidates[0]
        for error in catalog.validate(receipt, "receipt-v2.schema.json"):
            errors.append(f"generation {generation} receipt schema {error}")
        expected = {
            "status": "committed",
            "workspace_id": manifest.get("workspace_id"),
            "transaction_id": metadata.get("transaction_id"),
            "operation": metadata.get("operation_family"),
            "generation_before": generation - 1,
            "generation_after": generation,
        }
        if any(receipt.get(key) != value for key, value in expected.items()):
            errors.append(f"generation {generation} receipt identity does not match generation metadata")
        if metadata.get("workspace_id") != manifest.get("workspace_id"):
            errors.append(f"generation {generation} metadata workspace identity mismatch")


def _validate_legacy_content_history(
    manifest: dict[str, Any],
    generations: dict[int, tuple[Path, dict[str, Any], str]],
    catalog: SchemaCatalog,
    errors: list[str],
) -> None:
    generation_zero = generations.get(0)
    migrated_from = manifest.get("migrated_from") or {}
    contract_declared = "legacy_oversize_content_provenance_count" in migrated_from
    retained_provenance = any(
        any("legacy_content_provenance" in row for row in _physical_jsonl(directory / "episodes.jsonl"))
        for directory, _, _ in generations.values()
    )
    if generation_zero is None:
        if contract_declared or retained_provenance:
            errors.append("legacy content provenance origin generation 0 is missing")
        return
    g0_path, g0_metadata, _ = generation_zero
    g0_episodes = _physical_jsonl(g0_path / "episodes.jsonl")
    transformations = legacy_content_transformations(g0_episodes)
    digest = sha256_bytes(dump_canonical(transformations).encode("utf-8"))
    contract_present = bool(transformations) or contract_declared
    if contract_present:
        if g0_metadata.get("operation_family") != "migrate-copy":
            errors.append("legacy content provenance was not created by generation-0 copy migration")
        if migrated_from.get("legacy_oversize_content_provenance_count") != len(transformations):
            errors.append("legacy content provenance count does not match generation 0")
        if migrated_from.get("legacy_oversize_content_provenance_sha256") != digest:
            errors.append("legacy content provenance digest does not match generation 0")
        receipts = [
            row for row in _physical_jsonl(g0_path / "receipts.jsonl")
            if row.get("operation") == "migrate-copy"
        ]
        if len(receipts) != 1:
            errors.append("legacy content provenance lacks one generation-0 migration receipt")
        else:
            receipt = receipts[0]
            expected_identity = {
                "kind": "migration-copied",
                "status": "committed",
                "workspace_id": manifest.get("workspace_id"),
                "transaction_id": g0_metadata.get("transaction_id"),
                "operation": "migrate-copy",
                "generation_before": -1,
                "generation_after": 0,
            }
            if any(receipt.get(key) != value for key, value in expected_identity.items()):
                errors.append("migration receipt identity does not match generation 0")
            if g0_metadata.get("workspace_id") != manifest.get("workspace_id"):
                errors.append("generation-0 migration workspace identity mismatch")
            if (receipt.get("mapping") or {}).get("lossless_oversize_content_rows") != len(transformations):
                errors.append("migration receipt legacy content count mismatch")
            if receipt.get("legacy_oversize_content_provenance_sha256") != digest:
                errors.append("migration receipt legacy content digest mismatch")
            if transformations and "lossless-oversize-content" not in str(receipt.get("mapping_policy") or ""):
                errors.append("migration receipt does not name the lossless oversize mapping policy")
    allowed = {
        str(row.get("id") or ""): dump_canonical(row)
        for row in g0_episodes
        if "legacy_content_provenance" in row
    }
    provenance_maps: dict[int, dict[str, str]] = {}
    for generation, (directory, _, _) in sorted(generations.items()):
        generation_map: dict[str, str] = {}
        for row in _physical_jsonl(directory / "episodes.jsonl"):
            if "legacy_content_provenance" not in row:
                continue
            rid = str(row.get("id") or "")
            rendered = dump_canonical(row)
            generation_map[rid] = rendered
            for error in catalog.validate(row, "episode-v2.schema.json"):
                errors.append(f"generation {generation} legacy row {rid} schema {error}")
            for error in legacy_content_provenance_errors(row):
                errors.append(f"generation {generation} legacy row {rid}: {error}")
            if allowed.get(rid) != rendered:
                errors.append(f"generation {generation} legacy content provenance did not originate unchanged in generation 0")
        provenance_maps[generation] = generation_map
    if contract_present:
        last_generation = max(generations)
        missing = [generation for generation in range(last_generation + 1) if generation not in generations]
        if missing:
            errors.append("legacy content provenance history has missing generations: " + ", ".join(str(item) for item in missing))
            return
        for generation in range(1, last_generation + 1):
            prior_map = provenance_maps[generation - 1]
            current_map = provenance_maps[generation]
            operation = str(generations[generation][1].get("operation_family") or "")
            if operation == "forget":
                if any(prior_map.get(key) != value for key, value in current_map.items()):
                    errors.append(f"generation {generation} forget introduced or altered legacy content provenance")
            elif operation == "restore-forget":
                previous_operation = str(generations[generation - 1][1].get("operation_family") or "")
                if generation < 2 or previous_operation != "forget" or current_map != provenance_maps[generation - 2]:
                    errors.append(f"generation {generation} restore-forget does not match the exact pre-forget provenance map")
            elif current_map != prior_map:
                errors.append(f"generation {generation} changed legacy content provenance under operation {operation or 'unknown'}")


def _validate_references(collections: dict[str, list[dict[str, Any]]], errors: list[str]) -> None:
    episodes, records, proposals = collections["episodes"], collections["state"], collections["proposals"]
    episode_ids = {row.get("id") for row in episodes}
    occurrence_ids = {row.get("id") for row in episodes if row.get("type") == "failure_occurrence"}
    record_ids = {row.get("id") for row in records}
    for row in episodes:
        if row.get("type") == "failure_occurrence":
            occurrence = row.get("occurrence") or {}
            if contains_secret(dump_canonical(occurrence)):
                errors.append(f"{row.get('id')}: secret-shaped occurrence evidence")
            if occurrence.get("source_pointer") != (row.get("source") or {}).get("locator"):
                errors.append(f"{row.get('id')}: source pointer/locator mismatch")
    for row in records:
        rid = str(row.get("id"))
        if set(row.get("source_ids") or []) - episode_ids:
            errors.append(f"{rid}: missing source episodes")
        if set(row.get("supersedes") or []) - record_ids:
            errors.append(f"{rid}: supersedes unknown state")
        if set(row.get("conflicts_with") or []) - record_ids:
            errors.append(f"{rid}: conflicts with unknown state")
        if row.get("kind") != "failure":
            continue
        pattern = row.get("failure_pattern") or {}
        if set(pattern.get("occurrence_ids") or []) - occurrence_ids and "forgotten" not in (row.get("tags") or []):
            errors.append(f"{rid}: failure pattern links non-occurrence evidence")
        if pattern.get("causal_state") == "verified" and not pattern.get("causal_evidence_ids"):
            errors.append(f"{rid}: verified cause lacks evidence")
        if pattern.get("resolution_state") in {"resolved", "regressed"} and not pattern.get("outcome_evidence_ids"):
            errors.append(f"{rid}: governed resolution lacks outcome evidence")
        for name, field in (pattern.get("advice") or {}).items():
            if field.get("accepted"):
                required = ("authority_record_id", "authority", "accepted_at", "evidence_ids", "policy_id", "valid_from")
                if any(field.get(key) in (None, "", []) for key in required):
                    errors.append(f"{rid}: accepted advice field {name} lacks field authority/evidence/validity")
                if set(field.get("evidence_ids") or []) - episode_ids:
                    errors.append(f"{rid}: accepted advice field {name} cites unknown evidence")
            elif any(field.get(key) for key in ("authority_record_id", "authority", "accepted_at")):
                errors.append(f"{rid}: unaccepted advice field {name} carries authority")
    for row in proposals:
        rid = str(row.get("id"))
        if set(row.get("source_ids") or []) - episode_ids:
            errors.append(f"{rid}: proposal has missing source episodes")
        if row.get("target_id") and row.get("target_id") not in record_ids:
            errors.append(f"{rid}: proposal targets unknown state")
        if row.get("applied_record_id") and row.get("applied_record_id") not in record_ids:
            errors.append(f"{rid}: proposal names unknown applied state")
        if row.get("origin") == "faultline":
            pattern = row.get("failure_pattern") or {}
            if pattern.get("lifecycle_state") == "proposed" and any((field or {}).get("accepted") for field in (pattern.get("advice") or {}).values()):
                errors.append(f"{rid}: proposal self-authorizes advice")


def _validate_v2(root: Path, manifest: dict[str, Any], source_before: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    catalog = _catalog()
    for error in catalog.validate(manifest, "continuity-manifest-v2.schema.json"):
        errors.append("manifest schema " + error)
    try:
        stable_manifest, _ = open_snapshot(root)
    except ContinuityError as exc:
        errors.append(str(exc)); stable_manifest = manifest
    generations = _generation_inventory(root, catalog, errors, warnings)
    _validate_generation_receipt_identities(stable_manifest, generations, catalog, errors)
    _validate_legacy_content_history(stable_manifest, generations, catalog, errors)
    active_generation = int(stable_manifest.get("generation", -1))
    active = generations.get(active_generation)
    if active is None:
        errors.append("active generation is absent from inventory")
        active_path = root / "generations" / "missing"
    else:
        active_path, active_metadata, active_digest = active
        if stable_manifest.get("active_generation_path") != active_path.relative_to(root).as_posix():
            errors.append("active generation path mismatch")
        if stable_manifest.get("active_generation_manifest_sha256") != active_digest:
            errors.append("active generation digest mismatch")
        if stable_manifest.get("committing_transaction_id") != active_metadata.get("transaction_id"):
            errors.append("active manifest/transaction identity mismatch")
    unfinished = pending_transactions(root)
    if unfinished:
        errors.append("recovery_required: " + ", ".join(path.name for path in unfinished))
    for directory in sorted((root / "transactions").iterdir()) if (root / "transactions").is_dir() else []:
        if not directory.is_dir():
            continue
        journal_path = directory / "journal.json"
        if not journal_path.is_file():
            errors.append(f"{directory.name}: transaction journal missing"); continue
        try:
            journal = read_json(journal_path)
            for error in catalog.validate(journal, "transaction-v2.schema.json"):
                errors.append(f"{directory.name} journal schema {error}")
            if journal.get("format") != TRANSACTION_FORMAT:
                errors.append(f"{directory.name}: journal format mismatch")
            if journal.get("transaction_id") != directory.name:
                errors.append(f"{directory.name}: journal identity mismatch")
        except ContinuityError as exc:
            errors.append(f"{directory.name}: {exc}")
    collections = {
        "episodes": _physical_jsonl(active_path / "episodes.jsonl") if active else [],
        "state": _physical_jsonl(active_path / "state.jsonl") if active else [],
        "proposals": _physical_jsonl(active_path / "proposals.jsonl") if active else [],
    }
    all_rows = [row for values in collections.values() for row in values]
    ids = [row.get("id") for row in all_rows]
    duplicate = sorted({value for value in ids if value and ids.count(value) > 1})
    if any(not isinstance(value, str) or not value for value in ids):
        errors.append("every active canonical row requires an ID")
    if duplicate:
        errors.append("duplicate active canonical IDs: " + ", ".join(duplicate))
    scope = stable_manifest.get("scope") or {}
    for name, rows in collections.items():
        for index, row in enumerate(rows, 1):
            rid = row.get("id") or f"{name}[{index}]"
            for error in catalog.validate(row, SCHEMAS[name]):
                errors.append(f"{rid} schema {error}")
            if name == "episodes":
                for error in legacy_content_provenance_errors(row):
                    errors.append(f"{rid}: {error}")
            if not scope_within_manifest(row.get("scope"), scope):
                errors.append(f"{rid}: scope escapes workspace")
    _validate_references(collections, errors)
    receipts = _physical_jsonl(active_path / "receipts.jsonl") if active else []
    idempotency = _physical_jsonl(active_path / "idempotency.jsonl") if active else []
    receipt_ids = {row.get("id") for row in receipts}
    transaction_ids: set[str] = set()
    for row in receipts:
        for error in catalog.validate(row, "receipt-v2.schema.json"):
            errors.append(f"receipt {row.get('id')} schema {error}")
        if row.get("transaction_id") in transaction_ids:
            errors.append(f"duplicate canonical transaction receipt: {row.get('transaction_id')}")
        transaction_ids.add(row.get("transaction_id"))
        if contains_secret(dump_canonical(row)):
            errors.append(f"receipt {row.get('id')}: secret-shaped material")
    namespaces: set[tuple[Any, Any, Any]] = set()
    for row in idempotency:
        for error in catalog.validate(row, "idempotency-v1.schema.json"):
            errors.append(f"idempotency {row.get('idempotency_key')} schema {error}")
        namespace = (row.get("workspace_id"), row.get("operation_family"), row.get("idempotency_key"))
        if namespace in namespaces:
            errors.append(f"duplicate idempotency namespace: {namespace[1:]}")
        namespaces.add(namespace)
        if row.get("receipt_id") not in receipt_ids:
            errors.append(f"idempotency {row.get('idempotency_key')}: missing receipt")
        result = row.get("result")
        if not isinstance(result, dict) or __import__("hashlib").sha256(dump_canonical(result).encode("utf-8")).hexdigest() != row.get("result_digest"):
            errors.append(f"idempotency {row.get('idempotency_key')}: result digest mismatch")
    if manifest.get("capabilities", {}).get("semantic_ranking") is False:
        notes.append("semantic ranking unavailable; deterministic compilation remains valid")
    source_after = tree_digest(root)
    if source_after != source_before:
        errors.append("read-only validation changed or raced source bytes")
    return {
        "format": "cd-continuity-validation/v2", "workspace": str(root), "workspace_id": manifest.get("workspace_id"),
        "workspace_format": FORMAT, "compatibility_mode": "v2_native", "observed_generation": manifest.get("generation"),
        "status": "valid" if not errors else "invalid", "errors": errors, "warnings": warnings, "capability_notes": notes,
        "source_tree_sha256_before": source_before, "source_tree_sha256_after": source_after, "source_mutated": False,
        "counts": {"generations": len(generations), "episodes": len(collections["episodes"]), "state": len(collections["state"]), "proposals": len(collections["proposals"]), "receipts": len(receipts), "idempotency": len(idempotency), "unfinished_transactions": len(unfinished)},
    }


def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    source_before = tree_digest(root)
    manifest = read_json(root / "manifest.json")
    observed = manifest.get("format")
    if observed == LEGACY_FORMAT:
        return _v1_validate(root, manifest, source_before)
    if observed == FORMAT:
        return _validate_v2(root, manifest, source_before)
    raise ContinuityError("Unsupported workspace major format", "version_unsupported")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("workspace"); p.add_argument("--json", action="store_true"); return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv); report = validate(Path(args.workspace).expanduser().resolve())
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"{report['status'].upper()}: {report['workspace']}")
            for kind in ("errors", "warnings", "capability_notes"):
                for item in report[kind]: print(kind[:-1].upper() + ": " + item)
            print("COUNTS: " + json.dumps(report["counts"], sort_keys=True))
        return 0 if report["status"] in {"valid", "valid_with_known_limits"} else 1
    except (ContinuityError, SchemaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
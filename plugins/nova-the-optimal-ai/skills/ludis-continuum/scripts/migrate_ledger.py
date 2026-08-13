from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from ledgerlib import (
    KNOWN_OBJECT_KINDS,
    LEDGER_FORMAT_V2,
    campaign_id_from_seed,
    detect_format,
    is_valid_id,
    validate,
)

LEGACY_TOP_LEVEL = {
    "ludis_version", "updated", "campaign", "table_contract", "objects",
    "sessions", "approvals", "publication", "next_prep",
}
LEGACY_CAMPAIGN_FIELDS = {"id", "title", "premise", "system", "edition", "tier", "current_horizon"}
LEGACY_TABLE_FIELDS = {"player_preferences", "lines", "veils", "other_boundaries"}
LEGACY_OBJECT_FIELDS = {
    "id", "kind", "status", "visibility", "authority", "provenance", "confidence", "tenure",
    "title", "summary", "content", "claims", "links", "asset_ids", "contradicts", "tags",
}
LEGACY_SESSION_FIELDS = {"id", "scheduled_for", "status", "title", "notes", "links"}
LEGACY_PUBLICATION_FIELDS = {"status"}


@dataclass(frozen=True)
class MigrationReport:
    source_format: str
    destination_format: str
    campaign_id: str
    unknown_fields: tuple[str, ...]
    quarantined_object_ids: tuple[str, ...]
    legacy_player_approval_ids: tuple[str, ...]
    current_approvals_created: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _split_fields(record: dict[str, Any], known: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    current = {key: copy.deepcopy(value) for key, value in record.items() if key in known}
    legacy = {key: copy.deepcopy(value) for key, value in record.items() if key not in known}
    return current, legacy


def _attach_legacy(target: dict[str, Any], legacy: dict[str, Any]) -> None:
    if legacy:
        target["extensions"] = {"legacy_v0_1": legacy}


def _resolve_campaign_id(campaign: dict[str, Any], campaign_id: Optional[str], campaign_seed: Optional[str]) -> str:
    supplied: Optional[str] = None
    if campaign_id is not None:
        supplied = campaign_id
    elif campaign_seed is not None:
        supplied = campaign_id_from_seed(campaign_seed)

    existing = campaign.get("id")
    if existing is not None:
        if not is_valid_id(existing):
            raise ValueError("legacy campaign.id is invalid; resolve it explicitly in the source before migration")
        if supplied is not None and supplied != existing:
            raise ValueError("supplied campaign id does not match the existing legacy campaign.id")
        return existing

    if supplied is None:
        raise ValueError("legacy ledger has no campaign.id; supply --campaign-id or --campaign-seed")
    if not is_valid_id(supplied):
        raise ValueError("campaign id must use lowercase letters, digits, dots, underscores, or hyphens")
    return supplied


def migrate_legacy(
    value: dict[str, Any],
    *,
    campaign_id: Optional[str] = None,
    campaign_seed: Optional[str] = None,
) -> tuple[dict[str, Any], MigrationReport]:
    if campaign_id is not None and campaign_seed is not None:
        raise ValueError("choose campaign_id or campaign_seed, not both")
    if detect_format(value) != "legacy_v0_1":
        raise ValueError("migration accepts only a ludis_version 0.1.0 ledger")
    legacy_errors = validate(value)
    if legacy_errors:
        raise ValueError("legacy ledger is invalid: " + "; ".join(legacy_errors))

    campaign_source = value.get("campaign")
    if not isinstance(campaign_source, dict):
        raise ValueError("legacy campaign must be an object")
    resolved_campaign_id = _resolve_campaign_id(campaign_source, campaign_id, campaign_seed)

    unknown_fields: list[str] = []
    quarantined: list[str] = []
    legacy_player_approvals: list[str] = []

    campaign, campaign_legacy = _split_fields(campaign_source, LEGACY_CAMPAIGN_FIELDS)
    campaign["id"] = resolved_campaign_id
    if campaign_legacy:
        unknown_fields.extend(f"campaign.{key}" for key in sorted(campaign_legacy))
        _attach_legacy(campaign, campaign_legacy)

    table_source = value.get("table_contract")
    if not isinstance(table_source, dict):
        raise ValueError("legacy table_contract must be an object")
    table_contract, table_legacy = _split_fields(table_source, LEGACY_TABLE_FIELDS)
    for field in sorted(LEGACY_TABLE_FIELDS):
        table_contract.setdefault(field, [])
    if table_legacy:
        unknown_fields.extend(f"table_contract.{key}" for key in sorted(table_legacy))
        _attach_legacy(table_contract, table_legacy)

    objects: list[dict[str, Any]] = []
    for index, source in enumerate(value.get("objects", [])):
        if not isinstance(source, dict):
            raise ValueError(f"objects[{index}] must be an object")
        current, legacy = _split_fields(source, LEGACY_OBJECT_FIELDS)
        current.setdefault("links", [])
        current.setdefault("asset_ids", [])
        kind = current.get("kind")
        if kind in KNOWN_OBJECT_KINDS:
            current["export_eligibility"] = "eligible"
        else:
            current["export_eligibility"] = "quarantined_unmapped"
            quarantined.append(str(current.get("id", f"objects[{index}]")))
        if source.get("player_export_approved") is True:
            legacy_player_approvals.append(str(current.get("id", f"objects[{index}]")))
        if legacy:
            unknown_fields.extend(f"objects[{index}].{key}" for key in sorted(legacy))
            _attach_legacy(current, legacy)
        objects.append(current)

    sessions: list[dict[str, Any]] = []
    for index, source in enumerate(value.get("sessions", [])):
        if not isinstance(source, dict):
            raise ValueError(f"sessions[{index}] must be an object")
        current, legacy = _split_fields(source, LEGACY_SESSION_FIELDS)
        if legacy:
            unknown_fields.extend(f"sessions[{index}].{key}" for key in sorted(legacy))
            _attach_legacy(current, legacy)
        sessions.append(current)

    publication_source = value.get("publication")
    if not isinstance(publication_source, dict):
        raise ValueError("legacy publication must be an object")
    publication, publication_legacy = _split_fields(publication_source, LEGACY_PUBLICATION_FIELDS)
    publication.setdefault("status", "private_draft")
    if publication_legacy:
        unknown_fields.extend(f"publication.{key}" for key in sorted(publication_legacy))
        _attach_legacy(publication, publication_legacy)

    unknown_top = {key: copy.deepcopy(value[key]) for key in sorted(set(value) - LEGACY_TOP_LEVEL)}
    unknown_fields.extend(f"ledger.{key}" for key in unknown_top)
    legacy_envelope: dict[str, Any] = {"ludis_version": value["ludis_version"]}
    if value.get("approvals"):
        legacy_envelope["approvals"] = copy.deepcopy(value["approvals"])
    if unknown_top:
        legacy_envelope["unmapped"] = unknown_top

    migrated: dict[str, Any] = {
        "format": LEDGER_FORMAT_V2,
        "campaign": campaign,
        "table_contract": table_contract,
        "objects": objects,
        "assets": [],
        "sessions": sessions,
        # Legacy approval records and player_export_approved booleans are evidence
        # about the old ledger, not current exact-candidate authority.
        "approvals": [],
        "publication": publication,
        "extensions": {"legacy_v0_1": legacy_envelope},
    }
    if "updated" in value:
        migrated["updated"] = copy.deepcopy(value["updated"])
    if "next_prep" in value:
        migrated["next_prep"] = copy.deepcopy(value["next_prep"])

    migrated_errors = validate(migrated)
    if migrated_errors:
        raise ValueError("migration result is invalid: " + "; ".join(migrated_errors))

    report = MigrationReport(
        source_format="legacy_v0_1",
        destination_format=LEDGER_FORMAT_V2,
        campaign_id=resolved_campaign_id,
        unknown_fields=tuple(sorted(unknown_fields)),
        quarantined_object_ids=tuple(quarantined),
        legacy_player_approval_ids=tuple(legacy_player_approvals),
    )
    return migrated, report


def default_source_copy_path(output: Path) -> Path:
    return output.with_name(output.stem + ".source-v0.1" + output.suffix)


def write_migration(
    source: Path,
    output: Path,
    *,
    source_copy: Optional[Path] = None,
    campaign_id: Optional[str] = None,
    campaign_seed: Optional[str] = None,
) -> tuple[MigrationReport, Path]:
    source = source.resolve()
    output = output.resolve()
    source_copy = (source_copy or default_source_copy_path(output)).resolve()
    if output == source:
        raise ValueError("in-place migration is forbidden; choose a new --output path")
    if source_copy in {source, output}:
        raise ValueError("source-copy path must differ from source and output")
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    if source_copy.exists():
        raise FileExistsError(f"source copy already exists: {source_copy}")

    source_bytes = source.read_bytes()
    value = json.loads(source_bytes.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ledger root must be an object")
    migrated, report = migrate_legacy(value, campaign_id=campaign_id, campaign_seed=campaign_seed)
    migrated_bytes = (json.dumps(migrated, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    source_copy.parent.mkdir(parents=True, exist_ok=True)
    with source_copy.open("xb") as handle:
        handle.write(source_bytes)
    try:
        with output.open("xb") as handle:
            handle.write(migrated_bytes)
    except Exception:
        # The copy was created by this call and the migration did not complete.
        source_copy.unlink(missing_ok=True)
        raise
    return report, source_copy


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or write a non-destructive Ludis 0.1 -> v2 ledger migration. Dry-run is the default."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, help="Write v2 JSON here. Omit for a dry run.")
    parser.add_argument("--source-copy", type=Path, help="Exact-byte legacy copy path; requires --output.")
    identity = parser.add_mutually_exclusive_group()
    identity.add_argument("--campaign-id")
    identity.add_argument("--campaign-seed", help="Owner-supplied seed used only to derive a deterministic id.")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.source_copy is not None and args.output is None:
        print("FAIL: --source-copy requires --output")
        return 2
    try:
        if args.output is None:
            raw = args.source.read_bytes()
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("ledger root must be an object")
            _, report = migrate_legacy(value, campaign_id=args.campaign_id, campaign_seed=args.campaign_seed)
            print("DRY RUN: no files written")
        else:
            report, source_copy = write_migration(
                args.source,
                args.output,
                source_copy=args.source_copy,
                campaign_id=args.campaign_id,
                campaign_seed=args.campaign_seed,
            )
            print(f"PASS: wrote {args.output.resolve()}")
            print(f"PASS: preserved exact source bytes at {source_copy}")
        print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
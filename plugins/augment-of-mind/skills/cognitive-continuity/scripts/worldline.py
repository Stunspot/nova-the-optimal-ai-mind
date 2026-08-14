#!/usr/bin/env python3
"""Deterministic Worldline projections over Cognitive Continuity v1/v2."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from eligibility_policy import POLICY_ID, contains_secret_data, evaluate, sanitize_object, sanitize_text
from schema_validation import SchemaCatalog, SchemaError
from workspace_runtime import (
    FORMAT, IMPLEMENTATION_VERSION, LEGACY_FORMAT, ContinuityError, dump_canonical, generation_path,
    open_snapshot, open_workspace, read_json, read_jsonl, sha256_bytes, sha256_file,
)

REQUEST_FORMAT = "cd-worldline-request/v1"
VIEW_FORMAT = "cd-worldline-view/v1"
RUNTIME_VERSION = IMPLEMENTATION_VERSION
SCHEMAS = Path(__file__).resolve().parents[1] / "assets" / "schemas"
VALUE_BOUNDARY = (
    "This expiring view reports source-linked Continuity state. It does not authorize action, "
    "persist a checkpoint, prove completion, verification, publication, model attention, or user value."
)
LOST_GUARANTEE = (
    "No durable Continuity write, receipt, generation, freshness, correction, forgetting, "
    "or later-session availability is established."
)
WORDS = re.compile(r"[a-z0-9]+")
COMPLETE = re.compile(r"(?i)\b(?:complete|completed|done|finished|closed|verified|published|released)\b")
PHASE_TAGS = {"phase", "project-phase", "worldline:phase"}
STATUS_TAGS = {"status", "project-status", "worldline:status"}
BLOCKER_TAGS = {"blocker", "blocked", "worldline:blocker"}
NEXT_TAGS = {"next", "next-action", "next_action", "worldline:next-action"}


def _validate(value: Any, schema: str, code: str = "schema_invalid") -> None:
    errors = SchemaCatalog(SCHEMAS).validate(value, schema)
    if errors:
        raise ContinuityError(f"{schema} validation failed: " + "; ".join(errors[:5]), code)


def _time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContinuityError("Invalid as_of", "schema_invalid") from exc
    if result.tzinfo is None:
        raise ContinuityError("as_of requires a timezone", "schema_invalid")
    return result.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _words(value: str | None) -> set[str]:
    return {part for part in WORDS.findall((value or "").casefold()) if len(part) > 2}


def _scope_allowed(bound: Any, requested: dict[str, Any]) -> bool:
    if not isinstance(bound, dict):
        return False
    for key in ("user", "agent", "project"):
        if bound.get(key) != "*" and bound.get(key) != requested.get(key):
            return False
    return bound.get("thread") in (None, "*") or bound.get("thread") == requested.get("thread")


def _writable(root: Path) -> bool:
    mask = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    try:
        manifest = root / "manifest.json"
        return bool(root.stat().st_mode & mask) and bool(manifest.stat().st_mode & mask) and os.access(root, os.W_OK)
    except OSError:
        return False


def _snapshot(request: dict[str, Any], registry_path: Path | None) -> dict[str, Any]:
    choice = request["workspace"]
    root, _ = open_workspace(
        choice.get("path"), writable=False, mode=choice["selection_mode"],
        registry_path=registry_path, grant_id=choice.get("grant_id"),
    )
    manifest = read_json(root / "manifest.json")
    observed = manifest.get("format")
    if observed == FORMAT:
        manifest, _ = open_snapshot(root)
        mode = "v2_native"
        schema_version: int | str | None = manifest.get("workspace_schema_version")
        generation: int | None = int(manifest["generation"])
        manifest_schema = "continuity-manifest-v2.schema.json"
    elif observed == LEGACY_FORMAT:
        mode = "v1_read_only"
        schema_version = manifest.get("version")
        generation = None
        manifest_schema = "continuity-manifest.schema.json"
    else:
        raise ContinuityError(f"Unsupported Continuity workspace format: {observed!r}", "version_unsupported")
    _validate(manifest, manifest_schema, "workspace_invalid")
    if not _scope_allowed(manifest.get("scope"), request["scope"]):
        raise ContinuityError("Requested scope is outside workspace scope", "scope_denied")
    return {
        "root": root,
        "manifest": manifest,
        "episodes": read_jsonl(root / "episodes" / "events.jsonl"),
        "records": read_jsonl(root / "state" / "records.jsonl"),
        "mode": mode,
        "schema_version": schema_version,
        "generation": generation,
        "manifest_sha256": sha256_file(root / "manifest.json"),
        "source_writable": _writable(root),
    }


def _score(row: dict[str, Any], task: set[str], required: set[str]) -> tuple[int, str, str]:
    overlap = len(task & _words(str(row.get("content") or "")))
    bonus = 1_000_000 if str(row.get("id")) in required else 0
    return bonus + overlap * 100, str(row.get("recorded_at") or ""), str(row.get("id") or "")


def _item(row: dict[str, Any], episodes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sources = sorted({str(value) for value in row.get("source_ids") or []})
    outcome = any(episodes.get(source, {}).get("type") == "outcome" for source in sources)
    return {
        "id": str(row["id"]), "kind": str(row.get("kind") or "state"),
        "statement": str(row.get("content") or ""), "recorded_at": row.get("recorded_at"),
        "authority": row.get("authority"), "confidence": row.get("confidence"),
        "source_ids": sources, "supersedes": sorted(row.get("supersedes") or []),
        "conflicts_with": sorted(row.get("conflicts_with") or []),
        "evidence_state": "completion_evidence_present" if outcome else "source_supported",
    }


def _eligible(snapshot: dict[str, Any], request: dict[str, Any], deadline: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str], dict[str, int], bool]:
    v1 = snapshot["manifest"]["format"] == LEGACY_FORMAT
    episode_schema = "episode.schema.json" if v1 else "episode-v2.schema.json"
    state_schema = "state-record.schema.json" if v1 else "state-record-v2.schema.json"
    catalog = SchemaCatalog(SCHEMAS)
    for row in snapshot["episodes"]:
        if catalog.validate(row, episode_schema):
            raise ContinuityError("Episode ledger contains schema-invalid state", "workspace_invalid")
    for row in snapshot["records"]:
        if catalog.validate(row, state_schema):
            raise ContinuityError("State ledger contains schema-invalid state", "workspace_invalid")
    now = _time(request["as_of"])
    environment = request["environment"]
    raw_episode_ids = {str(row["id"]) for row in snapshot["episodes"]}
    unreachable = set(request["unreachable_source_ids"])
    omissions: dict[str, int] = {}
    omitted: set[str] = set()
    partial = False

    def reject(row: dict[str, Any], reason: str) -> None:
        omissions[reason] = omissions.get(reason, 0) + 1
        omitted.add(str(row.get("id") or ""))

    episodes: list[dict[str, Any]] = []
    for row in snapshot["episodes"]:
        if time.monotonic() >= deadline:
            partial = True
            reject(row, "deadline_exceeded")
            continue
        allowed, reason, clean = evaluate(
            row, scope=request["scope"], ceiling=request["sensitivity_ceiling"], now=now,
            environment=environment["name"], environment_version=environment["version"],
            episode_ids=raw_episode_ids, unreachable_source_ids=unreachable,
            allowed_statuses=(None, "current"), schema_valid=True,
        )
        episodes.append(clean) if allowed and clean is not None else reject(row, reason)
    eligible_episode_ids = {str(row["id"]) for row in episodes}
    records: list[dict[str, Any]] = []
    for row in snapshot["records"]:
        if time.monotonic() >= deadline:
            partial = True
            reject(row, "deadline_exceeded")
            continue
        allowed, reason, clean = evaluate(
            row, scope=request["scope"], ceiling=request["sensitivity_ceiling"], now=now,
            environment=environment["name"], environment_version=environment["version"],
            episode_ids=eligible_episode_ids, unreachable_source_ids=unreachable,
            allowed_statuses=("current", "conflicted"), schema_valid=True,
        )
        records.append(clean) if allowed and clean is not None else reject(row, reason)
    all_ids = raw_episode_ids | {str(row["id"]) for row in snapshot["records"]}
    eligible_ids = eligible_episode_ids | {str(row["id"]) for row in records}
    missing = sorted(set(request["required_ids"]) - all_ids)
    ineligible = sorted((set(request["required_ids"]) & all_ids) - eligible_ids)
    if missing:
        raise ContinuityError("Required IDs are absent: " + ", ".join(missing), "required_record_missing")
    if ineligible:
        raise ContinuityError("Required IDs are ineligible: " + ", ".join(ineligible), "required_record_ineligible")
    return episodes, records, omitted, omissions, partial



def _portable(request: dict[str, Any], error: ContinuityError) -> dict[str, Any]:
    material = request.get("portable_material")
    required = set(request["required_ids"])
    if not isinstance(material, dict):
        raise error
    declared = {str(value) for value in material.get("source_ids") or []}
    pointer = material.get("resumption_pointer")
    useful = sum(len(material.get(name) or []) for name in ("decisions", "commitments", "blockers", "next_actions"))
    observed = set(declared)
    valid = bool(declared and isinstance(pointer, dict) and pointer.get("text") and pointer.get("source_ids") and useful)
    for name in ("decisions", "commitments", "blockers", "next_actions", "artifact_locators", "chronology", "conflicts"):
        for item in material.get(name) or []:
            sources = {str(value) for value in item.get("source_ids") or []} if isinstance(item, dict) else set()
            valid = valid and bool(sources) and sources.issubset(declared)
            if isinstance(item, dict) and item.get("id"):
                observed.add(str(item["id"]))
    if isinstance(pointer, dict):
        valid = valid and set(pointer.get("source_ids") or []).issubset(declared)
        observed.update(str(value) for value in pointer.get("record_ids") or [])
    if not valid or not required.issubset(observed):
        raise error
    material = sanitize_object(material)
    categories = {name: [] for name in ("decisions", "commitments", "blockers", "next_actions", "artifact_locators", "chronology", "conflicts")}
    kinds = {"decisions": "decision", "commitments": "commitment", "blockers": "blocker", "next_actions": "next_action"}
    for name, kind in kinds.items():
        for source in material[name]:
            categories[name].append({
                "id": source["id"], "kind": kind, "statement": source["statement"],
                "recorded_at": source.get("recorded_at"), "authority": source.get("authority"),
                "confidence": None, "source_ids": sorted(source["source_ids"]),
                "supersedes": [], "conflicts_with": sorted(source.get("conflicts_with") or []),
                "evidence_state": "caller_supplied_unverified",
            })
    for source in material["artifact_locators"]:
        categories["artifact_locators"].append({
            "id": source["id"], "locator": source["locator"], "custody": "source_owned",
            "owner": source["owner"], "source_ids": sorted(source["source_ids"]), "recorded_at": None,
        })
    for source in material["chronology"]:
        categories["chronology"].append({
            "id": source["id"], "item_type": "caller_material", "event_type": source["event_type"],
            "at": source["at"], "summary": source["summary"], "source_ids": sorted(source["source_ids"]),
        })
    for source in material["conflicts"]:
        categories["conflicts"].append({
            "id": source["id"], "statement": source["statement"],
            "record_ids": sorted({source["id"], *source.get("conflicts_with", [])}),
            "source_ids": sorted(source["source_ids"]),
        })
    availability = "missing" if error.code in {"selector_missing", "workspace_missing"} else (
        "unsupported" if error.code == "version_unsupported" else
        "invalid" if error.code in {"workspace_invalid", "recovery_required", "snapshot_changed"} else "unavailable"
    )
    view = _base(request, None, ["caller_material_not_continuity_verified", "portable_checkpoint_unpersisted", error.code], False)
    view.update({
        "status": "degraded",
        "durability": {
            "source_state": "caller_material_only", "source_writable": None,
            "view_persisted": False, "portable": True, "save_claim": False,
            "guarantee_lost": LOST_GUARANTEE,
        },
        "workspace": {
            "availability": availability, "compatibility_mode": "portable_no_store",
            "workspace_id": None, "workspace_format": None, "workspace_schema_version": None,
            "generation": None, "manifest_sha256": None,
        },
        "compiler": {
            "runtime_id": "cd-worldline-runtime/v1", "runtime_version": RUNTIME_VERSION,
            "schema_id": "cd-worldline-view/v1", "mode": "portable_deterministic",
            "generation_retry_count": 0,
        },
        "resumption_pointer": {
            "state": "grounded", "text": material["resumption_pointer"]["text"],
            "source_ids": sorted(material["resumption_pointer"]["source_ids"]),
            "record_ids": sorted(material["resumption_pointer"]["record_ids"]),
        },
    })
    view = _budget(view, categories, None, None, set(), {}, request)
    view["source_ids"] = sorted(set(view["source_ids"]) | declared)
    return _finish(view, request["budget"])


def _base(request: dict[str, Any], snapshot: dict[str, Any] | None, degradation: list[str], partial: bool) -> dict[str, Any]:
    if snapshot is None:
        workspace = {
            "availability": "unavailable", "compatibility_mode": "portable_no_store",
            "workspace_id": None, "workspace_format": None, "workspace_schema_version": None,
            "generation": None, "manifest_sha256": None,
        }
        durability = {
            "source_state": "caller_material_only", "source_writable": None,
            "view_persisted": False, "portable": True, "save_claim": False,
            "guarantee_lost": LOST_GUARANTEE,
        }
        compiler_mode = "portable_deterministic"
    else:
        manifest = snapshot["manifest"]
        v1 = snapshot["mode"] == "v1_read_only"
        workspace = {
            "availability": "available", "compatibility_mode": snapshot["mode"],
            "workspace_id": manifest.get("workspace_id"), "workspace_format": manifest.get("format"),
            "workspace_schema_version": snapshot["schema_version"], "generation": snapshot["generation"],
            "manifest_sha256": snapshot["manifest_sha256"],
        }
        durability = {
            "source_state": "durable_v1_read_only" if v1 else "durable_v2",
            "source_writable": snapshot["source_writable"], "view_persisted": False,
            "portable": False, "save_claim": False, "guarantee_lost": None,
        }
        compiler_mode = "deterministic"
        if v1:
            degradation.append("v1_read_only_compatibility")
        if not snapshot["source_writable"]:
            degradation.append("source_not_writable_query_only")
    return {
        "format": VIEW_FORMAT, "view_id": "WLV-" + "0" * 24,
        "request_id": request["request_id"], "correlation_id": request["correlation_id"],
        "operation": "worldline.compile", "requested_mode": request["mode"],
        "status": "partial" if partial else ("degraded" if degradation else "ok"),
        "scope": request["scope"], "as_of": request["as_of"],
        "expires_at": _iso(_time(request["as_of"]) + timedelta(minutes=request["expiry_minutes"])),
        "durability": durability, "workspace": workspace, "policy_version": POLICY_ID,
        "compiler": {
            "runtime_id": "cd-worldline-runtime/v1", "runtime_version": RUNTIME_VERSION,
            "schema_id": "cd-worldline-view/v1", "mode": compiler_mode,
            "generation_retry_count": 0,
        },
        "current_phase": None, "current_status": None, "decisions": [], "commitments": [],
        "blockers": [], "next_actions": [], "artifact_locators": [], "chronology": [],
        "conflicts": [], "source_ids": [], "omitted_ids": [], "omitted_id_count": 0,
        "omission_counts": {}, "degradation": sorted(set(degradation)),
        "resumption_pointer": {"state": "unavailable", "text": None, "source_ids": [], "record_ids": []},
        "counts": {
            "candidate_records": 0, "candidate_episodes": 0, "eligible_records": 0,
            "eligible_episodes": 0, "selected_material": 0, "conflicts": 0,
        },
        "value_boundary": VALUE_BOUNDARY,
    }


def _finish(view: dict[str, Any], budget: int) -> dict[str, Any]:
    seed = dict(view)
    seed["view_id"] = "WLV-" + "0" * 24
    view["view_id"] = "WLV-" + sha256_bytes(dump_canonical(seed).encode("utf-8"))[:24]
    if len(dump_canonical(view)) > budget:
        raise ContinuityError("Worldline budget cannot hold the view envelope", "budget_exceeded")
    if contains_secret_data(view):
        raise ContinuityError("Worldline view failed final redaction scan", "redaction_rejected")
    _validate(view, "worldline-view.schema.json")
    return view


def _budget(
    view: dict[str, Any], categories: dict[str, list[dict[str, Any]]],
    phase: dict[str, Any] | None, status: dict[str, Any] | None,
    omitted: set[str], omissions: dict[str, int], request: dict[str, Any],
) -> dict[str, Any]:
    budget = request["budget"]
    required = set(request["required_ids"])
    for name, value in (("current_phase", phase), ("current_status", status)):
        if value is not None:
            view[name] = value
    limits = {"resume": 12, "status": 8, "checkpoint": 40, "inspect": 60}
    order = {
        "resume": ("conflicts", "blockers", "next_actions", "commitments", "decisions", "artifact_locators", "chronology"),
        "status": ("conflicts", "blockers", "commitments", "decisions", "next_actions", "artifact_locators", "chronology"),
        "checkpoint": ("decisions", "commitments", "blockers", "next_actions", "artifact_locators", "conflicts", "chronology"),
        "inspect": ("conflicts", "chronology", "decisions", "commitments", "blockers", "next_actions", "artifact_locators"),
    }[request["mode"]]
    for name in order:
        view[name] = list(categories[name][: limits[request["mode"]]])
        for item in categories[name][limits[request["mode"]]:]:
            omitted.add(str(item["id"]))
            omissions["mode_limit"] = omissions.get("mode_limit", 0) + 1

    def sync() -> None:
        source_ids: set[str] = set()
        for current in (view["current_phase"], view["current_status"]):
            if current:
                source_ids.update(current["source_ids"])
        for category in ("decisions", "commitments", "blockers", "next_actions", "artifact_locators", "chronology", "conflicts"):
            for item in view[category]:
                source_ids.update(item["source_ids"])
        view["source_ids"] = sorted(source_ids)
        resume = view["next_actions"][0] if view["next_actions"] else (view["commitments"][0] if view["commitments"] else None)
        view["resumption_pointer"] = (
            {
                "state": "grounded", "text": resume["statement"],
                "source_ids": resume["source_ids"], "record_ids": [resume["id"]],
            }
            if resume else {"state": "unavailable", "text": None, "source_ids": [], "record_ids": []}
        )
        all_omitted = sorted(value for value in omitted if value and value not in source_ids)
        view["omitted_id_count"] = len(all_omitted)
        view["omitted_ids"] = all_omitted
        view["omission_counts"] = {key: omissions[key] for key in sorted(omissions)}
        selected = sum(len(view[name]) for name in ("decisions", "commitments", "blockers", "next_actions", "artifact_locators", "chronology", "conflicts"))
        view["counts"]["selected_material"] = selected + int(bool(view["current_phase"])) + int(bool(view["current_status"]))
        view["counts"]["conflicts"] = len(view["conflicts"])

    sync()
    while len(dump_canonical(view)) > budget:
        removed = False
        for name in reversed(order):
            for index in range(len(view[name]) - 1, -1, -1):
                item = view[name][index]
                if str(item["id"]) in required or required.intersection(item.get("source_ids") or []):
                    continue
                removed_item = view[name].pop(index)
                omitted.add(str(removed_item["id"]))
                omissions["budget"] = omissions.get("budget", 0) + 1
                removed = True
                break
            if removed:
                break
        if not removed:
            for name in ("current_phase", "current_status"):
                current = view[name]
                if current is not None and str(current["id"]) not in required:
                    omitted.add(str(current["id"]))
                    omissions["budget"] = omissions.get("budget", 0) + 1
                    view[name] = None
                    removed = True
                    break
        if not removed:
            while len(dump_canonical(view)) > budget and view["omitted_ids"]:
                view["omitted_ids"].pop()
            break
        sync()
    return view

def _compile_once(request: dict[str, Any], snapshot: dict[str, Any], deadline: float) -> dict[str, Any]:
    episodes, records, omitted, omissions, partial = _eligible(snapshot, request, deadline)
    task = _words(request["task"])
    required = set(request["required_ids"])
    episodes.sort(key=lambda row: _score(row, task, required), reverse=True)
    records.sort(key=lambda row: _score(row, task, required), reverse=True)
    by_episode = {str(row["id"]): row for row in episodes}
    categories = {name: [] for name in ("decisions", "commitments", "blockers", "next_actions", "artifact_locators", "chronology", "conflicts")}
    classified: set[str] = set()
    phases: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    degradation = ["deadline_exceeded"] if partial else []
    for row in records:
        record_id = str(row["id"])
        tags = {str(value).casefold() for value in row.get("tags") or []}
        if row.get("status") == "conflicted" or row.get("conflicts_with"):
            related = sorted({record_id, *[str(value) for value in row.get("conflicts_with") or []]})
            categories["conflicts"].append({
                "id": "WLC-" + sha256_bytes("|".join(related).encode("utf-8"))[:16],
                "statement": str(row.get("content") or ""), "record_ids": related,
                "source_ids": sorted({str(value) for value in row.get("source_ids") or []}),
            })
            classified.add(record_id)
        if row.get("status") != "current":
            continue
        content = str(row.get("content") or "")
        view_item = _item(row, by_episode)
        if tags & PHASE_TAGS or content.casefold().startswith("phase:"):
            phases.append(view_item); classified.add(record_id)
        if tags & STATUS_TAGS or content.casefold().startswith("status:"):
            if COMPLETE.search(content) and view_item["evidence_state"] != "completion_evidence_present":
                omitted.add(record_id)
                omissions["completion_evidence_missing"] = omissions.get("completion_evidence_missing", 0) + 1
                degradation.append("completion_claim_withheld:" + record_id)
            else:
                statuses.append(view_item); classified.add(record_id)
        kind = row.get("kind")
        if kind == "decision":
            categories["decisions"].append(view_item); classified.add(record_id)
        if kind == "commitment":
            categories["commitments"].append(view_item); classified.add(record_id)
        if kind == "failure" or tags & BLOCKER_TAGS:
            categories["blockers"].append(view_item); classified.add(record_id)
        if kind == "goal" or tags & NEXT_TAGS:
            categories["next_actions"].append(view_item); classified.add(record_id)
    episodes.sort(key=lambda row: (str(row.get("recorded_at") or ""), str(row["id"])))
    for row in episodes:
        episode_id = str(row["id"])
        categories["chronology"].append({
            "id": episode_id, "item_type": "episode", "event_type": str(row.get("type") or "event"),
            "at": row.get("recorded_at"), "summary": str(row.get("content") or ""), "source_ids": [episode_id],
        })
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        locator = source.get("locator")
        if isinstance(locator, str) and locator:
            categories["artifact_locators"].append({
                "id": "WLA-" + sha256_bytes((episode_id + "|" + locator).encode("utf-8"))[:16],
                "locator": locator, "custody": "source_owned", "owner": str(source.get("kind") or "external"),
                "source_ids": [episode_id], "recorded_at": row.get("recorded_at"),
            })
    for row in records:
        record_id = str(row["id"])
        if (request["mode"] == "inspect" or record_id in required) and record_id not in classified:
            categories["chronology"].append({
                "id": record_id, "item_type": "state_record", "event_type": str(row.get("kind") or "state"),
                "at": row.get("recorded_at"), "summary": str(row.get("content") or ""),
                "source_ids": sorted({str(value) for value in row.get("source_ids") or []}),
            })
            classified.add(record_id)
        if record_id not in classified:
            omitted.add(record_id)
            omissions["not_worldline_material"] = omissions.get("not_worldline_material", 0) + 1
    categories["chronology"].sort(key=lambda item: (str(item.get("at") or ""), item["id"]))
    view = _base(request, snapshot, degradation, partial)
    view["counts"].update({
        "candidate_records": len(snapshot["records"]), "candidate_episodes": len(snapshot["episodes"]),
        "eligible_records": len(records), "eligible_episodes": len(episodes),
    })
    return _finish(_budget(view, categories, phases[0] if phases else None, statuses[0] if statuses else None, omitted, omissions, request), request["budget"])


def compile_worldline(request: dict[str, Any], *, registry_path: Path | None = None) -> dict[str, Any]:
    """Compile a read-only Worldline view; never create state or claim a save."""
    _validate(request, "worldline-request.schema.json")
    if contains_secret_data(request):
        raise ContinuityError("Worldline request failed redaction policy", "redaction_rejected")
    request = dict(request)
    request["task"] = sanitize_text(request["task"])
    deadline = time.monotonic() + request["deadline_ms"] / 1000.0
    try:
        snapshot = _snapshot(request, registry_path)
    except ContinuityError as exc:
        return _portable(request, exc)
    if not snapshot["source_writable"] and request.get("portable_material"):
        return _portable(request, ContinuityError("Selected Continuity source is not writable", "workspace_not_writable"))
    first_generation = snapshot["generation"]
    view = _compile_once(request, snapshot, deadline)
    if snapshot["mode"] == "v2_native":
        current = read_json(snapshot["root"] / "manifest.json").get("generation")
        if current != first_generation:
            retry = _snapshot(request, registry_path)
            view = _compile_once(request, retry, deadline)
            final = read_json(retry["root"] / "manifest.json").get("generation")
            if final != retry["generation"]:
                raise ContinuityError("Workspace changed during both Worldline reads", "snapshot_changed")
            view["compiler"]["generation_retry_count"] = 1
            view = _finish(view, request["budget"])
    return view


def _csv(value: str | None) -> list[str]:
    return list(dict.fromkeys(part.strip() for part in (value or "").split(",") if part.strip()))


def _load_json(path: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContinuityError(f"{label} is unavailable or invalid", "schema_invalid") from exc
    if not isinstance(value, dict):
        raise ContinuityError(f"{label} must be an object", "schema_invalid")
    return value


def _request_from_args(args: argparse.Namespace) -> dict[str, Any]:
    as_of = args.as_of or _iso(datetime.now(timezone.utc))
    scope = {"user": args.user, "project": args.project, "agent": args.agent, "thread": args.thread}
    seed = dump_canonical({"mode": args.mode, "task": args.task, "scope": scope, "as_of": as_of})
    request_id = args.request_id or "WLR-" + sha256_bytes(seed.encode("utf-8"))[:16]
    selection = args.selection_mode or ("generic_explicit" if args.workspace else "nova_ambient")
    request = {
        "format": REQUEST_FORMAT, "request_id": request_id,
        "correlation_id": args.correlation_id or request_id, "operation": "worldline.compile",
        "mode": args.mode, "task": args.task, "scope": scope, "authority": args.authority,
        "sensitivity_ceiling": args.sensitivity, "as_of": as_of,
        "expiry_minutes": args.expiry_minutes, "budget": args.budget, "deadline_ms": args.deadline_ms,
        "required_ids": _csv(args.required_ids),
        "workspace": {"selection_mode": selection, "path": args.workspace, "grant_id": args.grant_id},
        "environment": {"name": args.environment, "version": args.environment_version},
        "unreachable_source_ids": _csv(args.unreachable_source_ids),
    }
    if args.portable_material:
        request["portable_material"] = _load_json(args.portable_material, "portable material")
    return request


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--request")
    sub = root.add_subparsers(dest="mode")
    for mode in ("resume", "status", "checkpoint", "inspect"):
        command = sub.add_parser(mode)
        command.add_argument("workspace", nargs="?")
        command.add_argument("--task", required=True)
        command.add_argument("--user", required=True)
        command.add_argument("--project", required=True)
        command.add_argument("--agent", required=True)
        command.add_argument("--thread")
        command.add_argument("--authority", default="user-requested-read")
        command.add_argument("--sensitivity", choices=["ordinary", "limited", "sensitive", "restricted"], default="limited")
        command.add_argument("--as-of")
        command.add_argument("--expiry-minutes", type=int, default=30)
        command.add_argument("--budget", type=int, default=12000)
        command.add_argument("--deadline-ms", type=int, default=5000)
        command.add_argument("--required-ids", default="")
        command.add_argument("--environment")
        command.add_argument("--environment-version")
        command.add_argument("--unreachable-source-ids", default="")
        command.add_argument("--selection-mode", choices=["generic_explicit", "nova_ambient", "nova_explicit_authorized"])
        command.add_argument("--grant-id")
        command.add_argument("--portable-material")
        command.add_argument("--request-id")
        command.add_argument("--correlation-id")
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        if args.request:
            if args.mode:
                raise ContinuityError("--request cannot be combined with a convenience mode", "schema_invalid")
            request = _load_json(args.request, "Worldline request")
        else:
            if not args.mode:
                raise ContinuityError("Provide --request or a Worldline mode", "schema_invalid")
            request = _request_from_args(args)
        print(dump_canonical(compile_worldline(request)))
        return 0
    except (ContinuityError, SchemaError) as exc:
        code = exc.code if isinstance(exc, ContinuityError) else "schema_invalid"
        print(dump_canonical({
            "format": "cd-worldline-error/v1", "status": "error", "code": code, "message": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

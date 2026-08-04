#!/usr/bin/env python3
"""Structural integrity and projection mechanics for Observatory cases.

The guardrail validates syntax, references, capture fields, time order,
coordinate ranges, readiness check presence, and projection invariants. It does
not determine credibility, identity, truth, causation, privacy, legal safety,
editorial approval, or whether a case should be published.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


BOUNDARY = "STRUCTURAL_INTEGRITY_ONLY"
FORMAT = "cd-observatory-case/v1"
PHASES = {"orient", "scoped", "collecting", "preserved", "normalized", "related", "challenged", "watching", "presenting", "review", "handoff"}
POSTURES = {"provisional", "blocked", "reviewable", "watch-ready", "publication-ready"}
COLLECTIONS = ("sources", "captures", "observations", "claims", "events", "entities", "relations", "inferences", "hypotheses", "contradictions", "assessments", "recommendations", "decisions", "outcomes", "artifacts", "checks", "blockers", "history")
INVARIANT_FIELDS = ("id", "kind", "status", "confidence", "uncertainty", "provenance_ids")
SHA_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
UNRESOLVED = {"candidate", "disputed", "open", "provisional", "unresolved", "unverified"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_time(value: Any, field: str, errors: list[str], item_id: str) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        errors.append(f"{item_id}: {field} must be an ISO-8601 string or null")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{item_id}: {field} is not valid ISO-8601")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{item_id}: {field} requires a timezone")
        return None
    return parsed


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise ValueError("URL must use http or https and include a host")
    host = parts.hostname.lower() if parts.hostname else ""
    port = parts.port
    default_port = (parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443)
    netloc = host if not port or default_port else f"{host}:{port}"
    if parts.username or parts.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    tracking = {"fbclid", "gclid", "mc_cid", "mc_eid"}
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in tracking and not key.lower().startswith("utm_")]
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", urlencode(sorted(query)), ""))


def _all_items(case: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    output: list[tuple[str, dict[str, Any]]] = []
    for collection in COLLECTIONS:
        values = case.get(collection, [])
        if isinstance(values, list):
            output.extend((collection, item) for item in values if isinstance(item, dict))
    return output


def validate_case(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if case.get("format") != FORMAT:
        errors.append(f"format must be {FORMAT}")
    for field in ("case_id", "title", "question", "audience_or_decision", "time_horizon", "scope", "collection_authority", "harm_model", "evidence_burden", "stop_condition"):
        if not isinstance(case.get(field), str) or not case.get(field):
            errors.append(f"{field} is required")
    if case.get("phase") not in PHASES:
        errors.append("phase is missing or invalid")
    if case.get("posture") not in POSTURES:
        errors.append("posture is missing or invalid")

    identifiers: set[str] = set()
    items: list[tuple[str, dict[str, Any]]] = []
    for collection in COLLECTIONS:
        values = case.get(collection)
        if not isinstance(values, list):
            errors.append(f"{collection} must be an array")
            continue
        for index, item in enumerate(values):
            if not isinstance(item, dict):
                errors.append(f"{collection}[{index}] must be an object")
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id:
                errors.append(f"{collection}[{index}] requires a stable id")
                continue
            if item_id in identifiers:
                errors.append(f"duplicate id: {item_id}")
            identifiers.add(item_id)
            items.append((collection, item))

    for collection, item in items:
        item_id = item["id"]
        for field, value in item.items():
            if not field.endswith("_ids"):
                continue
            if not isinstance(value, list):
                errors.append(f"{item_id}: {field} must be an array")
                continue
            for reference in value:
                if reference not in identifiers:
                    errors.append(f"{item_id}: dangling {field} reference {reference}")

        for field in ("published_at", "updated_at", "retrieved_at", "event_start", "event_end", "first_seen_at", "last_seen_at"):
            if field in item:
                parse_time(item.get(field), field, errors, item_id)
        first = parse_time(item.get("first_seen_at"), "first_seen_at", [], item_id)
        last = parse_time(item.get("last_seen_at"), "last_seen_at", [], item_id)
        if first and last and first > last:
            errors.append(f"{item_id}: first_seen_at is after last_seen_at")
        start = parse_time(item.get("event_start"), "event_start", [], item_id)
        end = parse_time(item.get("event_end"), "event_end", [], item_id)
        if start and end and start > end:
            errors.append(f"{item_id}: event_start is after event_end")

        if collection == "captures":
            for field in ("source_ids", "original_url", "canonical_url", "retrieved_at", "artifact_path", "sha256", "preservation_status"):
                if field not in item or item.get(field) in (None, "", []):
                    errors.append(f"{item_id}: capture requires {field}")
            try:
                expected = canonical_url(item.get("original_url", ""))
                if item.get("canonical_url") != expected:
                    errors.append(f"{item_id}: canonical_url does not match deterministic normalization")
            except ValueError as exc:
                errors.append(f"{item_id}: {exc}")
            if item.get("preservation_status") == "preserved" and not SHA_RE.fullmatch(str(item.get("sha256", ""))):
                errors.append(f"{item_id}: preserved capture requires a SHA-256 hash")
        location = item.get("location")
        if location is not None:
            if not isinstance(location, dict):
                errors.append(f"{item_id}: location must be an object")
            else:
                latitude, longitude = location.get("latitude"), location.get("longitude")
                if latitude is not None and (not isinstance(latitude, (int, float)) or not -90 <= latitude <= 90):
                    errors.append(f"{item_id}: latitude is outside -90..90")
                if longitude is not None and (not isinstance(longitude, (int, float)) or not -180 <= longitude <= 180):
                    errors.append(f"{item_id}: longitude is outside -180..180")
                if (latitude is None) != (longitude is None):
                    errors.append(f"{item_id}: latitude and longitude must appear together")
                if latitude is None and not location.get("region"):
                    errors.append(f"{item_id}: uncertain location requires a region label")

    next_action = case.get("next_action")
    if not isinstance(next_action, dict):
        errors.append("next_action must be an object")
    else:
        for field in ("action", "owner", "advance_when"):
            if not next_action.get(field):
                errors.append(f"next_action requires {field}")

    passed_checks = {item.get("check_type") for item in case.get("checks", []) if isinstance(item, dict) and item.get("status") == "passed"}
    if case.get("posture") == "watch-ready":
        if not isinstance(case.get("watch"), dict):
            errors.append("watch-ready requires a watch specification")
        for required in ("watch-specification", "baseline-integrity"):
            if required not in passed_checks:
                errors.append(f"watch-ready requires passed {required} check")
    if case.get("posture") == "publication-ready":
        for required in ("provenance", "citation-integrity", "redaction", "editorial-challenge"):
            if required not in passed_checks:
                errors.append(f"publication-ready requires passed {required} check")
        if not any(item.get("artifact_type") == "publication-package" for item in case.get("artifacts", []) if isinstance(item, dict)):
            errors.append("publication-ready requires a named publication-package artifact")
        if publication_blockers(case):
            errors.append("publication-ready is blocked by material unresolved conditions")
    return sorted(set(errors))


def publication_blockers(case: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for item in case.get("blockers", []):
        if isinstance(item, dict) and item.get("status", "open") not in {"closed", "resolved"} and item.get("severity") in {"high", "material"}:
            blockers.append(item.get("id", "unnamed blocker"))
    for entity in case.get("entities", []):
        if isinstance(entity, dict) and entity.get("resolution_status") in {"collision", "unresolved"} and entity.get("material_to_publication", False):
            blockers.append(entity.get("id", "unresolved entity"))
    for claim in case.get("claims", []):
        if isinstance(claim, dict) and claim.get("high_risk", False) and claim.get("human_review") != "approved":
            blockers.append(claim.get("id", "high-risk claim"))
    return sorted(set(blockers))


def common(item: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "id": item["id"],
        "kind": item.get("kind", kind.rstrip("s")),
        "status": item.get("status", "unresolved"),
        "confidence": item.get("confidence", "unrated"),
        "uncertainty": item.get("uncertainty", "not stated"),
        "provenance_ids": item.get("provenance_ids", item.get("source_ids", item.get("capture_ids", []))),
    }


def project_case(case: dict[str, Any]) -> dict[str, Any]:
    ledger: list[dict[str, Any]] = []
    registry: dict[str, dict[str, Any]] = {}
    for collection, item in _all_items(case):
        projected = common(item, collection)
        projected["summary"] = item.get("summary", item.get("statement", item.get("name", item.get("title", ""))))
        ledger.append(projected)
        registry[item["id"]] = projected

    node_collections = {"entities", "events", "claims", "hypotheses", "sources"}
    nodes = [dict(common(item, collection), label=item.get("name", item.get("title", item.get("statement", item["id"])))) for collection, item in _all_items(case) if collection in node_collections]
    edges = []
    for relation in case.get("relations", []):
        if not isinstance(relation, dict):
            continue
        edge = common(relation, "relations")
        edge.update({"from_id": relation.get("from_id"), "to_id": relation.get("to_id"), "relation_type": relation.get("relation_type", "unspecified")})
        edges.append(edge)

    timeline = []
    for collection in ("captures", "events", "claims"):
        for item in case.get(collection, []):
            if not isinstance(item, dict):
                continue
            time_value = item.get("event_start") or item.get("published_at") or item.get("retrieved_at") or item.get("first_seen_at")
            if time_value:
                entry = common(item, collection)
                entry.update({"time": time_value, "time_kind": "event_start" if item.get("event_start") else "published_at" if item.get("published_at") else "retrieved_at" if item.get("retrieved_at") else "first_seen_at", "label": item.get("summary", item.get("statement", item.get("title", item["id"])))})
                timeline.append(entry)
    timeline.sort(key=lambda item: (item["time"], item["id"]))

    features = []
    for collection in ("events", "entities", "observations"):
        for item in case.get(collection, []):
            if not isinstance(item, dict) or not isinstance(item.get("location"), dict):
                continue
            location = item["location"]
            geometry = None
            if location.get("latitude") is not None and location.get("longitude") is not None:
                geometry = {"type": "Point", "coordinates": [location["longitude"], location["latitude"]]}
            properties = common(item, collection)
            properties.update({"label": item.get("summary", item.get("name", item["id"])), "region": location.get("region"), "precision": location.get("precision", "unknown")})
            features.append({"type": "Feature", "id": item["id"], "geometry": geometry, "properties": properties})
    return {
        "ledger": {"format": "cd-observatory-ledger/v1", "case_id": case["case_id"], "items": sorted(ledger, key=lambda item: item["id"])},
        "graph": {"format": "cd-observatory-graph/v1", "case_id": case["case_id"], "nodes": sorted(nodes, key=lambda item: item["id"]), "edges": sorted(edges, key=lambda item: item["id"])},
        "timeline": {"format": "cd-observatory-timeline/v1", "case_id": case["case_id"], "items": timeline},
        "map": {"type": "FeatureCollection", "observatory_format": "cd-observatory-map/v1", "case_id": case["case_id"], "features": sorted(features, key=lambda item: item["id"])},
        "registry": registry,
    }


def verify_projection_invariants(case: dict[str, Any], projections: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    registry = projections["registry"]
    projected: list[dict[str, Any]] = []
    projected.extend(projections["ledger"]["items"])
    projected.extend(projections["graph"]["nodes"])
    projected.extend(projections["graph"]["edges"])
    projected.extend(projections["timeline"]["items"])
    projected.extend(feature["properties"] for feature in projections["map"]["features"])
    for item in projected:
        source = registry.get(item.get("id"))
        if not source:
            errors.append(f"projection contains unknown id {item.get('id')}")
            continue
        for field in INVARIANT_FIELDS:
            if item.get(field) != source.get(field):
                errors.append(f"{item.get('id')}: projection changed invariant {field}")
    return sorted(set(errors))


def semantic_fingerprint(item: dict[str, Any]) -> str:
    ignored = {"retrieved_at", "last_seen_at", "runtime", "generated_at"}
    value = {key: item[key] for key in sorted(item) if key not in ignored}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest().upper()


def delta_report(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    base = {item["id"]: item for _, item in _all_items(baseline)}
    now = {item["id"]: item for _, item in _all_items(current)}
    result = {"newly_observed": [], "materially_changed": [], "corrected_or_superseded": [], "newly_contradicted": [], "no_longer_supported": [], "unchanged": [], "still_unresolved": []}
    for item_id in sorted(set(base) | set(now)):
        before, after = base.get(item_id), now.get(item_id)
        if before is None:
            result["newly_observed"].append(item_id)
        elif after is None:
            result["no_longer_supported"].append(item_id)
            continue
        elif semantic_fingerprint(before) == semantic_fingerprint(after):
            result["unchanged"].append(item_id)
        else:
            result["materially_changed"].append(item_id)
        if after:
            status = after.get("status", "")
            if status in {"corrected", "superseded"} or after.get("supersedes_ids"):
                result["corrected_or_superseded"].append(item_id)
            if status == "contradicted" and (before is None or before.get("status") != "contradicted"):
                result["newly_contradicted"].append(item_id)
            if status in {"unsupported", "withdrawn"}:
                result["no_longer_supported"].append(item_id)
            if status in UNRESOLVED:
                result["still_unresolved"].append(item_id)
    for key in result:
        result[key] = sorted(set(result[key]))
    return {"format": "cd-observatory-delta/v1", "baseline_case_id": baseline.get("case_id"), "current_case_id": current.get("case_id"), "classes": result, "semantic_truth_assessed": False}


def receipt(file_path: Path, source_id: str, capture_id: str, url: str, published_at: str | None, retrieved_at: str | None) -> dict[str, Any]:
    return {
        "id": capture_id,
        "source_ids": [source_id],
        "original_url": url,
        "canonical_url": canonical_url(url),
        "published_at": published_at,
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "artifact_path": file_path.name,
        "sha256": sha256(file_path),
        "preservation_status": "preserved",
        "failure": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-case")
    validate.add_argument("case", type=Path)
    project = commands.add_parser("project")
    project.add_argument("case", type=Path)
    project.add_argument("output", type=Path)
    delta = commands.add_parser("delta")
    delta.add_argument("baseline", type=Path)
    delta.add_argument("current", type=Path)
    delta.add_argument("output", type=Path, nargs="?")
    capture = commands.add_parser("capture-receipt")
    capture.add_argument("file", type=Path)
    capture.add_argument("--source-id", required=True)
    capture.add_argument("--capture-id", required=True)
    capture.add_argument("--url", required=True)
    capture.add_argument("--published-at")
    capture.add_argument("--retrieved-at")
    capture.add_argument("--output", type=Path)
    publication = commands.add_parser("audit-publication")
    publication.add_argument("case", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture-receipt":
            result = receipt(args.file, args.source_id, args.capture_id, args.url, args.published_at, args.retrieved_at)
            if args.output:
                write_json(args.output, result)
            else:
                print(json.dumps(result, indent=2))
            return 0
        if args.command == "delta":
            result = delta_report(load_json(args.baseline), load_json(args.current))
            if args.output:
                write_json(args.output, result)
            else:
                print(json.dumps(result, indent=2))
            return 0
        case = load_json(args.case)
        errors = validate_case(case)
        if args.command == "validate-case":
            result = {"label": BOUNDARY, "valid": not errors, "errors": errors, "semantic_truth_assessed": False}
            print(json.dumps(result, indent=2))
            return 0 if not errors else 1
        if args.command == "audit-publication":
            blockers = publication_blockers(case)
            result = {"label": BOUNDARY, "structurally_publishable": not errors and not blockers, "case_errors": errors, "blockers": blockers, "truth_legality_safety_assessed": False}
            print(json.dumps(result, indent=2))
            return 0 if result["structurally_publishable"] else 1
        if errors:
            print(json.dumps({"label": BOUNDARY, "valid": False, "errors": errors}, indent=2))
            return 1
        projections = project_case(case)
        invariant_errors = verify_projection_invariants(case, projections)
        for name in ("ledger", "graph", "timeline", "map"):
            write_json(args.output / f"{name}.json", projections[name])
        manifest = {"format": "cd-observatory-projection-manifest/v1", "case_id": case["case_id"], "invariant_errors": invariant_errors, "files": [{"path": f"{name}.json", "sha256": sha256(args.output / f"{name}.json")} for name in ("ledger", "graph", "timeline", "map")], "semantic_truth_assessed": False}
        write_json(args.output / "projection-manifest.json", manifest)
        print(json.dumps(manifest, indent=2))
        return 0 if not invariant_errors else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"label": BOUNDARY, "valid": False, "errors": [str(exc)]}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())

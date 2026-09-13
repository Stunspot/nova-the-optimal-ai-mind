#!/usr/bin/env python3
"""Worldline: a bounded, source-linked autobiographical timeline over Continuity."""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import html
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import urlsplit, quote

from eligibility_policy import contains_secret_data, sanitize_text
from schema_validation import SchemaCatalog, SchemaError
from workspace_runtime import (
    FORMAT, LEGACY_FORMAT, IMPLEMENTATION_VERSION, ContinuityError,
    dump_canonical, generation_path, open_workspace, open_snapshot_identity,
    read_json, _read_direct_file_bytes, sha256_bytes, utc_now,
)
from worldline_domain import safe_locator, validate_event, effective_policy

REQUEST_FORMAT = "cd-worldline-request/v2"
VIEW_FORMAT = "cd-worldline-view/v2"
SCHEMAS = Path(__file__).resolve().parents[1] / "assets" / "schemas"
_CATALOG = SchemaCatalog(SCHEMAS)
LEVELS = {"ordinary": 0, "limited": 1, "sensitive": 2, "restricted": 3}


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ContinuityError("A timezone-bearing timestamp is required", "schema_invalid")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContinuityError("Invalid timestamp", "schema_invalid") from exc
    if result.tzinfo is None:
        raise ContinuityError("Timestamp requires a timezone", "schema_invalid")
    return result.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate(value: Any, schema: str) -> None:
    errors = _CATALOG.validate(value, schema)
    if errors:
        raise ContinuityError(f"{schema}: " + "; ".join(errors[:4]), "schema_invalid")


def _choice(value: dict[str, Any]) -> dict[str, Any]:
    result = value.get("workspace") or {}
    if not isinstance(result, dict):
        raise ContinuityError("workspace must be an object", "schema_invalid")
    return {"selection_mode": result.get("selection_mode", "nova_ambient"),
            "path": result.get("path"), "grant_id": result.get("grant_id")}


def _snapshot(value: dict[str, Any], registry_path: Path | None = None) -> dict[str, Any]:
    choice = _choice(value)
    root, token = open_workspace(choice["path"], writable=False,
        mode=choice["selection_mode"], registry_path=registry_path, grant_id=choice["grant_id"])
    metadata = None
    observed = read_json(root / "manifest.json")
    if observed.get("format") == FORMAT:
        manifest, metadata, identity = open_snapshot_identity(root)
        path = generation_path(root, manifest) / "episodes.jsonl"
        payload, _ = _read_direct_file_bytes(path, boundary=root)
        if sha256_bytes(payload) != metadata["members"]["episodes.jsonl"]["sha256"]:
            raise ContinuityError("Episode snapshot changed during read", "snapshot_changed")
        mode = "v2_native"
    elif observed.get("format") == LEGACY_FORMAT:
        manifest = observed
        raw, _ = _read_direct_file_bytes(root / "manifest.json", boundary=root)
        identity = sha256_bytes(raw)
        path = root / "episodes" / "events.jsonl"
        payload, _ = _read_direct_file_bytes(path, boundary=root) if path.exists() else (b"", None)
        mode = "v1_read_only"
    else:
        raise ContinuityError("Unsupported workspace", "version_unsupported")
    try:
        rows = [json.loads(line) for line in payload.decode("utf-8-sig").splitlines() if line.strip()]
    except (ValueError, UnicodeError) as exc:
        raise ContinuityError("Invalid episode snapshot", "workspace_invalid") from exc
    return {"root": root, "manifest": manifest, "identity": identity,
            "rows": rows, "compatibility": mode, "token": token, "metadata": metadata}


def _scope(manifest: dict[str, Any], requested: dict[str, Any]) -> dict[str, Any]:
    bound = manifest.get("scope") or {}
    result = {"user": requested.get("user", bound.get("user")),
              "agent": requested.get("agent", bound.get("agent")),
              "project": requested.get("project"), "thread": requested.get("thread")}
    for key in ("user", "agent"):
        if not isinstance(result[key], str) or not result[key] or result[key] == "*":
            raise ContinuityError(f"An exact {key} is required", "scope_denied")
        if bound.get(key) not in ("*", result[key]):
            raise ContinuityError("Requested owner is outside this workspace", "scope_denied")
    for key in ("project", "thread"):
        wanted, allowed = result[key], bound.get(key)
        if wanted == "*":
            raise ContinuityError("Use an omitted facet to browse all permitted history", "schema_invalid")
        if wanted is not None and (not isinstance(wanted, str) or not wanted):
            raise ContinuityError("Invalid scope facet", "schema_invalid")
        if allowed not in (None, "*"):
            if wanted not in (None, allowed):
                raise ContinuityError("Requested facet is outside this workspace", "scope_denied")
            result[key] = allowed
    return result


def _matches(row: dict[str, Any], scope: dict[str, Any]) -> bool:
    rs = row.get("scope")
    if not isinstance(rs, dict) or any(rs.get(k) != scope[k] for k in ("user", "agent")):
        return False
    return all(scope.get(k) is None or rs.get(k) == scope[k] for k in ("project", "thread"))


def _privacy(row: dict[str, Any], ceiling: str, now: datetime) -> bool:
    if row.get("content") == "[forgotten]" or "forgotten" in (row.get("tags") or []):
        return False
    if LEVELS.get(row.get("sensitivity"), 99) > LEVELS[ceiling]:
        return False
    if row.get("expires_at") and _time(row["expires_at"]) <= now:
        return False
    return not contains_secret_data(row)


def _source(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["locator"] = safe_locator(result["locator"])
    for key in ("label", "owner"):
        result[key] = sanitize_text(str(result[key]))
    return result


def _entry(row: dict[str, Any], root: dict[str, Any], count: int,
           unavailable: set[str]) -> dict[str, Any]:
    event = row.get("worldline_event")
    if event:
        sources = [_source(source) for source in event["sources"]]
        title = sanitize_text(event["title"])
        kind = sanitize_text(event["kind"])
        occurred = event["occurred_at"]
        ended = event["ended_at"]
        basis, precision = event["time_basis"], event["time_precision"]
        topics = [sanitize_text(topic) for topic in event["topics"]]
        related = list(event["related_ids"])
        origin = "native"
    else:
        text = " ".join(str(row.get("content") or "").split())
        title = sanitize_text(text[:179] + "…" if len(text) > 180 else text)
        kind = str(row.get("type") or "episode")
        occurred = row["recorded_at"]
        ended, basis, precision = None, "recorded", "unknown"
        topics, related, sources = [], [], []
        locator = (row.get("source") or {}).get("locator")
        if locator:
            try:
                sources = [{"kind": "other", "locator": safe_locator(locator),
                            "label": "Original source", "owner": "unspecified"}]
            except ContinuityError:
                sources = []
        origin = "legacy_episode"
    scope = {**row["scope"], "thread": row["scope"].get("thread")}
    if scope.get("project") == "*":
        scope["project"] = None
    return {"id": root["id"], "revision_id": row["id"], "origin": origin,
        "source_kind": row["source"]["kind"],
        "title": title, "kind": kind, "occurred_at": occurred, "ended_at": ended,
        "time_basis": basis, "time_precision": precision,
        "first_recorded_at": root["recorded_at"], "recorded_at": row["recorded_at"],
        "scope": scope, "topics": topics, "sources": sources, "related_ids": related,
        "correction_count": count,
        "content_availability": "unavailable" if row["id"] in unavailable or root["id"] in unavailable or "source-unreachable" in row.get("tags", []) or "source-unreachable" in root.get("tags", []) else "unverified"}


def select_worldline_rows(manifest: dict[str, Any], rows: list[dict[str, Any]],
                          request: dict[str, Any], now: datetime) -> tuple[list[dict], dict[str, list[dict]], dict]:
    """Shared historical selection for query and explicit timeline transfer.

    The returned families contain only eligible canonical revisions for returned
    root identities. Association never grants source or deletion authority.
    """
    scope = _scope(manifest, request.get("scope") or {})
    as_of = _time(request.get("as_of") or _iso(now))
    ceiling = request.get("sensitivity_ceiling", "ordinary")
    if ceiling not in LEVELS:
        raise ContinuityError("Invalid sensitivity ceiling", "schema_invalid")
    deadline = request.get("_deadline", float("inf"))
    omissions: Counter = Counter()
    owned: dict[str, dict] = {}
    legacy: list[dict] = []
    for row in rows:
        if time.monotonic() > deadline:
            raise ContinuityError("Timeline selection exceeded its deadline; no complete count is available", "deadline_exceeded")
        if not isinstance(row, dict) or not _matches(row, scope):
            continue
        if "worldline_policy" in row:
            continue
        try:
            schema = "episode-v2.schema.json" if manifest.get("format") == FORMAT else "episode.schema.json"
            _validate(row, schema)
            _time(row["recorded_at"])
            if row.get("worldline_event"):
                validate_event(row["worldline_event"])
                owned[row["id"]] = row
            elif request.get("include_legacy", True):
                legacy.append(row)
        except (ContinuityError, SchemaError, KeyError, TypeError):
            omissions["invalid_owned_record"] += 1
    chains: dict[str, list[dict]] = {}
    # Corrections may only target the same exact scope; crossing or broken chains
    # are withheld rather than projected as invented new events.
    for identifier, row in owned.items():
        path, seen = [], set()
        current = row
        valid = True
        while True:
            if current["id"] in seen:
                valid = False
                break
            seen.add(current["id"])
            path.append(current)
            parents = current["worldline_event"]["supersedes"]
            if not parents:
                break
            parent = owned.get(parents[0])
            if parent is None or parent["scope"] != row["scope"]:
                valid = False
                break
            current = parent
        if not valid:
            omissions["invalid_revision_chain"] += 1
            continue
        root_id = path[-1]["id"]
        existing = chains.setdefault(root_id, [])
        if identifier not in {item["id"] for item in existing}:
            existing.append(row)
    entries: list[dict] = []
    families: dict[str, list[dict]] = {}
    retracted = 0
    unavailable = set(request.get("unreachable_source_ids") or [])
    for root_id, family in chains.items():
        if time.monotonic() > deadline:
            raise ContinuityError("Timeline deadline reached", "deadline_exceeded")
        root = owned[root_id]
        children: dict[str, list[dict]] = {}
        for row in family:
            for parent in row["worldline_event"]["supersedes"]:
                children.setdefault(parent, []).append(row)
        if any(len(values) != 1 for values in children.values()):
            omissions["branched_revision_chain"] += 1
            continue
        ordered = [root]
        while ordered[-1]["id"] in children:
            ordered.append(children[ordered[-1]["id"]][0])
        try:
            # Current privacy is enforced before historical knowledge selection.
            # An old as_of or cursor cannot reveal a now-restricted description.
            if not _privacy(ordered[-1], ceiling, now):
                omissions["privacy_or_retention"] += 1
                continue
            eligible = [row for row in ordered if _time(row["recorded_at"]) <= as_of]
            if not eligible or eligible[0]["id"] != root_id:
                continue
            current = ordered[-1]
            selected = eligible[-1]
            if not _privacy(selected, ceiling, now):
                omissions["privacy_or_retention"] += 1
                continue
            is_retracted = current["worldline_event"]["disposition"] == "retracted"
            if is_retracted:
                retracted += 1
                if request.get("mode") != "inspect":
                    continue
            item = _entry(selected, root, len(eligible) - 1, unavailable)
            item["disposition"] = "retracted" if is_retracted else "recorded"
            if "source-unreachable" in current.get("tags", []):
                item["content_availability"] = "unavailable"
            if _time(item["occurred_at"]) > as_of:
                continue
            entries.append(item)
            families[root_id] = eligible
        except (ContinuityError, KeyError, TypeError):
            omissions["invalid_owned_record"] += 1
    for row in legacy:
        try:
            if not _privacy(row, ceiling, now) or _time(row["recorded_at"]) > as_of:
                continue
            item = _entry(row, row, 0, unavailable)
            item["disposition"] = "recorded"
            entries.append(item)
            families[row["id"]] = [row]
        except (ContinuityError, KeyError, TypeError):
            omissions["invalid_owned_record"] += 1
    permitted_ids = {row["id"] for values in families.values() for row in values}
    for item in entries:
        item["related_ids"] = [identity for identity in item["related_ids"] if identity in permitted_ids]
    start = _time(request["from_time"]) if request.get("from_time") else None
    end = _time(request["to_time"]) if request.get("to_time") else None
    if start and end and start >= end:
        raise ContinuityError("from_time must precede to_time", "schema_invalid")
    words = re.findall(r"\w+", (request.get("search") or "").casefold(), flags=re.UNICODE)
    wanted_topics = {value.casefold() for value in request.get("topics", [])}
    kinds = set(request.get("kinds") or [])
    filtered = []
    for item in entries:
        at = _time(item["occurred_at"])
        corpus = " ".join([item["title"], item["kind"], *item["topics"]]).casefold()
        if start and at < start or end and at >= end:
            continue
        if not all(word in corpus for word in words):
            continue
        if not wanted_topics.issubset({value.casefold() for value in item["topics"]}):
            continue
        if kinds and item["kind"] not in kinds:
            continue
        if request.get("mode") == "inspect" and request.get("event_id") not in (
                item["id"], *[row["id"] for row in families[item["id"]]]):
            continue
        filtered.append(item)
    filtered.sort(key=lambda item: (_time(item["occurred_at"]), item["id"]),
                  reverse=request.get("order", "desc") == "desc")
    visible_families = {item["id"]: families[item["id"]] for item in filtered}
    coverage = {"eligible_events": len(filtered), "native_events": sum(item["origin"] == "native" for item in filtered),
        "legacy_events": sum(item["origin"] == "legacy_episode" for item in filtered),
        "source_link_missing": sum(not item["sources"] for item in filtered), "retracted_families": retracted,
        "omissions": dict(omissions), "complete_for_selected_snapshot": True,
        "history_boundary": "Retained eligible occurrences and labelled legacy episodes; not complete host history."}
    return filtered, visible_families, coverage


def _decode_cursor(value: str) -> dict[str, Any]:
    if not isinstance(value, str) or not 1 <= len(value) <= 4096:
        raise ContinuityError("Invalid timeline cursor", "cursor_invalid")
    try:
        raw = base64.b64decode(value.encode("ascii"), altchars=b"-_", validate=True)
        obj = json.loads(raw)
        body = obj["body"]
        if set(obj) != {"body", "digest"} or obj["digest"] != sha256_bytes(dump_canonical(body).encode("utf-8")):
            raise ValueError("digest")
        if set(body) != {"workspace_id", "generation", "query", "as_of", "last"}:
            raise ValueError("shape")
        if not isinstance(body["last"], list) or len(body["last"]) != 2:
            raise ValueError("key")
        _time(body["as_of"])
        _time(body["last"][0])
        if not isinstance(body["last"][1], str) or len(body["last"][1]) > 200:
            raise ValueError("identity")
        return body
    except (ValueError, TypeError, KeyError, UnicodeError, ContinuityError) as exc:
        raise ContinuityError("Invalid timeline cursor; restart the query", "cursor_invalid") from exc


def _fingerprint(request: dict[str, Any]) -> str:
    omit = {"request_id", "cursor", "page_size", "budget", "deadline_ms"}
    value = {key: val for key, val in request.items() if key not in omit and not key.startswith("_")}
    return sha256_bytes(dump_canonical(value).encode("utf-8"))


def _cursor(snapshot: dict, request: dict, entry: dict) -> str:
    body = {"workspace_id": snapshot["manifest"].get("workspace_id"),
        "generation": snapshot["manifest"].get("generation"), "query": _fingerprint(request),
        "as_of": request["as_of"], "last": [_iso(_time(entry["occurred_at"])), entry["id"]]}
    value = {"body": body, "digest": sha256_bytes(dump_canonical(body).encode("utf-8"))}
    return base64.urlsafe_b64encode(dump_canonical(value).encode("utf-8")).decode("ascii")


def _normalize(value: dict[str, Any], snapshot: dict[str, Any], now: datetime) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContinuityError("Worldline request must be an object", "schema_invalid")
    cursor = _decode_cursor(value["cursor"]) if value.get("cursor") else None
    defaults = {"format": REQUEST_FORMAT, "mode": "browse", "authority": "user-requested-read",
        "as_of": cursor["as_of"] if cursor else _iso(now), "sensitivity_ceiling": "ordinary",
        "from_time": None, "to_time": None, "search": None, "topics": [], "kinds": [],
        "include_legacy": True, "order": "desc", "page_size": 30, "cursor": None,
        "event_id": None, "bucket": "day", "display_offset_minutes": 0,
        "budget": 20000, "deadline_ms": 5000, "unreachable_source_ids": []}
    result = {**defaults, **value}
    result["workspace"] = _choice(value)
    result["scope"] = _scope(snapshot["manifest"], value.get("scope") or {})
    result.setdefault("request_id", "WLT-" + hashlib.sha256(dump_canonical(result).encode("utf-8")).hexdigest()[:16])
    _validate(result, "worldline-request-v2.schema.json")
    if contains_secret_data(result):
        raise ContinuityError("Timeline request failed secret screening", "redaction_rejected")
    if result["mode"] == "inspect" and not result["event_id"]:
        raise ContinuityError("inspect requires an event ID", "schema_invalid")
    if result["mode"] != "inspect" and result["event_id"] is not None:
        raise ContinuityError("event_id is only accepted for inspect", "schema_invalid")
    if _time(result["as_of"]) > now + timedelta(seconds=1):
        raise ContinuityError("as_of cannot claim future experience", "schema_invalid")
    return result


def _buckets(entries: list[dict], request: dict) -> dict:
    buckets, topics, kinds = Counter(), Counter(), Counter()
    offset = timedelta(minutes=request["display_offset_minutes"])
    for entry in entries:
        at = _time(entry["occurred_at"]) + offset
        if request["bucket"] == "month":
            label = at.strftime("%Y-%m")
        elif request["bucket"] == "week":
            label = (at - timedelta(days=at.weekday())).strftime("%Y-%m-%d")
        else:
            label = at.strftime("%Y-%m-%d")
        buckets[label] += 1
        topics.update(entry["topics"])
        kinds.update([entry["kind"]])
    return {"bucket": request["bucket"], "display_offset_minutes": request["display_offset_minutes"],
        "buckets": [{"period": key, "events": count} for key, count in sorted(buckets.items())],
        "topics": dict(sorted(topics.items())), "kinds": dict(sorted(kinds.items()))}


def _unchanged(snapshot: dict) -> bool:
    payload, _ = _read_direct_file_bytes(snapshot["root"] / "manifest.json", boundary=snapshot["root"])
    return sha256_bytes(payload) == snapshot["identity"]


def query_worldline(value: dict[str, Any], *, registry_path: Path | None = None) -> dict[str, Any]:
    """Return bounded recognition records; never write or fetch source content."""
    started = time.monotonic()
    now = datetime.now(timezone.utc)
    snapshot = _snapshot(value, registry_path)
    request = _normalize(value, snapshot, now)
    manifest = snapshot["manifest"]
    cursor = _decode_cursor(request["cursor"]) if request["cursor"] else None
    if cursor:
        if cursor["workspace_id"] != manifest.get("workspace_id") or cursor["generation"] != manifest.get("generation"):
            raise ContinuityError("Timeline changed; restart the query", "cursor_stale")
        if cursor["query"] != _fingerprint(request):
            raise ContinuityError("Cursor belongs to different filters; restart the query", "cursor_mismatch")
    selection = {**request, "_deadline": started + request["deadline_ms"] / 1000}
    entries, families, coverage = select_worldline_rows(manifest, snapshot["rows"], selection, now)
    full_entries = entries
    if cursor:
        last = (_time(cursor["last"][0]), cursor["last"][1])
        entries = [item for item in entries if
            ((_time(item["occurred_at"]), item["id"]) < last if request["order"] == "desc"
             else (_time(item["occurred_at"]), item["id"]) > last)]
    page = entries[:request["page_size"]]
    result = {"format": VIEW_FORMAT, "mode": request["mode"], "status": "ok",
        "request_id": request["request_id"], "entries": [], "next_cursor": None, "has_more": False,
        "coverage": coverage,
        "provenance": {"workspace_id": manifest.get("workspace_id"), "generation": manifest.get("generation"),
            "manifest_sha256": snapshot["identity"], "runtime_version": IMPLEMENTATION_VERSION,
            "compatibility": snapshot["compatibility"], "effective_scope": request["scope"],
            "as_of": request["as_of"], "privacy_checked_at": _iso(now), "selected_ids": []},
        "query": {key: request[key] for key in ("from_time", "to_time", "search", "topics", "kinds",
            "include_legacy", "order", "bucket", "display_offset_minutes", "sensitivity_ceiling")},
        "capture_policy": effective_policy(snapshot["rows"], {**manifest["scope"], **{k: request["scope"][k] for k in ("user", "agent")}}, now),
        "persisted": False, "source_mutated": False, "save_claim": False}
    if request["mode"] == "overview":
        result["overview"] = _buckets(full_entries, request)
    if request["mode"] == "inspect":
        result["revisions"] = []
        if page:
            item = page[0]
            chain = families[item["id"]]
            result["revisions"] = [_entry(row, chain[0], index, set(request["unreachable_source_ids"]))
                                   for index, row in enumerate(chain)
                                   if _privacy(row, request["sensitivity_ceiling"], now)]
            permitted = {row["id"] for rows in families.values() for row in rows}
            for revision in result["revisions"]:
                revision["related_ids"] = [key for key in revision["related_ids"] if key in permitted]
    def finish(chosen: list[dict]) -> dict:
        result["entries"] = chosen
        result["provenance"]["selected_ids"] = [item["id"] for item in chosen]
        result["has_more"] = len(entries) > len(chosen)
        result["next_cursor"] = _cursor(snapshot, request, chosen[-1]) if chosen and result["has_more"] else None
        result["coverage"]["returned_events"] = len(chosen)
        return result
    finish(page)
    while page and len(dump_canonical(result)) > request["budget"]:
        page = page[:-1]
        finish(page)
    if len(dump_canonical(result)) > request["budget"] or entries and not page:
        minimum = copy.deepcopy(result)
        if entries:
            minimum["entries"] = [entries[0]]
        raise ContinuityError(f"Increase budget; next result needs at least {len(dump_canonical(minimum))} characters", "budget_too_small")
    if time.monotonic() > selection["_deadline"]:
        raise ContinuityError("Timeline deadline reached; no complete result emitted", "deadline_exceeded")
    if not _unchanged(snapshot):
        raise ContinuityError("Timeline changed during reading; restart the query", "snapshot_changed")
    _validate(result, "worldline-view-v2.schema.json")
    return result


def _href(locator: str) -> str | None:
    safe_locator(locator)
    scheme = urlsplit(locator).scheme.casefold()
    if scheme in ("https", "http"):
        return locator
    if re.match(r"^[A-Za-z]:[\\/]", locator):
        return "file:///" + quote(PureWindowsPath(locator).as_posix(), safe="/:")
    if locator.startswith("/") and not locator.startswith("//"):
        return Path(locator).as_uri()
    return None


def render_worldline(value: dict[str, Any], output: str | Path, *, limit: int = 300,
                     registry_path: Path | None = None) -> dict[str, Any]:
    """Create one explicitly requested, bounded HTML derivative without a server."""
    if not isinstance(limit, int) or not 1 <= limit <= 2000:
        raise ContinuityError("Render limit must be 1..2000", "schema_invalid")
    if not output:
        raise ContinuityError("render requires explicit output", "schema_invalid")
    now = datetime.now(timezone.utc)
    snapshot = _snapshot(value, registry_path)
    request = _normalize({**value, "mode": "browse", "cursor": None, "event_id": None}, snapshot, now)
    request["_deadline"] = time.monotonic() + request["deadline_ms"] / 1000
    entries, _, coverage = select_worldline_rows(snapshot["manifest"], snapshot["rows"], request, now)
    cards = copy.deepcopy(entries[:limit])
    for card in cards:
        for source in card["sources"]:
            source["href"] = _href(source["locator"])
    data = {"format": "cd-worldline-render-data/v2", "entries": cards, "coverage": coverage, "generated_at": _iso(now),
            "generation": snapshot["manifest"].get("generation"),
            "display_offset_minutes": request["display_offset_minutes"],
            "source_ids": [item["id"] for item in cards],
            "query": {key: request[key] for key in ("from_time", "to_time", "search", "topics", "kinds")}}
    encoded = json.dumps(data, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    page = _HTML.replace("__WORLDLINE_DATA__", encoded)
    payload = page.encode("utf-8")
    if len(payload) > 8_000_000:
        raise ContinuityError("Rendered view exceeds 8 MB; choose a smaller window", "render_too_large")
    if not _unchanged(snapshot):
        raise ContinuityError("Timeline changed before rendering; retry with a fresh view", "snapshot_changed")
    destination = Path(output).expanduser().absolute()
    if destination.exists():
        raise ContinuityError("Choose an absent output path; existing files are preserved", "output_exists")
    # Only an explicit derivative path may be written, never a canonical member.
    root = snapshot["root"].resolve()
    try:
        relative = destination.resolve().relative_to(root)
    except ValueError:
        relative = None
    if relative is not None and destination.suffix.lower() != ".html":
        raise ContinuityError("Governed timeline projections require an .html filename", "output_invalid")
    if relative is not None and (not relative.parts or relative.parts[0] != "projections"):
        raise ContinuityError("Within Continuity, render only beneath projections", "custody_denied")
    from workspace_runtime import atomic_new_bytes, _has_reparse_component
    if _has_reparse_component(destination, destination.anchor and Path(destination.anchor)):
        raise ContinuityError("Output must not cross indirect paths", "custody_reparse_escape")
    def publish() -> None:
        if _has_reparse_component(destination, Path(destination.anchor)):
            raise ContinuityError("Output path became indirect", "custody_reparse_escape")
        if not _unchanged(snapshot):
            raise ContinuityError("Timeline changed before publication; retry", "snapshot_changed")
        destination.parent.mkdir(parents=True, exist_ok=True)
        atomic_new_bytes(destination, payload)
    if relative is not None:
        if snapshot["compatibility"] != "v2_native":
            raise ContinuityError("Legacy stores require an external render destination or explicit migration", "migration_required")
        from workspace_runtime import workspace_lock
        from workspace_runtime import revalidate_resolution
        with workspace_lock(root):
            revalidate_resolution(snapshot["token"], root)
            publish()
    else:
        publish()
    return {"format": "cd-worldline-render/v2", "path": str(destination), "rendered_events": len(cards),
        "eligible_events": len(entries), "omitted_events": len(entries) - len(cards),
        "source_ids": data["source_ids"], "generation": data["generation"], "canonical_mutation": False,
        "artifact_sha256": sha256_bytes(payload), "capture_save_claim": False}

_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Worldline · A persistent past</title>
<style>
:root{color-scheme:dark;--bg:#11151b;--panel:#1a2029;--ink:#edf2f8;--muted:#a8b6c7;--line:#334052;--accent:#7cdecf}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:40px 24px 80px}header p{max-width:75ch;color:var(--muted)}h1{font-size:clamp(2.4rem,6vw,4rem);letter-spacing:-.05em;line-height:1.1;margin:8px 0 18px}.eyebrow{font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}.controls{position:sticky;top:0;z-index:1;display:flex;flex-wrap:wrap;gap:12px;background:var(--bg);padding:18px 0;border-bottom:1px solid var(--line)}label{display:flex;flex-direction:column;gap:4px;font-size:.8rem;color:var(--muted)}label:first-child{flex:1;min-width:190px}input,select,button{font:inherit;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink)}button{cursor:pointer}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:3px}#count{color:var(--muted);font-size:.9rem}.day{display:grid;grid-template-columns:145px 1fr;gap:24px;margin-top:30px}.day h2{font-size:.95rem;font-weight:500;color:var(--muted);margin:0;padding-top:18px}.events{border-left:1px solid var(--line);padding-left:24px}.event{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:14px}.event:before{content:'';position:absolute;width:8px;height:8px;border-radius:50%;background:var(--accent);left:-29px;top:26px}.event h3{font-size:1.12rem;line-height:1.4;margin:6px 0 10px;overflow-wrap:anywhere}.meta,.small{font-size:.78rem;color:var(--muted)}.tags{display:flex;gap:6px;flex-wrap:wrap}.tag{font-size:.72rem;border:1px solid var(--line);border-radius:20px;padding:2px 8px;color:var(--accent)}details{margin-top:15px}summary{cursor:pointer;color:var(--muted);font-size:.85rem}details p{overflow-wrap:anywhere;font-size:.85rem}a{color:var(--accent);text-underline-offset:3px}.empty{padding:40px 0;color:var(--muted)}footer{border-top:1px solid var(--line);margin-top:40px;padding-top:18px;color:var(--muted);font-size:.8rem}@media(max-width:620px){main{padding:24px 16px}.day{display:block}.day h2{margin-bottom:12px}.events{margin-left:4px;padding-left:18px}.event:before{left:-23px}.controls{gap:8px}}
</style></head><body><main><header><div class="eyebrow">A persistent past</div><h1>Worldline</h1><p>Recognize what happened. Follow the thread when its substance matters.</p><p id="coverage"></p><p id="window" class="small"></p></header>
<div class="controls"><label>Find in this view<input id="search" type="search" placeholder="An idea, topic, or occurrence"></label><label>Kind<select id="kind"><option value="">All kinds</option></select></label><label>Topic<select id="topic"><option value="">All topics</option></select></label><label>Order<select id="order"><option value="desc">Newest first</option><option value="asc">Oldest first</option></select></label></div><p id="count" aria-live="polite"></p><section id="timeline" aria-label="Timeline of occurrences"></section><footer id="footer"></footer></main>
<script id="worldline-data" type="application/json">__WORLDLINE_DATA__</script>
<script>
'use strict';const data=JSON.parse(document.getElementById('worldline-data').textContent);const byId=id=>document.getElementById(id);const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e};
const dateKey=e=>new Date(Date.parse(e.occurred_at)+data.display_offset_minutes*60000).toISOString().slice(0,10);
const loaded=data.entries.length,total=data.coverage.eligible_events;
byId('coverage').textContent=`${loaded} of ${total} eligible occurrences loaded. ${data.coverage.native_events} native events; ${data.coverage.legacy_events} retained legacy episodes. This is a bounded snapshot of the indexed past.`;
byId('window').textContent=`Selected window: ${data.query.from_time??'earliest retained'} to ${data.query.to_time??'present snapshot'} (end exclusive). ${data.query.search?'Search: '+data.query.search+'. ':''}${data.query.topics.length?'Topics: '+data.query.topics.join(', ')+'. ':''}${data.query.kinds.length?'Kinds: '+data.query.kinds.join(', ')+'. ':''}`;
for(const field of ['kind','topic']){const values=[...new Set(data.entries.flatMap(e=>field==='kind'?[e.kind]:e.topics))].sort();for(const value of values){const o=el('option',value);o.value=value;byId(field).append(o)}}
function draw(){const query=byId('search').value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);const kind=byId('kind').value,topic=byId('topic').value,order=byId('order').value;const rows=data.entries.filter(e=>{const text=[e.title,e.kind,...e.topics].join(' ').toLocaleLowerCase();return query.every(q=>text.includes(q))&&(!kind||e.kind===kind)&&(!topic||e.topics.includes(topic))}).sort((a,b)=>{const n=Date.parse(a.occurred_at)-Date.parse(b.occurred_at)||a.id.localeCompare(b.id);return order==='asc'?n:-n});const container=byId('timeline');container.replaceChildren();byId('count').textContent=`Showing ${rows.length} of ${loaded} loaded occurrences. Filters apply to this saved view.`;if(!rows.length){container.append(el('p','No matching retained occurrences in this view. That does not mean nothing happened.','empty'));return}let day=null,events=null;for(const e of rows){const key=dateKey(e);if(key!==day){day=key;const section=el('section',undefined,'day');section.append(el('h2',key));events=el('div',undefined,'events');section.append(events);container.append(section)}const card=el('article',undefined,'event');card.id=e.id;const timing=e.time_basis==='recorded'?'Recorded here · occurrence time unknown':`${e.time_precision} precision · ${e.time_basis}`;card.append(el('div',`${e.kind} · ${timing}${e.origin==='legacy_episode'?' · legacy episode':''}`,'meta'));card.append(el('h3',e.title));const tags=el('div',undefined,'tags');if(e.scope.project)tags.append(el('span',e.scope.project,'tag'));for(const topic of e.topics)tags.append(el('span',topic,'tag'));card.append(tags);const details=el('details');details.append(el('summary',`Sources and details${e.correction_count?' · corrected':''}`));if(!e.sources.length)details.append(el('p','No source link was retained for this legacy episode.'));for(const source of e.sources){const p=el('p');if(source.href){const a=el('a',source.label);a.href=source.href;a.target='_blank';a.rel='noopener noreferrer';p.append(a)}else p.append(el('span',source.label));p.append(el('br'));p.append(el('span',source.locator,'small'));details.append(p)}details.append(el('p',`Event: ${e.id} · revision: ${e.revision_id}`,'small'));details.append(el('p',`Indexed ${e.recorded_at}. Source access ${e.content_availability}.`,'small'));if(e.related_ids.length)details.append(el('p',`Related occurrences: ${e.related_ids.join(', ')}`,'small'));card.append(details);events.append(card)}}
for(const id of ['search','kind','topic','order'])byId(id).addEventListener('input',draw);
byId('footer').textContent=`Generated ${data.generated_at}. Source generation ${data.generation??'legacy'}. Fixed display offset: ${data.display_offset_minutes} minutes. ${total-loaded} eligible occurrences were omitted by this artifact's bound. Use Worldline browse or render with another time window to continue; this file does not fetch new history.`;draw();
</script></body></html>'''


def _json_input(path: str) -> dict:
    try:
        raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8-sig")
        if len(raw) > 1_000_000:
            raise ValueError("input too large")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("object required")
        return result
    except (OSError, ValueError, UnicodeError) as exc:
        raise ContinuityError("Request JSON is missing, too large, or invalid", "schema_invalid") from exc


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--request", help="Exact request JSON file, or - for stdin")
    commands = root.add_subparsers(dest="command")
    for name in ("browse", "overview", "inspect", "capture", "policy", "render"):
        cmd = commands.add_parser(name)
        cmd.add_argument("workspace", nargs="?")
        cmd.add_argument("--user")
        cmd.add_argument("--agent")
        cmd.add_argument("--project")
        cmd.add_argument("--thread")
        cmd.add_argument("--authority")
        cmd.add_argument("--selection-mode", choices=("generic_explicit", "nova_ambient", "nova_explicit_authorized"))
        cmd.add_argument("--grant-id")
        if name in ("browse", "overview", "inspect", "render"):
            cmd.add_argument("--from", dest="from_time")
            cmd.add_argument("--to", dest="to_time")
            cmd.add_argument("--as-of")
            cmd.add_argument("--search")
            cmd.add_argument("--topic", action="append", default=[])
            cmd.add_argument("--kind", action="append", default=[])
            cmd.add_argument("--sensitivity", choices=tuple(LEVELS), default="ordinary")
            cmd.add_argument("--native-only", action="store_true")
            cmd.add_argument("--order", choices=("asc", "desc"), default="desc")
            cmd.add_argument("--page-size", type=int, default=30)
            cmd.add_argument("--cursor")
            cmd.add_argument("--budget", type=int, default=20000)
            cmd.add_argument("--deadline-ms", type=int, default=5000)
            cmd.add_argument("--bucket", choices=("day", "week", "month"), default="day")
            cmd.add_argument("--display-offset-minutes", type=int, default=0)
            cmd.add_argument("--unreachable-source-id", action="append", default=[])
            if name == "inspect":
                cmd.add_argument("--event-id", required=True)
            if name == "render":
                cmd.add_argument("--output", required=True)
                cmd.add_argument("--limit", type=int, default=300)
        else:
            cmd.add_argument("--input", help="Compact JSON object, or - for stdin")
            cmd.add_argument("--event-key", help="Stable source event identity for idempotency")
            cmd.add_argument("--expected-generation", type=int)
            cmd.add_argument("--idempotency-key")
            if name == "capture":
                cmd.add_argument("--title")
                cmd.add_argument("--source")
                cmd.add_argument("--source-label", default="Original source")
                cmd.add_argument("--source-owner", default="unspecified")
                cmd.add_argument("--source-kind", choices=("user", "agent", "tool", "file", "import", "system"), default="agent")
                cmd.add_argument("--kind")
                cmd.add_argument("--occurred-at")
                cmd.add_argument("--current", action="store_true")
                cmd.add_argument("--ended-at")
                cmd.add_argument("--time-basis", choices=("observed", "source_reported", "inferred", "recorded"))
                cmd.add_argument("--time-precision", choices=("instant", "day", "range", "unknown"))
                cmd.add_argument("--topic", action="append", default=[])
                cmd.add_argument("--related-id", action="append", default=[])
                cmd.add_argument("--supersedes")
                cmd.add_argument("--retract", action="store_true")
                cmd.add_argument("--capture-mode", choices=("routine", "explicit"), default="routine")
                cmd.add_argument("--no-retention", action="store_true")
                cmd.add_argument("--sensitivity", choices=tuple(LEVELS))
                cmd.add_argument("--retention")
                cmd.add_argument("--expires-at")
            else:
                cmd.add_argument("--mode", choices=("ordinary", "off"), required=False)
                cmd.add_argument("--authority-source")
    return root


def _base_args(args: argparse.Namespace) -> dict:
    return {"workspace": {"selection_mode": args.selection_mode or ("generic_explicit" if args.workspace else "nova_ambient"),
            "path": args.workspace, "grant_id": args.grant_id},
        "scope": {key: getattr(args, key) for key in ("user", "agent", "project", "thread")
                  if getattr(args, key) is not None}}


def _read_args(args: argparse.Namespace) -> dict:
    value = {**_base_args(args), "format": REQUEST_FORMAT,
        "mode": "browse" if args.command == "render" else args.command,
        "authority": args.authority or "user-requested-read", "from_time": args.from_time, "to_time": args.to_time,
        "search": args.search, "topics": args.topic, "kinds": args.kind, "include_legacy": not args.native_only,
        "sensitivity_ceiling": args.sensitivity, "order": args.order, "page_size": args.page_size,
        "cursor": args.cursor, "budget": args.budget, "deadline_ms": args.deadline_ms,
        "bucket": args.bucket, "display_offset_minutes": args.display_offset_minutes,
        "unreachable_source_ids": args.unreachable_source_id}
    if args.as_of:
        value["as_of"] = args.as_of
    if args.command == "inspect":
        value["event_id"] = args.event_id
    return value


def _replay_time(snapshot: dict, key: str) -> str | None:
    if snapshot["compatibility"] != "v2_native":
        return None
    from workspace_runtime import normalize_idempotency_key
    key = normalize_idempotency_key(key)
    member = "idempotency.jsonl"
    payload, _ = _read_direct_file_bytes(generation_path(snapshot["root"], snapshot["manifest"]) / member,
                                        boundary=snapshot["root"])
    if sha256_bytes(payload) != snapshot["metadata"]["members"][member]["sha256"]:
        raise ContinuityError("Idempotency snapshot changed", "snapshot_changed")
    for line in payload.decode("utf-8").splitlines():
        record = json.loads(line)
        if record.get("operation_family") != "worldline.capture" or record.get("idempotency_key") != key:
            continue
        identity = record.get("result", {}).get("episode_id")
        row = next((row for row in snapshot["rows"] if row.get("id") == identity), None)
        if row and row.get("worldline_event"):
            return row["worldline_event"]["occurred_at"]
    return None


def _write_args(args: argparse.Namespace) -> dict:
    compact = _json_input(args.input) if args.input else {}
    base = _base_args(args)
    if compact.get("workspace"):
        base["workspace"] = compact["workspace"]
    snapshot = _snapshot(base)
    scope = _scope(snapshot["manifest"], {**base["scope"], **compact.get("scope", {})})
    # New records use the manifest's project bound or its projectless '*' facet.
    scope["project"] = scope["project"] or snapshot["manifest"]["scope"].get("project") or "*"
    common = {**base, "scope": scope,
        "authority": args.authority or compact.get("authority"),
        "expected_generation": args.expected_generation if args.expected_generation is not None else snapshot["manifest"].get("generation"),
        "idempotency_key": args.idempotency_key or compact.get("idempotency_key")}
    if args.command == "policy":
        mode = args.mode or compact.get("mode") or (compact.get("policy") or {}).get("mode")
        source = args.authority_source or compact.get("authority_source") or (compact.get("policy") or {}).get("authority_source")
        if not mode:
            policy_scope = {**snapshot["manifest"]["scope"], **{k: scope[k] for k in ("user", "agent")}}
            return {"operation": "policy-read", "policy": effective_policy(snapshot["rows"], policy_scope, datetime.now(timezone.utc))}
        common["scope"]["project"] = snapshot["manifest"]["scope"].get("project") or "*"
        common["scope"]["thread"] = snapshot["manifest"]["scope"].get("thread")
        if not common["authority"] or not source:
            raise ContinuityError("Policy changes require authority and its source", "authority_required")
        common["format"] = "cd-worldline-policy-request/v1"
        common["policy"] = {"format": "cd-worldline-policy/v1", "mode": mode, "authority_source": source}
        key = args.event_key or compact.get("event_key")
        if not common["idempotency_key"]:
            if not key:
                raise ContinuityError("Policy changes require a stable --event-key", "schema_invalid")
            common["idempotency_key"] = hashlib.sha256((source + "\0" + key).encode()).hexdigest()
        return common
    event = compact.get("event")
    parent_id = args.supersedes or next(iter(compact.get("supersedes", [])), None)
    target = None
    if parent_id and not event:
        target = next((row for row in snapshot["rows"] if row.get("id") == parent_id), None)
        if not target or not target.get("worldline_event"):
            raise ContinuityError("Correction target is absent", "source_unreachable")
        for key in ("project", "thread"):
            if key not in base["scope"] and key not in compact.get("scope", {}):
                common["scope"][key] = target["scope"][key]
    if not event:
        prior = copy.deepcopy(target["worldline_event"]) if target else {}
        first = next(iter(prior.get("sources", [])), {})
        title = args.title or compact.get("title") or prior.get("title")
        locator = args.source or compact.get("source") or first.get("locator")
        occurred = args.occurred_at or compact.get("occurred_at") or prior.get("occurred_at")
        if not common["idempotency_key"]:
            key = args.event_key or compact.get("event_key")
            if not key or not locator:
                raise ContinuityError("Capture needs a stable event key and source", "schema_invalid")
            common["idempotency_key"] = hashlib.sha256((locator + "\0" + key).encode()).hexdigest()
        if (args.current or compact.get("current")) and not occurred:
            occurred = _replay_time(snapshot, common["idempotency_key"]) or utc_now()
        if not title or not locator or not occurred:
            raise ContinuityError("Capture needs title, source, and honest occurred-at (or --current)", "schema_invalid")
        sources = prior.get("sources") or [{"kind": "other", "locator": locator,
            "label": compact.get("source_label", args.source_label), "owner": compact.get("source_owner", args.source_owner)}]
        sources[0]["locator"] = locator
        if "source_label" in compact or args.source_label != "Original source":
            sources[0]["label"] = compact.get("source_label", args.source_label)
        if "source_owner" in compact or args.source_owner != "unspecified":
            sources[0]["owner"] = compact.get("source_owner", args.source_owner)
        event = {"format": "cd-worldline-event/v2", "title": title,
            "kind": args.kind or compact.get("kind") or prior.get("kind", "conversation"),
            "disposition": "retracted" if args.retract else compact.get("disposition", "recorded"),
            "occurred_at": occurred, "ended_at": args.ended_at or compact.get("ended_at", prior.get("ended_at")),
            "time_basis": args.time_basis or compact.get("time_basis") or prior.get("time_basis") or ("observed" if args.current or compact.get("current") else "source_reported"),
            "time_precision": args.time_precision or compact.get("time_precision") or prior.get("time_precision", "instant"),
            "sources": sources,
            "topics": compact.get("topics", args.topic or prior.get("topics", [])),
            "related_ids": compact.get("related_ids", args.related_id or prior.get("related_ids", [])),
            "supersedes": [parent_id] if parent_id else []}
    common.update({"format": "cd-worldline-capture/v2", "event": event,
        "source_kind": compact.get("source_kind", args.source_kind),
        "capture_mode": compact.get("capture_mode", "explicit" if event["supersedes"] else args.capture_mode),
        "retention_guard": bool(args.no_retention or compact.get("retention_guard", False))})
    if "privacy_change_authorized" in compact:
        common["privacy_change_authorized"] = compact["privacy_change_authorized"]
    for key in ("sensitivity", "retention", "expires_at"):
        supplied = getattr(args, key)
        if supplied is not None or key in compact:
            common[key] = supplied if supplied is not None else compact[key]
    key = args.event_key or compact.get("event_key")
    if not common["idempotency_key"]:
        if not key:
            raise ContinuityError("Capture needs a stable --event-key or idempotency-key", "schema_invalid")
        common["idempotency_key"] = hashlib.sha256((event["sources"][0]["locator"] + "\0" + key).encode()).hexdigest()
    if not common["authority"]:
        if common["capture_mode"] == "routine":
            common["authority"] = "agent-standing-worldline"
        else:
            raise ContinuityError("Explicit capture requires actual current human authority", "authority_required")
    return common


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        if args.request:
            if args.command:
                raise ContinuityError("Choose exact request or convenience command", "schema_invalid")
            request = _json_input(args.request)
            form = request.get("format")
            if form == "cd-worldline-capture/v2":
                from continuity_store_v2 import capture_worldline
                result = capture_worldline(request)
            elif form == "cd-worldline-policy-request/v1":
                from continuity_store_v2 import set_worldline_policy
                result = set_worldline_policy(request)
            elif request.get("mode") == "render":
                request = dict(request)
                output, limit = request.pop("output", None), request.pop("limit", 300)
                result = render_worldline(request, output, limit=limit)
            else:
                result = query_worldline(request)
        elif args.command in ("browse", "overview", "inspect", "render"):
            request = _read_args(args)
            result = render_worldline(request, args.output, limit=args.limit) if args.command == "render" else query_worldline(request)
        elif args.command in ("capture", "policy"):
            from continuity_store_v2 import capture_worldline, set_worldline_policy
            request = _write_args(args)
            if request.get("operation") == "policy-read":
                result = request
            else:
                result = capture_worldline(request) if args.command == "capture" else set_worldline_policy(request)
        else:
            raise ContinuityError("Choose browse, overview, inspect, capture, policy, or render", "schema_invalid")
        print(dump_canonical(result))
        return 0
    except (ContinuityError, SchemaError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, ContinuityError) else "schema_invalid"
        print(dump_canonical({"format": "cd-worldline-error/v2", "status": "no_view", "code": code,
            "message": str(exc), "restart": code in ("cursor_stale", "cursor_mismatch", "snapshot_changed"),
            "save_claim": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only Project Bridge projection and separate browsing preferences."""
from __future__ import annotations
import hashlib, json, os, re, sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SKILL_ROOT = ROOT.parent
sys.path.insert(0, str((SKILL_ROOT / "scripts").resolve()))
import project_control as control

PRODUCT = "dennis-stratton-project-management"
BUILD = "dennis-project-bridge-0.6.0-c3-package-20261016"
STORE_ENV = "DENNIS_PROJECT_HOME"
DEMO_ID = "demo-community-exhibition"


def module_path(value: Path) -> Path:
    path = Path(value).resolve(strict=False)
    if os.name == "nt" and not str(path).startswith("\\\\?\\"):
        text = str(path)
        path = Path(("\\\\?\\UNC\\" + text[2:]) if text.startswith("\\\\") else ("\\\\?\\" + text))
    return path


def resolve_user_store(explicit: Path | None = None) -> tuple[Path, str]:
    if explicit is not None:
        return control.resolve_store(explicit)
    if os.environ.get(STORE_ENV, "").strip():
        return control.resolve_store(None)
    # Nova's local selector is an explicit registry, not a drive scan. On other
    # hosts the native resolver falls back to Dennis's documented user store.
    data_root = os.environ.get("NOVA_DATA_ROOT", "").strip()
    selectors = Path(data_root) / "estate" / "path-selectors.json" if data_root else Path(r"E:\Indranet\Nova\estate\path-selectors.json")
    try:
        values = json.loads(selectors.read_text(encoding="utf-8")).get("active_values", {})
        selected = values.get(STORE_ENV)
        if isinstance(selected, str) and selected.strip():
            return control.resolve_store(Path(selected.strip()))[0], "nova-path-selectors"
    except (OSError, ValueError, TypeError):
        pass
    return control.resolve_store(None)


def safe_data_home(path: Path, app_root: Path = SKILL_ROOT) -> Path:
    home = module_path(path)
    root = module_path(app_root)
    h, r = str(home).casefold().rstrip("\\/"), str(root).casefold().rstrip("\\/")
    if h == r or h.startswith(r + "\\") or h.startswith(r + "/"):
        raise ValueError("Project Bridge reading preferences must live outside the installed skill folder.")
    if r.startswith(h + "\\") or r.startswith(h + "/"):
        raise ValueError("Choose a dedicated reading-preferences folder, not an ancestor of the installed skill.")
    return home


def _safe_id(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,119}", value) is not None


def _project_key(project_id: str) -> str:
    return hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:24]


def _summary(record: dict) -> dict:
    project = record.get("project", {})
    current = record.get("current", {})
    hierarchy = record.get("hierarchy", [])
    work = record.get("work_packages", [])
    criteria = record.get("exit_criteria", [])
    evidence = record.get("evidence", [])
    decisions = record.get("decisions", [])
    return {
        "project": {key: project.get(key) for key in ("id", "name", "outcome", "status", "owner", "updated_at")},
        "current": {key: current.get(key) for key in ("path", "active_commitment_id", "as_of", "posture", "purpose_connection", "next_action", "next_decision")},
        "forecast": {key: record.get("forecast", {}).get(key) for key in ("as_of", "unit", "lower", "upper", "confidence", "basis", "baseline", "variance", "next_update")} if isinstance(record.get("forecast"), dict) else {},
        "hierarchy": [{key: row.get(key) for key in ("id", "kind", "label", "parent_id", "status", "purpose", "exit_criteria_ids")} for row in hierarchy if isinstance(row, dict)],
        "work_packages": [{key: row.get(key) for key in ("id", "parent_id", "outcome", "status", "dependency_ids", "acceptance_criteria_ids", "owner", "next_action")} for row in work if isinstance(row, dict)],
        "exit_criteria": [{key: row.get(key) for key in ("id", "owner_id", "description", "status", "evidence_ids")} for row in criteria if isinstance(row, dict)],
        "evidence": [{key: row.get(key) for key in ("id", "claim", "level", "locator", "observed_at", "method", "limits", "actor")} for row in evidence if isinstance(row, dict)],
        "decisions": [{key: row.get(key) for key in ("id", "status", "decision", "options", "rationale", "authority", "source_id", "date", "supersedes_ids")} for row in decisions if isinstance(row, dict)],
        "source_authority": [{key: row.get(key) for key in ("id", "rank", "kind", "locator", "scope", "observed_at", "status")} for row in record.get("source_authority", []) if isinstance(row, dict)],
    }


def _record_lookup(store: Path, project_id: str) -> tuple[dict, Path, list[dict]] | None:
    if project_id == DEMO_ID:
        path = SKILL_ROOT / "examples" / "community-exhibition" / "project-control.json"
        if not path.is_file():
            return None
        record = control.load_record(path)
        return record, path, control.validate_record(record)[0]
    rows, _ = control.scan_store(store)
    matches = [row for row in rows if row.get("project_id") == project_id]
    if len(matches) != 1:
        return None
    row = matches[0]
    errors, _warnings = control.validate_record(row["record"])
    return row["record"], Path(row["path"]), errors


def project_list(store: Path) -> dict:
    rows, diagnostics = control.scan_store(store)
    projects = []
    for row in rows:
        record = row["record"]
        errors, warnings = control.validate_record(record)
        summary = _summary(record)
        summary["fingerprint"] = row["fingerprint"]
        summary["valid"] = not errors
        summary["errors"] = errors[:12]
        summary["warnings"] = warnings[:12]
        projects.append(summary)
    return {"store": str(store), "store_exists": store.is_dir(), "store_source": "explicit-or-resolved", "projects": projects, "diagnostics": diagnostics, "demo_available": (SKILL_ROOT / "examples" / "community-exhibition" / "project-control.json").is_file()}


def get_project(store: Path, project_id: str) -> dict | None:
    found = _record_lookup(store, project_id)
    if not found:
        return None
    record, path, errors = found
    summary = _summary(record)
    summary["fingerprint"] = control.fingerprint(record)
    summary["valid"] = not errors
    summary["errors"] = errors[:12]
    summary["warnings"] = control.validate_record(record)[1][:12]
    summary["record_location"] = str(path)
    return summary


def _snapshot_view(project: dict) -> dict:
    return {
        "project": project.get("project"), "current": project.get("current"), "forecast": project.get("forecast"),
        "hierarchy": project.get("hierarchy"), "work_packages": project.get("work_packages"),
        "exit_criteria": project.get("exit_criteria"), "evidence": project.get("evidence"),
        "decisions": project.get("decisions"), "fingerprint": project.get("fingerprint"),
    }


def _diff(before: dict | None, after: dict) -> list[dict]:
    if not before:
        return []
    groups = {
        "Purpose and scope": ("project",),
        "Current route and next action": ("current",),
        "Declared work and dependencies": ("hierarchy", "work_packages"),
        "Completion evidence": ("exit_criteria", "evidence"),
        "Decisions": ("decisions",),
    }
    result = []
    for label, keys in groups.items():
        if any(before.get(key) != after.get(key) for key in keys):
            result.append({"area": label, "before": {key: before.get(key) for key in keys}, "after": {key: after.get(key) for key in keys}})
    return result


def save_view(data_home: Path, store: Path, value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Choose a supported reading position.")
    project_id = value.get("project_id")
    if project_id is not None and not _safe_id(project_id):
        raise ValueError("The selected project identifier is invalid.")
    skin = value.get("skin", "proofspan")
    if skin not in {"proofspan", "bridge", "folio", "redline"}:
        raise ValueError("Choose one of the four supported appearances.")
    mode = value.get("filter", "active")
    if mode not in {"active", "all"}:
        raise ValueError("Choose active or all work.")
    station = value.get("station_id")
    scroll = value.get("scroll_y", 0)
    if station is not None and not _safe_id(station):
        raise ValueError("The selected station is invalid.")
    if not isinstance(scroll, int) or isinstance(scroll, bool) or not 0 <= scroll <= 10000000:
        raise ValueError("The saved reading position is invalid.")
    current = get_project(store, project_id) if project_id else None
    changes = []
    if current:
        if station is not None and station not in {x["id"] for x in current["hierarchy"] + current["work_packages"]}:
            station = None
        snapshot_dir = data_home / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / (_project_key(project_id) + ".json")
        prior = None
        if snapshot_path.exists():
            try: prior = json.loads(snapshot_path.read_text(encoding="utf-8"))
            except (OSError, ValueError): prior = None
        latest = _snapshot_view(current)
        if not isinstance(prior, dict) or prior.get("latest", {}).get("fingerprint") != latest["fingerprint"]:
            previous = prior.get("latest") if isinstance(prior, dict) else None
            history = {"previous": previous, "latest": latest}
            snapshot_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            history = prior
        changes = _diff(history.get("previous"), history.get("latest"))
    prefs_path = data_home / "reading-position.json"
    prefs = {}
    if prefs_path.exists():
        try:
            loaded = json.loads(prefs_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict): prefs = loaded
        except (OSError, ValueError): pass
    by_project = prefs.get("projects", {})
    if not isinstance(by_project, dict): by_project = {}
    source_id = value.get("source_id")
    if source_id is not None and not _safe_id(source_id): raise ValueError("The selected evidence reference is invalid.")
    if current and source_id and source_id not in {x.get("id") for x in current.get("evidence", [])}: source_id = None
    view = {"project_id": project_id, "station_id": station, "source_id": source_id, "filter": mode, "skin": skin, "scroll_y": scroll, "fingerprint": current.get("fingerprint") if current else None}
    if project_id:
        by_project[project_id] = view
    prefs["projects"] = by_project
    prefs["last_project"] = project_id or prefs.get("last_project")
    prefs_path.write_text(json.dumps(prefs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"view": view, "changes": changes, "snapshot_fingerprint": current.get("fingerprint") if current else None}


def load_view(data_home: Path) -> dict:
    path = data_home / "reading-position.json"
    if not path.exists(): return {"last_project": None, "projects": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict): raise ValueError("not an object")
        projects = value.get("projects", {})
        if not isinstance(projects, dict): projects = {}
        return {"last_project": value.get("last_project"), "projects": projects}
    except (OSError, ValueError):
        return {"error": "Saved reading position could not be restored. Your native project records are untouched.", "last_project": None, "projects": {}}


def _is_windows_absolute(text: str) -> bool:
    return re.match(r"^[A-Za-z]:[\\/]", text) is not None or text.startswith("\\\\")


def _path_from_locator(locator: str, record_path: Path, record: dict) -> Path | None:
    if not isinstance(locator, str) or not locator.strip(): return None
    locator = locator.strip()
    if urlsplit(locator).scheme and not _is_windows_absolute(locator): return None
    record_dir = record_path.parent.resolve(strict=False)
    roots: list[Path] = [record_dir]
    exact_files: set[Path] = set()
    for src in record.get("source_authority", []):
        if not isinstance(src, dict): continue
        raw = src.get("locator")
        if not isinstance(raw, str) or not raw.strip() or (urlsplit(raw).scheme and not _is_windows_absolute(raw)): continue
        try:
            p = Path(raw).expanduser()
            if not p.is_absolute() and not _is_windows_absolute(raw):
                p = (record_dir / p)
            p = p.resolve(strict=True)
            if p.is_dir(): roots.append(p)
            elif p.is_file(): roots.append(p.parent); exact_files.add(p)
        except (OSError, ValueError): continue
    try:
        raw_path = Path(locator).expanduser()
        if raw_path.is_absolute() or _is_windows_absolute(locator):
            target = raw_path.resolve(strict=True)
            if not target.is_file(): return None
        else:
            target = None
            for root in roots:
                candidate = (root / raw_path).resolve(strict=True)
                if candidate.is_file() and (candidate == root or root in candidate.parents):
                    target = candidate; break
            if target is None: return None
        allowed = target in exact_files or any(target == root or root in target.parents for root in roots)
        return target if allowed else None
    except (OSError, ValueError):
        return None


def _is_missing_authorized_locator(locator: str, record_path: Path, record: dict) -> bool:
    if not isinstance(locator, str) or not locator.strip() or (urlsplit(locator).scheme and not _is_windows_absolute(locator)):
        return False
    raw_text = locator.strip()
    if not ("/" in raw_text or "\\" in raw_text or Path(raw_text).suffix):
        return False
    try:
        raw = Path(raw_text).expanduser()
        base = record_path.parent.resolve(strict=False)
        roots = [base]
        for src in record.get("source_authority", []):
            if not isinstance(src, dict): continue
            entry = src.get("locator")
            if not isinstance(entry, str) or not entry.strip() or (urlsplit(entry).scheme and not _is_windows_absolute(entry)): continue
            candidate = Path(entry).expanduser()
            if not candidate.is_absolute() and not _is_windows_absolute(entry): candidate = base / candidate
            candidate = candidate.resolve(strict=False)
            if candidate.is_dir(): roots.append(candidate)
            elif candidate.suffix: roots.append(candidate.parent)
        candidates = [raw.resolve(strict=False)] if raw.is_absolute() or _is_windows_absolute(raw_text) else [(root / raw).resolve(strict=False) for root in roots]
        for candidate in candidates:
            if candidate.exists(): continue
            if any(candidate == root or root in candidate.parents for root in roots): return True
    except (OSError, ValueError):
        return False
    return False


def source_info(store: Path, project_id: str, evidence_id: str) -> dict:
    if not _safe_id(evidence_id): raise ValueError("The requested source reference is invalid.")
    found = _record_lookup(store, project_id)
    if not found: raise ValueError("This project is no longer available. Refresh the portfolio.")
    record, record_path, errors = found
    if errors: raise ValueError("This project record has structural errors. Inspect the visible diagnostics before following evidence.")
    evidence = [x for x in record.get("evidence", []) if isinstance(x, dict) and x.get("id") == evidence_id]
    if len(evidence) != 1: raise ValueError("This evidence reference is missing or ambiguous in the selected project.")
    item = evidence[0]
    locator = item.get("locator", "")
    target = _path_from_locator(locator, record_path, record)
    if not target:
        if _is_missing_authorized_locator(locator, record_path, record):
            return {"kind": "missing", "id": evidence_id, "claim": item.get("claim"), "locator": locator, "reason": "The source file is missing from its recorded location. Restore it or reconnect the project folder, then choose Refresh project. You can return to the route at any time."}
        return {"kind": "reference", "id": evidence_id, "claim": item.get("claim"), "locator": locator, "reason": "This is a descriptive reference or it points outside the project's authorized readable source roots."}
    suffix = target.suffix.casefold()
    if suffix not in {".md", ".txt", ".csv"}:
        return {"kind": "original", "id": evidence_id, "claim": item.get("claim"), "locator": locator, "name": target.name, "download": True}
    try: raw = target.read_bytes()
    except OSError as exc: return {"kind": "unavailable", "id": evidence_id, "claim": item.get("claim"), "locator": locator, "reason": str(exc)}
    if len(raw) > 512 * 1024:
        return {"kind": "original", "id": evidence_id, "claim": item.get("claim"), "locator": locator, "name": target.name, "download": True}
    try: text = raw.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        return {"kind": "original", "id": evidence_id, "claim": item.get("claim"), "locator": locator, "name": target.name, "download": True}
    return {"kind": "text", "id": evidence_id, "claim": item.get("claim"), "locator": locator, "name": target.name, "text": text}


def source_bytes(store: Path, project_id: str, evidence_id: str) -> tuple[str, bytes]:
    info = source_info(store, project_id, evidence_id)
    if info.get("kind") not in {"text", "original"}:
        raise ValueError(info.get("reason", "This reference has no available original file."))
    found = _record_lookup(store, project_id)
    record, record_path, _ = found
    item = next(x for x in record.get("evidence", []) if x.get("id") == evidence_id)
    target = _path_from_locator(item.get("locator", ""), record_path, record)
    if target is None: raise ValueError("The source left its authorized readable boundary.")
    return target.name, target.read_bytes()


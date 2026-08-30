#!/usr/bin/env python3
"""Nova the Optimal AI Free estate bootstrap, registry-backed launcher, and diagnostics."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

PRODUCT_VERSION = "3.0.0"
REGISTRY_FORMAT = "nova-path-selectors/v1"
MANIFEST_FORMAT = "nova-estate-manifest/v1"
ERROR_FORMAT = "nova-operation-error/v1"
REPARSE_ATTRIBUTE = 0x400
SELECTOR_KEYS = (
    "NOVA_DATA_ROOT",
    "NOVA_CONTINUITY_HOME",
    "DUNBAR_STORE",
    "CORKBOARD_HOME",
)
OPTIONAL_FUTURE_SELECTOR_KEYS = ("DENNIS_PROJECT_HOME",)
DISABLED_SELECTOR_KEYS = ("MIND_CORE_DATABASE", "MIND_HOOK_RECEIPT_DIRECTORY")
MANAGED_ENVIRONMENT_KEYS = SELECTOR_KEYS + OPTIONAL_FUTURE_SELECTOR_KEYS + DISABLED_SELECTOR_KEYS
SERVICE_ENTRYPOINTS = {
    "continuity": ("cognitive-continuity", "scripts", "continuity_store_v2.py"),
    "worldline": ("cognitive-continuity", "scripts", "worldline.py"),
    "dunbar": ("dunbar", "scripts", "dunbar.py"),
    "corkboard": ("corkboard", "scripts", "corkboard.py"),
}


class NovaEstateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit(value: Any, *, stream: Any = sys.stdout) -> None:
    json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=False)
    stream.write("\n")


def fail(code: str, message: str, *, detail: Any = None) -> int:
    payload: dict[str, Any] = {"format": ERROR_FORMAT, "code": code, "message": message}
    if detail is not None:
        payload["detail"] = detail
    emit(payload, stream=sys.stderr)
    return 2


def platform_default_root() -> Path:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "Collaborative Dynamics" / "Nova"
        return Path.home() / "AppData" / "Local" / "Collaborative Dynamics" / "Nova"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Collaborative Dynamics" / "Nova"
    base = os.environ.get("XDG_DATA_HOME")
    anchor = Path(base).expanduser() if base else Path.home() / ".local" / "share"
    return anchor / "collaborative-dynamics" / "nova"


def current_estate_locator_path() -> Path:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        anchor = Path(base) if base else Path.home() / "AppData" / "Local"
        return anchor / "Collaborative Dynamics" / "Nova Operations" / "current-estate.json"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Collaborative Dynamics" / "Nova Operations" / "current-estate.json"
    base = os.environ.get("XDG_CONFIG_HOME")
    anchor = Path(base).expanduser() if base else Path.home() / ".config"
    return anchor / "collaborative-dynamics" / "nova" / "current-estate.json"


def read_current_estate_locator() -> Path | None:
    path = current_estate_locator_path()
    if not os.path.lexists(path):
        return None
    value = read_json(path)
    if value.get("format") != "nova-current-estate-locator/v1":
        raise NovaEstateError(f"Unsupported current-estate locator format: {path}")
    raw = value.get("root")
    if not isinstance(raw, str) or not raw.strip() or not Path(raw).expanduser().is_absolute():
        raise NovaEstateError(f"Current-estate locator has no absolute root: {path}")
    lexical = _lexical_absolute(Path(raw).expanduser())
    _assert_no_link_or_reparse(lexical, "Current estate")
    selected = lexical.resolve(strict=False)
    default = _lexical_absolute(platform_default_root()).resolve(strict=False)
    if selected == default:
        raise NovaEstateError("The platform-default estate must not have a duplicate current-estate locator")
    return selected


def default_root() -> Path:
    """Discover the registry location without depending on a shell environment."""
    located = read_current_estate_locator()
    return located if located is not None else platform_default_root()


def root_selection_source(value: str | None) -> str:
    if value:
        return "explicit_cli"
    return "platform_current_estate_locator" if os.path.lexists(current_estate_locator_path()) else "platform_default"


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _assert_no_link_or_reparse(path: Path, label: str) -> None:
    current = _lexical_absolute(path)
    while True:
        if os.path.lexists(current):
            try:
                observed = os.lstat(current)
            except OSError as exc:
                raise NovaEstateError(f"Could not inspect {label} path edge {current}: {exc}") from exc
            if stat.S_ISLNK(observed.st_mode):
                raise NovaEstateError(f"{label} crosses a symbolic link: {current}")
            if getattr(observed, "st_file_attributes", 0) & REPARSE_ATTRIBUTE:
                raise NovaEstateError(f"{label} crosses a reparse edge: {current}")
        if current.parent == current:
            break
        current = current.parent


def normalize_root(value: str | None) -> Path:
    candidate = Path(value).expanduser() if value else default_root()
    if not candidate.is_absolute():
        raise NovaEstateError("Nova data root must be an absolute path")
    lexical = _lexical_absolute(candidate)
    if lexical == Path(lexical.anchor):
        raise NovaEstateError("Nova data root cannot be a filesystem root")
    if any(part.casefold() == ".codex" for part in lexical.parts):
        raise NovaEstateError("Nova-owned state cannot live under .codex")
    _assert_no_link_or_reparse(lexical, "Nova data root")
    return lexical.resolve(strict=False)


def layout(root: Path) -> dict[str, Path]:
    return {
        "NOVA_DATA_ROOT": root,
        "NOVA_CONTINUITY_HOME": root / "memory" / "continuity-v2",
        "DUNBAR_STORE": root / "memory" / "dunbar" / "people.sqlite3",
        "CORKBOARD_HOME": root / "memory" / "corkboard",
        "registry": root / "estate" / "path-selectors.json",
        "manifest": root / "estate" / "manifest.json",
        "env_file": root / "estate" / "nova.env",
    }


def legacy_1_0_0_partial(root: Path) -> bool:
    """Recognize only the proven-empty footprint left by the old init order."""
    if not root.is_dir():
        return False
    allowed = {
        "memory",
        "memory/corkboard",
        "memory/dunbar",
        "memory/continuity-v2",
        "projects",
        "projects/project-records",
        "estate",
    }
    required = {"memory/corkboard", "memory/dunbar", "projects/project-records"}
    observed: set[str] = set()
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in directories:
            path = current_path / name
            _assert_no_link_or_reparse(path, "Legacy partial estate")
            relative = path.relative_to(root).as_posix()
            if relative not in allowed:
                return False
            observed.add(relative)
        if files:
            return False
    return required.issubset(observed)

def skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def service_script(service: str) -> Path:
    try:
        relative = SERVICE_ENTRYPOINTS[service]
    except KeyError:
        raise NovaEstateError(f"Unknown Nova service: {service}") from None
    path = skill_root().joinpath(*relative)
    if not path.is_file():
        raise NovaEstateError(f"Nova service entrypoint is missing: {path}")
    return path


def continuity_paths() -> dict[str, Path]:
    root = skill_root() / "cognitive-continuity"
    return {
        "root": root,
        "store": root / "scripts" / "continuity_store_v2.py",
        "worldline": root / "scripts" / "worldline.py",
        "validate": root / "scripts" / "validate_continuity_v2.py",
        "runtime": root / "scripts" / "workspace_runtime.py",
        "mutation_probe": Path(__file__).resolve().parent / "probe_continuity_mutation.py",
    }


def require_continuity_package() -> dict[str, Path]:
    paths = continuity_paths()
    missing = [str(path) for key, path in paths.items() if key != "root" and not path.is_file()]
    if missing:
        raise NovaEstateError("Canonical Cognitive Continuity package is incomplete: " + ", ".join(missing))
    return paths


def read_json(path: Path) -> dict[str, Any]:
    _assert_no_link_or_reparse(path, "JSON configuration")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except FileNotFoundError:
        raise NovaEstateError(f"Required file is missing: {path}") from None
    except OSError as exc:
        raise NovaEstateError(f"Could not read {path}: {exc}") from exc
    if first != second:
        raise NovaEstateError(f"File changed during stable read: {path}")
    try:
        value = json.loads(first.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NovaEstateError(f"Could not decode {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise NovaEstateError(f"Expected a JSON object: {path}")
    return value


def registry_values(registry: dict[str, Any], root: Path) -> dict[str, str]:
    if registry.get("format") != REGISTRY_FORMAT:
        raise NovaEstateError(f"Unsupported selector registry format: {registry.get('format')!r}")
    active = registry.get("active_values")
    if not isinstance(active, dict):
        raise NovaEstateError("Selector registry lacks active_values")
    values: dict[str, str] = {}
    for key in SELECTOR_KEYS:
        raw = active.get(key)
        if not isinstance(raw, str) or not raw.strip():
            raise NovaEstateError(f"Selector registry lacks {key}")
        lexical = _lexical_absolute(Path(raw).expanduser())
        _assert_no_link_or_reparse(lexical, key)
        values[key] = str(lexical.resolve(strict=False))
    if Path(values["NOVA_DATA_ROOT"]) != root:
        raise NovaEstateError("Registry NOVA_DATA_ROOT does not match the selected root")
    for key in SELECTOR_KEYS[1:]:
        target = Path(values[key])
        try:
            target.relative_to(root)
        except ValueError:
            raise NovaEstateError(f"{key} escapes NOVA_DATA_ROOT") from None
        if any(part.casefold() == ".codex" for part in target.parts):
            raise NovaEstateError(f"{key} resolves under .codex")
    return values


def _fsync_parent(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_parent(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def custom_root_requires_locator(root: Path) -> bool:
    return root != _lexical_absolute(platform_default_root()).resolve(strict=False)


def assert_locator_conflict_free(root: Path) -> Path | None:
    located = read_current_estate_locator()
    if located is not None and located != root:
        raise NovaEstateError(
            f"Current-estate locator already selects {located}; refusing to select conflicting root {root}"
        )
    return located


def write_current_estate_locator(root: Path) -> None:
    if not custom_root_requires_locator(root):
        return
    path = current_estate_locator_path()
    _assert_no_link_or_reparse(path, "Current-estate locator")
    atomic_json(
        path,
        {
            "format": "nova-current-estate-locator/v1",
            "root": str(root),
            "registry": "estate/path-selectors.json",
            "set_at_utc": utc_now(),
            "authority": "discovery_pointer_only_registry_must_corroborate",
        },
    )


def remove_current_estate_locator_if_owned(root: Path) -> None:
    path = current_estate_locator_path()
    try:
        located = read_current_estate_locator()
    except NovaEstateError:
        return
    if located != root:
        return
    try:
        path.unlink()
        _fsync_parent(path.parent)
    except OSError:
        return


def process_environment(values: dict[str, str]) -> dict[str, str]:
    """Replace inherited Nova selectors with one exact registry snapshot."""
    env = os.environ.copy()
    for key in MANAGED_ENVIRONMENT_KEYS:
        env.pop(key, None)
    env.update({key: values[key] for key in SELECTOR_KEYS})
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env

def user_environment_values(keys: tuple[str, ...]) -> dict[str, str | None]:
    if platform.system() != "Windows":
        return {key: None for key in keys}
    import winreg

    values: dict[str, str | None] = {}
    try:
        handle = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ)
    except FileNotFoundError:
        return {key: None for key in keys}
    with handle:
        for key in keys:
            try:
                value, _ = winreg.QueryValueEx(handle, key)
                values[key] = str(value)
            except FileNotFoundError:
                values[key] = None
    return values


def require_windows_environment_flag_supported(requested: bool) -> None:
    if requested and platform.system() != "Windows":
        raise NovaEstateError("--apply-user-environment is a Windows-only convenience and must not be used on this platform")


def apply_windows_user_environment(values: dict[str, str]) -> None:
    require_windows_environment_flag_supported(True)
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as handle:
        for key, value in values.items():
            winreg.SetValueEx(handle, key, 0, winreg.REG_SZ, value)
    try:
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF,
            0x001A,
            0,
            "Environment",
            0x0002,
            5000,
            None,
        )
    except Exception:
        pass


def run_json(command: Sequence[str], *, env: dict[str, str] | None = None) -> tuple[int, Any, str]:
    completed = subprocess.run(
        list(command),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parsed: Any = None
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = stdout
    return completed.returncode, parsed, stderr


def service_command(service: str, service_args: Sequence[str]) -> list[str]:
    return [sys.executable, "-B", "-X", "utf8", str(service_script(service)), *service_args]


def run_service_process(
    service: str,
    service_args: Sequence[str],
    values: dict[str, str],
    *,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = service_command(service, service_args)
    options: dict[str, Any] = {
        "env": process_environment(values),
        "check": False,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if capture:
        options.update(
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return subprocess.run(command, **options)


def launcher_payload() -> dict[str, Any]:
    entries: dict[str, Any] = {}
    ready = True
    for service, relative in SERVICE_ENTRYPOINTS.items():
        path = skill_root().joinpath(*relative)
        present = path.is_file()
        entries[service] = {"path": str(path), "present": present}
        ready = ready and present
    return {
        "ready": ready,
        "shell_used": False,
        "selector_source": "estate/path-selectors.json",
        "services": entries,
    }


def probe_mutation_support(canonical: dict[str, Path], values: dict[str, str]) -> dict[str, Any]:
    code, result, stderr = run_json(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(canonical["mutation_probe"]),
            "--runtime",
            str(canonical["runtime"]),
            "--workspace",
            values["NOVA_CONTINUITY_HOME"],
        ],
        env=process_environment(values),
    )
    if not isinstance(result, dict):
        result = {
            "format": "nova-continuity-mutation-support/v1",
            "supported": False,
            "probe_completed": False,
            "code": "probe_output_invalid",
            "detail": result,
            "source_mutated": False,
        }
    result["exit_code"] = code
    if stderr:
        result["stderr"] = stderr
    return result


def continuity_support(values: dict[str, str], *, validate: bool) -> dict[str, Any]:
    canonical = require_continuity_package()
    env = process_environment(values)
    open_code, opened, open_stderr = run_json(
        [sys.executable, "-B", "-X", "utf8", str(canonical["store"]), "open"],
        env=env,
    )
    result: dict[str, Any] = {
        "read": {
            "supported": open_code == 0,
            "exit_code": open_code,
            "result": opened,
            "stderr": open_stderr or None,
        },
        "mutation": probe_mutation_support(canonical, values),
    }
    if validate:
        code, validated, stderr = run_json(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(canonical["validate"]),
                values["NOVA_CONTINUITY_HOME"],
            ],
            env=env,
        )
        result["validation"] = {
            "supported": code == 0,
            "exit_code": code,
            "result": validated,
            "stderr": stderr or None,
        }
    return result


def load_configured_root(root_value: str | None) -> tuple[Path, dict[str, str], dict[str, Path]]:
    root = normalize_root(root_value)
    paths = layout(root)
    registry = read_json(paths["registry"])
    return root, registry_values(registry, root), paths


def status_payload(root: Path, *, root_source: str = "explicit") -> dict[str, Any]:
    paths = layout(root)
    payload: dict[str, Any] = {
        "format": "nova-free-estate-status/v3",
        "product_version": PRODUCT_VERSION,
        "root": str(root),
        "root_selection_source": root_source,
        "selector_authority": "registry",
        "registry": {"path": str(paths["registry"]), "present": paths["registry"].is_file()},
        "manifest": {"path": str(paths["manifest"]), "present": paths["manifest"].is_file()},
        "configured": False,
        "global_environment_required": False,
        "restart_required": False,
        "current_estate_locator": {
            "path": str(current_estate_locator_path()),
            "present": os.path.lexists(current_estate_locator_path()),
            "role": "discovery_pointer_only",
        },
    }
    if not paths["registry"].is_file():
        if legacy_1_0_0_partial(root):
            payload["state"] = "legacy_1_0_0_partial"
            payload["repair"] = "retry init against the same root; only the proven-empty legacy footprint will be replaced"
        else:
            payload["state"] = "not_configured"
        payload["default_is_outside_codex"] = ".codex" not in {part.casefold() for part in root.parts}
        return payload
    try:
        registry = read_json(paths["registry"])

        values = registry_values(registry, root)
        support = continuity_support(values, validate=False)
        launcher = launcher_payload()
        environment_matches = {key: os.environ.get(key) == value for key, value in values.items()}
        continuity_present = Path(values["NOVA_CONTINUITY_HOME"]).is_dir()
        read_supported = bool(support["read"].get("supported"))
        mutation_supported = bool(support["mutation"].get("supported"))
        if read_supported and mutation_supported:
            operating_mode = "full"
        elif read_supported:
            operating_mode = "read_only"
        else:
            operating_mode = "unavailable"
        payload.update(
            selectors=values,
            environment_convenience={
                "supported": platform.system() == "Windows",
                "required": False,
                "matches_current_process": environment_matches,
            },
            configured=True,
            continuity_present=continuity_present,
            continuity_read_support=support["read"],
            continuity_mutation_support=support["mutation"],
            continuity_operating_mode=operating_mode,
            launcher=launcher,
            state=(
                "configured"
                if continuity_present and launcher["ready"]
                else "configured_service_missing"
            ),
        )
    except NovaEstateError as exc:
        payload["state"] = "registry_invalid"
        payload["error"] = str(exc)
    return payload

def command_plan(args: argparse.Namespace) -> int:
    root = normalize_root(args.root)
    paths = layout(root)
    emit(
        {
            "format": "nova-free-estate-plan/v3",
            "product_version": PRODUCT_VERSION,
            "root": str(root),
            "current": status_payload(root, root_source=root_selection_source(args.root)),
            "proposed_selectors": {key: str(paths[key]) for key in SELECTOR_KEYS},
            "effects_if_authorized": [
                "initialize one absent Cognitive Continuity v2 workspace",
                "publish one complete selector registry and estate manifest",
                "create empty Corkboard and Dunbar locations",
                "optionally set current-user environment selectors on Windows",
            ],
            "runtime_contract": {
                "selector_authority": "registry",
                "global_environment_required": False,
                "launcher": "nova_estate.py run",
            },
            "does_not": [
                "install or replace the Nova the Optimal AI plugin",
                "import contacts, conversations, projects, reminders, or existing stores",
                "enable Arm's Reach, a prompt hook, a local model, embeddings, or a vector database",
                "delete, migrate, merge, or publish data",
            ],
        }
    )
    return 0


def command_status(args: argparse.Namespace) -> int:
    root = normalize_root(args.root)
    emit(status_payload(root, root_source=root_selection_source(args.root)))
    return 0


def _create_parent_chain(parent: Path) -> list[Path]:
    missing: list[Path] = []
    cursor = parent
    while not cursor.exists():
        missing.append(cursor)
        if cursor.parent == cursor:
            raise NovaEstateError(f"Cannot create estate parent: {parent}")
        cursor = cursor.parent
    _assert_no_link_or_reparse(cursor, "Estate parent")
    created: list[Path] = []
    try:
        for path in reversed(missing):
            path.mkdir()
            created.append(path)
    except OSError as exc:
        for path in reversed(created):
            try:
                path.rmdir()
            except OSError:
                pass
        raise NovaEstateError(f"Could not create estate parent {parent}: {exc}") from exc
    return created


def _cleanup_empty_parents(created: Sequence[Path]) -> None:
    for path in reversed(created):
        try:
            path.rmdir()
        except OSError:
            pass


def _bootstrap_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in MANAGED_ENVIRONMENT_KEYS:
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _selector_values(paths: dict[str, Path]) -> dict[str, str]:
    return {key: str(paths[key]) for key in SELECTOR_KEYS}


def _env_text(values: dict[str, str]) -> str:
    return "\n".join(f"export {key}={json.dumps(value)}" for key, value in values.items()) + "\n"


def command_init(args: argparse.Namespace) -> int:
    require_windows_environment_flag_supported(args.apply_user_environment)
    root = normalize_root(args.root)
    locator_preexisting = assert_locator_conflict_free(root)
    paths = layout(root)
    legacy_partial = False
    if root.exists():
        current = status_payload(root, root_source="explicit_cli")
        if current.get("configured"):
            emit(
                {
                    "format": "nova-free-estate-init/v3",
                    "state": "already_configured",
                    "status": current,
                    "source_mutated": False,
                }
            )
            return 0
        if current.get("state") == "legacy_1_0_0_partial":
            legacy_partial = True
        else:
            raise NovaEstateError("Estate target already exists but is not a complete configured estate; inspect it before repair")

    canonical = require_continuity_package()
    created_parents: list[Path] = []
    staging: Path | None = None
    legacy_backup: Path | None = None
    published = False
    try:
        created_parents = _create_parent_chain(root.parent)
        staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.init-", dir=root.parent))
        staged_paths = layout(staging)
        staged_paths["CORKBOARD_HOME"].mkdir(parents=True, exist_ok=False)
        staged_paths["DUNBAR_STORE"].parent.mkdir(parents=True, exist_ok=False)
        continuity = staged_paths["NOVA_CONTINUITY_HOME"]
        code, receipt, stderr = run_json(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(canonical["store"]),
                "init",
                str(continuity),
                "--user",
                args.user,
                "--project",
                "*",
                "--agent",
                "Nova",
            ],
            env=_bootstrap_environment(),
        )
        if code != 0:
            raise NovaEstateError(f"Cognitive Continuity initialization failed: {stderr or receipt}")

        selector_values = _selector_values(paths)
        previous = (
            user_environment_values(SELECTOR_KEYS)
            if args.apply_user_environment
            else {key: None for key in SELECTOR_KEYS}
        )
        registry = {
            "format": REGISTRY_FORMAT,
            "set_at_utc": utc_now(),
            "scope": "UserEnvironmentAndProductRegistry" if args.apply_user_environment else "ProductRegistry",
            "requires_codex_restart": bool(args.apply_user_environment),
            "previous_user_values": previous,
            "active_values": {
                **selector_values,
                "MIND_CORE_DATABASE": None,
                "MIND_HOOK_RECEIPT_DIRECTORY": None,
            },
            "note": "The registry is authoritative. Global environment selectors are optional Windows convenience only.",
        }
        manifest = {
            "format": MANIFEST_FORMAT,
            "product": "Nova the Optimal AI Free",
            "product_version": PRODUCT_VERSION,
            "created_at_utc": utc_now(),
            "selector_registry": "estate/path-selectors.json",
            "service_launcher": "nova-operations/scripts/nova_estate.py run",
            "services": {
                "continuity": "memory/continuity-v2",
                "dunbar": "memory/dunbar/people.sqlite3",
                "corkboard": "memory/corkboard",
            },
            "source_imported": False,
        }
        atomic_json(staged_paths["manifest"], manifest)
        atomic_text(staged_paths["env_file"], _env_text(selector_values))
        atomic_json(staged_paths["registry"], registry)
        _fsync_parent(staging)
        if legacy_partial:
            if not legacy_1_0_0_partial(root):
                raise NovaEstateError("Legacy partial estate changed during repair; nothing was replaced")
            legacy_backup = root.parent / f".{root.name}.legacy-1.0.0-{secrets.token_hex(8)}"
            os.rename(root, legacy_backup)
            try:
                os.rename(staging, root)
            except BaseException:
                os.rename(legacy_backup, root)
                legacy_backup = None
                raise
        else:
            os.rename(staging, root)
        staging = None
        published = True
        _fsync_parent(root.parent)
        write_current_estate_locator(root)
        if legacy_backup is not None:
            shutil.rmtree(legacy_backup)
            legacy_backup = None
    except BaseException:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if published:
            if locator_preexisting is None:
                remove_current_estate_locator_if_owned(root)
            shutil.rmtree(root, ignore_errors=True)
            if legacy_backup is not None and legacy_backup.exists() and not root.exists():
                os.rename(legacy_backup, root)
                legacy_backup = None
        _cleanup_empty_parents(created_parents)
        raise

    environment_applied = False
    if args.apply_user_environment:
        apply_windows_user_environment(selector_values)
        environment_applied = True
    emit(
        {
            "format": "nova-free-estate-init/v3",
            "state": "initialized",
            "root": str(root),
            "selectors": selector_values,
            "continuity_receipt": receipt,
            "environment_applied": environment_applied,
            "global_environment_required": False,
            "restart_required": environment_applied,
            "source_mutated": True,
            "recovered_legacy_1_0_0_partial": legacy_partial,
        }
    )
    return 0


def command_upgrade(args: argparse.Namespace) -> int:
    """Refresh a compatible Nova estate without claiming optional edition selectors."""
    require_windows_environment_flag_supported(args.apply_user_environment)
    root = normalize_root(args.root)
    assert_locator_conflict_free(root)
    paths = layout(root)
    registry = read_json(paths["registry"])
    manifest = read_json(paths["manifest"])
    values = registry_values(registry, root)
    if manifest.get("format") != MANIFEST_FORMAT:
        raise NovaEstateError(f"Unsupported estate manifest format: {manifest.get('format')!r}")

    source_mutated = False
    if manifest.get("product") != "Nova the Optimal AI Free" or manifest.get("product_version") != PRODUCT_VERSION:
        manifest["product"] = "Nova the Optimal AI Free"
        manifest["product_version"] = PRODUCT_VERSION
        manifest["upgraded_at_utc"] = utc_now()
        source_mutated = True
    services = manifest.get("services")
    if not isinstance(services, dict):
        services = {}
        manifest["services"] = services
        source_mutated = True
    expected_services = {
        "continuity": "memory/continuity-v2",
        "dunbar": "memory/dunbar/people.sqlite3",
        "corkboard": "memory/corkboard",
    }
    for name, relative in expected_services.items():
        if services.get(name) != relative:
            services[name] = relative
            source_mutated = True
    if manifest.get("service_launcher") != "nova-operations/scripts/nova_estate.py run":
        manifest["service_launcher"] = "nova-operations/scripts/nova_estate.py run"
        source_mutated = True

    registry["set_at_utc"] = utc_now()
    registry["upgraded_for_product_version"] = PRODUCT_VERSION
    registry["requires_codex_restart"] = bool(args.apply_user_environment)
    registry["note"] = "The registry is authoritative. Global environment selectors are optional Windows convenience only."
    write_current_estate_locator(root)
    atomic_json(paths["manifest"], manifest)
    atomic_text(paths["env_file"], _env_text(values))
    atomic_json(paths["registry"], registry)
    environment_applied = False
    if args.apply_user_environment:
        apply_windows_user_environment(values)
        environment_applied = True
    emit(
        {
            "format": "nova-free-estate-upgrade/v3",
            "state": "upgraded" if source_mutated else "already_current",
            "product_version": PRODUCT_VERSION,
            "root": str(root),
            "selectors": values,
            "preserved_extra_selectors": sorted(
                key for key in registry.get("active_values", {}) if key not in SELECTOR_KEYS
            ),
            "environment_applied": environment_applied,
            "global_environment_required": False,
            "restart_required": environment_applied,
            "source_mutated": source_mutated,
        }
    )
    return 0

def command_run(args: argparse.Namespace) -> int:
    _, values, _ = load_configured_root(args.root)
    forwarded = list(args.service_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    completed = run_service_process(args.service, forwarded, values)
    return int(completed.returncode)


def command_doctor(args: argparse.Namespace) -> int:
    root, values, _ = load_configured_root(args.root)
    support = continuity_support(values, validate=True)
    launcher = launcher_payload()
    locations = {
        "continuity": Path(values["NOVA_CONTINUITY_HOME"]).is_dir(),
        "dunbar_parent": Path(values["DUNBAR_STORE"]).parent.is_dir(),
        "corkboard": Path(values["CORKBOARD_HOME"]).is_dir(),
    }
    read_supported = bool(support["read"].get("supported"))
    mutation_supported = bool(support["mutation"].get("supported"))
    validation_supported = bool(support["validation"].get("supported"))
    healthy = (
        read_supported
        and mutation_supported
        and validation_supported
        and launcher["ready"]
        and all(locations.values())
    )
    operating_mode = "full" if read_supported and mutation_supported else ("read_only" if read_supported else "unavailable")
    emit(
        {
            "format": "nova-free-estate-doctor/v3",
            "product_version": PRODUCT_VERSION,
            "root": str(root),
            "healthy": healthy,
            "operating_mode": operating_mode,
            "selector_authority": "registry",
            "global_environment_required": False,
            "environment_convenience": {
                "supported": platform.system() == "Windows",
                "required": False,
                "matches_current_process": {
                    key: os.environ.get(key) == value for key, value in values.items()
                },
            },
            "service_locations": locations,
            "launcher": launcher,
            "continuity_read_support": support["read"],
            "continuity_mutation_support": support["mutation"],
            "continuity_validation": support["validation"],
            "source_mutated": False,
        }
    )
    return 0 if healthy else 2


def command_worldline(args: argparse.Namespace) -> int:
    _, values, _ = load_configured_root(args.root)
    command_args = [
        args.mode,
        "--task",
        args.task,
        "--user",
        args.user,
        "--project",
        args.project,
        "--agent",
        "Nova",
    ]
    completed = run_service_process("worldline", command_args, values, capture=True)
    if completed.returncode == 0:
        sys.stdout.write(completed.stdout)
        if completed.stdout and not completed.stdout.endswith("\n"):
            sys.stdout.write("\n")
        return 0
    detail: Any = completed.stderr.strip() or completed.stdout.strip()
    try:
        detail = json.loads(detail)
    except (TypeError, json.JSONDecodeError):
        pass
    return fail("worldline_failed", "Canonical Worldline operation failed", detail=detail)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for name, function in (("plan", command_plan), ("status", command_status)):
        item = commands.add_parser(name)
        item.add_argument("--root")
        item.set_defaults(function=function)

    init = commands.add_parser("init")
    init.add_argument("--root", required=True)
    init.add_argument("--user", default="local-user")
    init.add_argument("--apply-user-environment", action="store_true")
    init.set_defaults(function=command_init)

    upgrade = commands.add_parser("upgrade")
    upgrade.add_argument("--root")
    upgrade.add_argument("--apply-user-environment", action="store_true")
    upgrade.set_defaults(function=command_upgrade)

    doctor = commands.add_parser("doctor")
    doctor.add_argument("--root")
    doctor.set_defaults(function=command_doctor)

    run = commands.add_parser("run", help="Run a bundled service with the exact registry selector snapshot")
    run.add_argument("--root")
    run.add_argument("service", choices=tuple(SERVICE_ENTRYPOINTS))
    run.add_argument("service_args", nargs=argparse.REMAINDER)
    run.set_defaults(function=command_run)

    worldline = commands.add_parser("worldline", help="Compatibility facade over the registry-backed worldline service")
    worldline.add_argument("--root")
    worldline.add_argument("--mode", choices=("resume", "status", "checkpoint", "inspect"), required=True)
    worldline.add_argument("--project", required=True)
    worldline.add_argument("--task", required=True)
    worldline.add_argument("--user", default="local-user")
    worldline.set_defaults(function=command_worldline)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        return int(args.function(args))
    except NovaEstateError as exc:
        return fail("estate_error", str(exc))
    except OSError as exc:
        return fail("estate_io_error", str(exc))
    except KeyboardInterrupt:
        return fail("cancelled", "Operation cancelled before completion")


if __name__ == "__main__":
    raise SystemExit(main())
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

DEFAULT_IGNORES = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "node_modules", "vendor",
    ".venv", "venv", "env", "dist", "build", "coverage", ".coverage",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__", "target",
}


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def iter_files(root: Path, max_files: int = 50_000, extra_ignores: Iterable[str] = ()):
    root = root.resolve()
    ignores = DEFAULT_IGNORES | set(extra_ignores)
    seen = 0
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in ignores and not Path(current, d).is_symlink())
        for name in sorted(files):
            path = Path(current, name)
            if path.is_symlink():
                continue
            seen += 1
            if seen > max_files:
                raise RuntimeError(f"file cap exceeded ({max_files})")
            yield path


def load_data(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError("YAML input requires optional PyYAML; use canonical JSON for no-dependency validation") from exc
        return yaml.safe_load(text)
    raise ValueError(f"unsupported data format: {path.suffix}")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

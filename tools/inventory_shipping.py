from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
EXPECTED = ("augment-of-mind", "nova-the-optimal-ai")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_plugin(plugin_name: str) -> dict:
    plugin_root = (PLUGINS / plugin_name).resolve()
    if plugin_root.parent != PLUGINS.resolve() or not plugin_root.is_dir():
        raise ValueError(f"invalid plugin root: {plugin_name}")

    directories: list[dict] = []
    all_files: list[dict] = []
    symlinks: list[str] = []

    for current, child_dirs, child_files in os.walk(plugin_root, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(plugin_root).as_posix() or "."
        directory_record = {
            "path": relative_dir,
            "directories": sorted(child_dirs),
            "files": sorted(child_files),
        }
        directories.append(directory_record)

        for child_dir in child_dirs:
            candidate = current_path / child_dir
            if candidate.is_symlink():
                symlinks.append(candidate.relative_to(plugin_root).as_posix())

        for child_file in sorted(child_files):
            path = current_path / child_file
            relative_file = path.relative_to(plugin_root).as_posix()
            if path.is_symlink():
                symlinks.append(relative_file)
                continue
            all_files.append(
                {
                    "path": relative_file,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )

    tree = hashlib.sha256()
    for item in sorted(all_files, key=lambda record: record["path"]):
        tree.update(f'{item["path"]}\0{item["bytes"]}\0{item["sha256"]}\n'.encode("utf-8"))

    return {
        "plugin": plugin_name,
        "directory_count": len(directories),
        "file_count": len(all_files),
        "byte_count": sum(item["bytes"] for item in all_files),
        "tree_sha256": tree.hexdigest(),
        "symlinks": sorted(symlinks),
        "directories": sorted(directories, key=lambda record: record["path"]),
        "files": sorted(all_files, key=lambda record: record["path"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Enumerate every shipping plugin directory and file.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plugins = [inspect_plugin(name) for name in EXPECTED]
    receipt = {
        "format": "nova-mind-shipping-directory-inventory/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Every directory and file under the two shipping plugin roots; symlinks are listed and never followed.",
        "plugins": plugins,
        "totals": {
            "directories": sum(item["directory_count"] for item in plugins),
            "files": sum(item["file_count"] for item in plugins),
            "bytes": sum(item["byte_count"] for item in plugins),
            "symlinks": sum(len(item["symlinks"]) for item in plugins),
        },
    }
    rendered = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        destination = args.output if args.output.is_absolute() else ROOT / args.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if receipt["totals"]["symlinks"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

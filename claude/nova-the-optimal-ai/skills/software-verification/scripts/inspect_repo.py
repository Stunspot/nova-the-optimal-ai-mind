#!/usr/bin/env python3
"""Produce a bounded, non-content-reading repository inventory."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from common.filesystem import iter_files, relative_posix, write_json

LANGUAGE_EXTENSIONS = {
    ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript",
    ".py": "Python", ".java": "Java", ".kt": "Kotlin", ".go": "Go", ".rs": "Rust",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift", ".cpp": "C++",
    ".c": "C", ".h": "C/C++ Header", ".sql": "SQL", ".sh": "Shell", ".ps1": "PowerShell",
}
MANIFESTS = {
    "package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json", "pyproject.toml",
    "requirements.txt", "poetry.lock", "uv.lock", "Pipfile", "setup.py", "pom.xml",
    "build.gradle", "build.gradle.kts", "go.mod", "Cargo.toml", "Gemfile", "composer.json",
}
CONFIG_HINTS = ("pytest", "jest", "vitest", "playwright", "tox", "ruff", "mypy", "eslint", "tsconfig")
CI_PARTS = {".github/workflows", ".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile", ".circleci"}


def inspect(root: Path, max_files: int = 50_000) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"repository path is not a directory: {root}")
    languages: Counter[str] = Counter()
    manifests, configs, test_files, test_dirs, ci_files = [], [], [], set(), []
    warnings = []
    total = 0
    try:
        paths = iter_files(root, max_files=max_files)
        for path in paths:
            total += 1
            rel = relative_posix(path, root)
            suffix = path.suffix.lower()
            if suffix in LANGUAGE_EXTENSIONS:
                languages[LANGUAGE_EXTENSIONS[suffix]] += 1
            if path.name in MANIFESTS:
                manifests.append(rel)
            low = rel.lower()
            config_name = path.name.lower()
            if (".config." in config_name or any(config_name.startswith(hint) for hint in CONFIG_HINTS)) and suffix in {".json", ".js", ".cjs", ".mjs", ".ts", ".toml", ".ini", ".cfg", ".yaml", ".yml"}:
                configs.append(rel)
            parts = {p.lower() for p in path.parts}
            if "tests" in parts or "test" in parts or ".test." in path.name or ".spec." in path.name or path.name.startswith("test_"):
                test_files.append(rel)
                for marker in ("tests", "test", "__tests__"):
                    if marker in parts:
                        index = [p.lower() for p in path.parts].index(marker)
                        test_dirs.add(Path(*path.parts[: index + 1]).resolve().relative_to(root).as_posix())
                        break
            if any(ci in low for ci in CI_PARTS):
                ci_files.append(rel)
    except RuntimeError as exc:
        warnings.append(str(exc))

    return {
        "format_version": "1.0",
        "root": str(root),
        "file_count": total,
        "languages": [{"name": name, "files": count} for name, count in languages.most_common()],
        "manifests": sorted(manifests),
        "test_directories": sorted(test_dirs),
        "test_files": sorted(test_files)[:500],
        "test_file_count": len(test_files),
        "config_files": sorted(set(configs)),
        "ci_files": sorted(set(ci_files)),
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-files", type=int, default=50_000)
    args = parser.parse_args()
    try:
        result = inspect(args.repository, args.max_files)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.output:
        write_json(args.output, result)
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

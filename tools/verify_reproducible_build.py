#!/usr/bin/env python3
"""Build the contest releases twice and persist an observed reproducibility receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from build_release import RELEASE, ROOT, build


OBSERVED_FILES = (
    "augment-of-mind-1.0.0.zip",
    "nova-the-optimal-ai-1.0.0.zip",
    "release-receipt.json",
    "SHA256SUMS",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(run: int, elapsed_seconds: float) -> dict[str, object]:
    receipt = json.loads((RELEASE / "release-receipt.json").read_text(encoding="utf-8"))
    return {
        "run": run,
        "elapsed_seconds": round(elapsed_seconds, 6),
        "files": {
            name: {
                "sha256": sha256(RELEASE / name),
                "bytes": (RELEASE / name).stat().st_size,
            }
            for name in OBSERVED_FILES
        },
        "source_trees": {
            item["plugin"]: item["source_tree_sha256"] for item in receipt["archives"]
        },
        "member_counts": {
            item["plugin"]: item["member_count"] for item in receipt["archives"]
        },
    }


def run_build(run: int) -> dict[str, object]:
    started = time.perf_counter()
    build()
    return snapshot(run, time.perf_counter() - started)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "verification" / "build-reproducibility.json",
    )
    args = parser.parse_args()

    first = run_build(1)
    second = run_build(2)
    identical_files = first["files"] == second["files"]
    identical_sources = first["source_trees"] == second["source_trees"]
    identical_members = first["member_counts"] == second["member_counts"]
    valid = identical_files and identical_sources and identical_members
    report = {
        "format": "nova-mind-build-reproducibility/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "valid": valid,
        "runs": [first, second],
        "comparison": {
            "release_files_byte_identical": identical_files,
            "source_tree_hashes_identical": identical_sources,
            "member_counts_identical": identical_members,
        },
        "boundary": (
            "This receipt observes two consecutive builds from one source checkout and host. "
            "It proves byte reproducibility for these runs, not cross-platform reproducibility."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["comparison"], indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

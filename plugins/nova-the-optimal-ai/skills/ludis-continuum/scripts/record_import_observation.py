from __future__ import annotations

import argparse
import hashlib
import json
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGETS = ("alchemy", "foundry-v14")
RESULTS = ("imported", "partial", "failed")


class ObservationError(ValueError):
    """An import observation could not be recorded safely."""


def _file_signature(info: Any) -> tuple[int, int, int, int, int, int]:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_mode),
        int(info.st_size),
        int(info.st_mtime_ns),
        int(info.st_ctime_ns),
    )


@dataclass(frozen=True)
class FrozenObservationInput:
    source_path: Path
    resolved_path: Path
    signature: tuple[int, int, int, int, int, int]
    data: bytes
    sha256: str

    def record(self) -> dict[str, Any]:
        return {"name": self.source_path.name, "bytes": len(self.data), "sha256": self.sha256}


@dataclass(frozen=True)
class ObservationCapture:
    observation: dict[str, Any]
    inputs: tuple[FrozenObservationInput, ...]


def _freeze_file_evidence(path: Path) -> FrozenObservationInput:
    source_path = Path(path).absolute()
    try:
        resolved = source_path.resolve(strict=True)
        before = resolved.stat()
    except OSError as exc:
        raise ObservationError(f"evidence could not be resolved: {path}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise ObservationError(f"evidence is not a regular file: {path}")
    data = resolved.read_bytes()
    after = resolved.stat()
    signature = _file_signature(before)
    if signature != _file_signature(after) or len(data) != after.st_size:
        raise ObservationError(f"evidence changed while being read: {path}")
    return FrozenObservationInput(
        source_path=source_path,
        resolved_path=resolved,
        signature=signature,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _recheck_observation_inputs(inputs: tuple[FrozenObservationInput, ...]) -> None:
    for frozen in inputs:
        try:
            resolved_now = frozen.source_path.resolve(strict=True)
            if resolved_now != frozen.resolved_path:
                raise ObservationError(f"evidence path identity changed after capture: {frozen.source_path}")
            before = resolved_now.stat()
            if not stat.S_ISREG(before.st_mode) or _file_signature(before) != frozen.signature:
                raise ObservationError(f"evidence changed after capture: {frozen.source_path}")
            data = resolved_now.read_bytes()
            after = resolved_now.stat()
        except ObservationError:
            raise
        except OSError as exc:
            raise ObservationError(f"evidence could not be rechecked after capture: {frozen.source_path}") from exc
        if (
            _file_signature(before) != _file_signature(after)
            or _file_signature(after) != frozen.signature
            or data != frozen.data
            or hashlib.sha256(data).hexdigest() != frozen.sha256
        ):
            raise ObservationError(f"evidence changed after capture: {frozen.source_path}")


def file_evidence(path: Path) -> dict[str, Any]:
    frozen = _freeze_file_evidence(path)
    _recheck_observation_inputs((frozen,))
    return frozen.record()

def normalized_time(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    candidate = value.strip()
    if not candidate:
        raise ObservationError("observed_at cannot be empty")
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ObservationError("observed_at must be an ISO 8601 timestamp with a timezone") from exc
    if parsed.tzinfo is None:
        raise ObservationError("observed_at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def capture_observation(
    bundle: Path,
    *,
    target: str,
    target_version: str,
    result: str,
    asserted_by: str,
    observed_at: str | None = None,
    notes: str = "",
    evidence: list[Path] | None = None,
) -> ObservationCapture:
    if target not in TARGETS:
        raise ObservationError(f"unsupported target: {target}")
    if result not in RESULTS:
        raise ObservationError(f"unsupported result: {result}")
    if not target_version.strip():
        raise ObservationError("target_version is required")
    if not asserted_by.strip():
        raise ObservationError("asserted_by is required")

    evidence_paths = [Path(path) for path in (evidence or [])]
    names = [path.name.casefold() for path in evidence_paths]
    if len(names) != len(set(names)):
        raise ObservationError("evidence filenames must be unique (case-insensitive)")

    frozen_bundle = _freeze_file_evidence(bundle)
    frozen_evidence = tuple(_freeze_file_evidence(path) for path in evidence_paths)
    inputs = (frozen_bundle, *frozen_evidence)
    resolved_keys = [str(item.resolved_path).casefold() for item in inputs]
    if len(resolved_keys) != len(set(resolved_keys)):
        raise ObservationError("bundle and evidence paths must refer to distinct files")

    observation = {
        "format": "cd-ludis-import-observation/v1",
        "scope": "campaign_local_observation",
        "promotes_product_compatibility": False,
        "assertion_type": "unauthenticated_local_operator_attestation",
        "asserted_by": asserted_by.strip(),
        "observed_at": normalized_time(observed_at),
        "target": {"id": target, "version": target_version.strip()},
        "result": result,
        "bundle": frozen_bundle.record(),
        "evidence": [item.record() for item in frozen_evidence],
        "notes": notes.strip(),
        "limitations": (
            "This receipt records one local attempt against exact bytes. It does not authenticate identity, "
            "certify semantic correctness, or change Ludis product compatibility claims."
        ),
    }
    _recheck_observation_inputs(inputs)
    return ObservationCapture(observation=observation, inputs=inputs)


def build_observation(
    bundle: Path,
    *,
    target: str,
    target_version: str,
    result: str,
    asserted_by: str,
    observed_at: str | None = None,
    notes: str = "",
    evidence: list[Path] | None = None,
) -> dict[str, Any]:
    return capture_observation(
        bundle,
        target=target,
        target_version=target_version,
        result=result,
        asserted_by=asserted_by,
        observed_at=observed_at,
        notes=notes,
        evidence=evidence,
    ).observation

def write_observation(
    output: Path,
    observation: dict[str, Any],
    *,
    frozen_inputs: tuple[FrozenObservationInput, ...] = (),
) -> Path:
    output = output.resolve()
    if output.exists():
        raise ObservationError(f"immutable observation path already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(observation, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    if frozen_inputs:
        _recheck_observation_inputs(frozen_inputs)
    with output.open("xb") as destination:
        destination.write(payload)
    return output


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Record one local Alchemy or Foundry import attempt without promoting a product-wide claim."
    )
    command.add_argument("bundle", type=Path, help="Exact ZIP that was attempted.")
    command.add_argument("output", type=Path, help="New JSON receipt path; existing files are never replaced.")
    command.add_argument("--target", choices=TARGETS, required=True)
    command.add_argument("--target-version", required=True)
    command.add_argument("--result", choices=RESULTS, required=True)
    command.add_argument("--asserted-by", required=True)
    command.add_argument("--observed-at", help="Optional ISO 8601 timestamp with timezone; defaults to now in UTC.")
    command.add_argument("--notes", default="")
    command.add_argument("--evidence", type=Path, action="append", default=[])
    return command


def main() -> int:
    args = parser().parse_args()
    try:
        capture = capture_observation(
            args.bundle,
            target=args.target,
            target_version=args.target_version,
            result=args.result,
            asserted_by=args.asserted_by,
            observed_at=args.observed_at,
            notes=args.notes,
            evidence=args.evidence,
        )
        output = write_observation(args.output, capture.observation, frozen_inputs=capture.inputs)
        print(f"PASS: LOCAL IMPORT OBSERVATION: {output}")
        print(f"BUNDLE SHA256: {capture.observation['bundle']['sha256'].upper()}")
        print("COMPATIBILITY: unchanged; this receipt cannot promote product support")
        return 0
    except (ObservationError, OSError) as exc:
        print(f"FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
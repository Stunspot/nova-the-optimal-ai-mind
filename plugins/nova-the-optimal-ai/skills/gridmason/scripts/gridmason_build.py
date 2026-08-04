#!/usr/bin/env python3
"""Compile and verify deterministic Gridmason Build Spec v1 bundles.

This tool is deliberately static: it does not read or modify Minecraft worlds,
does not emit native Minecraft formats, and does not contact a network service.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any


FORMAT = "gridmason-build-spec/v1"
SCHEMA_VERSION = 1
EXPECTED_FILES = (
    "build-spec.canonical.json",
    "build-spec.sha256",
    "materials.csv",
    "layers.md",
    "preview.svg",
    "compile-receipt.json",
)
MAX_AXIS = 128
MAX_VOLUME = 65_536
MAX_LAYER_AREA = 4_096
MAX_PALETTE = 256
MAX_PLACEMENTS = 65_536
MAX_UNSUPPORTED = 32

ARTIFACT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
BLOCK_ID_RE = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")
PALETTE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,11}$")
STATE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
STATE_VALUE_RE = re.compile(r"^[a-z0-9_.-]{1,64}$")
SWATCH_RE = re.compile(r"^#[0-9A-F]{6}$")
VERSION_RE = re.compile(r"^[ -~]{1,64}$")

ENVIRONMENTS = {"vanilla", "paper", "server", "modded", "realm", "addon", "other"}
UNSUPPORTED_VALUES = {
    "entities",
    "block_entities",
    "scheduled_ticks",
    "inventories",
    "biomes",
    "fluids",
    "commands",
    "native_formats",
    "world_actions",
}
EVIDENCE_STATES = {"OBSERVED", "REPORTED", "STATICALLY VALID", "LIKELY", "UNVERIFIED"}


class BuildSpecError(ValueError):
    """The submitted document does not satisfy the Build Spec contract."""


class IntegrityError(BuildSpecError):
    """A compiled bundle is not byte-identical to its deterministic rendering."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BuildSpecError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise BuildSpecError(f"non-finite JSON value: {value}")


def load_spec(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"cannot read {path}: {exc}") from exc
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except json.JSONDecodeError as exc:
        raise BuildSpecError(f"invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(value, dict):
        raise BuildSpecError("root must be a JSON object")
    return value


def _expect_keys(value: dict[str, Any], expected: set[str], location: str) -> None:
    actual = set(value)
    missing = expected - actual
    extra = actual - expected
    if missing:
        raise BuildSpecError(f"{location} missing required fields: {', '.join(sorted(missing))}")
    if extra:
        raise BuildSpecError(f"{location} has unknown fields: {', '.join(sorted(extra))}")


def _string(value: Any, location: str, maximum: int = 4_096) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise BuildSpecError(f"{location} must be a non-empty string of at most {maximum} characters")
    if _contains_control_character(value):
        raise BuildSpecError(f"{location} must not contain control characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise BuildSpecError(f"{location} contains invalid Unicode") from exc
    return value


def _contains_control_character(value: str) -> bool:
    return any(ord(char) < 0x20 or 0x7F <= ord(char) <= 0x9F for char in value)


def _integer(value: Any, location: str, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool):
        raise BuildSpecError(f"{location} must be an integer")
    if isinstance(value, int):
        normalized = value
    elif isinstance(value, float) and value.is_integer():
        normalized = int(value)
    else:
        raise BuildSpecError(f"{location} must be an integer")
    if minimum is not None and normalized < minimum:
        raise BuildSpecError(f"{location} must be at least {minimum}")
    if maximum is not None and normalized > maximum:
        raise BuildSpecError(f"{location} must be at most {maximum}")
    return normalized


def _object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BuildSpecError(f"{location} must be an object")
    return value


def _coordinate_object(value: Any, location: str, *, positive: bool) -> dict[str, int]:
    item = _object(value, location)
    _expect_keys(item, {"x", "y", "z"}, location)
    low = 1 if positive else -(2**31)
    high = MAX_AXIS if positive else 2**31 - 1
    return {axis: _integer(item[axis], f"{location}.{axis}", low, high) for axis in ("x", "y", "z")}


def _canonical_state(value: Any, location: str) -> dict[str, str]:
    item = _object(value, location)
    normalized: dict[str, str] = {}
    for key, state_value in item.items():
        if not isinstance(key, str) or not STATE_KEY_RE.fullmatch(key):
            raise BuildSpecError(f"{location} has invalid state key: {key!r}")
        state_text = _string(state_value, f"{location}.{key}", 64)
        if not STATE_VALUE_RE.fullmatch(state_text):
            raise BuildSpecError(f"{location}.{key} has invalid state value")
        normalized[key] = state_text
    return dict(sorted(normalized.items()))


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def validate_and_normalize(spec: dict[str, Any]) -> dict[str, Any]:
    _expect_keys(
        spec,
        {
            "format",
            "schema_version",
            "artifact_id",
            "title",
            "target",
            "coordinate_frame",
            "origin",
            "size",
            "air_policy",
            "palette",
            "placements",
            "unsupported",
            "provenance",
        },
        "root",
    )
    if spec["format"] != FORMAT:
        raise BuildSpecError(f"format must equal {FORMAT!r}")
    _integer(spec["schema_version"], "schema_version", SCHEMA_VERSION, SCHEMA_VERSION)

    artifact_id = _string(spec["artifact_id"], "artifact_id", 63)
    if not ARTIFACT_ID_RE.fullmatch(artifact_id):
        raise BuildSpecError("artifact_id must contain lowercase letters, digits, and hyphens")
    title = _string(spec["title"], "title", 120)

    target = _object(spec["target"], "target")
    _expect_keys(target, {"edition", "game_version", "environment", "loader_or_server"}, "target")
    if target["edition"] not in {"java", "bedrock"}:
        raise BuildSpecError("target.edition must be 'java' or 'bedrock'")
    game_version = _string(target["game_version"], "target.game_version", 64)
    if not VERSION_RE.fullmatch(game_version):
        raise BuildSpecError("target.game_version must contain printable ASCII only")
    if target["environment"] not in ENVIRONMENTS:
        raise BuildSpecError("target.environment is not a supported v1 context")
    loader_or_server = target["loader_or_server"]
    if loader_or_server is not None:
        loader_or_server = _string(loader_or_server, "target.loader_or_server", 120)

    coordinate_frame = _object(spec["coordinate_frame"], "coordinate_frame")
    _expect_keys(coordinate_frame, {"x", "y", "z", "anchor"}, "coordinate_frame")
    required_frame = {"x": "east-positive", "y": "up-positive", "z": "south-positive", "anchor": "minimum-corner"}
    if coordinate_frame != required_frame:
        raise BuildSpecError("coordinate_frame must use the fixed v1 east/up/south minimum-corner convention")

    origin = _coordinate_object(spec["origin"], "origin", positive=False)
    size = _coordinate_object(spec["size"], "size", positive=True)
    volume = size["x"] * size["y"] * size["z"]
    if volume > MAX_VOLUME:
        raise BuildSpecError(f"size volume exceeds v1 limit of {MAX_VOLUME}")
    if size["x"] * size["z"] > MAX_LAYER_AREA:
        raise BuildSpecError(f"size layer area exceeds v1 limit of {MAX_LAYER_AREA}")
    if spec["air_policy"] != "omit":
        raise BuildSpecError("air_policy must equal 'omit' in v1")

    raw_palette = spec["palette"]
    if not isinstance(raw_palette, list) or not raw_palette or len(raw_palette) > MAX_PALETTE:
        raise BuildSpecError(f"palette must contain 1 to {MAX_PALETTE} entries")
    palette: list[dict[str, Any]] = []
    palette_keys: set[str] = set()
    block_states: set[tuple[str, bytes]] = set()
    for index, raw_entry in enumerate(raw_palette):
        location = f"palette[{index}]"
        entry = _object(raw_entry, location)
        _expect_keys(entry, {"key", "block_id", "states", "swatch"}, location)
        key = _string(entry["key"], f"{location}.key", 12)
        if not PALETTE_KEY_RE.fullmatch(key):
            raise BuildSpecError(f"{location}.key has invalid format")
        if key in palette_keys:
            raise BuildSpecError(f"palette key occurs more than once: {key}")
        palette_keys.add(key)
        block_id = _string(entry["block_id"], f"{location}.block_id", 128)
        if not BLOCK_ID_RE.fullmatch(block_id):
            raise BuildSpecError(f"{location}.block_id must be a normalized namespaced identifier")
        states = _canonical_state(entry["states"], f"{location}.states")
        state_marker = (block_id, canonical_json_bytes(states))
        if state_marker in block_states:
            raise BuildSpecError(f"palette block/state occurs more than once: {block_id}")
        block_states.add(state_marker)
        swatch = _string(entry["swatch"], f"{location}.swatch", 7)
        if not SWATCH_RE.fullmatch(swatch):
            raise BuildSpecError(f"{location}.swatch must be an uppercase #RRGGBB value")
        palette.append({"key": key, "block_id": block_id, "states": states, "swatch": swatch})
    palette.sort(key=lambda entry: entry["key"])
    palette_by_key = {entry["key"]: entry for entry in palette}

    raw_placements = spec["placements"]
    if not isinstance(raw_placements, list) or not raw_placements or len(raw_placements) > MAX_PLACEMENTS:
        raise BuildSpecError(f"placements must contain 1 to {MAX_PLACEMENTS} entries")
    placements: list[dict[str, Any]] = []
    occupied: set[tuple[int, int, int]] = set()
    for index, raw_placement in enumerate(raw_placements):
        location = f"placements[{index}]"
        placement = _object(raw_placement, location)
        _expect_keys(placement, {"x", "y", "z", "palette"}, location)
        x = _integer(placement["x"], f"{location}.x", 0, size["x"] - 1)
        y = _integer(placement["y"], f"{location}.y", 0, size["y"] - 1)
        z = _integer(placement["z"], f"{location}.z", 0, size["z"] - 1)
        coordinate = (x, y, z)
        if coordinate in occupied:
            raise BuildSpecError(f"duplicate placement coordinate: {coordinate}")
        occupied.add(coordinate)
        palette_key = _string(placement["palette"], f"{location}.palette", 12)
        if palette_key not in palette_by_key:
            raise BuildSpecError(f"{location}.palette does not resolve: {palette_key}")
        placements.append({"x": x, "y": y, "z": z, "palette": palette_key})
    placements.sort(key=lambda entry: (entry["y"], entry["z"], entry["x"], entry["palette"]))

    raw_unsupported = spec["unsupported"]
    if not isinstance(raw_unsupported, list) or len(raw_unsupported) > MAX_UNSUPPORTED:
        raise BuildSpecError(f"unsupported must contain at most {MAX_UNSUPPORTED} entries")
    unsupported: list[str] = []
    for index, item in enumerate(raw_unsupported):
        value = _string(item, f"unsupported[{index}]", 64)
        if value not in UNSUPPORTED_VALUES:
            raise BuildSpecError(f"unsupported[{index}] is not a named v1 limitation")
        unsupported.append(value)
    if len(set(unsupported)) != len(unsupported):
        raise BuildSpecError("unsupported values must be unique")
    if not {"entities", "block_entities"}.issubset(unsupported):
        raise BuildSpecError("unsupported must explicitly include entities and block_entities")
    unsupported.sort()

    provenance = _object(spec["provenance"], "provenance")
    _expect_keys(provenance, {"basis", "evidence_status", "notes"}, "provenance")
    basis = _string(provenance["basis"], "provenance.basis", 512)
    evidence_status = provenance["evidence_status"]
    if evidence_status not in EVIDENCE_STATES:
        raise BuildSpecError("provenance.evidence_status is not a Gridmason evidence state")
    notes = provenance["notes"]
    if not isinstance(notes, str) or len(notes) > 2_048 or _contains_control_character(notes):
        raise BuildSpecError("provenance.notes must be a string of at most 2048 characters without control characters")
    try:
        notes.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise BuildSpecError("provenance.notes contains invalid Unicode") from exc

    return {
        "air_policy": "omit",
        "artifact_id": artifact_id,
        "coordinate_frame": required_frame,
        "format": FORMAT,
        "origin": origin,
        "palette": palette,
        "placements": placements,
        "provenance": {"basis": basis, "evidence_status": evidence_status, "notes": notes},
        "schema_version": SCHEMA_VERSION,
        "size": size,
        "target": {
            "edition": target["edition"],
            "environment": target["environment"],
            "game_version": game_version,
            "loader_or_server": loader_or_server,
        },
        "title": title,
        "unsupported": unsupported,
    }


def _materials_csv(spec: dict[str, Any]) -> bytes:
    counts = {entry["key"]: 0 for entry in spec["palette"]}
    for placement in spec["placements"]:
        counts[placement["palette"]] += 1
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["palette_key", "block_id", "states_json", "count"])
    for entry in spec["palette"]:
        if counts[entry["key"]]:
            writer.writerow(
                [
                    entry["key"],
                    entry["block_id"],
                    canonical_json_bytes(entry["states"]).decode("utf-8").rstrip("\n"),
                    counts[entry["key"]],
                ]
            )
    return stream.getvalue().encode("utf-8")


def _layers_markdown(spec: dict[str, Any]) -> bytes:
    size = spec["size"]
    placement_map = {(item["x"], item["y"], item["z"]): item["palette"] for item in spec["placements"]}
    counts = {entry["key"]: 0 for entry in spec["palette"]}
    for palette_key in placement_map.values():
        counts[palette_key] += 1
    lines = [
        f"# {spec['title']}",
        "",
        f"Artifact: `{spec['artifact_id']}`",
        "Coordinate frame: x east-positive; y up-positive; z south-positive; origin is the minimum corner.",
        "Air policy: omitted cells are air.",
        "",
        "## Palette",
        "",
        "| Key | Block ID | States | Count |",
        "| --- | --- | --- | ---: |",
    ]
    for entry in spec["palette"]:
        states = canonical_json_bytes(entry["states"]).decode("utf-8").rstrip("\n")
        lines.append(f"| {entry['key']} | `{entry['block_id']}` | `{states}` | {counts[entry['key']]} |")
    occupied_y = sorted({item["y"] for item in spec["placements"]})
    for y in occupied_y:
        lines.extend(["", f"## Layer y={y}", "", "`z \\ x` | " + " | ".join(str(x) for x in range(size["x"])), "--- | " + " | ".join("---" for _ in range(size["x"]))])
        for z in range(size["z"]):
            row = [placement_map.get((x, y, z), ".") for x in range(size["x"])]
            lines.append(f"{z} | " + " | ".join(row))
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def _preview_svg(spec: dict[str, Any]) -> bytes:
    size = spec["size"]
    palette = {entry["key"]: entry for entry in spec["palette"]}
    highest: dict[tuple[int, int], dict[str, Any]] = {}
    for placement in spec["placements"]:
        coordinate = (placement["x"], placement["z"])
        previous = highest.get(coordinate)
        if previous is None or placement["y"] > previous["y"]:
            highest[coordinate] = placement
    cell = 16
    width = size["x"] * cell
    height = size["z"] * cell
    title = html.escape(f"{spec['title']} — schematic top-down preview", quote=True)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{title}">',
        f"<title>{title}</title>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>',
    ]
    for z in range(size["z"]):
        for x in range(size["x"]):
            placement = highest.get((x, z))
            if placement is None:
                continue
            entry = palette[placement["palette"]]
            lines.append(
                f'<rect x="{x * cell}" y="{z * cell}" width="{cell}" height="{cell}" fill="{entry["swatch"]}" data-palette="{entry["key"]}"/> '
            )
    lines.append("</svg>")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _receipt(spec: dict[str, Any]) -> bytes:
    return canonical_json_bytes(
        {
            "artifact_id": spec["artifact_id"],
            "format": FORMAT,
            "schema_version": SCHEMA_VERSION,
            "status": "STATICALLY VALID",
            "unsupported": spec["unsupported"],
            "validation_scope": [
                "closed-schema",
                "coordinate-bounds",
                "palette-references",
                "placement-uniqueness",
                "deterministic-derivatives",
            ],
        }
    )


def render_bundle(spec: dict[str, Any]) -> dict[str, bytes]:
    canonical = canonical_json_bytes(spec)
    digest = hashlib.sha256(canonical).hexdigest()
    return {
        "build-spec.canonical.json": canonical,
        "build-spec.sha256": f"{digest}  build-spec.canonical.json\n".encode("ascii"),
        "materials.csv": _materials_csv(spec),
        "layers.md": _layers_markdown(spec),
        "preview.svg": _preview_svg(spec),
        "compile-receipt.json": _receipt(spec),
    }


def compile_spec(input_path: Path, output_dir: Path) -> None:
    if output_dir.exists():
        raise OSError(f"output directory already exists: {output_dir}")
    if not output_dir.parent.is_dir():
        raise OSError(f"output parent does not exist: {output_dir.parent}")
    staging = output_dir.parent / f".{output_dir.name}.gridmason-staging"
    if staging.exists():
        raise OSError(f"staging directory already exists: {staging}")
    spec = validate_and_normalize(load_spec(input_path))
    rendered = render_bundle(spec)
    staging_created = False
    try:
        staging.mkdir()
        staging_created = True
        for name in EXPECTED_FILES:
            (staging / name).write_bytes(rendered[name])
        verify_bundle(staging)
        os.replace(staging, output_dir)
    except BaseException:
        if staging_created and staging.exists():
            shutil.rmtree(staging)
        raise


def canonicalize_spec(input_path: Path, output_path: Path) -> None:
    if output_path.exists():
        raise OSError(f"output file already exists: {output_path}")
    if not output_path.parent.is_dir():
        raise OSError(f"output parent does not exist: {output_path.parent}")
    spec = validate_and_normalize(load_spec(input_path))
    with output_path.open("xb") as handle:
        handle.write(canonical_json_bytes(spec))


def verify_bundle(bundle_dir: Path) -> None:
    if not bundle_dir.is_dir():
        raise OSError(f"bundle directory does not exist: {bundle_dir}")
    actual_names = {path.name for path in bundle_dir.iterdir()}
    expected_names = set(EXPECTED_FILES)
    if actual_names != expected_names:
        raise IntegrityError("bundle must contain exactly the six v1 output files")
    canonical_path = bundle_dir / "build-spec.canonical.json"
    raw_canonical = canonical_path.read_bytes()
    try:
        spec = validate_and_normalize(
            json.loads(raw_canonical.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_non_finite)
        )
    except (UnicodeDecodeError, json.JSONDecodeError, BuildSpecError) as exc:
        raise IntegrityError(f"canonical JSON is invalid: {exc}") from exc
    expected = render_bundle(spec)
    for name in EXPECTED_FILES:
        actual = (bundle_dir / name).read_bytes()
        if actual != expected[name]:
            raise IntegrityError(f"bundle file does not match deterministic rendering: {name}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and compile deterministic Gridmason Build Specs.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "canonicalize", "compile"):
        command = subcommands.add_parser(name)
        command.add_argument("spec", type=Path)
        if name == "canonicalize":
            command.add_argument("--output", required=True, type=Path)
        if name == "compile":
            command.add_argument("--out", required=True, type=Path)
    verify = subcommands.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            validate_and_normalize(load_spec(args.spec))
            print("STATICALLY VALID")
        elif args.command == "canonicalize":
            canonicalize_spec(args.spec, args.output)
            print("STATICALLY VALID")
        elif args.command == "compile":
            compile_spec(args.spec, args.out)
            print("STATICALLY VALID")
        else:
            verify_bundle(args.bundle)
            print("STATICALLY VALID")
        return 0
    except IntegrityError as exc:
        print(f"integrity error: {exc}", file=sys.stderr)
        return 4
    except BuildSpecError as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"I/O error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Safely inventory Officefile artifacts without opening them in office applications."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from officefile_safety import safe_relative, walk_officefile_files


OOXML_EXTENSIONS = {".docx": "DOCX", ".pptx": "PPTX", ".xlsx": "XLSX", ".docm": "DOCM", ".pptm": "PPTM", ".xlsm": "XLSM"}
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_ZIP_ENTRIES = 10_000
MAX_ZIP_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_RELATIONSHIP_PARTS = 100
MAX_PDF_SCAN_BYTES = 16 * 1024 * 1024
MAX_TEXT_SCAN_BYTES = 16 * 1024 * 1024
MAX_XML_PART_BYTES = 10 * 1024 * 1024
OOXML_REQUIRED_PART = {
    "DOCX": ("word/document.xml", "document"),
    "DOCM": ("word/document.xml", "document"),
    "PPTX": ("ppt/presentation.xml", "presentation"),
    "PPTM": ("ppt/presentation.xml", "presentation"),
    "XLSX": ("xl/workbook.xml", "workbook"),
    "XLSM": ("xl/workbook.xml", "workbook"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def scan_relationships(archive: zipfile.ZipFile, names: list[str]) -> tuple[list[str], bool]:
    external: list[str] = []
    relationship_parts = [name for name in names if name.endswith(".rels")]
    truncated = len(relationship_parts) > MAX_RELATIONSHIP_PARTS
    for name in relationship_parts[:MAX_RELATIONSHIP_PARTS]:
        info = archive.getinfo(name)
        if info.file_size > 1_000_000:
            continue
        try:
            text = archive.read(name).decode("utf-8", "replace")
        except (KeyError, OSError, RuntimeError):
            continue
        if 'TargetMode="External"' in text or "TargetMode='External'" in text:
            external.append(name)
    return external, truncated


def xml_root_kind(archive: zipfile.ZipFile, name: str) -> tuple[bool, str | None]:
    try:
        info = archive.getinfo(name)
        if info.file_size > MAX_XML_PART_BYTES:
            return False, None
        root = ET.fromstring(archive.read(name))
    except (KeyError, OSError, RuntimeError, ET.ParseError):
        return False, None
    return True, root.tag.rsplit("}", 1)[-1]


def inspect_ooxml(path: Path, kind: str) -> dict[str, Any]:
    result: dict[str, Any] = {"kind": kind, "container": "OOXML", "zip_valid": False, "key_parts": [], "macro_parts": [], "external_relationship_parts": []}
    if path.stat().st_size > MAX_FILE_BYTES:
        result["bounded_out"] = f"file exceeds {MAX_FILE_BYTES} byte inspection limit"
        return result
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            result["entry_count"] = len(names)
            total_uncompressed = sum(info.file_size for info in archive.infolist())
            result["uncompressed_bytes"] = total_uncompressed
            if len(names) > MAX_ZIP_ENTRIES or total_uncompressed > MAX_ZIP_UNCOMPRESSED_BYTES:
                result["bounded_out"] = "container exceeds entry-count or uncompressed-size inspection limit"
                return result
            bad_member = archive.testzip()
            result["zip_valid"] = bad_member is None
            result["zip_error_member"] = bad_member
            result["key_parts"] = [part for part in ("[Content_Types].xml", "_rels/.rels", "word/document.xml", "ppt/presentation.xml", "xl/workbook.xml") if part in names]
            result["macro_parts"] = [name for name in names if name.lower().endswith("vbaproject.bin")]
            external, truncated = scan_relationships(archive, names)
            result["external_relationship_parts"] = external
            result["relationship_scan_truncated"] = truncated
            content_types_valid, content_types_root = xml_root_kind(archive, "[Content_Types].xml")
            required_part, expected_root = OOXML_REQUIRED_PART[kind]
            required_xml_valid, required_root = xml_root_kind(archive, required_part)
            result["content_types_xml_valid"] = content_types_valid and content_types_root == "Types"
            result["required_part"] = required_part
            result["required_part_xml_valid"] = required_xml_valid
            result["required_root_kind"] = required_root
            result["required_root_expected"] = expected_root
            result["required_root_valid"] = required_xml_valid and required_root == expected_root
            result["structurally_plausible"] = result["zip_valid"] and result["content_types_xml_valid"] and result["required_root_valid"]
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        result["error"] = str(exc)
    return result


def inspect_pdf(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    with path.open("rb") as handle:
        head = handle.read(16)
        scan = handle.read(MAX_PDF_SCAN_BYTES)
        handle.seek(max(size - 1_000_000, 0))
        tail = handle.read(1_000_000)
    startxref_matches = list(re.finditer(rb"startxref\s+(\d+)\s+%%EOF", tail))
    startxref = int(startxref_matches[-1].group(1)) if startxref_matches else None
    target_hint = b""
    if startxref is not None and 0 <= startxref < size:
        with path.open("rb") as handle:
            handle.seek(startxref)
            target_hint = handle.read(512)
    startxref_target_valid = target_hint.startswith(b"xref") or bool(re.search(rb"\d+\s+\d+\s+obj\b[\s\S]{0,400}/Type\s*/XRef\b", target_hint))
    catalog_present = bool(re.search(rb"/Type\s*/Catalog\b", scan))
    page_present = bool(re.search(rb"/Type\s*/Page\b", scan))
    indirect_object_present = bool(re.search(rb"\d+\s+\d+\s+obj\b", scan))
    root_reference_present = bool(re.search(rb"/Root\s+\d+\s+\d+\s+R\b", tail))
    header_valid = head.startswith(b"%PDF-")
    eof_marker_present = b"%%EOF" in tail
    structurally_plausible = all((header_valid, eof_marker_present, catalog_present, page_present, indirect_object_present, root_reference_present, startxref_target_valid))
    return {
        "kind": "PDF",
        "header_valid": header_valid,
        "version_hint": head[5:8].decode("ascii", "replace") if header_valid else None,
        "eof_marker_present": eof_marker_present,
        "page_hint": len(re.findall(rb"/Type\s*/Page\b", scan)),
        "page_hint_scan_truncated": size > MAX_PDF_SCAN_BYTES,
        "catalog_present": catalog_present,
        "indirect_object_present": indirect_object_present,
        "root_reference_present": root_reference_present,
        "startxref": startxref,
        "startxref_target_valid": startxref_target_valid,
        "structurally_plausible": structurally_plausible,
        "note": "This is a bounded structural plausibility check, not full PDF parsing, rendering, accessibility, or semantic validation."
    }


def inspect_markdown(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    result: dict[str, Any] = {"kind": "MD", "utf8_valid": False, "nonempty": False, "structurally_plausible": False}
    if size > MAX_TEXT_SCAN_BYTES:
        result["bounded_out"] = f"file exceeds {MAX_TEXT_SCAN_BYTES} byte text inspection limit"
        return result
    try:
        text = path.read_bytes().decode("utf-8-sig", "strict")
    except UnicodeDecodeError as exc:
        result["error"] = str(exc)
        return result
    result["utf8_valid"] = True
    result["nonempty"] = bool(text.strip())
    result["structurally_plausible"] = result["nonempty"]
    return result


def inspect_csv(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    result: dict[str, Any] = {"kind": "CSV", "utf8_valid": False, "nonempty": False, "consistent_rows": False, "structurally_plausible": False}
    if size > MAX_TEXT_SCAN_BYTES:
        result["bounded_out"] = f"file exceeds {MAX_TEXT_SCAN_BYTES} byte text inspection limit"
        return result
    try:
        text = path.read_bytes().decode("utf-8-sig", "strict")
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error) as exc:
        result["error"] = str(exc)
        return result
    result["utf8_valid"] = True
    result["nonempty"] = bool(text.strip()) and bool(rows)
    widths = [len(row) for row in rows]
    result["row_count"] = len(rows)
    result["column_count"] = widths[0] if widths else 0
    result["consistent_rows"] = bool(widths) and widths[0] > 0 and all(width == widths[0] for width in widths)
    result["structurally_plausible"] = result["nonempty"] and result["consistent_rows"]
    return result


def inspect_file(path: Path, relative: str) -> dict[str, Any]:
    extension = path.suffix.lower()
    entry: dict[str, Any] = {"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path), "extension": extension or None}
    if not safe_relative(relative):
        entry["unsafe_name"] = True
        return entry
    if entry["size_bytes"] == 0:
        entry["empty"] = True
    if extension in OOXML_EXTENSIONS:
        entry["inspection"] = inspect_ooxml(path, OOXML_EXTENSIONS[extension])
    elif extension == ".pdf":
        entry["inspection"] = inspect_pdf(path)
    elif extension == ".csv":
        entry["inspection"] = inspect_csv(path)
    elif extension == ".md":
        entry["inspection"] = inspect_markdown(path)
    else:
        entry["inspection"] = {"kind": "other", "note": "No format-specific inspection performed."}
    return entry


def inspect_officefile(root_value: str | Path) -> dict[str, Any]:
    root, files, errors = walk_officefile_files(root_value)
    artifacts: list[dict[str, Any]] = []
    if root is not None:
        for path in files:
            relative = path.relative_to(root).as_posix()
            try:
                artifacts.append(inspect_file(path, relative))
            except OSError as exc:
                errors.append(f"cannot inspect {relative}: {exc}")
                continue
            inspection = artifacts[-1].get("inspection", {})
            extension = artifacts[-1].get("extension")
            if extension in OOXML_EXTENSIONS and inspection.get("structurally_plausible") is not True:
                errors.append(f"{relative}: OOXML structural inspection failed")
            if extension == ".pdf" and inspection.get("structurally_plausible") is not True:
                errors.append(f"{relative}: PDF structural inspection failed")
            if extension == ".csv" and inspection.get("structurally_plausible") is not True:
                errors.append(f"{relative}: CSV structural inspection failed")
            if extension == ".md" and inspection.get("structurally_plausible") is not True:
                errors.append(f"{relative}: Markdown structural inspection failed")
    return {"format": "officecraft-artifact-inspection/v1", "officefile": str(root or Path(root_value).absolute()), "inspected_at": utc_now(), "executed_embedded_code": False, "opened_in_native_application": False, "artifacts": artifacts, "errors": errors, "limitations": ["This inspection does not render files, verify visual quality, calculate spreadsheet formulas, decrypt content, or validate accessibility semantics."]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("officefile")
    parser.add_argument("--output", help="optional JSON evidence file; must not already exist")
    args = parser.parse_args(argv)
    report = inspect_officefile(args.officefile)
    if args.output:
        output = Path(args.output).resolve()
        if output.exists():
            print(json.dumps({"format": "officecraft-artifact-inspection/v1", "error": f"Refusing to overwrite output: {output}"}), file=sys.stderr)
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

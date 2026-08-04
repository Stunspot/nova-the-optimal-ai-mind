from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from init_officefile import initialize
from inspect_office_artifacts import inspect_officefile
from package_officefile import package_officefile
from validate_officefile import safe_relative, validate_officefile


EXAMPLE = SKILL_ROOT / "examples" / "monday-leadership-packet"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def valid_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")


def minimal_one_page_pdf() -> bytes:
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
    ]
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode("ascii"))
        data.extend(body)
        data.extend(b"\nendobj\n")
    xref_offset = len(data)
    data.extend(b"xref\n0 5\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    data.extend(f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(data)


def register_artifact(officefile: Path, *, status: str, artifact_format: str = "DOCX", path: str = "output/sample.docx", evidence: list[object] | None = None) -> None:
    register_path = officefile / "state" / "artifact-register.json"
    register = json.loads(register_path.read_text(encoding="utf-8"))
    register["artifacts"] = [{
        "artifact_id": "ART-SAMPLE",
        "path": path,
        "format": artifact_format,
        "role": "editable_source",
        "status": status,
        "editable": True,
        "canonical_source_id": None,
        "check_evidence": evidence or []
    }]
    write_json(register_path, register)


class OfficefileScriptTests(unittest.TestCase):
    def test_synthetic_packet_is_valid_and_has_no_produced_artifacts(self) -> None:
        report = validate_officefile(EXAMPLE)
        self.assertTrue(report["valid"], report["errors"])
        register = json.loads((EXAMPLE / "state" / "artifact-register.json").read_text(encoding="utf-8"))
        self.assertEqual({item["status"] for item in register["artifacts"]}, {"planned"})

    def test_init_is_non_overwriting_and_package_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            officefile = root / "new-officefile"
            created = initialize(officefile, "test-officefile")
            self.assertEqual(created["format"], "officecraft-init/v1")
            self.assertTrue(validate_officefile(officefile)["valid"])
            with self.assertRaises(ValueError):
                initialize(officefile)
            package = root / "officefile.zip"
            result = package_officefile(officefile, package)
            self.assertTrue(package.is_file())
            self.assertIn("state/brief.json", result["included_files"])
            with zipfile.ZipFile(package) as archive:
                self.assertIn("HANDOFF.md", archive.namelist())
            with self.assertRaises(ValueError):
                package_officefile(officefile, package)

    def test_package_preflight_includes_produced_artifact_and_cleans_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            officefile = root / "officefile"
            initialize(officefile)
            valid_docx(officefile / "output" / "sample.docx")
            register_artifact(officefile, status="produced")
            package = root / "produced.zip"
            package_officefile(officefile, package)
            with zipfile.ZipFile(package) as archive:
                self.assertIn("output/sample.docx", archive.namelist())

            failing = root / "failing.zip"
            with mock.patch("zipfile.ZipFile.write", side_effect=OSError("simulated write failure")):
                with self.assertRaises(OSError):
                    package_officefile(officefile, failing)
            self.assertFalse(failing.exists())
            self.assertFalse(list(root.glob(".failing.zip.*.tmp")))

    def test_validator_rejects_unsafe_windows_path_forms(self) -> None:
        self.assertTrue(safe_relative("output/file.docx"))
        for unsafe in ("../file.docx", "C:\\file.docx", "/file.docx", "output/file.docx:secret", "output/CON.txt", "output/report. ", "output/report ", "output/a<b.docx", "output/a>b.docx", 'output/a"b.docx', "output/a|b.docx", "output/a?b.docx", "output/a*b.docx", "output/a\x01b.docx"):
            self.assertFalse(safe_relative(unsafe), unsafe)

    def test_validator_rejects_format_mismatch_and_untrusted_sourced_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "invalid-officefile"
            initialize(officefile)
            register_artifact(officefile, status="planned", path="output/sample.pdf")
            manifest_path = officefile / "sources" / "manifest.json"
            manifest = {"format": "officecraft-source-manifest/v1", "sources": [{"source_id": "SRC-ILLUSTRATIVE", "path": "sources/example.txt", "source_type": "notes", "custody_status": "illustrative", "content_status": "illustrative"}]}
            (officefile / "sources" / "example.txt").write_text("example", encoding="utf-8")
            write_json(manifest_path, manifest)
            ledger_path = officefile / "state" / "content-ledger.json"
            write_json(ledger_path, {"format": "officecraft-content-ledger/v1", "items": [{"item_id": "ITEM", "kind": "fact", "value": "example", "source_ids": ["SRC-ILLUSTRATIVE"], "source_status": "sourced"}]})
            report = validate_officefile(officefile)
            self.assertFalse(report["valid"])
            self.assertTrue(any("format does not match" in error for error in report["errors"]))
            self.assertTrue(any("sourced item depends" in error for error in report["errors"]))

    def test_inspected_office_artifact_requires_matching_structural_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "inspected-officefile"
            initialize(officefile)
            sample = officefile / "output" / "sample.docx"
            valid_docx(sample)
            register_artifact(officefile, status="inspected")
            self.assertFalse(validate_officefile(officefile)["valid"])
            inspection = inspect_officefile(officefile)
            evidence_path = officefile / "review" / "inspection.json"
            write_json(evidence_path, inspection)
            register_artifact(officefile, status="inspected", evidence=[{"path": "review/inspection.json"}])
            report = validate_officefile(officefile)
            self.assertTrue(report["valid"], report["errors"])
            sample.write_bytes(b"changed after inspection")
            report = validate_officefile(officefile)
            self.assertFalse(report["valid"])
            self.assertTrue(any("direct bounded structural inspection" in error or "digest does not match" in error for error in report["errors"]))

    def test_malformed_json_types_return_structured_invalid_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "type-officefile"
            initialize(officefile)
            brief = json.loads((officefile / "state" / "brief.json").read_text(encoding="utf-8"))
            brief["state"] = ["intake"]
            brief["title"] = []
            brief["audience"] = {}
            brief["purpose"] = []
            brief["requested_outcomes"] = {}
            brief["constraints"] = []
            write_json(officefile / "state" / "brief.json", brief)
            write_json(officefile / "sources" / "manifest.json", {"format": "officecraft-source-manifest/v1", "sources": [{"source_id": ["bad"], "path": "sources/x", "source_type": {"bad": True}, "custody_status": [], "content_status": []}]})
            write_json(officefile / "state" / "content-ledger.json", {"format": "officecraft-content-ledger/v1", "items": [{"item_id": {"bad": True}, "kind": [], "value": [], "source_ids": [{"bad": True}], "source_status": []}]})
            register_artifact(officefile, status="planned")
            register = json.loads((officefile / "state" / "artifact-register.json").read_text(encoding="utf-8"))
            register["artifacts"][0]["artifact_id"] = ["bad"]
            register["artifacts"][0]["status"] = {"bad": True}
            register["artifacts"][0]["format"] = []
            register["artifacts"][0]["canonical_source_id"] = {"bad": True}
            write_json(officefile / "state" / "artifact-register.json", register)
            review = json.loads((officefile / "review" / "officecraft-review.json").read_text(encoding="utf-8"))
            review["operator_review"]["status"] = ["PASS"]
            write_json(officefile / "review" / "officecraft-review.json", review)
            report = validate_officefile(officefile)
            self.assertFalse(report["valid"])
            self.assertIsInstance(report["errors"], list)

    def test_forged_saved_inspection_cannot_replace_direct_container_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "forged-officefile"
            initialize(officefile)
            sample = officefile / "output" / "sample.docx"
            sample.write_bytes(b"plain text wearing a docx hat")
            digest = hashlib.sha256(sample.read_bytes()).hexdigest()
            forged = {
                "format": "officecraft-artifact-inspection/v1",
                "errors": [],
                "artifacts": [{"path": "output/sample.docx", "sha256": digest, "inspection": {"kind": "DOCX", "zip_valid": True, "key_parts": ["word/document.xml"]}}]
            }
            write_json(officefile / "review" / "forged-inspection.json", forged)
            register_artifact(officefile, status="inspected", evidence=[{"path": "review/forged-inspection.json"}])
            report = validate_officefile(officefile)
            self.assertFalse(report["valid"])
            self.assertTrue(any("fails direct bounded structural inspection" in error for error in report["errors"]))

    def test_reviewed_and_approved_states_require_current_digest_bound_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "review-officefile"
            initialize(officefile)
            sample = officefile / "output" / "sample.docx"
            valid_docx(sample)
            inspection = inspect_officefile(officefile)
            write_json(officefile / "review" / "inspection.json", inspection)
            digest = hashlib.sha256(sample.read_bytes()).hexdigest()
            brief_path = officefile / "state" / "brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["state"] = "reviewable"
            brief["approval_owner"] = "Casey Owner"
            write_json(brief_path, brief)
            register_artifact(officefile, status="reviewed", evidence=[{"path": "review/inspection.json"}])
            self.assertFalse(validate_officefile(officefile)["valid"])

            review_path = officefile / "review" / "officecraft-review.json"
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["operator_review"] = {"status": "PASS_WITH_CONDITIONS", "officefile_state": "reviewable", "reviewed_artifacts": [{"artifact_id": "ART-SAMPLE", "sha256": digest}], "findings": []}
            write_json(review_path, review)
            self.assertTrue(validate_officefile(officefile)["valid"])

            register_artifact(officefile, status="approved", evidence=[{"path": "review/inspection.json"}])
            self.assertFalse(validate_officefile(officefile)["valid"])
            review["approval_records"] = [{"artifact_id": "ART-SAMPLE", "sha256": digest, "approval_owner": "Casey Owner", "authority_kind": "accountable_owner", "approved_use": "Monday leadership meeting", "approved_at": "2026-07-21T13:45:00Z"}]
            write_json(review_path, review)
            self.assertTrue(validate_officefile(officefile)["valid"])
            review["approval_records"][0]["approved_at"] = "2999-01-01T00:00:00Z"
            write_json(review_path, review)
            self.assertFalse(validate_officefile(officefile)["valid"])
            review["approval_records"][0]["approved_at"] = "2026-07-21T13:45:00Z"
            review["approval_records"][0]["approval_owner"] = "Someone Else"
            write_json(review_path, review)
            self.assertFalse(validate_officefile(officefile)["valid"])

    def test_package_rejects_mutation_between_validation_snapshots_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            officefile = root / "snapshot-officefile"
            initialize(officefile)
            output = root / "snapshot.zip"
            real_validate = validate_officefile

            def mutate_after_validation(path: Path) -> dict[str, object]:
                result = real_validate(path)
                (officefile / "HANDOFF.md").write_text("mutated during validation", encoding="utf-8")
                return result

            with mock.patch("package_officefile.validate_officefile", side_effect=mutate_after_validation):
                with self.assertRaisesRegex(ValueError, "changed during validation"):
                    package_officefile(officefile, output)
            self.assertFalse(output.exists())
            self.assertFalse(list(root.glob(".snapshot.zip.*.tmp")))

    def test_ooxml_named_garbage_part_fails_xml_root_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "bad-xml-officefile"
            initialize(officefile)
            sample = officefile / "output" / "bad.docx"
            with zipfile.ZipFile(sample, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types/>")
                archive.writestr("word/document.xml", "garbage")
            report = inspect_officefile(officefile)
            entry = next(item for item in report["artifacts"] if item["path"] == "output/bad.docx")
            self.assertFalse(entry["inspection"]["structurally_plausible"])
            self.assertTrue(any("OOXML structural inspection failed" in error for error in report["errors"]))

    def test_csv_markdown_checkers_and_undefined_other_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "text-officefile"
            initialize(officefile)
            csv_path = officefile / "output" / "sample.csv"
            md_path = officefile / "output" / "sample.md"
            csv_path.write_text("name,value\nalpha,1\n", encoding="utf-8")
            md_path.write_text("# Ready\n", encoding="utf-8")
            inspection = inspect_officefile(officefile)
            self.assertEqual(inspection["errors"], [])
            write_json(officefile / "review" / "text-inspection.json", inspection)
            register_artifact(officefile, status="inspected", artifact_format="CSV", path="output/sample.csv", evidence=[{"path": "review/text-inspection.json"}])
            self.assertTrue(validate_officefile(officefile)["valid"])
            register_artifact(officefile, status="inspected", artifact_format="MD", path="output/sample.md", evidence=[{"path": "review/text-inspection.json"}])
            self.assertTrue(validate_officefile(officefile)["valid"])
            csv_path.write_text("name,value\nalpha\n", encoding="utf-8")
            register_artifact(officefile, status="inspected", artifact_format="CSV", path="output/sample.csv", evidence=[{"path": "review/text-inspection.json"}])
            self.assertFalse(validate_officefile(officefile)["valid"])
            other = officefile / "output" / "sample.bin"
            other.write_bytes(b"unknown")
            register_artifact(officefile, status="inspected", artifact_format="OTHER", path="output/sample.bin", evidence=[{}])
            report = validate_officefile(officefile)
            self.assertFalse(report["valid"])
            self.assertTrue(any("no defined structural checker" in error for error in report["errors"]))

    def test_pass_review_must_match_current_state_and_registered_produced_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "global-review-officefile"
            initialize(officefile)
            sample = officefile / "output" / "sample.docx"
            valid_docx(sample)
            register_artifact(officefile, status="produced")
            digest = hashlib.sha256(sample.read_bytes()).hexdigest()
            review_path = officefile / "review" / "officecraft-review.json"
            review = json.loads(review_path.read_text(encoding="utf-8"))
            review["operator_review"] = {"status": "PASS", "officefile_state": "shaped", "reviewed_artifacts": [{"artifact_id": "ART-SAMPLE", "sha256": digest}], "findings": []}
            write_json(review_path, review)
            self.assertFalse(validate_officefile(officefile)["valid"])
            review["operator_review"]["officefile_state"] = "intake"
            review["operator_review"]["reviewed_artifacts"][0]["artifact_id"] = "ART-MISSING"
            write_json(review_path, review)
            self.assertFalse(validate_officefile(officefile)["valid"])
            review["operator_review"]["reviewed_artifacts"][0] = {"artifact_id": "ART-SAMPLE", "sha256": digest}
            write_json(review_path, review)
            self.assertTrue(validate_officefile(officefile)["valid"])

            review["operator_review"]["reviewed_artifacts"] = []
            write_json(review_path, review)
            report = validate_officefile(officefile)
            self.assertFalse(report["valid"])
            self.assertTrue(any("needs digest-bound reviewed_artifacts" in error for error in report["errors"]))

    def test_corrupt_ooxml_and_pdf_return_nonzero_inspector_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "corrupt-officefile"
            initialize(officefile)
            for name, contents in (("bad.docx", b"not a zip"), ("bad.pdf", b"not a PDF")):
                (officefile / "output" / name).write_bytes(contents)
                result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts" / "inspect_office_artifacts.py"), str(officefile)], capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                (officefile / "output" / name).unlink()

    def test_small_valid_pdf_passes_bounded_oracle_and_lexical_decoy_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            officefile = Path(temporary) / "pdf-officefile"
            initialize(officefile)
            sample = officefile / "output" / "sample.pdf"
            sample.write_bytes(minimal_one_page_pdf())
            inspection = inspect_officefile(officefile)
            self.assertEqual(inspection["errors"], [])
            entry = next(item for item in inspection["artifacts"] if item["path"] == "output/sample.pdf")
            self.assertTrue(entry["inspection"]["structurally_plausible"])
            self.assertTrue(entry["inspection"]["eof_marker_present"])
            write_json(officefile / "review" / "pdf-inspection.json", inspection)
            register_artifact(officefile, status="inspected", artifact_format="PDF", path="output/sample.pdf", evidence=[{"path": "review/pdf-inspection.json"}])
            self.assertTrue(validate_officefile(officefile)["valid"])

            sample.write_bytes(b"%PDF-1.4\n/Type /Catalog /Type /Page /Root 1 0 R\nstartxref\n9\n%%EOF\n")
            decoy = inspect_officefile(officefile)
            self.assertTrue(any("PDF structural inspection failed" in error for error in decoy["errors"]))
            self.assertFalse(validate_officefile(officefile)["valid"])

    def test_symlink_and_windows_junction_are_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            officefile = root / "tree-officefile"
            outside = root / "outside"
            initialize(officefile)
            outside.mkdir()
            (outside / "secret.txt").write_text("outside", encoding="utf-8")
            link = officefile / "output" / "link"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError):
                pass
            else:
                self.assertFalse(validate_officefile(officefile)["valid"])
                self.assertTrue(inspect_officefile(officefile)["errors"])
                with self.assertRaises(ValueError):
                    package_officefile(officefile, root / "symlink.zip")
                link.unlink()

            junction = officefile / "output" / "junction"
            if os.name != "nt":
                self.skipTest("Windows junction test is only applicable on Windows")
            created = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)], capture_output=True, text=True, check=False)
            if created.returncode != 0:
                self.skipTest("Windows junction creation is unavailable on this host")
            self.assertFalse(validate_officefile(officefile)["valid"])
            self.assertTrue(inspect_officefile(officefile)["errors"])
            with self.assertRaises(ValueError):
                package_officefile(officefile, root / "junction.zip")


if __name__ == "__main__":
    unittest.main()

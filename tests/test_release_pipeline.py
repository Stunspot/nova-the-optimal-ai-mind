from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import build_release
from release_lib import deterministic_zip, zip_filename_findings

BUILDER = REPO / "tools" / "build_release.py"
VERIFIER = REPO / "tools" / "verify_package.py"
RIGHTS_DOCS = (
    "LICENSE.md", "ATTRIBUTION.md", "NOTICE.md", "TRADEMARKS.md",
    "PROVENANCE.md", "THIRD-PARTY-NOTICES.md",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReleasePipelineTests(unittest.TestCase):
    def test_build_is_deterministic_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nova-free-release-") as directory:
            base = Path(directory)
            command = [
                sys.executable, "-B", "-X", "utf8", str(BUILDER),
                "--repo", str(REPO),
                "--output-parent", str(base / "dist"),
                "--artifact-parent", str(base / "release"),
            ]
            first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_result = json.loads(first.stdout)
            self.assertEqual(first_result["candidate_state"], "built_from_frozen_source")
            self.assertTrue(first_result["independent_review_required"])
            self.assertEqual(
                first_result["archive_filename_encoding"],
                "strict_utf8_local_and_central_headers",
            )
            self.assertEqual(first_result["redistribution_state"], "permitted_under_included_licenses")
            self.assertEqual(first_result["publication_state"], "not_published")
            self.assertNotIn("sealed_candidate", first_result)
            customer = Path(first_result["customer_zip"])
            codex = Path(first_result["codex_zip"])
            claude = Path(first_result["claude_zip"])
            first_hashes = {path.name: digest(path) for path in (customer, codex, claude)}

            verify = subprocess.run(
                [sys.executable, "-B", "-X", "utf8", str(VERIFIER), first_result["package_root"]],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            verification = json.loads(verify.stdout)
            self.assertEqual(verification["verdict"], "PASS")
            self.assertEqual(verification["observed"]["standalone_rights_envelopes"], 27)

            second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(second.returncode, 0, second.stderr)
            second_result = json.loads(second.stdout)
            second_paths = (Path(second_result["customer_zip"]), Path(second_result["codex_zip"]), Path(second_result["claude_zip"]))
            self.assertEqual(first_hashes, {path.name: digest(path) for path in second_paths})

            package_root = Path(second_result["package_root"])
            with zipfile.ZipFile(second_result["customer_zip"]) as archive:
                names = archive.namelist()
            prefix = "nova-the-optimal-ai-free-3.1.3/"
            self.assertTrue(all(name.startswith(prefix) for name in names))
            self.assertIn(prefix + "codex/.agents/plugins/marketplace.json", names)
            self.assertIn(prefix + "claude/nova-the-optimal-ai/.claude-plugin/plugin.json", names)
            for name in RIGHTS_DOCS:
                self.assertIn(prefix + name, names)
            for skill_id in ("promptcraft", "software-verification", "agent-swarm-orchestration", "job-application-builder"):
                rights = package_root / "claude" / "folders" / skill_id / "nova-free-rights"
                for name in (*RIGHTS_DOCS, "README.md"):
                    self.assertTrue((rights / name).is_file(), f"{skill_id}/{name}")
            self.assertTrue(
                (
                    package_root
                    / "claude/folders/software-verification/nova-free-rights/component-notices/testforge/LICENSE.md"
                ).is_file()
            )
            for binding in ("codex", "claude"):
                manifest = json.loads((package_root / binding / "BUILD-MANIFEST.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["candidate_state"], "built_from_frozen_source")
                self.assertTrue(manifest["independent_review_required"])
                self.assertEqual(
                    manifest["archive_filename_encoding"],
                    "strict_utf8_local_and_central_headers",
                )
                self.assertEqual(manifest["rights"]["external_rights_blockers"], [])
                self.assertRegex(manifest["source_lock_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(manifest["source_map_sha256"], r"^[0-9a-f]{64}$")
                self.assertNotIn("sealed_candidate", manifest)

    def test_unicode_archive_names_use_strict_utf8_headers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nova-free-unicode-zip-") as directory:
            base = Path(directory)
            source = base / "source"
            names = (
                "guides/en–dash.md",
                "guides/em—dash.md",
                "guides/smart’apostrophe.md",
            )
            for index, name in enumerate(names):
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(f"fixture {index}\n".encode("utf-8"))
            archive_path = base / "unicode.zip"
            deterministic_zip(source, archive_path, prefix="fixture")
            expected = sorted(f"fixture/{name}" for name in names)
            self.assertEqual([], zip_filename_findings(archive_path, expected))
            with zipfile.ZipFile(archive_path) as archive:
                info_by_name = {info.filename: info for info in archive.infolist()}
                self.assertEqual(set(expected), set(info_by_name))
                for name in expected:
                    self.assertTrue(info_by_name[name].flag_bits & 0x0800)
                    self.assertEqual(
                        (source / name.removeprefix("fixture/")).read_bytes(),
                        archive.read(name),
                    )

    def test_malformed_utf8_archive_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nova-free-bad-zip-name-") as directory:
            base = Path(directory)
            source = base / "source"
            target = source / "guide—review.md"
            target.parent.mkdir(parents=True)
            target.write_text("fixture\n", encoding="utf-8", newline="\n")
            archive_path = base / "malformed.zip"
            deterministic_zip(source, archive_path, prefix="fixture")
            raw = archive_path.read_bytes()
            valid = "—".encode("utf-8")
            self.assertEqual(raw.count(valid), 2)
            archive_path.write_bytes(raw.replace(valid, b"\xd4\xc7\xf4"))
            findings = zip_filename_findings(
                archive_path,
                ["fixture/guide—review.md"],
            )
            self.assertTrue(
                any("not valid UTF-8" in finding for finding in findings),
                findings,
            )

            unflagged_path = base / "unflagged.zip"
            unflagged = bytearray(archive_path.read_bytes())
            for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
                header = unflagged.find(signature)
                self.assertNotEqual(header, -1)
                flags = int.from_bytes(
                    unflagged[header + flag_offset:header + flag_offset + 2],
                    "little",
                )
                unflagged[header + flag_offset:header + flag_offset + 2] = (
                    flags & ~0x0800
                ).to_bytes(2, "little")
            unflagged_path.write_bytes(unflagged)
            unflagged_findings = zip_filename_findings(
                unflagged_path,
                ["fixture/guide—review.md"],
            )
            self.assertTrue(
                any("not valid UTF-8" in finding for finding in unflagged_findings),
                unflagged_findings,
            )
            self.assertTrue(
                any("lacks the UTF-8 flag" in finding for finding in unflagged_findings),
                unflagged_findings,
            )

            drive_path = base / "drive-qualified.zip"
            with zipfile.ZipFile(drive_path, "w") as archive:
                archive.writestr("C:/escape.txt", b"escape")
            drive_findings = zip_filename_findings(
                drive_path,
                ["C:/escape.txt"],
            )
            self.assertTrue(
                any("unsafe ZIP member name" in finding for finding in drive_findings),
                drive_findings,
            )

    def test_source_lock_validation_rejects_stale_source_map(self) -> None:
        source_lock = json.loads((REPO / "design" / "source-lock.json").read_text(encoding="utf-8"))
        source_lock["source_map_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "Source map does not match"):
            build_release.validate_source_lock(
                REPO,
                REPO / "plugins" / "nova-the-optimal-ai",
                source_lock,
            )

    def test_require_clean_rejects_untracked_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nova-free-clean-") as directory:
            base = Path(directory)
            with patch.object(build_release, "git_value", side_effect=["deadbeef", "?? plugins/nova-the-optimal-ai/UNTRACKED.md"]):
                with self.assertRaisesRegex(RuntimeError, "including untracked files"):
                    build_release.build(REPO, base / "dist", base / "release", True)


if __name__ == "__main__":
    unittest.main()

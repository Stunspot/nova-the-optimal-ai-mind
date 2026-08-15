from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import scripts.package_loomfile as package_module
from scripts.init_loomfile import REQUIRED_DIRECTORIES, initialize
from scripts.package_loomfile import package
from scripts.validate_loomfile import validate


def manifest_from(archive_path: Path, root_name: str) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        return json.loads(
            archive.read(f"{root_name}/review/release-manifest.json").decode("utf-8")
        )


def assert_archive_manifest_matches(
    test: unittest.TestCase, archive_path: Path, root_name: str
) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(
            archive.read(f"{root_name}/review/release-manifest.json").decode("utf-8")
        )
        for entry in manifest["files"]:
            payload = archive.read(f"{root_name}/{entry['path']}")
            test.assertEqual(len(payload), entry["bytes"], entry["path"])
            test.assertEqual(
                hashlib.sha256(payload).hexdigest(), entry["sha256"], entry["path"]
            )


def project_snapshot(root: Path) -> list[tuple[str, str, str]]:
    snapshot: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            snapshot.append(("directory", relative, ""))
        elif path.is_file():
            snapshot.append(
                ("file", relative, hashlib.sha256(path.read_bytes()).hexdigest())
            )
    return snapshot


class InitializeLoomfileTests(unittest.TestCase):
    def test_new_loomfile_immediately_satisfies_the_state_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "first-project"
            created = initialize(destination, "First project")
            for relative in REQUIRED_DIRECTORIES:
                self.assertTrue((created / relative).is_dir(), relative)
            errors, warnings = validate(created)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_success_manifest_matches_every_archived_payload_without_mutating_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            archive = root / "project.zip"
            initialize(destination, "Manifest identity")
            manifest_path = destination / "review" / "release-manifest.json"
            manifest_before = manifest_path.read_bytes()

            package(destination, archive)

            assert_archive_manifest_matches(self, archive, destination.name)
            self.assertEqual(manifest_path.read_bytes(), manifest_before)

    def test_fresh_archive_round_trip_preserves_required_directories_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            archive = root / "project.zip"
            initialize(destination, "Round-trip validation")

            package(destination, archive)

            with tempfile.TemporaryDirectory() as extracted_directory:
                with zipfile.ZipFile(archive) as packaged_zip:
                    packaged_zip.extractall(extracted_directory)
                extracted_root = Path(extracted_directory) / destination.name
                for relative in REQUIRED_DIRECTORIES:
                    self.assertTrue((extracted_root / relative).is_dir(), relative)
                errors, warnings = validate(extracted_root)
                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])

    def test_existing_archive_refusal_preserves_archive_and_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            archive = root / "project.zip"
            initialize(destination, "Existing archive")
            package(destination, archive)
            archive_before = archive.read_bytes()
            manifest_path = destination / "review" / "release-manifest.json"
            manifest_before = manifest_path.read_bytes()

            with self.assertRaisesRegex(ValueError, "output already exists"):
                package(destination, archive)

            self.assertEqual(archive.read_bytes(), archive_before)
            self.assertEqual(manifest_path.read_bytes(), manifest_before)

    def test_output_inside_loomfile_is_rejected_without_project_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            initialize(destination, "Contained output")
            archive = destination / "review" / "release.zip"
            before = project_snapshot(destination)

            with self.assertRaisesRegex(ValueError, "output must be outside the Loomfile"):
                package(destination, archive)

            self.assertFalse(archive.exists())
            self.assertEqual(project_snapshot(destination), before)
            self.assertEqual(list(root.glob(f".{archive.name}.*.tmp")), [])

    def test_competing_output_is_not_overwritten_and_project_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            archive = root / "project.zip"
            initialize(destination, "Competing archive")
            manifest_path = destination / "review" / "release-manifest.json"
            manifest_before = manifest_path.read_bytes()
            competing_bytes = b"created by another process"

            def create_competing_output(*_args, **_kwargs):  # type: ignore[no-untyped-def]
                archive.write_bytes(competing_bytes)
                raise FileExistsError("simulated competing output")

            with patch.object(package_module.os, "link", side_effect=create_competing_output):
                with self.assertRaisesRegex(FileExistsError, "simulated competing output"):
                    package(destination, archive)

            self.assertEqual(archive.read_bytes(), competing_bytes)
            self.assertEqual(manifest_path.read_bytes(), manifest_before)
            self.assertEqual(list(root.glob(f".{archive.name}.*.tmp")), [])

    def test_mid_archive_failure_preserves_project_and_allows_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            archive = root / "project.zip"
            initialize(destination, "Interrupted archive")
            manifest_path = destination / "review" / "release-manifest.json"
            manifest_before = manifest_path.read_bytes()
            real_write = package_module._write_file_entry
            calls = 0

            def failing_write(*args, **kwargs):  # type: ignore[no-untyped-def]
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated archive write failure")
                return real_write(*args, **kwargs)

            with patch.object(package_module, "_write_file_entry", side_effect=failing_write):
                with self.assertRaisesRegex(OSError, "simulated archive write failure"):
                    package(destination, archive)

            self.assertEqual(manifest_path.read_bytes(), manifest_before)
            self.assertFalse(archive.exists())
            self.assertEqual(list(root.glob(f".{archive.name}.*.tmp")), [])

            packaged, _ = package(destination, archive)
            self.assertEqual(packaged, archive)
            assert_archive_manifest_matches(self, archive, destination.name)

    def test_source_change_during_packaging_matches_archived_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            archive = root / "project.zip"
            initialize(destination, "Concurrent source change")
            story = destination / "output" / "web" / "story.txt"
            story.write_text("before", encoding="utf-8")
            real_open = zipfile.ZipFile.open
            changed = False

            def mutate_before_entry(zip_self, name, *args, **kwargs):  # type: ignore[no-untyped-def]
                nonlocal changed
                if not changed and str(name).endswith("output/web/story.txt"):
                    story.write_text("after", encoding="utf-8")
                    changed = True
                return real_open(zip_self, name, *args, **kwargs)

            with patch.object(zipfile.ZipFile, "open", new=mutate_before_entry):
                package(destination, archive)

            self.assertTrue(changed)
            with zipfile.ZipFile(archive) as packaged_zip:
                self.assertEqual(
                    packaged_zip.read("project/output/web/story.txt"), b"after"
                )
            assert_archive_manifest_matches(self, archive, destination.name)

    def test_registered_source_change_is_rejected_by_archived_state_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            archive = root / "project.zip"
            initialize(destination, "Registered source change")
            source = destination / "sources" / "originals" / "source.txt"
            source.write_text("before", encoding="utf-8")
            source_manifest_path = destination / "sources" / "manifest.json"
            source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
            source_manifest["sources"] = [
                {
                    "id": "S1",
                    "path": "sources/originals/source.txt",
                    "sha256": hashlib.sha256(b"before").hexdigest(),
                }
            ]
            source_manifest_path.write_text(
                json.dumps(source_manifest, indent=2) + "\n", encoding="utf-8"
            )
            real_write = package_module._write_file_entry
            changed = False

            def mutate_registered_source(
                packaged_zip: zipfile.ZipFile, path: Path, arcname: str
            ) -> dict[str, object]:
                nonlocal changed
                if not changed and path == source:
                    source.write_text("after", encoding="utf-8")
                    changed = True
                return real_write(packaged_zip, path, arcname)

            with patch.object(
                package_module, "_write_file_entry", side_effect=mutate_registered_source
            ):
                with self.assertRaisesRegex(
                    ValueError, "Packaged Loomfile validation failed"
                ):
                    package(destination, archive)

            self.assertTrue(changed)
            self.assertFalse(archive.exists())
            self.assertEqual(list(root.glob(f".{archive.name}.*.tmp")), [])
            self.assertEqual(list(root.glob(f".{archive.name}.verify.*")), [])

            source.write_text("before", encoding="utf-8")
            package(destination, archive)
            assert_archive_manifest_matches(self, archive, destination.name)

    def test_link_side_effect_then_interrupt_preserves_valid_output_and_blocks_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            archive = root / "project.zip"
            initialize(destination, "Interrupted commit")
            manifest_path = destination / "review" / "release-manifest.json"
            manifest_before = manifest_path.read_bytes()
            real_link = os.link
            interrupted = False

            def link_then_interrupt(source: Path, target: Path) -> None:
                nonlocal interrupted
                real_link(source, target)
                interrupted = True
                raise KeyboardInterrupt("simulated interruption after final link")

            with patch.object(package_module.os, "link", side_effect=link_then_interrupt):
                with self.assertRaisesRegex(KeyboardInterrupt, "simulated interruption"):
                    package(destination, archive)

            self.assertTrue(interrupted)
            self.assertTrue(archive.exists())
            assert_archive_manifest_matches(self, archive, destination.name)
            archive_before = archive.read_bytes()
            self.assertEqual(manifest_path.read_bytes(), manifest_before)
            self.assertEqual(list(root.glob(f".{archive.name}.*.tmp")), [])
            self.assertEqual(list(root.glob(f".{archive.name}.verify.*")), [])

            with self.assertRaisesRegex(ValueError, "output already exists"):
                package(destination, archive)
            self.assertEqual(archive.read_bytes(), archive_before)

    def test_post_link_replacement_is_preserved_during_interrupted_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project"
            archive = root / "project.zip"
            initialize(destination, "Competing replacement")
            manifest_path = destination / "review" / "release-manifest.json"
            manifest_before = manifest_path.read_bytes()
            competing_bytes = b"replacement created by another process"
            real_remove = package_module._remove_if_present
            interrupted = False

            def replace_output_then_interrupt(path: Path) -> None:
                nonlocal interrupted
                if path.name.endswith(".tmp") and archive.exists() and not interrupted:
                    archive.unlink()
                    archive.write_bytes(competing_bytes)
                    interrupted = True
                    raise KeyboardInterrupt("simulated interruption after replacement")
                real_remove(path)

            with patch.object(
                package_module, "_remove_if_present", side_effect=replace_output_then_interrupt
            ):
                with self.assertRaisesRegex(KeyboardInterrupt, "simulated interruption"):
                    package(destination, archive)

            self.assertTrue(interrupted)
            self.assertEqual(archive.read_bytes(), competing_bytes)
            self.assertEqual(manifest_path.read_bytes(), manifest_before)
            self.assertEqual(list(root.glob(f".{archive.name}.*.tmp")), [])
            self.assertEqual(list(root.glob(f".{archive.name}.verify.*")), [])


if __name__ == "__main__":
    unittest.main()

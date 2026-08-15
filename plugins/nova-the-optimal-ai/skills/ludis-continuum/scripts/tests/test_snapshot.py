from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import snapshot_campaign
from exportlib import ExportError
from snapshot_campaign import build_snapshot


class SnapshotTests(unittest.TestCase):
    def test_snapshot_is_deterministic_and_excludes_prior_checkpoints(self):
        with tempfile.TemporaryDirectory() as temporary:
            campaign = Path(temporary) / "campaign"
            (campaign / "checkpoints").mkdir(parents=True)
            (campaign / "campaign-ledger.json").write_text(json.dumps({"campaign": {"id": "x"}}), encoding="utf-8")
            (campaign / "notes.md").write_text("A useful note.\n", encoding="utf-8")
            (campaign / "checkpoints" / "old.zip").write_bytes(b"old")
            first, first_archive, first_content = build_snapshot(campaign, campaign / "checkpoints" / "first.zip")
            second, second_archive, second_content = build_snapshot(campaign, campaign / "checkpoints" / "second.zip")
            self.assertEqual(first_archive, second_archive)
            self.assertEqual(first_content, second_content)
            with zipfile.ZipFile(first) as archive:
                self.assertNotIn("checkpoints/old.zip", archive.namelist())
                self.assertIn("snapshot-manifest.json", archive.namelist())
                self.assertIn("notes.md", archive.namelist())

    def test_explicit_snapshot_output_inside_campaign_excludes_only_owned_work_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            campaign = Path(temporary) / "campaign"
            campaign.mkdir()
            (campaign / "campaign-ledger.json").write_text(json.dumps({"campaign": {"id": "x"}}), encoding="utf-8")
            (campaign / "notes.md").write_text("kept source\n", encoding="utf-8")
            output = campaign / "snapshot.zip"
            built, _, _ = build_snapshot(campaign, output)
            self.assertEqual(built, output.resolve())
            with zipfile.ZipFile(output) as archive:
                self.assertIn("notes.md", archive.namelist())
                self.assertNotIn("snapshot.zip", archive.namelist())
    def test_snapshot_rechecks_the_entire_source_set_after_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            campaign = Path(temporary) / "campaign"
            campaign.mkdir()
            notes = campaign / "notes.md"
            old_notes = b"old notes\n"
            new_notes = b"new notes\n"
            notes.write_bytes(old_notes)
            ledger = {"campaign": {"id": "x"}, "notes_sha256": hashlib.sha256(old_notes).hexdigest()}
            ledger_path = campaign / "campaign-ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            real_freeze = snapshot_campaign.freeze_file

            def mutate_generation(path, label):
                frozen = real_freeze(path, label)
                if path == ledger_path.resolve():
                    notes.write_bytes(new_notes)
                    replacement = {"campaign": {"id": "x"}, "notes_sha256": hashlib.sha256(new_notes).hexdigest()}
                    ledger_path.write_text(json.dumps(replacement), encoding="utf-8")
                return frozen

            with patch("snapshot_campaign.freeze_file", side_effect=mutate_generation):
                with self.assertRaisesRegex(ExportError, "changed before snapshot"):
                    build_snapshot(campaign, campaign / "checkpoint.zip")
            self.assertFalse((campaign / "checkpoint.zip").exists())

    def test_snapshot_final_publish_preserves_uncoordinated_occupant(self):
        with tempfile.TemporaryDirectory() as temporary:
            campaign = Path(temporary) / "campaign"
            campaign.mkdir()
            (campaign / "campaign-ledger.json").write_text(json.dumps({"campaign": {"id": "x"}}), encoding="utf-8")
            output = Path(temporary) / "checkpoint.zip"
            external = b"external recovery file won publication race"
            original_link = snapshot_campaign.os.link
            injected = False

            def occupy_then_link(source, destination):
                nonlocal injected
                if not injected:
                    injected = True
                    destination.write_bytes(external)
                return original_link(source, destination)

            with patch("snapshot_campaign.os.link", side_effect=occupy_then_link):
                with self.assertRaisesRegex(ExportError, "external file preserved"):
                    build_snapshot(campaign, output)
            self.assertTrue(injected)
            self.assertEqual(output.read_bytes(), external)
            recoveries = list(output.parent.glob(".checkpoint.zip.*.ludis-unpublished"))
            self.assertEqual(len(recoveries), 1)
            with zipfile.ZipFile(recoveries[0]) as archive:
                self.assertIn("snapshot-manifest.json", archive.namelist())
    def test_snapshot_recovery_publish_preserves_existing_recovery_occupant(self):
        with tempfile.TemporaryDirectory() as temporary:
            campaign = Path(temporary) / "campaign"
            campaign.mkdir()
            (campaign / "campaign-ledger.json").write_text(json.dumps({"campaign": {"id": "x"}}), encoding="utf-8")
            output = Path(temporary) / "checkpoint.zip"
            destination_external = b"external final occupant"
            recovery_external = b"older independent recovery evidence"
            original_link = snapshot_campaign.os.link
            link_calls = 0
            occupied_recovery = None

            def occupy_final_and_recovery(source, destination):
                nonlocal link_calls, occupied_recovery
                link_calls += 1
                if link_calls == 1:
                    destination.write_bytes(destination_external)
                elif link_calls == 2:
                    destination.write_bytes(recovery_external)
                    occupied_recovery = destination
                return original_link(source, destination)

            with patch("snapshot_campaign.os.link", side_effect=occupy_final_and_recovery):
                with self.assertRaisesRegex(ExportError, "external file preserved"):
                    build_snapshot(campaign, output)
            self.assertEqual(output.read_bytes(), destination_external)
            self.assertIsNotNone(occupied_recovery)
            self.assertEqual(occupied_recovery.read_bytes(), recovery_external)
            recoveries = list(output.parent.glob(".checkpoint.zip.*.ludis-unpublished*"))
            self.assertEqual(len(recoveries), 2)
            published = next(path for path in recoveries if path.resolve() != occupied_recovery.resolve())
            with zipfile.ZipFile(published) as archive:
                self.assertIn("snapshot-manifest.json", archive.namelist())
    def test_snapshot_refuses_to_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            campaign = Path(temporary) / "campaign"
            campaign.mkdir()
            (campaign / "campaign-ledger.json").write_text(json.dumps({"campaign": {"id": "x"}}), encoding="utf-8")
            output = Path(temporary) / "existing.zip"
            original = b"preserve this recovery evidence"
            output.write_bytes(original)
            with self.assertRaisesRegex(ExportError, "immutable snapshot path"):
                build_snapshot(campaign, output)
            self.assertEqual(output.read_bytes(), original)

    def test_competing_snapshots_reserve_the_same_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            campaign = Path(temporary) / "campaign"
            campaign.mkdir()
            (campaign / "campaign-ledger.json").write_text(json.dumps({"campaign": {"id": "x"}}), encoding="utf-8")
            output = Path(temporary) / "checkpoint.zip"
            entered = threading.Event()
            release = threading.Event()
            original = snapshot_campaign.write_deterministic_zip

            def delayed_first(*args, **kwargs):
                entered.set()
                if not release.wait(10):
                    raise AssertionError("timed out waiting for snapshot release")
                return original(*args, **kwargs)

            with patch("snapshot_campaign.write_deterministic_zip", side_effect=delayed_first):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    winner = pool.submit(build_snapshot, campaign, output)
                    self.assertTrue(entered.wait(10))
                    try:
                        with self.assertRaisesRegex(ExportError, "another Ludis operation"):
                            build_snapshot(campaign, output)
                    finally:
                        release.set()
                    won_output, _, _ = winner.result(timeout=20)
            self.assertEqual(won_output, output.resolve())
            self.assertTrue(output.is_file())
            self.assertEqual(list(output.parent.glob("*.ludis-lock")), [])


if __name__ == "__main__":
    unittest.main()

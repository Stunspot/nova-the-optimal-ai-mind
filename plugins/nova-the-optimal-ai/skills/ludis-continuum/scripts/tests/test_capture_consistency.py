from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import exportlib
from exportlib import ExportError, capture_campaign


def _object_record(object_id: str, asset_ids: list[str]) -> dict:
    return {
        "id": object_id,
        "kind": "scene",
        "status": "active_canon",
        "visibility": "player_safe",
        "authority": "gm_approved",
        "provenance": ["capture test"],
        "confidence": "high",
        "tenure": "campaign",
        "title": object_id,
        "content": "Stable capture fixture.",
        "links": [],
        "asset_ids": asset_ids,
        "export_eligibility": "eligible",
    }


class CaptureConsistencyTests(unittest.TestCase):
    def make_campaign(self, root: Path) -> Path:
        campaign = root / "campaign"
        media = campaign / "media"
        media.mkdir(parents=True)
        (media / "first.bin").write_bytes(b"first stable source")
        (media / "second.bin").write_bytes(b"second stable source")
        ledger = {
            "format": "cd-ludis-campaign-ledger/v2",
            "campaign": {"id": "capture-test", "title": "Capture Test"},
            "table_contract": {
                "player_preferences": [],
                "lines": [],
                "veils": [],
                "other_boundaries": [],
            },
            "objects": [_object_record("scene-one", ["asset-first", "asset-second"])],
            "assets": [
                {
                    "id": "asset-first",
                    "path": "media/first.bin",
                    "kind": "handout",
                    "visibility": "player_safe",
                    "rights": {"status": "owned"},
                    "provenance": ["capture test"],
                },
                {
                    "id": "asset-second",
                    "path": "media/second.bin",
                    "kind": "handout",
                    "visibility": "player_safe",
                    "rights": {"status": "owned"},
                    "provenance": ["capture test"],
                },
            ],
            "sessions": [],
            "approvals": [],
            "publication": {"status": "private_draft"},
            "extensions": {},
        }
        (campaign / "campaign-ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        return campaign

    def test_unchanged_declared_source_set_captures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            campaign = self.make_campaign(root)
            captured = capture_campaign(campaign, root / "capture")
            self.assertEqual(
                [entry["path"] for entry in captured.capture_manifest["files"]],
                ["campaign-ledger.json", "media/first.bin", "media/second.bin"],
            )

    def test_asset_changed_after_its_read_fails_end_of_capture_recheck(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            campaign = self.make_campaign(root)
            first = campaign / "media" / "first.bin"
            real_capture_one = exportlib._capture_one

            def mutate_earlier_source(source, destination, relative_path):
                result = real_capture_one(source, destination, relative_path)
                if relative_path == "media/second.bin":
                    first.write_bytes(b"first source changed after its capture")
                return result

            with patch("exportlib._capture_one", side_effect=mutate_earlier_source):
                with self.assertRaisesRegex(ExportError, "source changed before capture completed: media/first.bin"):
                    capture_campaign(campaign, root / "capture")

    def test_ledger_changed_after_its_read_fails_end_of_capture_recheck(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            campaign = self.make_campaign(root)
            ledger = campaign / "campaign-ledger.json"
            real_capture_one = exportlib._capture_one

            def mutate_ledger_late(source, destination, relative_path):
                result = real_capture_one(source, destination, relative_path)
                if relative_path == "media/second.bin":
                    ledger.write_bytes(ledger.read_bytes() + b" ")
                return result

            with patch("exportlib._capture_one", side_effect=mutate_ledger_late):
                with self.assertRaisesRegex(ExportError, "source changed before capture completed: campaign-ledger.json"):
                    capture_campaign(campaign, root / "capture")


if __name__ == "__main__":
    unittest.main()

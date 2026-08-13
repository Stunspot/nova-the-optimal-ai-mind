from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


class CommandIntegrationTests(unittest.TestCase):
    def run_command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", *arguments], capture_output=True, text=True)

    def test_init_requires_explicit_owner_identity_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "campaign"
            result = self.run_command(str(SCRIPTS / "init_campaign.py"), str(destination))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(destination.exists())

    def test_init_with_seed_writes_valid_v2_ledger(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "campaign"
            result = self.run_command(
                str(SCRIPTS / "init_campaign.py"),
                str(destination),
                "--campaign-seed", "my home table",
                "--title", "Home Game",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            ledger = json.loads((destination / "campaign-ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["format"], "cd-ludis-campaign-ledger/v2")
            self.assertTrue(ledger["campaign"]["id"].startswith("campaign-"))
            self.assertEqual(ledger["campaign"]["title"], "Home Game")

    def test_init_refuses_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "campaign"
            destination.mkdir()
            (destination / "keep.txt").write_text("keep", encoding="utf-8")
            result = self.run_command(str(SCRIPTS / "init_campaign.py"), str(destination), "--campaign-id", "campaign-home")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((destination / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_player_safe_legacy_command_builds_candidate_not_loose_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "player.candidate.zip"
            ledger = ROOT / "examples" / "tonight-pack" / "campaign" / "campaign-ledger.json"
            result = self.run_command(str(SCRIPTS / "export_player_safe.py"), str(ledger), str(output))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output.is_file())
            self.assertTrue(Path(str(output) + ".preview.html").is_file())
            self.assertIn("APPROVAL REQUIRED", result.stdout)

    def test_promote_records_local_assertion(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "campaign-ledger.json"
            source = ROOT / "scripts" / "tests" / "fixtures" / "ledger" / "v2-valid.json"
            ledger = json.loads(source.read_text(encoding="utf-8"))
            target = ledger["objects"][0]
            target["status"] = "proposed"
            target["authority"] = "user_proposed"
            ledger["approvals"] = []
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            result = self.run_command(
                str(SCRIPTS / "promote_object.py"), str(ledger_path), target["id"],
                "--gm-approved", "--asserted-by", "Example GM",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            updated = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["approvals"][-1]["asserted_by"], "Example GM")
            self.assertIn("unauthenticated", result.stdout)


if __name__ == "__main__":
    unittest.main()
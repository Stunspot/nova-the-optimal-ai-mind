from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "record_import_observation.py"
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))
import record_import_observation as observation_module  # noqa: E402


class ImportObservationTests(unittest.TestCase):
    def run_command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *arguments], capture_output=True, text=True)

    def test_receipt_binds_bundle_and_evidence_without_promoting_support(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "campaign.zip"
            evidence = root / "import-log.txt"
            output = root / "observation.json"
            bundle.write_bytes(b"exact bundle bytes")
            evidence.write_bytes(b"Foundry import completed")
            result = self.run_command(
                str(bundle), str(output),
                "--target", "foundry-v14",
                "--target-version", "14.365",
                "--result", "imported",
                "--asserted-by", "Example GM",
                "--observed-at", "2026-08-13T10:30:00-05:00",
                "--notes", "Disposable-world smoke test.",
                "--evidence", str(evidence),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(receipt["format"], "cd-ludis-import-observation/v1")
            self.assertEqual(receipt["observed_at"], "2026-08-13T15:30:00Z")
            self.assertEqual(receipt["bundle"]["sha256"], hashlib.sha256(bundle.read_bytes()).hexdigest())
            self.assertEqual(receipt["evidence"][0]["sha256"], hashlib.sha256(evidence.read_bytes()).hexdigest())
            self.assertIs(receipt["promotes_product_compatibility"], False)
            self.assertIn("cannot promote", result.stdout)

    def test_file_evidence_fails_closed_when_source_mutates_during_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "evidence.bin"
            source.write_bytes(b"captured bytes")
            real_read_bytes = Path.read_bytes
            injected = False

            def mutate_after_read(candidate):
                nonlocal injected
                data = real_read_bytes(candidate)
                if not injected and candidate == source.resolve():
                    injected = True
                    candidate.write_bytes(data + b" changed")
                return data

            with patch.object(Path, "read_bytes", autospec=True, side_effect=mutate_after_read):
                with self.assertRaisesRegex(observation_module.ObservationError, "changed while being read"):
                    observation_module.file_evidence(source)
            self.assertTrue(injected)
    def test_bundle_changed_after_its_read_fails_complete_set_recheck(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "campaign.zip"
            bundle.write_bytes(b"captured bundle")
            real_freeze = observation_module._freeze_file_evidence
            injected = False

            def freeze_then_mutate(path):
                nonlocal injected
                frozen = real_freeze(path)
                if Path(path) == bundle and not injected:
                    injected = True
                    bundle.write_bytes(b"later bundle generation")
                return frozen

            with patch.object(observation_module, "_freeze_file_evidence", side_effect=freeze_then_mutate):
                with self.assertRaisesRegex(observation_module.ObservationError, "changed after capture"):
                    observation_module.build_observation(
                        bundle,
                        target="foundry-v14",
                        target_version="14.365",
                        result="imported",
                        asserted_by="Example GM",
                    )
            self.assertTrue(injected)

    def test_earlier_evidence_changed_after_read_fails_complete_set_recheck(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "campaign.zip"
            first = root / "first.log"
            second = root / "second.log"
            bundle.write_bytes(b"bundle")
            first.write_bytes(b"first generation")
            second.write_bytes(b"second evidence")
            real_freeze = observation_module._freeze_file_evidence
            injected = False

            def freeze_then_mutate(path):
                nonlocal injected
                frozen = real_freeze(path)
                if Path(path) == second and not injected:
                    injected = True
                    first.write_bytes(b"later first generation")
                return frozen

            with patch.object(observation_module, "_freeze_file_evidence", side_effect=freeze_then_mutate):
                with self.assertRaisesRegex(observation_module.ObservationError, "changed after capture"):
                    observation_module.build_observation(
                        bundle,
                        target="alchemy",
                        target_version="current-web",
                        result="partial",
                        asserted_by="Example GM",
                        evidence=[first, second],
                    )
            self.assertTrue(injected)

    def test_path_replacement_after_capture_fails_identity_recheck(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "campaign.zip"
            replacement = root / "replacement.zip"
            bundle.write_bytes(b"captured bundle")
            replacement.write_bytes(b"replacement generation")
            real_freeze = observation_module._freeze_file_evidence
            injected = False

            def freeze_then_replace(path):
                nonlocal injected
                frozen = real_freeze(path)
                if Path(path) == bundle and not injected:
                    injected = True
                    os.replace(replacement, bundle)
                return frozen

            with patch.object(observation_module, "_freeze_file_evidence", side_effect=freeze_then_replace):
                with self.assertRaisesRegex(observation_module.ObservationError, "changed after capture"):
                    observation_module.build_observation(
                        bundle,
                        target="foundry-v14",
                        target_version="14.365",
                        result="failed",
                        asserted_by="Example GM",
                    )
            self.assertTrue(injected)

    def test_stable_source_set_and_prewrite_recheck(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "campaign.zip"
            evidence = root / "import.log"
            output = root / "observation.json"
            bundle.write_bytes(b"stable bundle")
            evidence.write_bytes(b"stable evidence")
            capture = observation_module.capture_observation(
                bundle,
                target="foundry-v14",
                target_version="14.365",
                result="imported",
                asserted_by="Example GM",
                evidence=[evidence],
            )
            self.assertEqual(capture.observation["bundle"]["sha256"], hashlib.sha256(b"stable bundle").hexdigest())
            observation_module.write_observation(output, capture.observation, frozen_inputs=capture.inputs)
            self.assertTrue(output.is_file())

            second_capture = observation_module.capture_observation(
                bundle,
                target="foundry-v14",
                target_version="14.365",
                result="imported",
                asserted_by="Example GM",
                evidence=[evidence],
            )
            evidence.write_bytes(b"changed before receipt write")
            second_output = root / "second-observation.json"
            with self.assertRaisesRegex(observation_module.ObservationError, "changed after capture"):
                observation_module.write_observation(
                    second_output,
                    second_capture.observation,
                    frozen_inputs=second_capture.inputs,
                )
            self.assertFalse(second_output.exists())

    def test_duplicate_or_ambiguous_evidence_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "campaign.zip"
            first = root / "a" / "same.log"
            second = root / "b" / "SAME.LOG"
            bundle.write_bytes(b"bundle")
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            with self.assertRaisesRegex(observation_module.ObservationError, "filenames must be unique"):
                observation_module.build_observation(
                    bundle,
                    target="alchemy",
                    target_version="current-web",
                    result="failed",
                    asserted_by="Example GM",
                    evidence=[first, second],
                )
            with self.assertRaisesRegex(observation_module.ObservationError, "distinct files"):
                observation_module.build_observation(
                    bundle,
                    target="alchemy",
                    target_version="current-web",
                    result="failed",
                    asserted_by="Example GM",
                    evidence=[bundle],
                )

    def test_existing_receipt_is_immutable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "campaign.zip"
            output = root / "observation.json"
            bundle.write_bytes(b"bundle")
            output.write_text("keep", encoding="utf-8")
            result = self.run_command(
                str(bundle), str(output),
                "--target", "alchemy",
                "--target-version", "current-web",
                "--result", "failed",
                "--asserted-by", "Example GM",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep")

    def test_naive_timestamp_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "campaign.zip"
            output = root / "observation.json"
            bundle.write_bytes(b"bundle")
            result = self.run_command(
                str(bundle), str(output),
                "--target", "alchemy",
                "--target-version", "current-web",
                "--result", "partial",
                "--asserted-by", "Example GM",
                "--observed-at", "2026-08-13T10:30:00",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
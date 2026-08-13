from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import export_target
from export_target import (
    TargetExportError,
    approve_target,
    build_target,
    verify_target_zip,
)
from exportlib import ExportError, sha256_file


class TargetExportIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.campaign = ROOT / "examples" / "tonight-pack" / "campaign"

    def test_alchemy_example_builds_individual_and_bulk_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "mara-alchemy.zip"
            result = build_target(self.campaign, output, "alchemy", "gm")
            self.assertTrue(result.finalized)
            report = verify_target_zip(output)
            self.assertEqual(report["target"], "alchemy")
            self.assertFalse(report["compatibility"]["live_import_verified"])
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertIn("_all.json", names)
                bulk = json.loads(archive.read("_all.json"))
                self.assertEqual([item["name"] for item in bulk["characters"]], ["Mara Venn"])
                self.assertEqual(bulk["characters"][0]["systemKey"], "5e")

    def test_foundry_example_builds_v14_level_module_deterministically(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = build_target(self.campaign, root / "one.zip", "foundry-v14", "gm")
            second = build_target(self.campaign, root / "two.zip", "foundry-v14", "gm")
            self.assertEqual(first.artifact_sha256, second.artifact_sha256)
            with zipfile.ZipFile(first.artifact) as archive:
                payload = json.loads(archive.read("data/ludis-foundry-v14.json"))
                self.assertEqual(payload["target"], {"build": 365, "generation": 14})
                self.assertEqual(payload["audience"], "gm")
                self.assertNotIn("Actor", payload["documents"])
                self.assertNotIn("Item", payload["documents"])
                scene = next(record for record in payload["documents"]["Scene"] if record["sourceId"] == "scene-tollhouse")
                self.assertNotIn("background", scene["scene"])
                self.assertTrue(scene["levels"][0]["background"]["src"].startswith("modules/"))
                scene_flags = scene["scene"]["flags"]["ludis"]
                self.assertEqual(scene_flags["campaignId"], payload["pack"]["id"])
                self.assertEqual(scene_flags["sourceId"], "scene-tollhouse")
                self.assertEqual(scene_flags["audience"], "gm")
                self.assertRegex(scene_flags["importRevisionSha256"], r"^[0-9a-f]{64}$")

    def test_player_foundry_candidate_has_visual_preview_and_finalizes_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_target(
                self.campaign,
                root / "player-foundry.candidate.zip",
                "foundry-v14",
                "player",
            )
            preview = result.preview.read_text(encoding="utf-8")
            self.assertIn("data:image/png;base64,", preview)
            self.assertIn("Top-down map of a roofless stone-and-timber tollhouse beside a river, with a muddy fenced yard and broken cart.", preview)
            self.assertIn("Members not rendered here", preview)
            self.assertIn("one required review surface, not the whole candidate", preview)
            self.assertNotIn("Mara Venn", preview)
            self.assertNotIn("The Name Mara Removed", preview)
            with zipfile.ZipFile(result.artifact) as archive:
                payload = json.loads(archive.read("data/ludis-foundry-v14.json"))
                self.assertEqual(payload["audience"], "player")
                documents = payload["documents"]["JournalEntry"] + payload["documents"]["RollTable"]
                self.assertTrue(all(document["ownership"]["default"] == 2 for document in documents))
                self.assertTrue(all(record["scene"]["ownership"]["default"] == 2 for record in payload["documents"]["Scene"]))
            candidate_digest = sha256_file(result.artifact)
            final, receipt = approve_target(result.artifact, "Example GM")
            self.assertEqual(sha256_file(final), candidate_digest)
            approval = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(approval["target"], "foundry-v14")
            self.assertEqual(approval["assertion_type"], "unauthenticated_local_operator_attestation")

    def test_competing_target_builds_reserve_artifact_and_sidecar_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "foundry.zip"
            overlapping_output = Path(str(output) + ".preview.html")
            started = threading.Event()
            release = threading.Event()
            call_guard = threading.Lock()
            calls = 0
            original = export_target._build_target_reserved

            def delayed_first(*args, **kwargs):
                nonlocal calls
                with call_guard:
                    calls += 1
                    call_number = calls
                if call_number == 1:
                    started.set()
                    if not release.wait(10):
                        raise AssertionError("timed out waiting to release first target build")
                return original(*args, **kwargs)

            with patch.object(export_target, "_build_target_reserved", side_effect=delayed_first):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    winner = pool.submit(build_target, self.campaign, output, "foundry-v14", "gm")
                    self.assertTrue(started.wait(10), "first target build did not acquire its reservation")
                    try:
                        with self.assertRaisesRegex(ExportError, "another Ludis operation"):
                            build_target(self.campaign, overlapping_output, "foundry-v14", "gm")
                    finally:
                        release.set()
                    result = winner.result(timeout=20)

            self.assertEqual(result.artifact, output.resolve())
            verify_target_zip(output)
            self.assertTrue(result.preview.read_bytes().lower().startswith(b"<!doctype html>"))
            self.assertFalse(Path(str(overlapping_output) + ".audit.json").exists())
            self.assertFalse(Path(str(overlapping_output) + ".preview.html").exists())
            self.assertEqual(list(root.glob("*.ludis-lock")), [])

    def test_competing_target_approvals_reserve_final_and_receipt_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = build_target(
                self.campaign,
                root / "player.candidate.zip",
                "foundry-v14",
                "player",
            ).artifact
            final = root / "approved.zip"
            receipt = root / "approved.zip.approval.json"
            overlapping_final = receipt
            overlapping_receipt = root / "approved.zip.approval.json.approval.json"
            started = threading.Event()
            release = threading.Event()
            call_guard = threading.Lock()
            calls = 0
            original = export_target._approve_target_reserved

            def delayed_first(*args, **kwargs):
                nonlocal calls
                with call_guard:
                    calls += 1
                    call_number = calls
                if call_number == 1:
                    started.set()
                    if not release.wait(10):
                        raise AssertionError("timed out waiting to release first target approval")
                return original(*args, **kwargs)

            with patch.object(export_target, "_approve_target_reserved", side_effect=delayed_first):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    winner = pool.submit(approve_target, candidate, "First GM", final)
                    self.assertTrue(started.wait(10), "first target approval did not acquire its reservation")
                    try:
                        with self.assertRaisesRegex(ExportError, "another Ludis operation"):
                            approve_target(candidate, "Second GM", overlapping_final)
                    finally:
                        release.set()
                    won_final, won_receipt = winner.result(timeout=20)

            self.assertEqual(won_final, final.resolve())
            self.assertEqual(won_receipt, receipt.resolve())
            self.assertEqual(final.read_bytes(), candidate.read_bytes())
            approval = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(approval["asserted_by"], "First GM")
            self.assertFalse(overlapping_receipt.exists())
            self.assertEqual(list(root.glob("*.ludis-lock")), [])

    def test_uncooperative_target_occupant_is_preserved_at_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "foundry.zip"
            original_publish = export_target.publish_file_if_absent

            def occupy_artifact(staged, destination, label):
                if label == "target artifact":
                    destination.write_bytes(b"foreign target occupant")
                return original_publish(staged, destination, label)

            with patch.object(export_target, "publish_file_if_absent", side_effect=occupy_artifact):
                with self.assertRaisesRegex(TargetExportError, "immutable target artifact path became occupied"):
                    build_target(self.campaign, output, "foundry-v14", "gm")
            self.assertEqual(output.read_bytes(), b"foreign target occupant")

    def test_target_approval_idempotence_requires_complete_untampered_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_target(self.campaign, root / "player.candidate.zip", "foundry-v14", "player")
            final, receipt = approve_target(result.artifact, "Example GM")
            original_receipt = receipt.read_bytes()
            second_final, second_receipt = approve_target(result.artifact, "Example GM")
            self.assertEqual((second_final, second_receipt), (final, receipt))
            self.assertEqual(receipt.read_bytes(), original_receipt)
            with self.assertRaisesRegex(TargetExportError, "different local operator"):
                approve_target(result.artifact, "Someone Else")
            self.assertEqual(receipt.read_bytes(), original_receipt)

            baseline = json.loads(original_receipt)
            mutations = {
                "format": "foreign-receipt/v9",
                "state": "draft",
                "target": "alchemy",
                "adapter": "foreign-adapter/v9",
                "candidate_sha256": "0" * 64,
                "preview_sha256": "1" * 64,
                "audit_sha256": "2" * 64,
                "approved_at": "not-a-timestamp",
                "limitations": "tampered",
            }
            for field, value in mutations.items():
                with self.subTest(field=field):
                    changed = dict(baseline)
                    changed[field] = value
                    receipt.write_text(json.dumps(changed), encoding="utf-8")
                    with self.assertRaisesRegex(TargetExportError, "different evidence"):
                        approve_target(result.artifact, "Example GM")
            missing = dict(baseline)
            missing.pop("preview_sha256")
            receipt.write_text(json.dumps(missing), encoding="utf-8")
            with self.assertRaisesRegex(TargetExportError, "different evidence"):
                approve_target(result.artifact, "Example GM")
            extra = dict(baseline)
            extra["unbound"] = True
            receipt.write_text(json.dumps(extra), encoding="utf-8")
            with self.assertRaisesRegex(TargetExportError, "different evidence"):
                approve_target(result.artifact, "Example GM")
            receipt.write_text(json.dumps(baseline), encoding="utf-8")
            with self.assertRaisesRegex(TargetExportError, "different evidence"):
                approve_target(result.artifact, "Example GM")
            receipt.write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(TargetExportError, "receipt is unreadable"):
                approve_target(result.artifact, "Example GM")

    def test_target_candidate_mutation_stales_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_target(self.campaign, root / "player.candidate.zip", "foundry-v14", "player")
            result.preview.write_text(result.preview.read_text(encoding="utf-8") + "changed", encoding="utf-8")
            with self.assertRaisesRegex(TargetExportError, "preview bytes changed"):
                approve_target(result.artifact, "Example GM")

    def test_target_approval_fails_if_preview_or_audit_changes_during_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = build_target(self.campaign, root / "player.candidate.zip", "foundry-v14", "player")
            audit = Path(str(result.artifact) + ".audit.json")
            original_verify = export_target.verify_target_zip

            def mutate_evidence_during_verify(path):
                result.preview.write_text(result.preview.read_text(encoding="utf-8") + "changed", encoding="utf-8")
                audit.write_text(audit.read_text(encoding="utf-8") + " ", encoding="utf-8")
                return original_verify(path)

            with patch.object(export_target, "verify_target_zip", side_effect=mutate_evidence_during_verify):
                with self.assertRaisesRegex(TargetExportError, "changed before approval completed"):
                    approve_target(result.artifact, "Example GM")
            self.assertFalse((root / "player.zip").exists())
            self.assertFalse((root / "player.zip.approval.json").exists())
    def test_alchemy_does_not_infer_campaign_system(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copied = root / "campaign"
            shutil.copytree(self.campaign, copied)
            ledger_path = copied / "campaign-ledger.json"
            source = json.loads(ledger_path.read_text(encoding="utf-8"))
            npc = next(obj for obj in source["objects"] if obj["id"] == "npc-mara-venn")
            del npc["data"]["systemKey"]
            ledger_path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaisesRegex(TargetExportError, "explicit systemKey"):
                build_target(copied, root / "alchemy.zip", "alchemy", "gm")

    def test_verify_rejects_noncanonical_unsafe_and_colliding_target_names(self):
        injected_names = ["./module.json", "scripts//alias.mjs", "C:/module.json", "../outside/", "MODULE.JSON"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, name in enumerate(injected_names):
                with self.subTest(name=name):
                    output = root / f"foundry-{index}.zip"
                    build_target(self.campaign, output, "foundry-v14", "gm")
                    with zipfile.ZipFile(output, "a") as archive:
                        archive.writestr(name, b"unsafe")
                    with self.assertRaises(TargetExportError):
                        verify_target_zip(output)

    def test_standalone_verifier_rejects_foundry_code_and_manifest_injection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "foundry.zip"
            build_target(self.campaign, original, "foundry-v14", "gm")
            with zipfile.ZipFile(original, "r") as archive:
                baseline = {name: archive.read(name) for name in archive.namelist()}

            variants = []

            appended_importer = dict(baseline)
            appended_importer["scripts/importer.mjs"] += b"\nconsole.log('appended');\n"
            variants.append(("appended-importer", appended_importer))

            scripted_manifest = dict(baseline)
            manifest = json.loads(scripted_manifest["module.json"])
            manifest["scripts"] = ["scripts/evil.js"]
            scripted_manifest["module.json"] = (json.dumps(manifest) + "\n").encode("utf-8")
            variants.append(("manifest-scripts", scripted_manifest))

            altered_esmodules = dict(baseline)
            manifest = json.loads(altered_esmodules["module.json"])
            manifest["esmodules"] = ["scripts/importer.mjs", "scripts/evil.mjs"]
            altered_esmodules["module.json"] = (json.dumps(manifest) + "\n").encode("utf-8")
            variants.append(("altered-esmodules", altered_esmodules))

            extra_code = dict(baseline)
            extra_code["scripts/evil.mjs"] = b"export default true;\n"
            variants.append(("extra-code", extra_code))

            extra_document = dict(baseline)
            extra_document["README.txt"] = b"unlisted member"
            variants.append(("unlisted-member", extra_document))

            for label, members in variants:
                with self.subTest(label=label):
                    damaged = root / f"{label}.zip"
                    with zipfile.ZipFile(damaged, "w", compression=zipfile.ZIP_STORED) as archive:
                        for name, data in sorted(members.items()):
                            archive.writestr(name, data)
                    with self.assertRaises(TargetExportError):
                        verify_target_zip(damaged)
    def test_verify_rejects_target_member_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "foundry.zip"
            build_target(self.campaign, output, "foundry-v14", "gm")
            with zipfile.ZipFile(output, "a") as archive:
                archive.writestr("data/ludis-foundry-v14.json", b"{}")
            with self.assertRaises(TargetExportError):
                verify_target_zip(output)


if __name__ == "__main__":
    unittest.main()
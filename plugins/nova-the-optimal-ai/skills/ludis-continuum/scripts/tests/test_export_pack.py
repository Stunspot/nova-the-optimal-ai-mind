from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import exportlib
from exportlib import (
    ExportError,
    approve_candidate,
    build_pack,
    capture_campaign,
    exclusive_output_lock,
    exclusive_output_locks,
    project_ledger,
    render_generic_pack,
    sha256_file,
    verify_pack,
    write_deterministic_zip,
)


def object_record(object_id: str, kind: str, visibility: str, **extra):
    value = {
        "id": object_id,
        "kind": kind,
        "status": "active_canon",
        "visibility": visibility,
        "authority": "gm_approved",
        "provenance": ["GM notebook"],
        "confidence": "high",
        "tenure": "campaign",
        "title": extra.pop("title", object_id.replace("-", " ").title()),
        "content": extra.pop("content", f"Content for {object_id}."),
        "links": extra.pop("links", []),
        "asset_ids": extra.pop("asset_ids", []),
        "export_eligibility": extra.pop("export_eligibility", "eligible"),
    }
    value.update(extra)
    return value


class ExportPackTests(unittest.TestCase):
    def make_campaign(self, root: Path) -> Path:
        campaign = root / "campaign"
        (campaign / "media").mkdir(parents=True)
        (campaign / "media" / "map.png").write_bytes(b"safe map bytes")
        uvtt = {
            "format": 0.2,
            "resolution": {"map_size": {"x": 10, "y": 8}, "pixels_per_grid": 100},
            "line_of_sight": [],
            "portals": [],
            "lights": [],
        }
        (campaign / "media" / "room.uvtt").write_text(json.dumps(uvtt), encoding="utf-8")
        ledger = {
            "format": "cd-ludis-campaign-ledger/v2",
            "campaign": {"id": "camp-test", "title": "The Kindly Cellar", "system": "system-neutral"},
            "table_contract": {"player_preferences": [], "lines": [], "veils": [], "other_boundaries": []},
            "objects": [
                object_record("secret-dragon", "npc", "gm_only", content="THE DRAGON IS THE MAYOR."),
                object_record("safe-map", "scene", "player_safe", asset_ids=["map-safe"], data={"grid": {"type": "square", "size": 100}}),
                object_record("rumors", "table", "player_safe", data={"entries": [{"text": "The well sings.", "weight": 2}]}),
                object_record("cellar", "scene", "gm_only", asset_ids=["uvtt-room"]),
            ],
            "assets": [
                {"id": "map-safe", "path": "media/map.png", "kind": "map", "visibility": "player_safe", "rights": {"status": "owned"}, "provenance": ["generated fixture"], "alt_text": "A cellar plan."},
                {"id": "uvtt-room", "path": "media/room.uvtt", "kind": "uvtt", "visibility": "gm_only", "rights": {"status": "owned"}, "provenance": ["generated fixture"]},
            ],
            "sessions": [],
            "approvals": [],
            "publication": {"status": "private_draft"},
            "next_prep": [],
            "extensions": {},
        }
        (campaign / "campaign-ledger.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        return campaign

    def test_gm_pack_is_byte_deterministic_and_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            first = build_pack(campaign, root / "one.zip", "gm")
            second = build_pack(campaign, root / "two.zip", "gm")
            self.assertEqual(first.artifact_sha256, second.artifact_sha256)
            report = verify_pack(first.artifact)
            self.assertEqual(report["audience"], "gm")
            with zipfile.ZipFile(first.artifact) as archive:
                self.assertIn("data/scenes.json", archive.namelist())
                self.assertIn("data/tables.csv", archive.namelist())
                self.assertIn("reports/loss-report.json", archive.namelist())

    def test_player_candidate_excludes_gm_content_and_finalizes_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            result = build_pack(campaign, root / "player.candidate.zip", "player")
            self.assertFalse(result.finalized)
            preview_text = result.preview.read_text(encoding="utf-8")
            self.assertIn("data:image/", preview_text)
            self.assertIn("one required review surface, not the whole candidate", preview_text)
            self.assertIn("inspect or listen to every member not rendered here", preview_text)
            candidate_bytes = result.artifact.read_bytes()
            with zipfile.ZipFile(result.artifact) as archive:
                combined = b"\n".join(archive.read(name) for name in archive.namelist())
                self.assertNotIn(b"THE DRAGON IS THE MAYOR", combined)
                self.assertNotIn(b"secret-dragon", combined)
                self.assertNotIn(b"GM notebook", combined)
                self.assertNotIn(b"media/map.png", combined)
            final, receipt = approve_candidate(result.artifact, "table GM")
            self.assertEqual(final.read_bytes(), candidate_bytes)
            approval = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(approval["assertion_type"], "unauthenticated_local_operator_attestation")
            self.assertEqual(approval["artifact_sha256"], sha256_file(result.artifact))

    def test_changed_candidate_cannot_use_old_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            result = build_pack(campaign, root / "player.candidate.zip", "player")
            result.artifact.write_bytes(result.artifact.read_bytes() + b"changed")
            with self.assertRaisesRegex(ExportError, "changed after audit"):
                approve_candidate(result.artifact, "table GM")

    def test_approval_fails_if_preview_or_audit_changes_during_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            result = build_pack(campaign, root / "player.candidate.zip", "player")
            audit = Path(str(result.artifact) + ".audit.json")
            original_verify = exportlib.verify_pack

            def mutate_evidence_during_verify(path):
                result.preview.write_text(result.preview.read_text(encoding="utf-8") + "changed", encoding="utf-8")
                audit.write_text(audit.read_text(encoding="utf-8") + " ", encoding="utf-8")
                return original_verify(path)

            with patch.object(exportlib, "verify_pack", side_effect=mutate_evidence_during_verify):
                with self.assertRaisesRegex(ExportError, "changed before approval completed"):
                    approve_candidate(result.artifact, "table GM")
            self.assertFalse((root / "player.zip").exists())
            self.assertFalse((root / "player.zip.approval.json").exists())
    def test_player_link_to_gm_object_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            ledger_path = campaign / "campaign-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["objects"][1]["links"] = ["secret-dragon"]
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "spoiler link|GM-only link"):
                build_pack(campaign, root / "player.candidate.zip", "player")

    def test_player_reference_to_gm_asset_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            ledger_path = campaign / "campaign-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["objects"][1]["asset_ids"].append("uvtt-room")
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "spoiler asset link|GM-only asset"):
                build_pack(campaign, root / "player.candidate.zip", "player")

    def test_asset_path_escape_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            (root / "outside.txt").write_text("secret", encoding="utf-8")
            ledger_path = campaign / "campaign-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["assets"][0]["path"] = "../outside.txt"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "must stay relative|unsafe asset path"):
                build_pack(campaign, root / "gm.zip", "gm")

    def test_invalid_uvtt_is_blocked_not_repaired_or_inferred(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            (campaign / "media" / "room.uvtt").write_text('{"format":0.2}', encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "UVTT asset.*missing"):
                build_pack(campaign, root / "gm.zip", "gm")

    def test_selected_subset_must_include_linked_objects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            ledger_path = campaign / "campaign-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["objects"][1]["links"] = ["rumors"]
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "omits linked object"):
                build_pack(campaign, root / "gm.zip", "gm", ["safe-map"])

    def test_player_output_requires_candidate_suffix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            with self.assertRaisesRegex(ExportError, "must end in .candidate.zip"):
                build_pack(campaign, root / "player.zip", "player")

    def test_lock_setup_and_partial_multi_reservation_failures_clean_up(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "setup.zip"
            lock = root / ".setup.zip.ludis-lock"
            with patch("exportlib.os.write", side_effect=OSError("injected write failure")):
                with self.assertRaisesRegex(OSError, "injected write failure"):
                    with exclusive_output_lock(output):
                        self.fail("lock body must not run after setup failure")
            self.assertFalse(lock.exists())
            with exclusive_output_lock(output):
                pass
            self.assertFalse(lock.exists())

            first = root / "first.zip"
            second = root / "second.zip"
            first_lock = root / ".first.zip.ludis-lock"
            with exclusive_output_lock(second):
                with self.assertRaisesRegex(ExportError, "another Ludis operation"):
                    with exclusive_output_locks((first, second)):
                        self.fail("partial multi-reservation must not succeed")
                self.assertFalse(first_lock.exists())
            self.assertEqual(list(root.glob("*.ludis-lock")), [])

    def test_lock_cleanup_preserves_original_failure_and_foreign_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "guarded.zip"
            lock = root / ".guarded.zip.ludis-lock"

            foreign_identity = SimpleNamespace(st_dev=-1, st_ino=-1)
            with patch("exportlib.os.fstat", return_value=foreign_identity):
                with self.assertRaisesRegex(ExportError, "identity changed"):
                    with exclusive_output_lock(output):
                        self.fail("identity mismatch must fail during setup")
            self.assertTrue(lock.exists(), "a path not proven to be descriptor-owned must be preserved")
            lock.unlink()

            original_unlink = Path.unlink

            def failed_lock_unlink(path, *args, **kwargs):
                if path.resolve() == lock.resolve():
                    raise OSError("injected cleanup failure")
                return original_unlink(path, *args, **kwargs)

            with patch.object(Path, "unlink", failed_lock_unlink):
                with self.assertRaisesRegex(RuntimeError, "original body failure") as raised:
                    with exclusive_output_lock(output):
                        raise RuntimeError("original body failure")
            notes = getattr(raised.exception, "__notes__", [])
            self.assertTrue(any("injected cleanup failure" in note for note in notes))
            self.assertTrue(lock.exists())
            lock.unlink()

            with patch.object(Path, "unlink", failed_lock_unlink):
                with self.assertRaisesRegex(ExportError, "operation may have completed"):
                    with exclusive_output_lock(output):
                        pass
            self.assertTrue(lock.exists())
            lock.unlink()

    def test_competing_generic_builds_reserve_artifact_and_sidecar_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            output = root / "gm.zip"
            overlapping_output = Path(str(output) + ".preview.html")
            started = threading.Event()
            release = threading.Event()
            call_guard = threading.Lock()
            calls = 0
            original = exportlib._build_pack_reserved

            def delayed_first(*args, **kwargs):
                nonlocal calls
                with call_guard:
                    calls += 1
                    call_number = calls
                if call_number == 1:
                    started.set()
                    if not release.wait(10):
                        raise AssertionError("timed out waiting to release first generic build")
                return original(*args, **kwargs)

            with patch.object(exportlib, "_build_pack_reserved", side_effect=delayed_first):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    winner = pool.submit(build_pack, campaign, output, "gm")
                    self.assertTrue(started.wait(10), "first generic build did not acquire its reservation")
                    try:
                        with self.assertRaisesRegex(ExportError, "another Ludis operation"):
                            build_pack(campaign, overlapping_output, "gm")
                    finally:
                        release.set()
                    result = winner.result(timeout=20)

            self.assertEqual(result.artifact, output.resolve())
            verify_pack(output)
            self.assertTrue(result.preview.is_file())
            self.assertTrue(result.preview.read_bytes().lower().startswith(b"<!doctype html>"))
            self.assertFalse(Path(str(overlapping_output) + ".audit.json").exists())
            self.assertFalse(Path(str(overlapping_output) + ".preview.html").exists())
            self.assertEqual(list(root.glob("*.ludis-lock")), [])

    def test_competing_generic_approvals_reserve_final_and_receipt_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            candidate = build_pack(campaign, root / "player.candidate.zip", "player").artifact
            final = root / "approved.zip"
            receipt = root / "approved.zip.approval.json"
            overlapping_final = receipt
            overlapping_receipt = root / "approved.zip.approval.json.approval.json"
            started = threading.Event()
            release = threading.Event()
            call_guard = threading.Lock()
            calls = 0
            original = exportlib._approve_candidate_reserved

            def delayed_first(*args, **kwargs):
                nonlocal calls
                with call_guard:
                    calls += 1
                    call_number = calls
                if call_number == 1:
                    started.set()
                    if not release.wait(10):
                        raise AssertionError("timed out waiting to release first generic approval")
                return original(*args, **kwargs)

            with patch.object(exportlib, "_approve_candidate_reserved", side_effect=delayed_first):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    winner = pool.submit(approve_candidate, candidate, "First GM", final)
                    self.assertTrue(started.wait(10), "first generic approval did not acquire its reservation")
                    try:
                        with self.assertRaisesRegex(ExportError, "another Ludis operation"):
                            approve_candidate(candidate, "Second GM", overlapping_final)
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

    def test_build_refuses_to_rewrite_immutable_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            output = root / "gm.zip"
            first = build_pack(campaign, output, "gm")
            first_bytes = output.read_bytes()
            with self.assertRaisesRegex(ExportError, "immutable export path already exists"):
                build_pack(campaign, output, "gm")
            self.assertEqual(output.read_bytes(), first_bytes)
            self.assertEqual(first.artifact_sha256, sha256_file(output))

    def test_uncooperative_build_occupant_is_preserved_at_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            output = root / "gm.zip"
            original_publish = exportlib.publish_file_if_absent

            def occupy_artifact(staged, destination, label):
                if label == "artifact":
                    destination.write_bytes(b"foreign build occupant")
                return original_publish(staged, destination, label)

            with patch.object(exportlib, "publish_file_if_absent", side_effect=occupy_artifact):
                with self.assertRaisesRegex(ExportError, "immutable artifact path became occupied"):
                    build_pack(campaign, output, "gm")
            self.assertEqual(output.read_bytes(), b"foreign build occupant")

    def test_uncooperative_approval_occupant_is_preserved_at_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            candidate = build_pack(campaign, root / "player.candidate.zip", "player").artifact
            final = root / "approved.zip"
            original_publish = exportlib.publish_file_if_absent

            def occupy_final(staged, destination, label):
                if label == "approved artifact":
                    destination.write_bytes(b"foreign approval occupant")
                return original_publish(staged, destination, label)

            with patch.object(exportlib, "publish_file_if_absent", side_effect=occupy_final):
                with self.assertRaisesRegex(ExportError, "immutable approved artifact path became occupied"):
                    approve_candidate(candidate, "Example GM", final)
            self.assertEqual(final.read_bytes(), b"foreign approval occupant")
            self.assertTrue((root / "approved.zip.approval.json").is_file())

    def test_approval_is_idempotent_only_for_same_assertion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            result = build_pack(campaign, root / "player.candidate.zip", "player")
            first_final, first_receipt = approve_candidate(result.artifact, "Example GM")
            receipt_bytes = first_receipt.read_bytes()
            second_final, second_receipt = approve_candidate(result.artifact, "Example GM")
            self.assertEqual(first_final, second_final)
            self.assertEqual(first_receipt, second_receipt)
            self.assertEqual(second_receipt.read_bytes(), receipt_bytes)
            with self.assertRaisesRegex(ExportError, "different local operator"):
                approve_candidate(result.artifact, "Someone Else")
            self.assertEqual(first_receipt.read_bytes(), receipt_bytes)

    def test_generic_approval_idempotence_rejects_receipt_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            result = build_pack(campaign, root / "player.candidate.zip", "player")
            _, receipt = approve_candidate(result.artifact, "Example GM")
            original_receipt = receipt.read_bytes()
            baseline = json.loads(original_receipt)
            mutations = {
                "state": "draft",
                "assertion_type": "authenticated_owner_assertion",
                "limitations": "tampered",
                "approved_at": "not-a-timestamp",
                "artifact": "other.zip",
                "candidate_sha256": "0" * 64,
                "preview_sha256": "1" * 64,
                "audit_sha256": "2" * 64,
            }
            for field, value in mutations.items():
                with self.subTest(field=field):
                    changed = dict(baseline)
                    changed[field] = value
                    receipt.write_text(json.dumps(changed), encoding="utf-8")
                    with self.assertRaisesRegex(ExportError, "different evidence"):
                        approve_candidate(result.artifact, "Example GM")
            embedded = json.loads(original_receipt)
            embedded["ledger_approval_record"]["candidate_sha256"] = "3" * 64
            receipt.write_text(json.dumps(embedded), encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "different evidence"):
                approve_candidate(result.artifact, "Example GM")
            missing = dict(baseline)
            missing.pop("state")
            receipt.write_text(json.dumps(missing), encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "different evidence"):
                approve_candidate(result.artifact, "Example GM")
            extra = dict(baseline)
            extra["unbound"] = True
            receipt.write_text(json.dumps(extra), encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "different evidence"):
                approve_candidate(result.artifact, "Example GM")
            receipt.write_text(json.dumps(baseline), encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "different evidence"):
                approve_candidate(result.artifact, "Example GM")
            receipt.write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "receipt is unreadable"):
                approve_candidate(result.artifact, "Example GM")

    def test_declared_asset_digest_mismatch_blocks_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            ledger_path = campaign / "campaign-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["assets"][0]["sha256"] = "0" * 64
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaisesRegex(ExportError, "digest does not match"):
                build_pack(campaign, root / "gm.zip", "gm")

    def test_zip_writer_rejects_noncanonical_unsafe_and_colliding_names(self):
        invalid_names = ["./module.json", "scripts//alias.mjs", "C:/module.json", "../outside/"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, name in enumerate(invalid_names):
                with self.subTest(name=name):
                    with self.assertRaises(ExportError):
                        write_deterministic_zip(root / f"invalid-{index}.zip", {name: b"unsafe"})
            with self.assertRaisesRegex(ExportError, "collision"):
                write_deterministic_zip(root / "collision.zip", {"README.md": b"one", "readme.MD": b"two"})

    def test_pack_verifier_rejects_noncanonical_unsafe_and_colliding_names(self):
        injected_names = ["./module.json", "scripts//alias.mjs", "C:/module.json", "../outside/", "readme.MD"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            for index, name in enumerate(injected_names):
                with self.subTest(name=name):
                    output = root / f"gm-{index}.zip"
                    build_pack(campaign, output, "gm")
                    with zipfile.ZipFile(output, "a") as archive:
                        archive.writestr(name, b"unsafe")
                    with self.assertRaises(ExportError):
                        verify_pack(output)

    def test_gm_asset_paths_stay_unique_when_long_ids_share_a_slug_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            first_source = campaign / "media" / "first" / "shared.png"
            second_source = campaign / "media" / "second" / "shared.png"
            first_source.parent.mkdir(parents=True)
            second_source.parent.mkdir(parents=True)
            first_source.write_bytes(b"first long-id asset")
            second_source.write_bytes(b"second long-id asset")
            common = "asset-" + ("x" * 90)
            first_id = common + "-one"
            second_id = common + "-two"
            ledger_path = campaign / "campaign-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["assets"].extend(
                [
                    {"id": first_id, "path": "media/first/shared.png", "kind": "map", "visibility": "gm_only", "rights": {"status": "owned"}, "provenance": ["generated fixture"]},
                    {"id": second_id, "path": "media/second/shared.png", "kind": "map", "visibility": "gm_only", "rights": {"status": "owned"}, "provenance": ["generated fixture"]},
                ]
            )
            ledger["objects"][0]["asset_ids"].extend([first_id, second_id])
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

            result = build_pack(campaign, root / "gm.zip", "gm")
            with zipfile.ZipFile(result.artifact) as archive:
                asset_index = json.loads(archive.read("data/assets.json"))
                paths = [str(item["pack_path"]) for item in asset_index]
                self.assertEqual(len(paths), len({path.casefold() for path in paths}))
                by_id = {str(item["id"]): str(item["pack_path"]) for item in asset_index}
                self.assertNotEqual(by_id[first_id].casefold(), by_id[second_id].casefold())
                self.assertEqual(archive.read(by_id[first_id]), b"first long-id asset")
                self.assertEqual(archive.read(by_id[second_id]), b"second long-id asset")

    def test_source_mutation_during_capture_fails_closed(self):

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            moving = campaign / "media" / "map.png"
            original_read = Path.read_bytes
            changed = False

            def racing_read(path):
                nonlocal changed
                data = original_read(path)
                if path.resolve() == moving.resolve() and not changed:
                    changed = True
                    path.write_bytes(data + b" changed")
                return data

            with patch.object(Path, "read_bytes", racing_read):
                with self.assertRaisesRegex(ExportError, "changed while it was being captured"):
                    capture_campaign(campaign, root / "capture")

    def test_render_uses_frozen_bytes_after_source_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = self.make_campaign(root)
            captured = capture_campaign(campaign, root / "capture")
            projection = project_ledger(captured.ledger, "player")
            (campaign / "media" / "map.png").write_bytes(b"later secret mutation")
            files = render_generic_pack(captured, projection, "player")
            asset_bytes = [data for name, data in files.items() if name.startswith("assets/")]
            self.assertEqual(asset_bytes, [b"safe map bytes"])


if __name__ == "__main__":
    unittest.main()
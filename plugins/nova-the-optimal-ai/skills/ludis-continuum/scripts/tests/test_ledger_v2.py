from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ledger"
sys.path.insert(0, str(SCRIPTS))

import ledgerlib as ledger_module  # noqa: E402
from ledgerlib import (  # noqa: E402
    LEDGER_FORMAT_V2,
    LedgerBusyError,
    LedgerLockCleanupError,
    LedgerWriteConflictError,
    campaign_id_from_seed,
    detect_format,
    exclusive_ledger_lock,
    ledger_lock_path,
    load,
    save,
    validate,
)
from migrate_ledger import migrate_legacy, write_migration  # noqa: E402
import promote_object as promotion_module  # noqa: E402


class LedgerV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.legacy_path = FIXTURES / "legacy-basic.json"
        self.v2_path = FIXTURES / "v2-valid.json"
        self.legacy = load(self.legacy_path)
        self.v2 = load(self.v2_path)

    def test_schema_identity_is_v2_and_keeps_legacy_branch(self) -> None:
        schema = json.loads((ROOT / "schemas" / "campaign-ledger.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], LEDGER_FORMAT_V2)
        self.assertEqual(len(schema["oneOf"]), 2)

    def test_recognizes_and_validates_both_generations(self) -> None:
        self.assertEqual(detect_format(self.legacy), "legacy_v0_1")
        self.assertEqual(detect_format(self.v2), LEDGER_FORMAT_V2)
        self.assertEqual(validate(self.legacy), [])
        self.assertEqual(validate(self.v2), [])

    def test_template_leaves_campaign_id_for_explicit_initialization(self) -> None:
        template = load(ROOT / "assets" / "campaign.template" / "campaign-ledger.json")
        self.assertEqual(detect_format(template), LEDGER_FORMAT_V2)
        self.assertTrue(any("campaign.id required" in error for error in validate(template)))

    def test_seed_derived_id_is_stable_and_owner_controlled(self) -> None:
        first = campaign_id_from_seed("Bell Below Bracken / home table")
        self.assertEqual(first, campaign_id_from_seed("Bell Below Bracken / home table"))
        self.assertNotEqual(first, campaign_id_from_seed("another table"))
        self.assertTrue(first.startswith("campaign-"))
        with self.assertRaises(ValueError):
            campaign_id_from_seed("   ")

    def test_migration_requires_an_explicit_id_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "--campaign-id or --campaign-seed"):
            migrate_legacy(self.legacy)

    def test_migration_with_seed_produces_valid_v2(self) -> None:
        migrated, report = migrate_legacy(self.legacy, campaign_seed="bell-home-table")
        self.assertEqual(validate(migrated), [])
        self.assertEqual(migrated["format"], LEDGER_FORMAT_V2)
        self.assertEqual(migrated["campaign"]["id"], campaign_id_from_seed("bell-home-table"))
        self.assertEqual(report.current_approvals_created, 0)

    def test_unknown_values_are_preserved_under_legacy_extensions(self) -> None:
        migrated, report = migrate_legacy(self.legacy, campaign_id="campaign-bracken")
        self.assertEqual(
            migrated["campaign"]["extensions"]["legacy_v0_1"]["weather_oracle"],
            "rain when the bell rings",
        )
        self.assertTrue(migrated["table_contract"]["extensions"]["legacy_v0_1"]["open_door"])
        self.assertEqual(migrated["sessions"][0]["extensions"]["legacy_v0_1"]["weather"], "rain")
        self.assertEqual(migrated["extensions"]["legacy_v0_1"]["unmapped"]["house_oracle"], {"die": "d6"})
        self.assertIn("ledger.house_oracle", report.unknown_fields)

    def test_legacy_boolean_is_evidence_not_current_approval(self) -> None:
        migrated, report = migrate_legacy(self.legacy, campaign_id="campaign-bracken")
        town = next(item for item in migrated["objects"] if item["id"] == "canon-town")
        self.assertTrue(town["extensions"]["legacy_v0_1"]["player_export_approved"])
        self.assertEqual(migrated["approvals"], [])
        self.assertEqual(report.legacy_player_approval_ids, ("canon-town",))
        self.assertEqual(
            migrated["extensions"]["legacy_v0_1"]["approvals"],
            self.legacy["approvals"],
        )

    def test_unknown_kind_retains_canon_but_is_quarantined_from_export(self) -> None:
        migrated, report = migrate_legacy(self.legacy, campaign_id="campaign-bracken")
        oddity = next(item for item in migrated["objects"] if item["id"] == "oddity-one")
        self.assertEqual(oddity["status"], "active_canon")
        self.assertEqual(oddity["authority"], "gm_approved")
        self.assertEqual(oddity["export_eligibility"], "quarantined_unmapped")
        self.assertEqual(report.quarantined_object_ids, ("oddity-one",))
        self.assertEqual(oddity["extensions"]["legacy_v0_1"]["unparsed_oracle"]["faces"], ["moon", "key"])

    def test_v2_rejects_unknown_top_level_field(self) -> None:
        value = copy.deepcopy(self.v2)
        value["mystery"] = 4
        self.assertTrue(any("ledger unknown field: mystery" in error for error in validate(value)))

    def test_v2_requires_namespaced_extensions(self) -> None:
        value = copy.deepcopy(self.v2)
        value["extensions"] = {"weather": {"rain": True}}
        self.assertTrue(any("must be namespaced" in error for error in validate(value)))
        value["extensions"] = {"org.example.weather": {"rain": True}}
        self.assertEqual(validate(value), [])

    def test_unknown_v2_kind_must_remain_quarantined(self) -> None:
        value = copy.deepcopy(self.v2)
        value["objects"][0]["kind"] = "dream_residue"
        self.assertTrue(any("unknown kind must be quarantined_unmapped" in error for error in validate(value)))
        value["objects"][0]["export_eligibility"] = "quarantined_unmapped"
        self.assertEqual(validate(value), [])

    def test_player_safe_graph_cannot_reach_gm_only_record_transitively(self) -> None:
        value = copy.deepcopy(self.v2)
        bridge = copy.deepcopy(value["objects"][0])
        bridge.update({"id": "public-bridge", "title": "A public bridge", "asset_ids": [], "links": ["secret-debt"]})
        value["objects"].append(bridge)
        value["objects"][0]["links"] = ["public-bridge"]
        errors = validate(value)
        self.assertTrue(any("canon-town -> public-bridge -> secret-debt" in error for error in errors))

    def test_player_safe_record_cannot_reference_gm_only_asset(self) -> None:
        value = copy.deepcopy(self.v2)
        value["assets"][0]["visibility"] = "gm_only"
        self.assertTrue(any("spoiler asset link" in error for error in validate(value)))

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "legacy.json"
            source.write_bytes(self.legacy_path.read_bytes())
            before = sorted(path.name for path in root.iterdir())
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "migrate_ledger.py"), str(source), "--campaign-id", "campaign-bracken"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("DRY RUN: no files written", result.stdout)
            self.assertEqual(before, sorted(path.name for path in root.iterdir()))

    def test_write_keeps_source_and_exact_byte_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "legacy.json"
            output = root / "campaign-v2.json"
            original = self.legacy_path.read_bytes()
            source.write_bytes(original)
            report, source_copy = write_migration(
                source,
                output,
                campaign_id="campaign-bracken",
            )
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(source_copy.read_bytes(), original)
            self.assertEqual(validate(load(output)), [])
            self.assertEqual(report.campaign_id, "campaign-bracken")

    def test_in_place_migration_is_refused_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "legacy.json"
            original = self.legacy_path.read_bytes()
            source.write_bytes(original)
            with self.assertRaisesRegex(ValueError, "in-place migration is forbidden"):
                write_migration(source, source, campaign_id="campaign-bracken")
            self.assertEqual(source.read_bytes(), original)

    def test_write_refuses_to_overwrite_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "legacy.json"
            output = root / "campaign-v2.json"
            source.write_bytes(self.legacy_path.read_bytes())
            output.write_text("do not replace", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_migration(source, output, campaign_id="campaign-bracken")
            self.assertEqual(output.read_text(encoding="utf-8"), "do not replace")

    def test_existing_campaign_id_cannot_be_silently_changed(self) -> None:
        value = copy.deepcopy(self.legacy)
        value["campaign"]["id"] = "campaign-existing"
        migrated, _ = migrate_legacy(value)
        self.assertEqual(migrated["campaign"]["id"], "campaign-existing")
        with self.assertRaisesRegex(ValueError, "does not match"):
            migrate_legacy(value, campaign_id="campaign-other")

    def test_legacy_duplicate_id_behavior_is_preserved(self) -> None:
        value = copy.deepcopy(self.legacy)
        value["objects"].append(copy.deepcopy(value["objects"][0]))
        self.assertTrue(any("duplicate id" in error for error in validate(value)))


    def test_atomic_save_write_failure_preserves_prior_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "campaign-ledger.json"
            original = self.v2_path.read_bytes()
            path.write_bytes(original)
            changed = copy.deepcopy(self.v2)
            changed["updated"] = "2026-08-13T01:00:00Z"
            with patch("ledgerlib._write_staged_bytes", side_effect=OSError("injected write failure")):
                with self.assertRaisesRegex(OSError, "injected write failure"):
                    save(path, changed)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.ludis-stage")), [])

    def test_atomic_save_replace_failure_preserves_prior_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "campaign-ledger.json"
            original = self.v2_path.read_bytes()
            path.write_bytes(original)
            changed = copy.deepcopy(self.v2)
            changed["updated"] = "2026-08-13T02:00:00Z"
            with patch("ledgerlib.os.replace", side_effect=OSError("injected replace failure")):
                with self.assertRaisesRegex(OSError, "injected replace failure"):
                    save(path, changed)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.ludis-stage")), [])

    @unittest.skipUnless(os.name == "nt", "Windows ReplaceFileW boundary test")
    def test_windows_final_replace_window_blocks_or_preserves_direct_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "campaign-ledger.json"
            path.write_bytes(self.v2_path.read_bytes())
            _, source_digest = ledger_module.load_with_digest(path)
            changed = copy.deepcopy(self.v2)
            changed["updated"] = "2026-08-13T02:30:00Z"
            external = "external editor reached final window"
            real_replace = ledger_module._windows_replace_file
            attempted = False
            direct_errors: list[OSError] = []

            def inject_direct_write(destination, replacement, backup):
                nonlocal attempted
                if not attempted:
                    attempted = True
                    try:
                        destination.write_text(external, encoding="utf-8")
                    except OSError as exc:
                        direct_errors.append(exc)
                return real_replace(destination, replacement, backup)

            save_error = None
            with patch("ledgerlib._windows_replace_file", side_effect=inject_direct_write):
                try:
                    save(path, changed, expected_sha256=source_digest)
                except LedgerWriteConflictError as exc:
                    save_error = exc

            self.assertTrue(attempted)
            if direct_errors:
                self.assertIsNone(save_error)
                self.assertEqual(load(path)["updated"], "2026-08-13T02:30:00Z")
            else:
                self.assertIsNotNone(save_error)
                self.assertEqual(path.read_text(encoding="utf-8"), external)
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.ludis-stage")), [])
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.ludis-backup")), [])
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.ludis-rejected")), [])
    def test_posix_displacement_rejects_and_restores_final_window_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "campaign-ledger.json"
            original = self.v2_path.read_bytes()
            path.write_bytes(original)
            expected = ledger_module._sha256(original)
            proposed_value = copy.deepcopy(self.v2)
            proposed_value["updated"] = "2026-08-13T02:31:00Z"
            proposed = (json.dumps(proposed_value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            staged = root / "staged.json"
            staged.write_bytes(proposed)
            external_value = copy.deepcopy(self.v2)
            external_value["updated"] = "external-final-window-change"
            external = (json.dumps(external_value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            real_rename = os.rename
            injected = False

            def inject_before_displacement(source, destination):
                nonlocal injected
                if Path(source) == path and not injected:
                    injected = True
                    path.write_bytes(external)
                return real_rename(source, destination)

            with patch("ledgerlib.os.rename", side_effect=inject_before_displacement):
                with self.assertRaisesRegex(LedgerWriteConflictError, "atomic displacement boundary"):
                    ledger_module._replace_expected_posix(staged, path, expected, proposed)
            self.assertTrue(injected)
            self.assertEqual(path.read_bytes(), external)
            self.assertEqual(list(root.glob(f".{path.name}.*.ludis-displaced")), [])
            self.assertEqual(list(root.glob(f".{path.name}.*.ludis-rejected")), [])

    def test_posix_publication_preserves_late_occupant_and_displaced_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "campaign-ledger.json"
            original = self.v2_path.read_bytes()
            path.write_bytes(original)
            expected = ledger_module._sha256(original)
            proposed_value = copy.deepcopy(self.v2)
            proposed_value["updated"] = "2026-08-13T02:32:00Z"
            proposed = (json.dumps(proposed_value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            staged = root / "staged.json"
            staged.write_bytes(proposed)
            external = b"late external ledger occupant"
            real_link = os.link
            injected = False

            def inject_before_publish(source, destination, *args, **kwargs):
                nonlocal injected
                if Path(source) == staged and Path(destination) == path and not injected:
                    injected = True
                    path.write_bytes(external)
                return real_link(source, destination, *args, **kwargs)

            with patch("ledgerlib.os.link", side_effect=inject_before_publish):
                with self.assertRaisesRegex(LedgerWriteConflictError, "publication boundary"):
                    ledger_module._replace_expected_posix(staged, path, expected, proposed)
            self.assertTrue(injected)
            self.assertEqual(path.read_bytes(), external)
            displaced = list(root.glob(f".{path.name}.*.ludis-displaced"))
            self.assertEqual(len(displaced), 1)
            self.assertEqual(displaced[0].read_bytes(), original)
            self.assertEqual(list(root.glob(f".{path.name}.*.ludis-rejected")), [])

    def test_posix_displacement_commit_installs_exact_proposed_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "campaign-ledger.json"
            original = self.v2_path.read_bytes()
            path.write_bytes(original)
            proposed_value = copy.deepcopy(self.v2)
            proposed_value["updated"] = "2026-08-13T02:33:00Z"
            proposed = (json.dumps(proposed_value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            staged = root / "staged.json"
            staged.write_bytes(proposed)
            ledger_module._replace_expected_posix(staged, path, ledger_module._sha256(original), proposed)
            self.assertEqual(path.read_bytes(), proposed)
            self.assertEqual(list(root.glob(f".{path.name}.*.ludis-displaced")), [])
            self.assertEqual(list(root.glob(f".{path.name}.*.ludis-rejected")), [])

    def test_replacement_lock_is_preserved_and_completion_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "campaign-ledger.json"
            path.write_bytes(self.v2_path.read_bytes())
            lock = ledger_lock_path(path)
            real_lstat = Path.lstat
            lock_stats = 0

            def changing_identity(candidate):
                nonlocal lock_stats
                state = real_lstat(candidate)
                if candidate == lock:
                    lock_stats += 1
                    if lock_stats >= 2:
                        return SimpleNamespace(st_dev=-1, st_ino=-1)
                return state

            with patch.object(Path, "lstat", autospec=True, side_effect=changing_identity):
                with self.assertRaisesRegex(LedgerLockCleanupError, "may have completed"):
                    with exclusive_ledger_lock(path):
                        pass
            self.assertTrue(lock.is_file())
            lock.unlink()
    def test_lock_cleanup_failure_does_not_mask_operation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "campaign-ledger.json"
            path.write_bytes(self.v2_path.read_bytes())
            with patch("ledgerlib.Path.unlink", side_effect=OSError("injected cleanup failure")):
                with self.assertRaisesRegex(RuntimeError, "original operation failure"):
                    with exclusive_ledger_lock(path):
                        raise RuntimeError("original operation failure")
            lock = ledger_lock_path(path)
            self.assertTrue(lock.is_file())
            lock.unlink()

    def test_competing_promotions_fail_explicitly_and_retry_without_lost_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "campaign-ledger.json"
            value = copy.deepcopy(self.v2)
            for obj in value["objects"]:
                obj["status"] = "proposed"
                obj["authority"] = "user_proposed"
            path.write_text(json.dumps(value), encoding="utf-8")

            entered = threading.Event()
            release = threading.Event()
            first_outcome: list[object] = []
            real_save = promotion_module.save

            def gated_save(*args, **kwargs):
                entered.set()
                if not release.wait(5):
                    raise TimeoutError("test did not release first writer")
                return real_save(*args, **kwargs)

            def first_writer() -> None:
                try:
                    first_outcome.append(
                        promotion_module.promote_object(
                            path,
                            "canon-town",
                            asserted_by="GM One",
                            at="2026-08-13T03:00:00Z",
                        )
                    )
                except BaseException as exc:
                    first_outcome.append(exc)

            with patch("promote_object.save", side_effect=gated_save):
                thread = threading.Thread(target=first_writer)
                thread.start()
                self.assertTrue(entered.wait(5), "first writer did not reach the gated save")
                with self.assertRaises(LedgerBusyError):
                    promotion_module.promote_object(
                        path,
                        "secret-debt",
                        asserted_by="GM Two",
                        at="2026-08-13T03:00:01Z",
                    )
                release.set()
                thread.join(5)

            self.assertFalse(thread.is_alive())
            self.assertEqual(len(first_outcome), 1)
            if isinstance(first_outcome[0], BaseException):
                raise first_outcome[0]
            after_first = load(path)
            self.assertEqual(next(obj for obj in after_first["objects"] if obj["id"] == "canon-town")["status"], "active_canon")
            self.assertEqual(next(obj for obj in after_first["objects"] if obj["id"] == "secret-debt")["status"], "proposed")

            promotion_module.promote_object(
                path,
                "secret-debt",
                asserted_by="GM Two",
                at="2026-08-13T03:00:02Z",
            )
            final = load(path)
            self.assertEqual({obj["id"] for obj in final["objects"] if obj["status"] == "active_canon"}, {"canon-town", "secret-debt"})
            self.assertEqual([item["object_id"] for item in final["approvals"]], ["canon-town", "secret-debt"])

    def test_promotion_rejects_reverse_direction_active_contradiction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "campaign-ledger.json"
            value = copy.deepcopy(self.v2)
            active = next(obj for obj in value["objects"] if obj["id"] == "canon-town")
            proposed = next(obj for obj in value["objects"] if obj["id"] == "secret-debt")
            active["claims"] = []
            active["contradicts"] = ["The ferrymen sank the bell"]
            proposed["claims"] = ["The ferrymen sank the bell"]
            proposed["contradicts"] = []
            proposed["status"] = "proposed"
            proposed["authority"] = "user_proposed"
            path.write_text(json.dumps(value), encoding="utf-8")

            with self.assertRaisesRegex(promotion_module.PromotionRejected, "unresolved active-canon contradiction"):
                promotion_module.promote_object(
                    path,
                    "secret-debt",
                    asserted_by="GM",
                    at="2026-08-13T03:30:00Z",
                )
            preserved = load(path)
            self.assertEqual(next(obj for obj in preserved["objects"] if obj["id"] == "secret-debt")["status"], "proposed")
            self.assertEqual(preserved["approvals"], [])

    def test_promotion_rejects_ledger_with_existing_active_active_contradiction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "campaign-ledger.json"
            value = copy.deepcopy(self.v2)
            first, second = value["objects"]
            first["claims"] = ["The bell still hangs"]
            first["contradicts"] = []
            second["claims"] = []
            second["contradicts"] = ["The bell still hangs"]
            proposed = copy.deepcopy(second)
            proposed["id"] = "new-proposal"
            proposed["title"] = "New proposal"
            proposed["status"] = "proposed"
            proposed["authority"] = "user_proposed"
            proposed["claims"] = []
            proposed["contradicts"] = []
            value["objects"].append(proposed)
            path.write_text(json.dumps(value), encoding="utf-8")

            with self.assertRaisesRegex(promotion_module.PromotionRejected, "already contains"):
                promotion_module.promote_object(
                    path,
                    "new-proposal",
                    asserted_by="GM",
                    at="2026-08-13T03:31:00Z",
                )
            self.assertEqual(load(path)["approvals"], [])
    def test_uncoordinated_source_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "campaign-ledger.json"
            value = copy.deepcopy(self.v2)
            value["objects"][0]["status"] = "proposed"
            value["objects"][0]["authority"] = "user_proposed"
            value["approvals"] = []
            path.write_text(json.dumps(value), encoding="utf-8")
            real_save = promotion_module.save

            def drift_then_save(ledger_path, proposed, *, expected_sha256=None):
                externally_changed = load(ledger_path)
                externally_changed["updated"] = "external-editor-change"
                real_save(ledger_path, externally_changed)
                return real_save(ledger_path, proposed, expected_sha256=expected_sha256)

            with patch("promote_object.save", side_effect=drift_then_save):
                with self.assertRaisesRegex(LedgerWriteConflictError, "ledger changed"):
                    promotion_module.promote_object(
                        path,
                        "canon-town",
                        asserted_by="GM",
                        at="2026-08-13T04:00:00Z",
                    )
            preserved = load(path)
            self.assertEqual(preserved["updated"], "external-editor-change")
            self.assertEqual(preserved["objects"][0]["status"], "proposed")
            self.assertEqual(preserved["approvals"], [])
            self.assertFalse(ledger_lock_path(path).exists())
if __name__ == "__main__":
    unittest.main()
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import compile_context_v2 as compiler
import continuity_store_v2 as store
import error_neighborhood as fault
import workspace_runtime as runtime

STORE = SCRIPTS / "continuity_store_v2.py"
FAULT = SCRIPTS / "error_neighborhood.py"
VALIDATE = SCRIPTS / "validate_continuity_v2.py"

LEGACY_HASHES = {
    "continuity_store.py": "e9cf9fae9e1fac745a6ac4fb7dd76f061ca16689c9d5076d7fab9bd4c02be02b",
    "compile_context.py": "32e9cdda9b9361544f49ea43833968a8d9fba9d1e04c65edf7637086e8821617",
    "validate_continuity.py": "5ee570df03a4905f9e8379d7fb33ce08936f76045a4f61213a48dabe9330a7fe",
    "tests/test_continuity.py": "c90d010158a70d2af347a9d84db16179dedd1c6a971b21b04c4b4be19d337add",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        item.relative_to(root).as_posix(): sha(item)
        for item in sorted(root.rglob("*")) if item.is_file()
    }


class WorkspaceCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir="E:/")
        self.base = Path(self.temporary.name)
        self.root = self.base / "workspace"
        result = self.cli(STORE, "init", self.root, "--user", "user", "--project", "project", "--agent", "nova")
        self.assertEqual(result["format"], runtime.RECEIPT_FORMAT)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def cli(self, script: Path, *args: object, expected: int = 0) -> dict:
        completed = subprocess.run(
            [sys.executable, str(script), *[str(item) for item in args]],
            text=True, capture_output=True, timeout=30,
        )
        if completed.returncode != expected:
            self.fail(f"{script.name} returned {completed.returncode}, expected {expected}\nstdout={completed.stdout}\nstderr={completed.stderr}")
        stream = completed.stdout if completed.stdout.strip() else completed.stderr
        if not stream.strip():
            return {}
        try:
            return json.loads(stream)
        except json.JSONDecodeError:
            return {"text": stream.strip()}

    @property
    def generation(self) -> int:
        return int(json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))["generation"])

    def episode(self, content: str = "ordinary source", *, key: str = "episode-1", sensitivity: str = "ordinary") -> dict:
        return self.cli(
            STORE, "episode", self.root, "--type", "tool_result", "--content", content,
            "--source-kind", "tool", "--authority", "user-stunspot", "--sensitivity", sensitivity,
            "--idempotency-key", key, "--expected-generation", self.generation,
        )

    def capture(self, source_event: str, *, operation_id: str | None = None, key: str | None = None,
                message: str = "refresh rejected") -> dict:
        args: list[object] = [
            "capture", self.root, "--expected-generation", self.generation,
            "--idempotency-key", key or f"capture-{source_event}",
            "--source-event-id", source_event, "--producer", "codex", "--tool", "web",
            "--provider", "oauth", "--operation-family", "token-refresh",
            "--error-code", "invalid_grant", "--error-class", "OAuthError",
            "--message", message, "--source-pointer", "tool result",
            "--environment", "windows", "--environment-version", "1",
            "--authority", "user-stunspot",
        ]
        if operation_id is not None:
            args += ["--operation-id", operation_id]
        return self.cli(FAULT, *args)


class FrozenCompatibilityTests(unittest.TestCase):
    def test_legacy_normative_files_are_byte_identical(self) -> None:
        for relative, expected in LEGACY_HASHES.items():
            self.assertEqual(sha(SCRIPTS / relative), expected, relative)


class KernelTests(WorkspaceCase):
    def test_init_mutate_validate_and_immutable_predecessor(self) -> None:
        predecessor = self.root / "generations" / "g-00000000000000000000"
        before = inventory(predecessor)
        receipt = self.episode()
        self.assertEqual(receipt["generation_before"], 0)
        self.assertEqual(receipt["generation_after"], 1)
        self.assertEqual(inventory(predecessor), before)
        result = self.cli(VALIDATE, self.root)
        self.assertIn("VALID:", result["text"])

    def test_generation_conflict_secret_rejection_and_collision_are_recursive_noops(self) -> None:
        baseline = inventory(self.root)
        denied = self.cli(
            STORE, "episode", self.root, "--type", "tool_result", "--content", "late",
            "--source-kind", "tool", "--authority", "user-stunspot", "--idempotency-key", "late",
            "--expected-generation", 99, expected=2,
        )
        self.assertIn("generation_conflict", denied["text"])
        self.assertEqual(inventory(self.root), baseline)
        denied = self.cli(
            STORE, "episode", self.root, "--type", "tool_result",
            "--content", "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            "--source-kind", "tool", "--authority", "user-stunspot", "--idempotency-key", "secret",
            "--expected-generation", self.generation, expected=2,
        )
        self.assertIn("redaction_rejected", denied["text"])
        self.assertEqual(inventory(self.root), baseline)
        first = self.episode("one", key="same")
        after = inventory(self.root)
        replay = self.cli(
            STORE, "episode", self.root, "--type", "tool_result", "--content", "one",
            "--source-kind", "tool", "--authority", "user-stunspot", "--sensitivity", "ordinary",
            "--idempotency-key", "same", "--expected-generation", 0,
        )
        self.assertEqual(replay["status"], "duplicate_committed")
        self.assertEqual(inventory(self.root), after)
        collision = self.cli(
            STORE, "episode", self.root, "--type", "tool_result", "--content", "two",
            "--source-kind", "tool", "--authority", "user-stunspot", "--sensitivity", "ordinary",
            "--idempotency-key", "same", "--expected-generation", self.generation, expected=2,
        )
        self.assertIn("idempotency_collision", collision["text"])
        self.assertEqual(inventory(self.root), after)

    def test_receipt_details_cannot_override_authoritative_core(self) -> None:
        root = self.root
        token = runtime.open_workspace(str(root), writable=False)[1]
        with runtime.transaction(
            root, "collision-mutant", expected_generation=self.generation, selector=token,
            authority="user-stunspot", idempotency_key="collision-mutant", request_payload={"x": 1},
        ) as tx:
            receipt = tx.finish("real-kind", {
                "kind": "forged", "status": "recovered", "workspace_id": "forged",
                "operation": "forged", "authority": "forged", "generation_after": 999,
            })
        self.assertEqual(receipt["kind"], "real-kind")
        self.assertEqual(receipt["status"], "committed")
        self.assertEqual(receipt["workspace_id"], json.loads((root / "manifest.json").read_text())["workspace_id"])
        self.assertEqual(receipt["operation"], "collision-mutant")
        self.assertEqual(receipt["authority"], "user-stunspot")
        self.assertEqual(receipt["generation_after"], 1)

class FaultlineTests(WorkspaceCase):
    def neighborhood(self, *, deadline: float = 1000) -> dict:
        return self.cli(
            FAULT, "neighborhood", self.root, "--task", "retry token refresh",
            "--producer", "codex", "--tool", "web", "--provider", "oauth",
            "--operation-family", "token-refresh", "--error-code", "invalid_grant",
            "--error-class", "OAuthError", "--environment", "windows",
            "--environment-version", "1", "--deadline-ms", deadline,
        )

    def test_capture_hashes_external_identity_and_never_persists_raw_values(self) -> None:
        raw_operation = "oauth-operation-from-provider-123"
        raw_event = "provider-event-with-user-path-C-drive"
        receipt = self.capture(raw_event, operation_id=raw_operation)
        tree = b"\n".join(path.read_bytes() for path in self.root.rglob("*") if path.is_file())
        self.assertNotIn(raw_operation.encode(), tree)
        self.assertNotIn(raw_event.encode(), tree)
        rows = runtime.read_jsonl(self.root / "episodes" / "events.jsonl")
        occurrence = rows[-1]["occurrence"]
        self.assertRegex(occurrence["operation_id"], r"^XID-[0-9a-f]{32}$")
        self.assertRegex(occurrence["source_event_id"], r"^XID-[0-9a-f]{32}$")
        self.assertTrue(receipt["source_evidence_ids"][0].startswith("XID-"))

    def test_recurrence_unknown_rows_never_increase_known_lower_bound(self) -> None:
        rows = []
        for index in range(6):
            rows.append({
                "id": f"EP-{index}",
                "occurrence": {"operation_id": "XID-known" if index == 0 else None, "retry_of": None},
            })
        self.assertEqual(fault.recurrence_lower_bound(rows), 1)
        unknown = [{"id": f"EP-u{index}", "occurrence": {"operation_id": None, "retry_of": None}} for index in range(5)]
        self.assertEqual(fault.recurrence_lower_bound(unknown), 1)
        unknown[1]["occurrence"]["retry_of"] = "EP-u0"
        self.assertEqual(fault.recurrence_lower_bound(unknown), 1)

    def test_multiple_missing_operation_ids_render_at_least_one_with_uncertainty(self) -> None:
        for index in range(5):
            self.capture(f"event-{index}", key=f"capture-{index}")
        result = self.neighborhood()
        self.assertEqual(result["selected_count"], 1)
        text = result["cards"][0]["recurrence"]["text"]
        self.assertIn("At least 1 ", text)
        self.assertIn("identity uncertainty", text)

    def test_deadline_returns_typed_empty_degraded_view_without_mutation(self) -> None:
        self.capture("event-deadline", operation_id="op-deadline")
        before = inventory(self.root)
        result = self.neighborhood(deadline=0)
        self.assertEqual(result["format"], "cd-error-neighborhood/v1")
        self.assertEqual(result["cards"], [])
        self.assertEqual(result["selected_count"], 0)
        self.assertIn("deadline_exceeded", result["degradation"])
        self.assertIn("not proof of safety", result["empty_means"])
        self.assertEqual(inventory(self.root), before)

    def test_secret_in_structured_capture_is_rejected_before_any_journal(self) -> None:
        before = inventory(self.root)
        result = self.cli(
            FAULT, "capture", self.root, "--expected-generation", self.generation,
            "--idempotency-key", "secret-capture", "--source-event-id", "event",
            "--producer", "codex", "--operation-family", "token-refresh",
            "--error-class", "OAuthError", "--message", "Bearer abcdefghijklmnopqrstuvwxyz",
            "--source-pointer", "tool result", "--authority", "user-stunspot", expected=2,
        )
        self.assertEqual(result["error"], "redaction_rejected")
        self.assertEqual(inventory(self.root), before)
        self.assertEqual(list((self.root / "transactions").glob("*/journal.json")), [])

    def test_recursive_secret_key_detection_covers_aliases(self) -> None:
        canary = "never-persist-this"
        for key in ("oauth_access_token_value", "authorization_header", "my_api_key", "nested_client_secret_copy"):
            self.assertTrue(fault.contains_secret_data({"outer": {key: canary}}), key)


class SelectorAndCustodyTests(WorkspaceCase):
    def _registry(self, root: Path, continuity: Path) -> Path:
        path = self.base / "selectors.json"
        value = {
            "format": "nova-path-selectors/v1", "set_at_utc": "2026-08-13T00:00:00Z",
            "active_values": {
                "NOVA_DATA_ROOT": str(root), "NOVA_CONTINUITY_HOME": str(continuity),
                "DUNBAR_STORE": str(root / "memory" / "dunbar" / "people.sqlite3"),
                "CORKBOARD_HOME": str(root / "memory" / "corkboard"),
                "MIND_CORE_DATABASE": str(root / "mind" / "r6" / "mind.sqlite"),
                "MIND_HOOK_RECEIPT_DIRECTORY": str(root / "mind" / "receipts"),
            },
        }
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_every_selector_capability_root_and_case_variant_is_denied_without_creation(self) -> None:
        nova = self.base / "NovaData"
        nova.mkdir()
        registry = self._registry(nova, nova / "memory" / "continuity")
        with mock.patch.object(runtime, "SELECTOR_REGISTRY", registry):
            targets = [
                nova / "memory" / "dunbar" / "artifact.json",
                nova / "memory" / "corkboard" / "artifact.json",
                nova / "mind" / "r6" / "artifact.json",
                nova / "mind" / "receipts" / "artifact.json",
                Path(str(nova).upper()) / "exports" / "artifact.json",
            ]
            for target in targets:
                with self.assertRaises(runtime.ContinuityError) as caught:
                    runtime.validate_external_target(self.root, str(target), "artifact", must_be_absent=True)
                self.assertEqual(caught.exception.code, "protected_target_denied")
                self.assertFalse(target.exists())
            prefix = self.base / "NovaData-not-owned" / "artifact.json"
            resolved = runtime.validate_external_target(self.root, str(prefix), "artifact", must_be_absent=True)
            self.assertEqual(resolved, prefix.resolve())

    def test_registry_swap_after_resolution_is_denied_under_lock_with_zero_creation(self) -> None:
        nova = self.base / "nova"
        first = nova / "memory" / "continuity-a"
        second = nova / "memory" / "continuity-b"
        runtime.initialize_workspace(str(first), user="user", project="project", agent="nova", thread=None, sensitivity="ordinary", retention="until-user-changes")
        runtime.initialize_workspace(str(second), user="user", project="project", agent="nova", thread=None, sensitivity="ordinary", retention="until-user-changes")
        registry = self._registry(nova, first)
        with mock.patch.dict(os.environ, {"NOVA_DATA_ROOT": str(nova), "NOVA_CONTINUITY_HOME": str(first)}):
            selected, token = runtime.open_workspace(None, writable=False, mode="nova", registry_path=registry)
        before = inventory(first)
        self._registry(nova, second)
        with self.assertRaises(runtime.ContinuityError) as caught:
            with runtime.transaction(
                selected, "selector-swap", expected_generation=0, selector=token,
                authority="user-stunspot", idempotency_key="selector-swap", request_payload={},
            ):
                pass
        self.assertEqual(caught.exception.code, "selector_registry_changed")
        self.assertEqual(inventory(first), before)

    def test_generic_late_reparse_witness_is_denied_under_lock(self) -> None:
        selected, token = runtime.open_workspace(str(self.root), writable=False)
        before = inventory(self.root)
        with mock.patch.object(runtime, "_has_reparse_component", return_value=True):
            with self.assertRaises(runtime.ContinuityError) as caught:
                with runtime.transaction(
                    selected, "late-reparse", expected_generation=0, selector=token,
                    authority="user-stunspot", idempotency_key="late-reparse", request_payload={},
                ):
                    pass
        self.assertEqual(caught.exception.code, "custody_reparse_escape")
        self.assertEqual(inventory(self.root), before)

def rewrite_active_member(root: Path, member: str, rows: list[dict]) -> None:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle = root / manifest["active_generation_path"]
    encoded = runtime.encode_jsonl(rows)
    (bundle / member).write_bytes(encoded)
    metadata_path = bundle / "generation.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["members"][member] = {
        "sha256": hashlib.sha256(encoded).hexdigest(), "bytes": len(encoded), "rows": len(rows),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest["active_generation_manifest_sha256"] = sha(metadata_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    runtime.open_snapshot(root)


class EligibilityTests(WorkspaceCase):
    def test_v2_compiler_omits_every_d07_canary_from_markdown_and_metadata(self) -> None:
        episode = self.episode("eligible source", key="source")
        record = self.cli(
            STORE, "record", self.root, "--kind", "decision", "--content", "eligible decision",
            "--source-ids", episode["episode_id"], "--authority", "user-stunspot",
            "--idempotency-key", "record", "--expected-generation", self.generation,
        )
        rows = runtime.read_jsonl(self.root / "state" / "records.jsonl")
        template = rows[-1]
        canaries = {
            "ST-env": ("CANARY_WRONG_ENV", {"tags": ["environment:linux"]}),
            "ST-unreachable": ("CANARY_UNREACHABLE", {"tags": ["source-unreachable"]}),
            "ST-time": ("CANARY_BAD_TIME", {"valid_from": "not-a-time"}),
            "ST-expired": ("CANARY_EXPIRED", {"expires_at": "2020-01-01T00:00:00Z"}),
            "ST-sensitive": ("CANARY_OVER_CEILING", {"sensitivity": "restricted"}),
            "ST-secret": ("Authorization: Bearer CANARY_SECRET_TOKEN_123456789", {}),
            "ST-conflict": ("CANARY_CONFLICT_OVER_CEILING", {"status": "conflicted", "sensitivity": "restricted"}),
        }
        for identifier, (content, changes) in canaries.items():
            row = json.loads(json.dumps(template))
            row.update({"id": identifier, "content": content, **changes})
            rows.append(row)
        rewrite_active_member(self.root, "state.jsonl", rows)
        markdown, metadata = compiler.compile_packet(
            self.root, "eligible decision", 12000, "limited", 5, [], [],
            environment="windows", environment_version="1", unreachable_source_ids=[],
        )
        rendered = markdown + json.dumps(metadata, sort_keys=True)
        self.assertIn("eligible decision", rendered)
        for content, _ in canaries.values():
            self.assertNotIn(content, rendered)
        self.assertNotIn("CANARY_SECRET_TOKEN", rendered)
        reasons = metadata["eligibility_omission_counts"]
        for reason in ("environment_mismatch", "source_unreachable", "schema_invalid", "expired", "sensitivity_denied", "redaction_rejected"):
            self.assertGreater(reasons.get(reason, 0), 0, reason)

    def test_secret_task_is_rejected_without_output(self) -> None:
        output = self.base / "context.md"
        result = self.cli(
            SCRIPTS / "compile_context_v2.py", self.root,
            "--task", "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            "--output", output, expected=2,
        )
        self.assertIn("redaction_rejected", result["text"])
        self.assertFalse(output.exists())
        self.assertFalse(Path(str(output) + ".json").exists())


class LifecycleTests(WorkspaceCase):
    def _plan(self, identifier: str, *, mode: str = "tombstone") -> tuple[Path, dict, str]:
        output = self.base / f"plan-{mode}.json"
        retention = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
        result = self.cli(
            STORE, "forget-plan", self.root, "--ids", identifier, "--authority", "user-stunspot",
            "--mode", mode, "--plan-output", output, "--plan-minutes", 30,
            "--retention-until", retention, "--destruction-owner", "user-stunspot",
            "--access-owner", "user-stunspot", "--encryption-disposition", "not-required",
        )
        return output, json.loads(output.read_text(encoding="utf-8")), retention

    def test_forget_tombstone_full_backup_and_exact_restore(self) -> None:
        canary = "FORGET_CANARY_PRIVATE_TEXT"
        episode = self.episode(canary, key="forget-source")
        plan_path, plan, retention = self._plan(episode["episode_id"])
        self.assertTrue(plan["apply_supported"])
        self.assertEqual(plan["blocking_reasons"], [])
        key = self.base / "backup.key"
        key.write_bytes(b"k" * 48)
        backup = self.base / "forget-backup"
        receipt = self.cli(
            STORE, "forget", self.root, "--plan", plan_path, "--plan-digest", plan["plan_digest"],
            "--backup-output", backup, "--backup-auth-key-file", key,
            "--retention-until", retention, "--destruction-owner", "user-stunspot",
            "--access-owner", "user-stunspot", "--encryption-disposition", "not-required",
            "--authority", "user-stunspot", "--idempotency-key", "forget-apply",
            "--expected-generation", self.generation,
        )
        self.assertEqual(receipt["kind"], "forgotten")
        self.assertTrue((backup / "backup.json").is_file())
        active = self.root / json.loads((self.root / "manifest.json").read_text())["active_generation_path"]
        active_bytes = b"\n".join(path.read_bytes() for path in active.iterdir() if path.is_file())
        self.assertNotIn(canary.encode(), active_bytes)
        tombstoned = runtime.read_jsonl(self.root / "episodes" / "events.jsonl")[-1]
        self.assertEqual(tombstoned["content"], "[forgotten]")
        restore = self.cli(
            STORE, "restore-forget", self.root, "--backup", backup,
            "--backup-auth-key-file", key, "--authority", "user-stunspot",
            "--idempotency-key", "forget-restore", "--expected-generation", self.generation,
        )
        self.assertEqual(restore["kind"], "forget-restored")
        restored = runtime.read_jsonl(self.root / "episodes" / "events.jsonl")
        self.assertTrue(any(row.get("content") == canary for row in restored))

    def test_derivative_plan_truthfully_blocks_apply(self) -> None:
        episode = self.episode("derivative source", key="derivative")
        contexts = self.root / "contexts"
        contexts.mkdir()
        (contexts / "view.json").write_text(json.dumps({"source_ids": [episode["episode_id"]]}), encoding="utf-8")
        _, plan, _ = self._plan(episode["episode_id"])
        self.assertFalse(plan["apply_supported"])
        self.assertIn("delete_named_derivatives_with_governed_adapter", plan["blocking_reasons"])
        self.assertEqual(plan["required_action"], "delete_named_derivatives_with_governed_adapter")

    def test_stale_plan_never_creates_backup(self) -> None:
        episode = self.episode("stale source", key="stale-source")
        plan_path, plan, retention = self._plan(episode["episode_id"])
        self.episode("intervening", key="intervening")
        key = self.base / "backup.key"; key.write_bytes(b"z" * 48)
        backup = self.base / "orphan-must-not-exist"
        result = self.cli(
            STORE, "forget", self.root, "--plan", plan_path, "--plan-digest", plan["plan_digest"],
            "--backup-output", backup, "--backup-auth-key-file", key,
            "--retention-until", retention, "--destruction-owner", "user-stunspot",
            "--access-owner", "user-stunspot", "--encryption-disposition", "not-required",
            "--authority", "user-stunspot", "--idempotency-key", "stale-forget",
            "--expected-generation", plan["execute_generation"], expected=2,
        )
        self.assertIn("plan_stale", result["text"])
        self.assertFalse(backup.exists())


class DestructiveLifecycleTests(WorkspaceCase):
    def _forget_fixture(self) -> tuple[str, Path, Path, dict]:
        episode = self.episode("named lifecycle target", key="lifecycle-source")
        identifier = episode["episode_id"]
        retention = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
        plan_path = self.base / "forget-plan.json"
        self.cli(
            STORE, "forget-plan", self.root, "--ids", identifier, "--authority", "user-stunspot",
            "--mode", "tombstone", "--plan-output", plan_path, "--plan-minutes", 30,
            "--retention-until", retention, "--destruction-owner", "user-stunspot",
            "--access-owner", "user-stunspot", "--encryption-disposition", "not-required",
        )
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        key = self.base / "backup.key"; key.write_bytes(b"a" * 48)
        backup = self.base / "backup"
        self.cli(
            STORE, "forget", self.root, "--plan", plan_path, "--plan-digest", plan["plan_digest"],
            "--backup-output", backup, "--backup-auth-key-file", key,
            "--retention-until", retention, "--destruction-owner", "user-stunspot",
            "--access-owner", "user-stunspot", "--encryption-disposition", "not-required",
            "--authority", "user-stunspot", "--idempotency-key", "forget",
            "--expected-generation", self.generation,
        )
        return identifier, key, backup, plan

    def test_named_prior_generation_deletion_is_exact_external_receipted_and_not_physical_erasure(self) -> None:
        identifier, key, backup, _ = self._forget_fixture()
        plan_path = self.base / "named-plan.json"
        self.cli(
            STORE, "forget-plan", self.root, "--ids", identifier, "--authority", "user-stunspot",
            "--mode", "tombstone", "--plan-output", plan_path, "--plan-minutes", 30,
            "--retention-until", "2020-01-01T00:00:00Z", "--destruction-owner", "user-stunspot",
            "--access-owner", "user-stunspot", "--encryption-disposition", "not-required",
        )
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        nodes = [node for node in plan["target_graph"] if node["class"] == "prior_generation"]
        self.assertTrue(nodes)
        node = nodes[-1]
        target = self.root / node["path"]
        generation_before = self.generation
        manifest_before = sha(self.root / "manifest.json")
        receipt_path = self.base / "named-delete-receipt.json"
        receipt = self.cli(
            STORE, "delete-named-custody", self.root, "--authority", "user-stunspot",
            "--plan", plan_path, "--plan-digest", plan["plan_digest"],
            "--target-class", "prior_generation", "--target", node["path"],
            "--target-sha256", node["artifact_sha256"], "--receipt-output", receipt_path,
        )
        self.assertEqual(receipt["status"], "application_deleted")
        self.assertTrue(receipt["lifecycle_outcomes"]["deleted_from_named_continuity_custody"])
        self.assertEqual(receipt["physical_erasure"], "not_established")
        self.assertFalse(target.exists())
        self.assertEqual(self.generation, generation_before)
        self.assertEqual(sha(self.root / "manifest.json"), manifest_before)
        self.assertNotIn(str(target), json.dumps(json.loads(receipt_path.read_text(encoding="utf-8"))))
        self.assertTrue(backup.exists())

    def test_authenticated_backup_destruction_after_retention(self) -> None:
        _, key, backup, _ = self._forget_fixture()
        metadata_path = backup / "backup.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["retention_until"] = "2020-01-01T00:00:00Z"
        metadata["authentication"]["mac"] = store._backup_mac(metadata, key.read_bytes())
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        digest = runtime.tree_digest(backup)
        before = inventory(self.root)
        receipt_path = self.base / "backup-destroy-receipt.json"
        receipt = self.cli(
            STORE, "backup-destroy", self.root, "--authority", "user-stunspot",
            "--backup", backup, "--backup-auth-key-file", key,
            "--backup-sha256", digest, "--receipt-output", receipt_path,
        )
        self.assertEqual(receipt["status"], "application_deleted")
        self.assertEqual(receipt["target_class"], "recovery_backup")
        self.assertFalse(backup.exists())
        self.assertTrue(receipt_path.exists())
        self.assertEqual(inventory(self.root), before)

    def test_active_retention_is_preintent_noop(self) -> None:
        _, key, backup, _ = self._forget_fixture()
        before_workspace = inventory(self.root); before_backup = inventory(backup)
        receipt_path = self.base / "must-not-exist.json"
        result = self.cli(
            STORE, "backup-destroy", self.root, "--authority", "user-stunspot",
            "--backup", backup, "--backup-auth-key-file", key,
            "--backup-sha256", runtime.tree_digest(backup), "--receipt-output", receipt_path, expected=2,
        )
        self.assertIn("retention_active", result["text"])
        self.assertEqual(inventory(self.root), before_workspace)
        self.assertEqual(inventory(backup), before_backup)
        self.assertFalse(receipt_path.exists())

    def test_injected_post_intent_failure_emits_partial_receipt_and_preserves_target(self) -> None:
        export = self.base / "known-export.json"
        export.write_text(json.dumps({"source_ids": ["external"]}), encoding="utf-8")
        episode = self.episode("external traversal", key="external")
        plan_path = self.base / "export-plan.json"
        self.cli(
            STORE, "forget-plan", self.root, "--ids", episode["episode_id"],
            "--authority", "user-stunspot", "--mode", "tombstone", "--plan-output", plan_path,
            "--plan-minutes", 30, "--retention-until", "2020-01-01T00:00:00Z",
            "--destruction-owner", "user-stunspot", "--access-owner", "user-stunspot",
            "--encryption-disposition", "not-required", "--known-export-receipts", export,
        )
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        node = next(node for node in plan["target_graph"] if node["class"] == "known_export")
        receipt_path = self.base / "partial.json"
        env = dict(os.environ); env["CONTINUITY_LIFECYCLE_FAIL_POINT"] = "after_intent"
        completed = subprocess.run([
            sys.executable, str(STORE), "delete-named-custody", str(self.root),
            "--authority", "user-stunspot", "--plan", str(plan_path), "--plan-digest", plan["plan_digest"],
            "--target-class", "known_export", "--target", node["path"],
            "--target-sha256", node["artifact_sha256"], "--receipt-output", str(receipt_path),
        ], text=True, capture_output=True, env=env, timeout=30)
        self.assertEqual(completed.returncode, 2)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "partial_failure")
        self.assertEqual(receipt["error_code"], "injected_lifecycle_failure")
        self.assertTrue(export.exists())


class ExportTests(WorkspaceCase):
    def test_scoped_export_leaves_source_exact_and_emits_destination_receipt(self) -> None:
        self.episode("EXPORT_VISIBLE_CANARY", key="export-visible", sensitivity="ordinary")
        self.episode("EXPORT_RESTRICTED_CANARY", key="export-restricted", sensitivity="restricted")
        before = inventory(self.root)
        output = self.base / "scoped-export.json"
        result = self.cli(
            STORE, "export", self.root, "--output", output, "--authority", "user-stunspot",
            "--sensitivity", "limited",
        )
        self.assertEqual(inventory(self.root), before)
        self.assertTrue(output.is_file())
        receipt_path = Path(result["receipt_output"])
        self.assertTrue(receipt_path.is_file())
        artifact_text = output.read_text(encoding="utf-8")
        self.assertIn("EXPORT_VISIBLE_CANARY", artifact_text)
        self.assertNotIn("EXPORT_RESTRICTED_CANARY", artifact_text)
        receipt_text = receipt_path.read_text(encoding="utf-8")
        self.assertNotIn(str(output), receipt_text)
        self.assertIn('"source_mutated": false', receipt_text.lower())


class CompatibilityAndRecoveryTests(WorkspaceCase):
    def _episode_command(self, root: Path, content: str, key: str, expected: int) -> list[str]:
        return [
            sys.executable, str(STORE), "episode", str(root), "--type", "tool_result",
            "--content", content, "--source-kind", "tool", "--authority", "user-stunspot",
            "--sensitivity", "ordinary", "--idempotency-key", key,
            "--expected-generation", str(expected),
        ]

    def test_overlapping_writers_serialize_one_commit_and_one_generation_conflict(self) -> None:
        commands = [
            self._episode_command(self.root, "writer one", "writer-one", 0),
            self._episode_command(self.root, "writer two", "writer-two", 0),
        ]
        processes = [subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for command in commands]
        results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
        self.assertEqual(sorted(result[2] for result in results), [0, 2])
        denied = next(result for result in results if result[2] == 2)
        self.assertIn("generation_conflict", denied[1])
        rows = runtime.read_jsonl(self.root / "episodes" / "events.jsonl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.generation, 1)
        self.cli(VALIDATE, self.root)

    def test_crash_recovery_preserves_prior_before_commit_and_committed_after_manifest(self) -> None:
        cases = [
            ("after_bundle_published", False),
            ("after_manifest_commit", True),
        ]
        for index, (point, crashed_committed) in enumerate(cases):
            root = self.base / f"crash-{index}"
            runtime.initialize_workspace(str(root), user="user", project="project", agent="nova", thread=None, sensitivity="ordinary", retention="manual")
            env = dict(os.environ); env["CONTINUITY_TEST_CRASHPOINT"] = point
            crashed = subprocess.run(self._episode_command(root, f"crashed-{index}", f"crash-{index}", 0), text=True, capture_output=True, env=env, timeout=30)
            self.assertEqual(crashed.returncode, 97, point)
            observed = int(json.loads((root / "manifest.json").read_text())["generation"])
            self.assertEqual(observed, 1 if crashed_committed else 0)
            follow = subprocess.run(self._episode_command(root, f"follow-{index}", f"follow-{index}", observed), text=True, capture_output=True, timeout=30)
            self.assertEqual(follow.returncode, 0, follow.stderr)
            rows = runtime.read_jsonl(root / "episodes" / "events.jsonl")
            contents = {row["content"] for row in rows}
            self.assertIn(f"follow-{index}", contents)
            self.assertEqual(f"crashed-{index}" in contents, crashed_committed)
            self.assertEqual(runtime.pending_transactions(root), [])
            validated = subprocess.run([sys.executable, str(VALIDATE), str(root)], text=True, capture_output=True, timeout=30)
            self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)

    def test_public_recover_reconciles_v2_and_keeps_v1_read_only(self) -> None:
        clean = self.cli(
            STORE, "recover", self.root, "--authority", "user-stunspot",
        )
        self.assertEqual(clean["status"], "clean")
        self.assertFalse(clean["source_mutated"])
        self.assertEqual(clean["generation_before"], clean["generation_after"])

        crashed_root = self.base / "public-recovery"
        runtime.initialize_workspace(
            str(crashed_root), user="user", project="project", agent="nova",
            thread=None, sensitivity="ordinary", retention="manual",
        )
        env = dict(os.environ)
        env["CONTINUITY_TEST_CRASHPOINT"] = "after_bundle_published"
        crashed = subprocess.run(
            self._episode_command(crashed_root, "public crash", "public-crash", 0),
            text=True, capture_output=True, env=env, timeout=30,
        )
        self.assertEqual(crashed.returncode, 97)
        recovered = self.cli(
            STORE, "recover", crashed_root, "--authority", "user-stunspot",
        )
        self.assertEqual(recovered["status"], "recovered")
        self.assertTrue(recovered["source_mutated"])
        self.assertEqual(len(recovered["recovered_transaction_ids"]), 1)
        self.assertEqual(runtime.pending_transactions(crashed_root), [])
        self.cli(VALIDATE, crashed_root)

        legacy = self.base / "legacy-recovery-guidance"
        initialized = subprocess.run([
            sys.executable, str(SCRIPTS / "continuity_store.py"), "init", str(legacy),
            "--user", "user", "--project", "project", "--agent", "nova",
        ], text=True, capture_output=True, timeout=30)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        before = inventory(legacy)
        guidance = self.cli(
            STORE, "recover", legacy, "--authority", "user-stunspot",
        )
        self.assertEqual(guidance["compatibility_mode"], "v1_read_only")
        self.assertEqual(guidance["status"], "guidance_only")
        self.assertFalse(guidance["source_mutated"])
        self.assertEqual(inventory(legacy), before)

    def test_v1_is_read_only_through_v2_and_copy_migration_is_source_exact(self) -> None:
        legacy_store = SCRIPTS / "continuity_store.py"
        legacy = self.base / "legacy"
        initialized = subprocess.run([
            sys.executable, str(legacy_store), "init", str(legacy),
            "--user", "user", "--project", "*", "--agent", "nova",
        ], text=True, capture_output=True, timeout=30)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        added = subprocess.run([
            sys.executable, str(legacy_store), "episode", str(legacy), "--type", "assertion",
            "--content", "legacy migration source", "--source-kind", "user", "--authority", "user-stunspot",
            "--valid-from", "2000-01-01",
        ], text=True, capture_output=True, timeout=30)
        self.assertEqual(added.returncode, 0, added.stderr)
        manifest_path = legacy / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = "0.2.0"
        manifest["policies"]["scope_model"] = "harness-global"
        manifest["capabilities"]["transactional_init"] = True
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        before = inventory(legacy)
        opened = self.cli(STORE, "open", legacy)
        self.assertEqual(opened["compatibility_mode"], "v1_read_only")
        denied = self.cli(
            STORE, "episode", legacy, "--type", "tool_result", "--content", "must not write",
            "--source-kind", "tool", "--authority", "user-stunspot", "--idempotency-key", "v1-denied",
            "--expected-generation", 0, expected=2,
        )
        self.assertIn("migration_required_for_mutation", denied["text"])
        self.assertEqual(inventory(legacy), before)
        fault_denied = self.cli(
            FAULT, "capture", legacy, "--expected-generation", 0, "--idempotency-key", "v1-fault",
            "--source-event-id", "event", "--producer", "codex", "--operation-family", "test",
            "--error-class", "Error", "--message", "failed", "--source-pointer", "tool",
            "--authority", "user-stunspot", expected=2,
        )
        self.assertEqual(fault_denied["error"], "operation_unsupported_v1")
        self.assertEqual(inventory(legacy), before)
        digest = runtime.tree_digest(legacy)
        bad_destination = self.base / "bad-migration"
        bad = self.cli(
            STORE, "migrate-copy", legacy, bad_destination, "--authority", "user-stunspot",
            "--source-tree-sha256", "0" * 64, expected=2,
        )
        self.assertIn("source_changed", bad["text"])
        self.assertFalse(bad_destination.exists())
        destination = self.base / "migrated"
        receipt = self.cli(
            STORE, "migrate-copy", legacy, destination, "--authority", "user-stunspot",
            "--source-tree-sha256", digest,
        )
        self.assertEqual(receipt["kind"], "migration-copied")
        self.assertEqual(receipt["mapping_policy"], "legacy-full-date-normalization/v2")
        self.assertEqual(receipt["mapping"]["normalized_temporal_fields"], 1)
        self.assertEqual(inventory(legacy), before)
        manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["format"], runtime.FORMAT)
        self.assertEqual(manifest["migrated_from"]["source_tree_sha256"], digest)
        self.assertEqual(manifest["migrated_from"]["temporal_normalization_count"], 1)
        migrated_episode = runtime.read_jsonl(destination / "episodes" / "events.jsonl")[0]
        self.assertEqual(migrated_episode["valid_from"], "2000-01-01T00:00:00Z")
        self.cli(VALIDATE, destination)


if __name__ == "__main__":
    unittest.main()
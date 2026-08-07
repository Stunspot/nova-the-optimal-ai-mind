from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MIND_ROOT = ROOT / "plugins" / "augment-of-mind"
HOOK_PATH = MIND_ROOT / "hooks" / "mind_prompt_submit.py"
DELIVERY_PATH = MIND_ROOT / "mind_core" / "hook_delivery.py"
CONTEXT_PATH = MIND_ROOT / "mind_core" / "hook_context.py"
import sys
sys.path.insert(0, str(MIND_ROOT))
from mind_core import hook_context as HOOK_CONTEXT
from mind_core import hook_delivery as HOOK


class FakeHosts:
    def __init__(self) -> None:
        self.handshakes: list[dict[str, Any]] = []

    def handshake(self, payload: dict[str, Any]) -> None:
        self.handshakes.append(payload)


class FakeReminders:
    def __init__(self) -> None:
        self.anchors: list[dict[str, Any]] | None = None

    def active_snapshot_binding(self) -> dict[str, Any]:
        return {
            "current": True,
            "model_id": "test-embedding-model",
            "snapshot_digest": "digest:snapshot",
            "associative_index_snapshot_id": "snapshot:test",
        }

    def issue_session_capability(self, *_args: Any, **_kwargs: Any) -> dict[str, str]:
        return {"session_capability": "session-capability:test"}

    def neighborhood(
        self,
        _token: str,
        _snapshot_id: str,
        anchors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.anchors = anchors
        canonical = HOOK.LEGACY_FIELD_HEADER + "\n\n$capability-example — Example capability"
        return {
            "field_id": "field:test",
            "snapshot_id": "snapshot:test",
            "mode": "hybrid_current" if anchors[0].get("lexical_hints") else "vector_current",
            "membership_manifest_digest": "digest:members",
            "representations": {
                "canonical": {"text": canonical},
                "compact": {"text": canonical},
            },
        }


class FakeCore:
    def __init__(self, reminders: FakeReminders) -> None:
        self.reminders = reminders
        self.hosts = FakeHosts()

    def __enter__(self) -> "FakeCore":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None


class SemanticArmReachTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database = Path(self.temporary.name) / "mind.sqlite"
        self.database.write_bytes(b"test")
        self.environment = {"MIND_CORE_DATABASE": str(self.database)}

    @staticmethod
    def event(prompt: str, transcript_path: Path | None = None) -> dict[str, Any]:
        return {
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt,
            "turn_id": "turn:test",
            "session_id": "session:test",
            "cwd": "E:\\Github\\project",
            "permission_mode": "default",
            "transcript_path": str(transcript_path) if transcript_path else None,
        }

    def test_plain_language_uses_semantic_association_without_identity_hints(self) -> None:
        reminders = FakeReminders()
        core = FakeCore(reminders)
        embedded: list[str] = []

        def embedder(texts: list[str], model: str, _url: str, _timeout: float) -> list[list[float]]:
            embedded.extend(texts)
            self.assertEqual(model, "test-embedding-model")
            return [[0.25, 0.75]]

        result, vector_state, _context_hash = HOOK.compile_associative_field(
            self.event("please help me untangle this decision"),
            environment=self.environment,
            embedder=embedder,
            core_factory=lambda _path: core,
        )

        self.assertIsNone(vector_state)
        self.assertEqual(result["field_id"], "field:test")
        self.assertEqual(len(embedded), 1)
        self.assertIn("please help me untangle this decision", embedded[0])
        self.assertIsNotNone(reminders.anchors)
        anchor = reminders.anchors[0]
        self.assertEqual(anchor["anchor_kind"], "turn_context")
        self.assertEqual(anchor["vector"], [0.25, 0.75])
        self.assertNotIn("lexical_hints", anchor)

    def test_bounded_recent_conversation_contributes_to_the_semantic_anchor(self) -> None:
        transcript = Path(self.temporary.name) / "rollout.jsonl"
        records = [
            {"item": {"role": "user", "content": [{"type": "input_text", "text": "We are comparing two release designs."}]}},
            {"item": {"role": "assistant", "content": [{"type": "output_text", "text": "The second design preserves rollback."}]}},
        ]
        transcript.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
        event = self.event("Which tradeoff matters now?", transcript)
        context = HOOK_CONTEXT.association_context(event)
        self.assertIn("We are comparing two release designs.", context)
        self.assertIn("The second design preserves rollback.", context)
        self.assertIn("Which tradeoff matters now?", context)
        self.assertLessEqual(len(context), HOOK_CONTEXT.MAX_ASSOCIATION_CONTEXT_CHARACTERS)

    def test_lexical_identity_supplements_the_semantic_vector(self) -> None:
        reminders = FakeReminders()
        core = FakeCore(reminders)

        result, vector_state, _context_hash = HOOK.compile_associative_field(
            self.event("Please use $capability-promotion for this update."),
            environment=self.environment,
            embedder=lambda *_args: [[0.25, 0.75]],
            core_factory=lambda _path: core,
        )

        self.assertEqual(result["field_id"], "field:test")
        self.assertIsNone(vector_state)
        anchor = reminders.anchors[0]
        self.assertEqual(anchor["vector"], [0.25, 0.75])
        self.assertIn("capability-promotion", anchor["lexical_hints"])

    def test_lexical_identity_does_not_replace_unavailable_semantics(self) -> None:
        def unavailable(*_args: Any) -> list[list[float]]:
            raise HOOK.RecallUnavailable("embedding unavailable")

        with self.assertRaises(HOOK.HookUnavailable) as captured:
            HOOK.compile_associative_field(
                self.event("Please use $capability-promotion for this update."),
                environment=self.environment,
                embedder=unavailable,
                core_factory=lambda _path: FakeCore(FakeReminders()),
            )
        self.assertEqual(captured.exception.code, "semantic_embedding_unavailable")

    def test_unavailable_semantics_does_not_delegate_retrieval_to_the_model(self) -> None:
        def unavailable(*_args: Any) -> list[list[float]]:
            raise HOOK.RecallUnavailable("embedding unavailable")

        def compiler(event: dict[str, Any], *, environment: dict[str, str]) -> tuple[dict[str, Any], str | None, str]:
            return HOOK.compile_associative_field(
                event,
                environment=environment,
                embedder=unavailable,
                core_factory=lambda _path: FakeCore(FakeReminders()),
            )

        output, receipt = HOOK.prepare_event(
            self.event("please help with this ordinary request"),
            environment=self.environment,
            compiler=compiler,
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        lowered = context.casefold()
        self.assertEqual(receipt["failure_code"], "semantic_embedding_unavailable")
        for forbidden in ("mcp", "resource reader", "skill discovery", "adapter", "server"):
            self.assertNotIn(forbidden, lowered)
        self.assertIn("makes no claim about capability availability", lowered)

    def test_rendered_field_uses_the_model_context_contract_exactly(self) -> None:
        reminders = FakeReminders()
        result = reminders.neighborhood("token", "snapshot", [{"anchor_kind": "turn_context"}])
        rendered = HOOK.render_additional_context(result, None)
        expected = HOOK.MODEL_CONTEXT_HEADER + "\n\n$capability-example — Example capability"
        self.assertEqual(rendered, expected)
        self.assertNotIn(HOOK.LEGACY_FIELD_HEADER, rendered)
        self.assertNotIn("advisory associative disclosure", rendered)
        self.assertNotIn("field=", rendered)
        header = HOOK.MODEL_CONTEXT_HEADER.casefold()
        self.assertIn("capabilities already present in assembled context", header)
        self.assertIn("surveyed memory may extend beyond the current harness", header)
        for forbidden in (
            "tools/skills/mcps",
            "mcp",
            "explor",
            "harness configuration",
            "resources/list",
            "resources/read",
        ):
            self.assertNotIn(forbidden, header)

    def test_rendered_field_rejects_nonvector_delivery(self) -> None:
        reminders = FakeReminders()
        result = reminders.neighborhood("token", "snapshot", [{"anchor_kind": "turn_context"}])
        with self.assertRaises(HOOK.HookUnavailable) as captured:
            HOOK.render_additional_context(result, "semantic_embedding_unavailable")
        self.assertEqual(captured.exception.code, "semantic_embedding_unavailable")

    def test_real_core_accepts_the_semantic_turn_context_anchor(self) -> None:
        mind_root = ROOT / "plugins" / "augment-of-mind"
        database = Path(self.temporary.name) / "integrated.sqlite"
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(mind_root)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        subprocess.run(
            [
                os.sys.executable,
                "-m",
                "mind_core.cli",
                "activate-estate-generation",
                "--database",
                str(database),
                "--bootstrap",
                str(ROOT / "bundle" / "reminder" / "associative-bootstrap.json"),
                "--index",
                str(ROOT / "bundle" / "reminder" / "associative-index-qwen3-embedding-0.6b.json"),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            env=environment,
        )
        index = json.loads(
            (ROOT / "bundle" / "reminder" / "associative-index-qwen3-embedding-0.6b.json").read_text(encoding="utf-8")
        )
        vector = index["vectors"][0]["values"]

        def embedder(_texts: list[str], _model: str, _url: str, _timeout: float) -> list[list[float]]:
            return [vector]

        result, vector_state, _context_hash = HOOK.compile_associative_field(
            self.event("Help me examine the structure and implications of this situation."),
            environment={"MIND_CORE_DATABASE": str(database)},
            embedder=embedder,
        )
        self.assertIsNone(vector_state)
        self.assertGreater(len(result["members"]), 0)
        self.assertEqual(result["anchors"][0]["anchor_kind"], "turn_context")
        rendered = HOOK.render_additional_context(result, vector_state)
        self.assertTrue(rendered.startswith(HOOK.MODEL_CONTEXT_HEADER + "\n\n"))
        self.assertNotIn(HOOK.LEGACY_FIELD_HEADER, rendered)

    def test_source_has_no_deferred_or_model_side_retrieval_path(self) -> None:
        source = HOOK_PATH.read_text(encoding="utf-8") + DELIVERY_PATH.read_text(encoding="utf-8") + CONTEXT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("HookDeferred", source)
        self.assertNotIn("CONTEXTUAL ASSOCIATION DEFERRED", source)
        self.assertNotIn("read_mcp_resource", source)


if __name__ == "__main__":
    unittest.main()

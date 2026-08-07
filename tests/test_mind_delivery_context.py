from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIND_ROOT = ROOT / "plugins" / "augment-of-mind"
sys.path.insert(0, str(MIND_ROOT))

from mind_core.delivery import compile_delivery
from mind_core.errors import ValidationError
from mind_core.model_context import LEGACY_FIELD_HEADER, MODEL_CONTEXT_HEADER
from mind_core.util import sha256_text


class MindDeliveryContextTests(unittest.TestCase):
    @staticmethod
    def field(mode: str = "vector_current") -> dict[str, object]:
        membership_digest = "a" * 64
        raw_text = (
            LEGACY_FIELD_HEADER
            + "\n\n- ⟦decision-intelligence⟧ Structure consequential choices."
        )
        representation = {
            "text": raw_text,
            "body_sha256": sha256_text(raw_text),
            "utf8_bytes": len(raw_text.encode("utf-8")),
            "membership_manifest_digest": membership_digest,
        }
        return {
            "field_id": "field:test",
            "snapshot_id": "snapshot:test",
            "scoped_estate_digest": "b" * 64,
            "membership_manifest_digest": membership_digest,
            "mode": mode,
            "representations": {
                "canonical": representation,
                "compact": representation,
            },
        }

    def test_portable_delivery_uses_the_shared_model_context(self) -> None:
        delivery = compile_delivery(self.field(), representation="canonical")
        expected = (
            MODEL_CONTEXT_HEADER
            + "\n\n- ⟦decision-intelligence⟧ Structure consequential choices."
        )
        self.assertEqual(delivery["text"], expected)
        self.assertEqual(delivery["body_sha256"], sha256_text(expected))
        self.assertEqual(delivery["utf8_bytes"], len(expected.encode("utf-8")))
        self.assertNotIn(LEGACY_FIELD_HEADER, delivery["text"])

    def test_portable_delivery_rejects_nonvector_fields(self) -> None:
        with self.assertRaises(ValidationError):
            compile_delivery(self.field("lexical_degraded"), representation="canonical")

    def test_recorded_contract_matches_the_runtime_header(self) -> None:
        contract = json.loads(
            (
                ROOT
                / "verification"
                / "associative-smoke"
                / "model-context-contract-v2.1.3.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(contract["mind_version"], "2.1.3")
        self.assertEqual(contract["header"], MODEL_CONTEXT_HEADER)
        self.assertEqual(
            contract["vector_backed_modes"],
            ["hybrid_current", "vector_current"],
        )
        self.assertEqual(contract["nonvector_delivery"], "degraded")
        self.assertFalse(contract["legacy_headers_present"])


if __name__ == "__main__":
    unittest.main()

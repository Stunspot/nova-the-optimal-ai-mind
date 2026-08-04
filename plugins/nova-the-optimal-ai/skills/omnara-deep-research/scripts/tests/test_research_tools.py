from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
SKILL = SCRIPTS.parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


campaign_tool = load("research_campaign")
citation_tool = load("citation_audit")
assembly_tool = load("assemble_report")


class ResearchToolTests(unittest.TestCase):
    def make_campaign(self, root: Path) -> Path:
        target = root / "campaign"
        campaign_tool.initialize(
            SKILL / "assets" / "campaign-vault",
            target,
            "Test campaign",
            "What evidence resolves the test question?",
            "deep",
        )
        return target

    def test_template_initializes_and_validates(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            self.assertEqual(campaign_tool.validate(target), [])
            data = json.loads((target / "campaign.json").read_text(encoding="utf-8"))
            self.assertEqual(data["tier"], "deep")

    def test_validator_rejects_unknown_claim_source(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            (target / "claim-ledger.jsonl").write_text(
                json.dumps({"id": "C001", "claim": "x", "source_ids": ["S999"]}) + "\n",
                encoding="utf-8",
            )
            self.assertTrue(any("unknown source S999" in item for item in campaign_tool.validate(target)))

    def test_citation_audit_passes_resolved_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            source = {
                "id": "S001",
                "url": "https://example.test/source",
                "states": ["discovered", "inspected", "opened", "deeply-read", "cited"],
            }
            claim = {
                "id": "C001",
                "claim": "Test claim",
                "importance": "consequential",
                "source_ids": ["S001"],
            }
            (target / "source-ledger.jsonl").write_text(json.dumps(source) + "\n", encoding="utf-8")
            (target / "claim-ledger.jsonl").write_text(json.dumps(claim) + "\n", encoding="utf-8")
            (target / "notes" / "S001.md").write_text(
                "# S001 Evidence\n\nThis full-reading note identifies the source, its scope, the bounded assertion it supports, "
                "the evidence location, the access date, and material limitations. It explicitly records that the source "
                "does not establish broader reliability, causation, or transfer beyond the tested claim.",
                encoding="utf-8",
            )
            (target / "report.md").write_text("A bounded claim. [S001]\n", encoding="utf-8")
            self.assertEqual(citation_tool.audit(target)["result"], "pass")

    def test_citation_audit_rejects_decorative_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            (target / "report.md").write_text("Unsupported. [S777]\n", encoding="utf-8")
            result = citation_tool.audit(target)
            self.assertEqual(result["result"], "fail")
            self.assertTrue(any("S777" in item for item in result["errors"]))

    def test_zero_evidence_campaign_cannot_complete_or_pass_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            campaign = json.loads((target / "campaign.json").read_text(encoding="utf-8"))
            campaign["phase"] = "complete"
            campaign["status"] = "partial-success"
            (target / "campaign.json").write_text(json.dumps(campaign) + "\n", encoding="utf-8")
            completed_text = (
                "This completed artifact contains enough ordinary words to clear the document-length floor while "
                "deliberately carrying no sources, no claims, and no citation markers. It models the dangerous case "
                "where polished prose could previously impersonate completed research without any retained evidence. "
            )
            for name, (minimum_words, _) in campaign_tool.COMPLETE_ARTIFACTS.items():
                repetitions = max(2, minimum_words // len(completed_text.split()) + 2)
                (target / name).write_text((completed_text * repetitions).strip() + "\n", encoding="utf-8")

            audit = citation_tool.audit(target)
            (target / "citation-audit-structural.json").write_text(
                json.dumps(audit, indent=2) + "\n", encoding="utf-8"
            )

            self.assertEqual(audit["result"], "fail")
            self.assertTrue(any("no citation markers" in item for item in audit["errors"]))
            errors = campaign_tool.validate(target)
            self.assertTrue(any("no cited sources" in item for item in errors))
            self.assertTrue(any("no source-linked claims" in item for item in errors))
            self.assertTrue(any("citation audit did not pass" in item for item in errors))

    def test_evidence_backed_audited_campaign_can_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            source = {
                "id": "S001",
                "url": "https://example.test/source",
                "states": ["discovered", "inspected", "opened", "deeply-read", "cited"],
            }
            claim = {
                "id": "C001",
                "claim": "The bounded test claim is supported by the retained source.",
                "importance": "consequential",
                "source_ids": ["S001"],
            }
            (target / "source-ledger.jsonl").write_text(json.dumps(source) + "\n", encoding="utf-8")
            (target / "claim-ledger.jsonl").write_text(json.dumps(claim) + "\n", encoding="utf-8")
            (target / "notes" / "S001.md").write_text(
                "# S001 Evidence\n\nThis substantive evidence note identifies the source, bounded assertion, scope, "
                "location, access context, limitations, and the exact claim supported. It records enough detail for an "
                "independent reviewer to distinguish direct support from broader inference or unsupported causation.",
                encoding="utf-8",
            )
            completed_text = (
                "This evidence-backed artifact records a bounded finding, the applicable scope, the retained support, "
                "the remaining limitation, and the decision boundary that prevents broader inference. "
            )
            for name, (minimum_words, _) in campaign_tool.COMPLETE_ARTIFACTS.items():
                repetitions = max(2, minimum_words // len(completed_text.split()) + 2)
                content = (completed_text * repetitions).strip() + "\n"
                if name == "report.md":
                    content += "The bounded test claim is supported. [S001]\n"
                (target / name).write_text(content, encoding="utf-8")

            audit = citation_tool.audit(target)
            self.assertEqual(audit["result"], "pass")
            (target / "citation-audit-structural.json").write_text(
                json.dumps(audit, indent=2) + "\n", encoding="utf-8"
            )
            campaign = json.loads((target / "campaign.json").read_text(encoding="utf-8"))
            campaign["phase"] = "complete"
            campaign["status"] = "complete"
            campaign["counters"].update({
                "discovered": 1,
                "inspected": 1,
                "opened": 1,
                "deeply_read": 1,
                "cited": 1,
            })
            (target / "campaign.json").write_text(json.dumps(campaign) + "\n", encoding="utf-8")

            self.assertEqual(campaign_tool.validate(target), [])

    def test_citation_audit_rejects_empty_evidence_note(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            source = {
                "id": "S001",
                "url": "https://example.test/source",
                "states": ["discovered", "inspected", "opened", "deeply-read", "cited"],
            }
            claim = {"id": "C001", "claim": "Consequential claim", "importance": "consequential", "source_ids": ["S001"]}
            (target / "source-ledger.jsonl").write_text(json.dumps(source) + "\n", encoding="utf-8")
            (target / "claim-ledger.jsonl").write_text(json.dumps(claim) + "\n", encoding="utf-8")
            (target / "notes" / "S001.md").write_text("# Evidence\n", encoding="utf-8")
            (target / "report.md").write_text("Unsupported consequential claim. [S001]\n", encoding="utf-8")
            result = citation_tool.audit(target)
            self.assertEqual(result["result"], "fail")
            self.assertTrue(any("substantive evidence note" in item for item in result["errors"]))

    def test_validator_rejects_counter_ledger_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            source = {"id": "S001", "url": "https://example.test/source", "states": ["discovered"]}
            (target / "source-ledger.jsonl").write_text(json.dumps(source) + "\n", encoding="utf-8")
            errors = campaign_tool.validate(target)
            self.assertTrue(any("counter discovered=0 does not match ledger count 1" in item for item in errors))

    def test_validator_rejects_impossible_source_state(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            source = {"id": "S001", "url": "https://example.test/source", "states": ["deeply-read", "cited"]}
            (target / "source-ledger.jsonl").write_text(json.dumps(source) + "\n", encoding="utf-8")
            errors = campaign_tool.validate(target)
            self.assertTrue(any("missing prerequisite states" in item for item in errors))

    def test_validator_rejects_template_complete_campaign(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            campaign = json.loads((target / "campaign.json").read_text(encoding="utf-8"))
            campaign["phase"] = "complete"
            campaign["status"] = "partial-success"
            (target / "campaign.json").write_text(json.dumps(campaign) + "\n", encoding="utf-8")
            errors = campaign_tool.validate(target)
            self.assertTrue(any("still contains template instructions" in item for item in errors))

    def test_assembly_orders_sections_and_reports_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_campaign(Path(temp))
            (target / "draft" / "02-second.md").write_text("# Second\nBeta", encoding="utf-8")
            (target / "draft" / "01-first.md").write_text("# First\nAlpha", encoding="utf-8")
            result = assembly_tool.assemble(target)
            report = (target / "report.md").read_text(encoding="utf-8")
            self.assertLess(report.index("# First"), report.index("# Second"))
            self.assertEqual(result["sections"], 2)


if __name__ == "__main__":
    unittest.main()

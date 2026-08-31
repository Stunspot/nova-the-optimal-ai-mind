from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from build_release import build
from release_lib import deterministic_zip, files, sha256_file, tree_digest
from verify_package import verify


class VerifierAdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="nova-free-adversarial-")
        base = Path(cls._temporary.name)
        result = build(REPO, base / "dist", base / "release", False)
        cls.pristine = Path(str(result["package_root"]))
        cls.cases = base / "cases"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()

    def clone(self, name: str) -> Path:
        target = self.cases / name
        shutil.copytree(self.pristine, target)
        return target

    def assert_finding(self, result: dict[str, object], phrase: str) -> None:
        self.assertEqual(result["verdict"], "FAIL", result)
        rendered = "\n".join(str(item) for item in result["findings"])
        self.assertIn(phrase, rendered)

    def rewrite_checksums(self, package: Path) -> None:
        checksum = package / "SHA256SUMS.txt"
        rows = [
            f"{sha256_file(path)}  {path.relative_to(package).as_posix()}"
            for path in files(package)
            if path != checksum
        ]
        checksum.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")

    def test_duplicate_and_traversal_checksum_rows_are_rejected(self) -> None:
        package = self.clone("malformed-checksum-paths")
        checksum = package / "SHA256SUMS.txt"
        rows = checksum.read_text(encoding="utf-8").splitlines()
        readme_digest = sha256_file(package / "README.md")
        rows.extend((rows[0], f"{readme_digest}  docs/../README.md"))
        checksum.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
        result = verify(package)
        self.assert_finding(result, "duplicate checksum path")
        rendered = "\n".join(str(item) for item in result["findings"])
        self.assertIn("invalid checksum path", rendered)

    def test_omitted_checksum_row_is_rejected(self) -> None:
        package = self.clone("omitted-checksum-row")
        checksum = package / "SHA256SUMS.txt"
        rows = [
            line
            for line in checksum.read_text(encoding="utf-8").splitlines()
            if not line.endswith("  README.md")
        ]
        checksum.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "checksum inventory differs")

    def test_synchronized_payload_drift_is_rejected_by_source_lock(self) -> None:
        package = self.clone("synchronized-payload-drift")
        skill_id = "promptcraft"
        codex_plugin = package / "codex" / "plugins" / "nova-the-optimal-ai"
        claude_plugin = package / "claude" / "nova-the-optimal-ai"
        folder = package / "claude" / "folders" / skill_id
        original = (codex_plugin / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")
        drifted = original + "\ncoordinated but unauthorized drift\n"
        for target in (
            codex_plugin / "skills" / skill_id / "SKILL.md",
            claude_plugin / "skills" / skill_id / "SKILL.md",
            folder / "SKILL.md",
        ):
            target.write_text(drifted, encoding="utf-8", newline="\n")

        zip_path = package / "claude" / "zips" / f"{skill_id}-3.1.0.zip"
        zip_sha = deterministic_zip(folder, zip_path, prefix=skill_id)
        manifest_path = package / "RELEASE-MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        record = next(item for item in manifest["skills"] if item["id"] == skill_id)
        record["payload_tree"] = tree_digest(codex_plugin / "skills" / skill_id)
        record["claude_zip_sha256"] = zip_sha
        manifest["host_trees"]["codex_plugin"] = tree_digest(codex_plugin)
        manifest["host_trees"]["claude_plugin"] = tree_digest(claude_plugin)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.rewrite_checksums(package)

        self.assert_finding(verify(package), f"source-lock skill tree mismatch: {skill_id}")

    def test_missing_skill_root_is_rejected(self) -> None:
        package = self.clone("missing-skill")
        shutil.rmtree(package / "codex" / "plugins" / "nova-the-optimal-ai" / "skills" / "promptcraft")
        self.assert_finding(verify(package), "codex roots differ")

    def test_host_skill_drift_is_rejected(self) -> None:
        package = self.clone("host-drift")
        target = package / "claude" / "nova-the-optimal-ai" / "skills" / "promptcraft" / "SKILL.md"
        target.write_text(target.read_text(encoding="utf-8") + "\nunsafe drift\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "Codex/Claude bytes differ for promptcraft")

    def test_broken_customer_reference_is_rejected(self) -> None:
        package = self.clone("broken-doc-link")
        target = package / "README.md"
        target.write_text(target.read_text(encoding="utf-8") + "\n[Missing guide](docs/NOT-HERE.md)\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "broken customer Markdown reference README.md")

    def test_codex_state_fallback_is_rejected(self) -> None:
        package = self.clone("state-fallback")
        target = package / "codex" / "plugins" / "nova-the-optimal-ai" / "skills" / "corkboard" / "scripts" / "corkboard.py"
        target.write_text(target.read_text(encoding="utf-8") + "\n# CODEX_HOME fallback\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "Stateful service retains CODEX_HOME fallback")

    def test_premature_candidate_seal_is_rejected(self) -> None:
        package = self.clone("premature-seal")
        target = package / "codex" / "BUILD-MANIFEST.json"
        value = json.loads(target.read_text(encoding="utf-8"))
        value["sealed_candidate"] = True
        target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "prematurely seals the candidate")

    def test_missing_standalone_rights_file_is_rejected(self) -> None:
        package = self.clone("missing-rights")
        target = package / "claude" / "folders" / "promptcraft" / "nova-free-rights" / "LICENSE.md"
        target.unlink()
        self.assert_finding(verify(package), "standalone rights envelope missing for promptcraft: LICENSE.md")

    def test_missing_component_notice_bundle_is_rejected(self) -> None:
        package = self.clone("missing-component-notice")
        target = package / "claude" / "folders" / "software-verification" / "nova-free-rights" / "component-notices" / "testforge"
        shutil.rmtree(target)
        self.assert_finding(verify(package), "standalone component notice missing for software-verification")

    def test_stale_component_license_metadata_is_rejected(self) -> None:
        package = self.clone("stale-component-rights")
        target = package / "codex" / "plugins" / "nova-the-optimal-ai" / "skills" / "answerlayer" / "manifest.json"
        value = json.loads(target.read_text(encoding="utf-8"))
        value["license"] = "Proprietary"
        value["rights_status"] = "private"
        target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "AnswerLayer rights metadata is not reconciled for Nova Free")

    def test_external_rights_blocker_is_rejected(self) -> None:
        package = self.clone("external-blocker")
        target = package / "RELEASE-MANIFEST.json"
        value = json.loads(target.read_text(encoding="utf-8"))
        value["rights"]["external_rights_blockers"] = ["invented blocker"]
        target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "release manifest still contains external rights blockers")

    def test_false_redistribution_state_is_rejected(self) -> None:
        package = self.clone("rights-overclaim")
        target = package / "RELEASE-MANIFEST.json"
        value = json.loads(target.read_text(encoding="utf-8"))
        value["rights"]["redistribution_state"] = "ready"
        target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "does not preserve the approved redistribution state")

    def test_publication_overclaim_is_rejected(self) -> None:
        package = self.clone("publication-overclaim")
        target = package / "RELEASE-MANIFEST.json"
        value = json.loads(target.read_text(encoding="utf-8"))
        value["publication_state"] = "published"
        target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
        self.assert_finding(verify(package), "release manifest overclaims publication")


if __name__ == "__main__":
    unittest.main()

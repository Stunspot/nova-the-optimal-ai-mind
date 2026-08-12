from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_release.py"
OUTPUTS = (
    ROOT / "dist",
    ROOT / "release" / "nova-mind-free-v2.0.8.zip",
    ROOT / "release" / "nova-mind-free-v2.0.8.zip.sha256",
    ROOT / "release" / "nova-mind-free-v2.0.8.build-receipt.json",
)


def digest(path: Path) -> str | None:
    if not path.exists():
        return None
    sha = hashlib.sha256()
    files = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
    for item in files:
        relative = item.name if path.is_file() else item.relative_to(path).as_posix()
        sha.update(relative.encode("utf-8"))
        sha.update(b"\0")
        sha.update(hashlib.sha256(item.read_bytes()).digest())
    return sha.hexdigest()


class ReleaseBuilderCliTests(unittest.TestCase):
    def test_help_is_non_mutating(self) -> None:
        before = {str(path): digest(path) for path in OUTPUTS}
        result = subprocess.run(
            [sys.executable, "-B", str(BUILDER), "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        after = {str(path): digest(path) for path in OUTPUTS}
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertEqual(before, after)

    def test_builder_requires_committed_tracked_source(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('"--untracked-files=no"', text)
        self.assertIn("tracked source changes must be committed", text)
        self.assertIn('parser.add_argument(\n        "--replace"', text)
        self.assertIn('"source_revision": revision', text)
        self.assertIn('"source_material_sha256": source_digest', text)

    def test_builder_derives_the_customer_archive_mind_link(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn(
            'source_mind_link = "plugins/augment-of-mind/README.md"',
            text,
        )
        self.assertIn(
            'packaged_mind_link = "codex/plugins/augment-of-mind/README.md"',
            text,
        )
        self.assertIn("packaged_readme_text.count(source_mind_link) != 1", text)


if __name__ == "__main__":
    unittest.main()

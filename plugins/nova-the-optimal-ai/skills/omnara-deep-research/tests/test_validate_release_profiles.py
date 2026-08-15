from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_release import RUNTIME_REQUIRED, validate

ROOT = Path(__file__).resolve().parents[1]


class ReleaseValidatorProfileTests(unittest.TestCase):
    def test_source_profile_validates_repository(self) -> None:
        errors, _, profile = validate(ROOT, "source")
        self.assertEqual(profile, "source")
        self.assertEqual(errors, [])

    def test_runtime_profile_validates_only_shipped_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "omnara-deep-research"
            for relative in RUNTIME_REQUIRED:
                source = ROOT / relative
                target = runtime / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            errors, _, profile = validate(runtime, "runtime")
            self.assertEqual(profile, "runtime")
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
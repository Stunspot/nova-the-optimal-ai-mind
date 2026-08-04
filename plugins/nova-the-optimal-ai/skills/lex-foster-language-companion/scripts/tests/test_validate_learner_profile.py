import copy
import json
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from validate_learner_profile import validate_profile


class LearnerProfileValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = json.loads(
            (SKILL_ROOT / "assets" / "learner-profile.template.json").read_text(
                encoding="utf-8"
            )
        )

    def test_template_is_valid(self):
        self.assertEqual(validate_profile(self.valid), [])

    def test_unknown_retrieval_reference_is_rejected(self):
        profile = copy.deepcopy(self.valid)
        profile["retrieval_queue"][0]["evidence_id"] = "missing"
        self.assertTrue(
            any("unknown evidence" in error for error in validate_profile(profile))
        )

    def test_duplicate_evidence_id_is_rejected(self):
        profile = copy.deepcopy(self.valid)
        profile["evidence"].append(copy.deepcopy(profile["evidence"][0]))
        self.assertTrue(
            any("duplicate evidence id" in error for error in validate_profile(profile))
        )

    def test_unsupported_mastery_label_is_rejected(self):
        profile = copy.deepcopy(self.valid)
        profile["evidence"][0]["state"] = "mastered"
        self.assertTrue(
            any("state must be one of" in error for error in validate_profile(profile))
        )

    def test_sparse_but_well_formed_profile_is_valid(self):
        profile = copy.deepcopy(self.valid)
        profile["goals"] = []
        profile["evidence"] = []
        profile["retrieval_queue"] = []
        self.assertEqual(validate_profile(profile), [])


if __name__ == "__main__":
    unittest.main()

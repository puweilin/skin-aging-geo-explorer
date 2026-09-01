import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from relevance_filter import assess_relevance


class GoldSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (REPO_ROOT / "tests" / "fixtures" / "relevance_gold_set.json").open(
            "r", encoding="utf-8"
        ) as handle:
            cls.records = json.load(handle)
        with (REPO_ROOT / "data" / "manual_curation_overrides.json").open(
            "r", encoding="utf-8"
        ) as handle:
            raw_overrides = json.load(handle)
        cls.overrides = {}
        for decision in ("include", "exclude"):
            for accession in raw_overrides.get(decision, {}):
                cls.overrides[accession] = decision

    def test_gold_set_has_stratified_120_records(self):
        self.assertEqual(len(self.records), 120)
        expected = [item["Expected_Decision"] for item in self.records]
        self.assertEqual(expected.count("include"), 60)
        self.assertEqual(expected.count("exclude"), 60)

    def test_final_decisions_match_gold_set(self):
        mismatches = []
        true_positive = false_positive = false_negative = 0
        for record in self.records:
            automated = assess_relevance(record).decision
            predicted = self.overrides.get(record["Accession"], automated)
            expected = record["Expected_Decision"]
            if predicted != expected:
                mismatches.append((record["Accession"], expected, predicted))
            if predicted == "include" and expected == "include":
                true_positive += 1
            elif predicted == "include" and expected != "include":
                false_positive += 1
            elif predicted != "include" and expected == "include":
                false_negative += 1

        precision = true_positive / max(1, true_positive + false_positive)
        recall = true_positive / max(1, true_positive + false_negative)
        self.assertGreaterEqual(precision, 0.95)
        self.assertGreaterEqual(recall, 0.90)
        self.assertEqual(mismatches, [])


if __name__ == "__main__":
    unittest.main()

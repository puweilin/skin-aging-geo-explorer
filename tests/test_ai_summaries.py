import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_ai_summaries import (
    accession_sequence,
    build_prompt,
    clean_summary,
    is_formally_included,
    needs_summary,
)


class AISummaryTests(unittest.TestCase):
    def test_only_formally_included_records_are_eligible(self):
        included = {
            "Accession": "GSE1",
            "Relevance_Final_Decision": "include",
            "AI_Summary_CN": "",
        }
        excluded = {
            "Accession": "GSE2",
            "Relevance_Final_Decision": "exclude",
            "AI_Summary_CN": "",
        }
        self.assertTrue(is_formally_included(included))
        self.assertTrue(needs_summary(included))
        self.assertFalse(needs_summary(excluded))

    def test_existing_summary_is_not_regenerated_without_force(self):
        record = {
            "Accession": "GSE1",
            "Relevance_Final_Decision": "include",
            "AI_Summary_CN": "这是一个已经生成且足够长的中文摘要。",
        }
        self.assertFalse(needs_summary(record))
        self.assertTrue(needs_summary(record, force=True))

    def test_deprecated_record_is_not_eligible(self):
        record = {
            "Accession": "GSE3",
            "Relevance_Final_Decision": "include",
            "Curation_Status": "deprecated",
            "AI_Summary_CN": "",
        }
        self.assertFalse(needs_summary(record))

    def test_prompt_forbids_relevance_redecision(self):
        prompt = build_prompt({
            "Accession": "GSE1",
            "Title": "Aging human skin",
            "Summary": "Young and old skin were compared.",
            "Overall_Design": "RNA-seq of skin biopsies.",
            "Relevance_Final_Decision": "include",
        })
        self.assertIn("不要重新判断纳入或排除", prompt)
        self.assertIn("GSE1", prompt)
        self.assertIn("RNA-seq of skin biopsies", prompt)

    def test_clean_summary_removes_reasoning_and_prefix(self):
        value = (
            "<think>internal reasoning</think>\n"
            "摘要：该研究比较年轻与老年供者皮肤活检的转录组，"
            "用于刻画年龄相关表达变化。"
        )
        cleaned = clean_summary(value)
        self.assertNotIn("think", cleaned)
        self.assertFalse(cleaned.startswith("摘要"))
        self.assertIn("年轻与老年", cleaned)

    def test_accession_sequence_rejects_duplicates(self):
        with self.assertRaises(ValueError):
            accession_sequence([
                {"Accession": "GSE1"},
                {"Accession": "GSE1"},
            ])


if __name__ == "__main__":
    unittest.main()

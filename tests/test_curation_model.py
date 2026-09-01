import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from curation_model import (
    apply_corpus_model,
    classify_data_type,
    extract_pubmed_ids,
    normalize_dataset_record,
)


class CurationModelTests(unittest.TestCase):
    def test_pubmed_entrez_repr_is_normalized(self):
        value = "IntegerElement(41530151, attributes={})"
        self.assertEqual(extract_pubmed_ids(value), ["41530151"])

    def test_scatac_precedes_generic_single_cell(self):
        result = classify_data_type(
            "Genome binding/occupancy profiling by high throughput sequencing",
            "Single cell analysis of open chromatin [scATAC-Seq]",
            "Single-cell ATAC sequencing of aged hair follicle stem cells.",
        )
        self.assertEqual(result, "scATAC-seq")

    def test_normalization_adds_multidimensional_metadata(self):
        record = normalize_dataset_record({
            "Accession": "GSE1",
            "Title": "Photoaging in human skin",
            "Organism": "Homo sapiens",
            "GEO_DataSet_Type": "Expression profiling by high throughput sequencing",
            "Summary": "Chronic UVB exposure alters collagen and inflammation.",
            "Overall_Design": "Young human skin biopsies, UVB and sham control.",
            "Sample_Count": 6,
            "Platform": "GPL1",
            "Country": "USA",
            "PubMed_IDs": "12345678",
            "Relevance_Evidence": {"age_contrast": ["photoaging_model"]},
        })
        self.assertEqual(record["Primary_Scope_Category"], "photoaging")
        self.assertIn("photoaging", record["Aging_Contexts"])
        self.assertIn("extracellular_matrix", record["Biological_Processes"])
        self.assertEqual(record["Dataset_Role"], "primary")

    def test_shared_pubmed_builds_one_study_family(self):
        records, families = apply_corpus_model([
            {
                "Accession": "GSE100",
                "Title": "Aging human skin [RNA-seq]",
                "Organism": "Homo sapiens",
                "Data_Type": "bulk RNA-seq",
                "Sample_Count": 6,
                "PubMed_IDs": "12345678",
                "Summary": "Young and old skin.",
                "Overall_Design": "Skin biopsies from young and old donors.",
                "Relevance_Evidence": {"age_contrast": ["young_vs_old"]},
            },
            {
                "Accession": "GSE101",
                "Title": "Aging human skin [ATAC-seq]",
                "Organism": "Homo sapiens",
                "Data_Type": "ATAC-seq",
                "Sample_Count": 6,
                "PubMed_IDs": "12345678",
                "Summary": "Young and old skin.",
                "Overall_Design": "Chromatin accessibility in young and old skin.",
                "Relevance_Evidence": {"age_contrast": ["young_vs_old"]},
            },
        ])
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0]["Dataset_Count"], 2)
        self.assertEqual(records[0]["Study_Family_ID"], records[1]["Study_Family_ID"])


if __name__ == "__main__":
    unittest.main()

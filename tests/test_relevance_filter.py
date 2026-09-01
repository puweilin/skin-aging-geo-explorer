import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from relevance_filter import assess_relevance, stage1_candidate


class SkinAgingRelevanceTests(unittest.TestCase):
    def test_includes_human_aged_skin(self):
        result = assess_relevance({
            "Title": "Transcriptional Profile of Aging in Healthy Human Skin",
            "Summary": "Gene expression was profiled in non sun-exposed skin from men aged 19-86.",
            "Overall_Design": "Skin biopsies from young and old donors were analyzed by microarray.",
        })
        self.assertEqual(result.decision, "include")

    def test_includes_single_cell_aging_skin(self):
        result = assess_relevance({
            "Title": "Single-cell transcriptomes of the aging human skin",
            "Summary": "Single-cell RNA sequencing compared sun-protected skin from young and old donors.",
            "Overall_Design": "Skin samples from three young and three old donors.",
        })
        self.assertEqual(result.decision, "include")

    def test_includes_photoaging_model(self):
        result = assess_relevance({
            "Title": "Retinoids in UVR-induced skin photoaging",
            "Summary": "Spatial transcriptomics measured treatment effects in photoaged skin.",
            "Overall_Design": "Chronic UVR photoaging mouse skin with control and treatment groups.",
        })
        self.assertEqual(result.decision, "include")
        self.assertEqual(result.scope_category, "photoaging")

    def test_includes_dermal_fibroblast_senescence(self):
        result = assess_relevance({
            "Title": "Replicative senescence in human dermal fibroblasts",
            "Summary": "RNA-seq characterized proliferating and senescent dermal fibroblasts.",
            "Overall_Design": "Primary dermal fibroblasts at early and late population doublings.",
        })
        self.assertEqual(result.decision, "include")

    def test_excludes_ovarian_aging(self):
        result = assess_relevance({
            "Title": "Ovarian follicle aging",
            "Summary": "Young and old mouse ovaries were sequenced.",
            "Overall_Design": "Oocytes and granulosa cells from aged ovaries.",
        })
        self.assertEqual(result.decision, "exclude")
        self.assertFalse(result.stage1_pass)

    def test_excludes_neural_disease_using_skin_fibroblasts(self):
        result = assess_relevance({
            "Title": "Parkinson disease neurons derived from patient fibroblasts",
            "Summary": "Skin fibroblasts from young and old patients were reprogrammed into iPSCs.",
            "Overall_Design": "iPSC-derived dopaminergic neurons were sequenced.",
        })
        self.assertEqual(result.decision, "exclude")

    def test_excludes_skin_cancer_without_aging_design(self):
        result = assess_relevance({
            "Title": "Age-related signatures in cutaneous melanoma",
            "Summary": "Melanoma tumors were profiled to identify prognostic genes.",
            "Overall_Design": "Primary and metastatic melanoma tumor samples.",
        })
        self.assertEqual(result.decision, "exclude")

    def test_reviews_progeria_dermal_fibroblasts(self):
        result = assess_relevance({
            "Title": "Premature aging in Hutchinson-Gilford progeria",
            "Summary": "Transcriptomes of patient dermal fibroblasts were analyzed.",
            "Overall_Design": "Dermal fibroblasts from HGPS patients and healthy controls.",
        })
        self.assertEqual(result.decision, "review")

    def test_stage1_requires_skin_and_aging(self):
        self.assertFalse(stage1_candidate({
            "Title": "Aging of the mouse kidney",
            "Summary": "Old and young kidneys.",
        }))
        self.assertFalse(stage1_candidate({
            "Title": "Human skin barrier",
            "Summary": "Keratinocyte differentiation.",
        }))

    def test_rejects_single_neonatal_age_as_aged_skin(self):
        result = assess_relevance({
            "Title": "Melanocytes from 3-day old skin",
            "Summary": "Wild-type and mutant melanocytes were compared.",
            "Overall_Design": "Melanocytes isolated from the skin of newborn mice.",
        })
        self.assertEqual(result.decision, "exclude")
        self.assertFalse(result.stage1_pass)

    def test_design_overrides_unrelated_summary_reference(self):
        result = assess_relevance({
            "Title": "Transcription elongation during cellular senescence",
            "Summary": "Published dermal fibroblast studies are discussed as aging context.",
            "Overall_Design": "RNA-seq of DLD-1 colorectal cancer cells.",
        })
        self.assertEqual(result.decision, "exclude")

    def test_rejects_skin_fibroblast_conversion_for_bone_repair(self):
        result = assess_relevance({
            "Title": "Rejuvenation and conversion of skin fibroblasts for bone repair",
            "Summary": "Skin fibroblasts were converted into MSC-like cells for cartilage repair.",
            "Overall_Design": "RNA-seq of converted MSC-like cells.",
        })
        self.assertEqual(result.decision, "exclude")

    def test_rejects_chondrocyte_assay_with_skin_aging_title(self):
        result = assess_relevance({
            "Title": "Aged skin exacerbates osteoarthritis",
            "Summary": "Skin aging conditioned medium was used to model OA.",
            "Overall_Design": "RNA-seq of control and treated articular chondrocytes.",
            "Sample_Titles": "Control CCs; aging SNL CCs",
        })
        self.assertEqual(result.decision, "exclude")

    def test_rejects_oral_keratinocyte_senescence(self):
        result = assess_relevance({
            "Title": "Senescence in human oral keratinocytes",
            "Summary": "RNA-seq and secretome analysis of senescent oral cells.",
            "Overall_Design": "Proliferating and senescent oral keratinocytes.",
        })
        self.assertEqual(result.decision, "exclude")

    def test_oral_administration_does_not_mean_oral_tissue(self):
        result = assess_relevance({
            "Title": "Single-cell transcriptomics of aged human epidermis",
            "Summary": "Young and old epidermal keratinocytes were compared.",
            "Overall_Design": "Skin samples from young and old women; none used oral contraceptives.",
        })
        self.assertEqual(result.decision, "include")

    def test_includes_skin_assay_in_cross_tissue_disease_study(self):
        result = assess_relevance({
            "Title": "Aged skin exacerbates experimental osteoarthritis",
            "Summary": "The study tests skin aging as a driver of disease.",
            "Overall_Design": "RNA-seq of epidermal skin tissues from control and conditional knockout mice.",
            "Sample_Titles": "epidermal skin control; epidermal skin knockout",
        })
        self.assertEqual(result.decision, "include")

    def test_includes_photoaging_mechanism_with_direct_skin_cells(self):
        result = assess_relevance({
            "Title": "UV response in primary human dermal fibroblasts",
            "Summary": "We examined expression changes to identify photoaging-related genes.",
            "Overall_Design": "Primary human dermal fibroblasts exposed to UV and sham control.",
        })
        self.assertEqual(result.decision, "include")

    def test_includes_skin_derived_fibroblast_senescence(self):
        result = assess_relevance({
            "Title": "Nrf2 induces a senescence-associated secretory phenotype",
            "Summary": "Fibroblast senescence was profiled by RNA sequencing.",
            "Overall_Design": "Fibroblasts isolated from mouse skin, mutant versus control.",
        })
        self.assertEqual(result.decision, "include")

    def test_rejects_embryonic_skin_development(self):
        result = assess_relevance({
            "Title": "Defective epidermal stratification",
            "Summary": "The introduction discusses stem-cell senescence during skin aging.",
            "Overall_Design": "RNA-seq of E15.5 embryonic back skin.",
        })
        self.assertEqual(result.decision, "exclude")


if __name__ == "__main__":
    unittest.main()

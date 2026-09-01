#!/usr/bin/env python3
"""Schema normalization and study-level grouping for Skin Aging GEO v2."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "2.0.0"
CURATION_VERSION = "2026-09-01"


def _compact(*values: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        " ".join(str(value or "") for value in values),
    ).strip()


def extract_pubmed_ids(value: Any) -> list[str]:
    """Return stable numeric PMIDs from Entrez objects, strings, or lists."""

    if value is None:
        return []
    values: Iterable[Any]
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]

    identifiers: set[str] = set()
    for item in values:
        try:
            numeric = str(int(item))
            if 5 <= len(numeric) <= 9:
                identifiers.add(numeric)
                continue
        except (TypeError, ValueError, OverflowError):
            pass
        for match in re.findall(r"(?<!\d)(\d{5,9})(?!\d)", str(item)):
            identifiers.add(match)
    return sorted(identifiers, key=int)


def normalize_pubmed_ids(value: Any) -> str:
    return "; ".join(extract_pubmed_ids(value))


def classify_data_type(
    gds_type: Any,
    title: Any,
    summary: Any,
    overall_design: Any = "",
) -> str:
    """Classify modality with specific single-cell assays before generic scRNA."""

    text = _compact(gds_type, title, summary, overall_design).lower()
    has_atac = bool(re.search(
        r"\b(?:scatac|snatac|atac[\s-]?seq|chromatin accessibility|open chromatin)\b",
        text,
    ))
    has_rna = bool(re.search(r"\b(?:rna[\s-]?seq|transcriptom\w*)\b", text))

    if re.search(r"spatial[\s-]+transcriptom|visium|slide[\s-]?seq|geomx|merfish|seqfish", text):
        return "spatial transcriptomics"
    if has_atac and has_rna and re.search(r"multiome|paired.{0,30}(?:rna|atac)", text):
        return "single-cell multiome"
    if re.search(
        r"\b(?:scatac|snatac)\b|single[\s-]+(?:cell|nucleus).{0,50}"
        r"(?:atac|chromatin accessibility|open chromatin)",
        text,
    ):
        return "scATAC-seq"
    if re.search(
        r"single[\s-]?(?:cell|nucleus)|\b(?:scrna|snrna)\b|10x[\s-]+genomics",
        text,
    ):
        return "scRNA-seq"
    if re.search(r"methylation|methylome|bisulfite|\bwgbs\b|\brrbs\b", text):
        return "DNA methylation"
    if has_atac:
        return "ATAC-seq"
    if re.search(r"\bchip[\s-]?(?:seq|chip)\b|cut&run|cut&tag|genome binding", text):
        return "ChIP/CUT&RUN"
    if re.search(r"non-coding rna|\bmirna\b|microrna|\blncrna\b|small rna", text):
        return "miRNA/ncRNA profiling"
    if re.search(r"protein profiling", str(gds_type), re.I) or re.search(r"mass spectrom", text):
        return "proteomics"
    if re.search(r"16s[\s-]+rrna|microbiome|metagenom", text):
        return "microbiome"
    if "expression profiling by array" in text or "microarray" in text:
        return "expression microarray"
    if re.search(r"high throughput sequencing|rna[\s-]?seq|transcriptom", text):
        return "bulk RNA-seq"
    if "sage" in text:
        return "SAGE"
    return str(gds_type or "Other")


def clean_study_title(value: Any) -> str:
    title = _compact(value)
    title = re.sub(
        r"\s*\[(?:rna|scrna|snrna|atac|scatac|chip|cut&run|wgbs|"
        r"methylation|spatial|mirna|lncrna|bulk|dataset|ds\d+)[^\]]*\]\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\s+", " ", title).strip(" .-_")
    return title


def _title_key(value: Any) -> str:
    title = clean_study_title(value).lower()
    return re.sub(r"[^a-z0-9]+", " ", title).strip()


def _matches(text: str, patterns: Mapping[str, str]) -> list[str]:
    return [
        label
        for label, pattern in patterns.items()
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    ]


def classify_dimensions(record: Mapping[str, Any]) -> dict[str, Any]:
    title = str(record.get("Title", ""))
    summary = str(record.get("Summary", ""))
    design = str(record.get("Overall_Design", ""))
    sample_titles = str(record.get("Sample_Titles", ""))
    combined = _compact(title, summary, design, sample_titles)
    decisive = _compact(title, design, sample_titles)

    contexts = _matches(combined, {
        "photoaging": (
            r"photo[\s-]?(?:aging|ageing)|photoaged|solar elastosis|actinic lentigines|"
            r"(?:chronic|repeated)[\s-]+uv\w*"
        ),
        "cellular_senescence": r"senescen\w*|\bsasp\b|replicative[\s-]+lifespan|\bsips\b",
        "rejuvenation_intervention": r"rejuvenat\w*|senolytic\w*|anti[\s-]?ag(?:e|ing|eing)\w*",
        "aged_skin_repair": r"(?:aged|aging|ageing).{0,100}(?:wound|healing|repair)|(?:wound|healing|repair).{0,100}(?:aged|aging|ageing)",
        "skin_appendage_aging": r"hair[\s-]+gr[ae]ying|hair[\s-]+thinning|(?:hair[\s-]+follicle|sebaceous|dermal[\s-]+white[\s-]+adipose).{0,100}(?:aged|aging|ageing)|(?:aged|aging|ageing).{0,100}(?:hair[\s-]+follicle|sebaceous|dermal[\s-]+white[\s-]+adipose)",
        "exposome_aging": r"(?:smok\w*|pollution|particulate|glycat\w*|infrared).{0,120}(?:skin[\s-]+)?(?:aged|aging|ageing|senescen\w*)",
        "premature_aging_model": r"\bhgps\b|progeria|werner[\s-]+syndrome|hutchinson[\s-]+gilford|premature[\s-]+ag(?:e|ing|eing)",
        "intrinsic_skin_aging": r"chronological[\s-]+(?:skin[\s-]+)?ag(?:e|ing|eing)|intrinsic[\s-]+(?:skin[\s-]+)?ag(?:e|ing|eing)|young.{0,100}(?:old|aged)|(?:old|aged).{0,100}young|skin[\s-]+ag(?:e|ing|eing)",
    })
    if not contexts:
        contexts = ["intrinsic_skin_aging"]

    processes = _matches(combined, {
        "extracellular_matrix": r"extracellular[\s-]+matrix|\becm\b|collagen|elastin|matrix metalloprote",
        "barrier_homeostasis": r"skin[\s-]+barrier|epidermal[\s-]+barrier|transepidermal|homeostasis",
        "immune_inflammation": r"inflamm\w*|immune|macrophage|interleukin|\bil[\s-]?17\b|nf[\s-]?κ?b",
        "wound_repair": r"wound|healing|tissue[\s-]+repair|regenerat\w*",
        "stem_cell_aging": r"stem[\s-]+cell|stemness|progenitor",
        "pigmentation": r"pigment|melanocyte|melanin|lentigines|gr[ae]ying",
        "oxidative_dna_damage": r"oxidative|reactive oxygen|\bros\b|dna[\s-]+damage|mitochond",
        "circadian_aging": r"circadian|\bbmal1\b|clock[\s-]+gene",
        "metabolic_aging": r"metabol\w*|adipose|calori[ce][\s-]+restriction|high[\s-]+fat",
        "skin_appendage_homeostasis": r"hair[\s-]+follicle|sebaceous|pilosebaceous",
    })
    if not processes:
        processes = ["skin_homeostasis"]

    tissues = _matches(combined, {
        "epidermis": r"epiderm\w*|keratinocyte",
        "dermis": r"\bdermis\b|dermal|fibroblast",
        "whole_skin": r"skin[\s-]+(?:biops|tissue|sample|section)|whole[\s-]+skin|backskin|dorsal[\s-]+skin",
        "skin_appendage": r"hair[\s-]+follicle|sebaceous|pilosebaceous",
        "dermal_adipose": r"dermal[\s-]+(?:white[\s-]+)?adipose|\bdwat\b",
    })

    cells = _matches(combined, {
        "dermal_fibroblast": r"dermal[\s-]+fibroblast|human[\s-]+skin[\s-]+fibroblast|\bhdf\b",
        "keratinocyte": r"keratinocyte",
        "melanocyte": r"melanocyte",
        "macrophage": r"macrophage",
        "endothelial_cell": r"endothelial[\s-]+cell",
        "epidermal_stem_cell": r"epidermal[\s-]+stem[\s-]+cell",
        "hair_follicle_stem_cell": r"hair[\s-]+follicle[\s-]+stem[\s-]+cell|\bhfsc\b",
        "dermal_papilla_cell": r"dermal[\s-]+papilla[\s-]+cell|\bhfdpc\b",
        "adipocyte": r"adipocyte",
        "t_cell": r"\bt[\s-]+cells?\b|cd4\+|cd8\+",
    })

    comparisons = _matches(combined, {
        "young_vs_old": r"young.{0,100}(?:old|aged)|(?:old|aged).{0,100}young",
        "age_series": r"different[\s-]+ages|age[\s-]+range|across[\s-]+the[\s-]+lifespan|\d+(?:\s*,\s*\d+){2,}[\s-]*(?:months?|years?)",
        "senescent_vs_control": r"senescen\w*.{0,100}(?:control|proliferat|non[\s-]?senescent)|(?:control|proliferat|non[\s-]?senescent).{0,100}senescen\w*",
        "sun_exposed_vs_protected": r"sun[\s-]+exposed.{0,100}(?:protected|unexposed)|(?:protected|unexposed).{0,100}sun[\s-]+exposed",
        "uv_vs_control": r"uv[ab]?[\s-]+(?:irradiat|expos)|(?:sham|control).{0,100}uv[ab]?",
        "treatment_rescue": r"(?:treat\w*|therapy|topical|senolytic).{0,120}(?:aged|aging|ageing|senescen|photoaging)",
    })

    exposures = _matches(combined, {
        "uva": r"\buva\d?\b",
        "uvb": r"\buvb\b",
        "solar_exposure": r"sun[\s-]+exposed|solar[\s-]+radiation",
        "infrared": r"infrared|ir[\s-]?a",
        "smoking": r"cigarette|tobacco|smok\w*",
        "pollution": r"pollution|particulate[\s-]+matter|\bpm2\.5\b",
        "glycation": r"glycat\w*|advanced[\s-]+glycation",
    })

    organisms = str(record.get("Organism", ""))
    models: list[str] = []
    if re.search(r"organoid|skin[\s-]+equivalent|3d[\s-]+skin", combined, re.I):
        models.append("skin_model_3d")
    if re.search(r"ex[\s-]?vivo|skin[\s-]+explants?", combined, re.I):
        models.append("ex_vivo_skin")
    if re.search(r"primary.{0,40}(?:fibroblast|keratinocyte|melanocyte)|primary[\s-]+cells?", combined, re.I):
        models.append("primary_cell_culture")
    if "Homo sapiens" in organisms and re.search(r"biops|volunteer|donor[\s-]+skin|human[\s-]+skin", combined, re.I):
        models.append("human_tissue_in_vivo")
    if "Mus musculus" in organisms and re.search(r"mouse|mice|murine", combined, re.I):
        models.append("mouse_in_vivo")
    if re.search(r"cell[\s-]+line|immortali[sz]", combined, re.I):
        models.append("cell_line")
    if not models:
        models.append("model_unspecified")

    age_groups = _matches(combined, {
        "young": r"\byoung(?:er)?\b",
        "adult": r"\badult\b",
        "old_or_aged": r"\b(?:old(?:er)?|aged)\b",
        "senescent": r"\bsenescen\w*\b",
    })
    sexes = _matches(combined, {
        "female": r"\bfemales?\b|\bwomen\b",
        "male": r"\bmales?\b|\bmen\b",
    })
    sites = _matches(combined, {
        "face": r"facial|face[\s-]+skin|cheek|forehead",
        "forearm": r"forearm",
        "back": r"backskin|back[\s-]+skin|dorsal[\s-]+skin",
        "buttock": r"buttock|gluteal",
        "breast": r"breast[\s-]+skin",
        "scalp": r"scalp",
        "abdomen": r"abdominal[\s-]+skin|abdomen",
        "eyelid": r"eyelid",
    })

    if re.search(r"photo[\s-]?(?:aging|ageing)|photoaged", decisive, re.I):
        primary_scope = "photoaging"
    elif re.search(r"(?:wound|healing|repair)", decisive, re.I) and re.search(r"aged|aging|ageing|senescen", decisive, re.I):
        primary_scope = "aged_skin_repair"
    elif re.search(r"hair[\s-]+follicle|sebaceous|dermal[\s-]+white[\s-]+adipose", decisive, re.I) and re.search(r"aged|aging|ageing", decisive, re.I):
        primary_scope = "skin_appendage_aging"
    elif re.search(r"rejuvenat|senolytic|anti[\s-]?ag", decisive, re.I):
        primary_scope = "rejuvenation_intervention"
    elif re.search(r"senescen|\bsasp\b|\bsips\b", decisive, re.I):
        primary_scope = "cellular_senescence"
    else:
        primary_scope = "intrinsic_skin_aging"

    extension_contexts = {"skin_appendage_aging", "premature_aging_model"}
    evidence_tier = "extension" if extension_contexts.intersection(contexts) else "core"

    return {
        "Primary_Scope_Category": primary_scope,
        "Aging_Contexts": sorted(set(contexts)),
        "Biological_Processes": sorted(set(processes)),
        "Tissue_Compartments": sorted(set(tissues)),
        "Cell_Types": sorted(set(cells)),
        "Model_Systems": sorted(set(models)),
        "Comparison_Designs": sorted(set(comparisons)),
        "Exposure_Types": sorted(set(exposures)),
        "Age_Groups": sorted(set(age_groups)),
        "Sexes": sorted(set(sexes)),
        "Anatomical_Sites": sorted(set(sites)),
        "Evidence_Tier": evidence_tier,
    }


def _series_relations(record: Mapping[str, Any]) -> list[str]:
    raw = record.get("Series_Relations", [])
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, list):
        return [str(value) for value in raw if str(value).strip()]
    return []


def _series_role(record: Mapping[str, Any]) -> str:
    relations = " ".join(_series_relations(record)).lower()
    if "subseries of" in relations:
        return "subseries"
    if "superseries of" in relations:
        return "superseries"
    return "standalone"


def _dataset_role(record: Mapping[str, Any]) -> str:
    evidence = record.get("Relevance_Evidence", {})
    if isinstance(evidence, Mapping):
        if evidence.get("age_contrast") or evidence.get("intervention"):
            return "primary"
    dimensions = classify_dimensions(record)
    if dimensions["Comparison_Designs"]:
        return "primary"
    return "supporting"


def normalize_dataset_record(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized["Schema_Version"] = SCHEMA_VERSION
    normalized["Curation_Version"] = CURATION_VERSION
    normalized["Curation_Status"] = normalized.get("Curation_Status", "active")
    normalized["PubMed_IDs"] = normalize_pubmed_ids(normalized.get("PubMed_IDs"))
    normalized["Data_Type"] = classify_data_type(
        normalized.get("GEO_DataSet_Type", normalized.get("Data_Type", "")),
        normalized.get("Title", ""),
        normalized.get("Summary", ""),
        normalized.get("Overall_Design", ""),
    )
    dimensions = classify_dimensions(normalized)
    normalized.update(dimensions)
    normalized["Scope_Category"] = dimensions["Primary_Scope_Category"]
    normalized["Dataset_Role"] = _dataset_role(normalized)
    normalized["Series_Role"] = _series_role(normalized)

    completeness_fields = (
        "Title", "Organism", "Data_Type", "Sample_Count", "Platform",
        "Overall_Design", "Country", "PubMed_IDs", "Aging_Contexts",
        "Comparison_Designs",
    )
    present = sum(bool(normalized.get(field)) for field in completeness_fields)
    normalized["Metadata_Completeness"] = round(100 * present / len(completeness_fields))
    flags: list[str] = []
    if not normalized.get("PubMed_IDs"):
        flags.append("missing_pubmed")
    if not normalized.get("Overall_Design"):
        flags.append("missing_overall_design")
    if not normalized.get("Country"):
        flags.append("missing_country")
    if normalized["Dataset_Role"] == "supporting":
        flags.append("supporting_dataset_no_direct_aging_contrast")
    if ";" in str(normalized.get("Organism", "")):
        flags.append("mixed_organism_record")
    normalized["Quality_Flags"] = flags
    return normalized


class _UnionFind:
    def __init__(self, keys: Iterable[str]):
        self.parent = {key: key for key in keys}

    def find(self, key: str) -> str:
        parent = self.parent[key]
        if parent != key:
            self.parent[key] = self.find(parent)
        return self.parent[key]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _accession_number(accession: str) -> int:
    match = re.search(r"\d+", accession)
    return int(match.group()) if match else 10**12


def build_study_families(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Attach family identifiers and return study-level aggregate records."""

    accessions = [str(record["Accession"]) for record in records]
    union_find = _UnionFind(accessions)

    by_pubmed: dict[str, list[str]] = defaultdict(list)
    by_title: dict[str, list[str]] = defaultdict(list)
    record_by_id = {str(record["Accession"]): record for record in records}
    for record in records:
        accession = str(record["Accession"])
        for pubmed_id in extract_pubmed_ids(record.get("PubMed_IDs")):
            by_pubmed[pubmed_id].append(accession)
        title_key = _title_key(record.get("Title"))
        if len(title_key) >= 28:
            by_title[title_key].append(accession)
        for relation in _series_relations(record):
            for related in re.findall(r"\bGSE\d+\b", relation, re.I):
                related = related.upper()
                if related in record_by_id:
                    union_find.union(accession, related)

    for groups in (by_pubmed, by_title):
        for members in groups.values():
            for accession in members[1:]:
                union_find.union(members[0], accession)

    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        accession = str(record["Accession"])
        components[union_find.find(accession)].append(record)

    families: list[dict[str, Any]] = []
    for members in components.values():
        members.sort(key=lambda item: _accession_number(str(item["Accession"])))
        related_gses = [str(item["Accession"]) for item in members]
        pubmed_ids = sorted({
            pubmed_id
            for item in members
            for pubmed_id in extract_pubmed_ids(item.get("PubMed_IDs"))
        }, key=int)
        superseries = [
            item for item in members if item.get("Series_Role") == "superseries"
        ]
        primary_record = superseries[0] if superseries else members[0]
        title_candidates = [
            clean_study_title(item.get("Title")) for item in members
            if clean_study_title(item.get("Title"))
        ]
        family_title = min(title_candidates, key=len) if title_candidates else related_gses[0]
        if pubmed_ids:
            family_id = f"SA-PMID-{pubmed_ids[0]}"
        elif len(members) > 1:
            digest = hashlib.sha1(_title_key(family_title).encode("utf-8")).hexdigest()[:10]
            family_id = f"SA-TITLE-{digest.upper()}"
        else:
            family_id = f"SA-GSE-{re.sub(r'\D', '', related_gses[0])}"

        contexts = sorted({
            value for item in members for value in item.get("Aging_Contexts", [])
        })
        scopes = sorted({str(item.get("Primary_Scope_Category", "")) for item in members if item.get("Primary_Scope_Category")})
        data_types = sorted({str(item.get("Data_Type", "Other")) for item in members})
        organisms = sorted({str(item.get("Organism", "Unknown")) for item in members})
        evidence_tier = "core" if any(item.get("Evidence_Tier") == "core" for item in members) else "extension"

        for item in members:
            item["Study_Family_ID"] = family_id
            item["Study_Family_Title"] = family_title
            item["Related_GSEs"] = related_gses
            if len(members) > 1 and "multi_dataset_study" not in item["Quality_Flags"]:
                item["Quality_Flags"].append("multi_dataset_study")

        families.append({
            "Schema_Version": SCHEMA_VERSION,
            "Curation_Version": CURATION_VERSION,
            "Study_Family_ID": family_id,
            "Title": family_title,
            "Primary_Accession": str(primary_record["Accession"]),
            "Related_GSEs": related_gses,
            "Dataset_Count": len(members),
            "Primary_Dataset_Count": sum(item.get("Dataset_Role") == "primary" for item in members),
            "Nominal_Sample_Total": sum(int(item.get("Sample_Count", 0) or 0) for item in members),
            "Sample_Count_Interpretation": "GEO Series 名义样本数之和；尚未跨 GSE/GSM 去重",
            "Organisms": organisms,
            "Data_Types": data_types,
            "Aging_Contexts": contexts,
            "Scope_Categories": scopes,
            "Evidence_Tier": evidence_tier,
            "PubMed_IDs": pubmed_ids,
            "Submission_Date": max(str(item.get("Submission_Date", "")) for item in members),
            "GEO_Link": primary_record.get("GEO_Link", ""),
        })

    families.sort(key=lambda item: (item.get("Submission_Date", ""), item["Study_Family_ID"]), reverse=True)
    records.sort(key=lambda item: (str(item.get("Submission_Date", "")), str(item.get("Accession", ""))), reverse=True)
    return records, families


def apply_corpus_model(
    records: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized = [normalize_dataset_record(record) for record in records]
    return build_study_families(normalized)

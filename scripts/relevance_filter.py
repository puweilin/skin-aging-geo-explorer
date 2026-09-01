#!/usr/bin/env python3
"""Explainable two-stage relevance filter for the Skin Aging GEO corpus."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

from curation_model import classify_dimensions


PatternSpec = tuple[str, str]


SKIN_PATTERNS: Sequence[PatternSpec] = (
    ("skin", r"\bskin\b"),
    ("cutaneous", r"\bcutaneous\b"),
    ("epidermis", r"\bepiderm\w*\b"),
    ("dermis", r"\bderm(?:is|al)\b"),
    ("dermal_fibroblast", r"\bdermal[\s-]+fibroblasts?\b"),
    ("keratinocyte", r"\bkeratinocytes?\b"),
    ("melanocyte", r"\bmelanocytes?\b"),
    ("skin_stem_cell", r"\b(?:skin|epidermal)[\s-]+stem[\s-]+cells?\b"),
    ("skin_model", r"\b(?:skin[\s-]+equivalents?|skin[\s-]+organoids?|"
     r"full[\s-]+thickness[\s-]+skin|skin[\s-]+explants?)\b"),
    ("skin_appendage", r"\b(?:hair[\s-]+follicles?|sebaceous[\s-]+glands?|"
     r"pilosebaceous)\b"),
)


AGING_PATTERNS: Sequence[PatternSpec] = (
    ("skin_aging", r"\b(?:skin|cutaneous|dermal|epidermal)[\s-]+ag(?:e|ing|eing)\w*\b"),
    ("aged_skin", r"(?<!day[\s-])(?<!days[\s-])(?<!week[\s-])(?<!weeks[\s-])"
     r"(?<!month[\s-])(?<!months[\s-])(?<!year[\s-])(?<!years[\s-])"
     r"\b(?:aged|old|young)[\s-]+(?:human[\s-]+|mouse[\s-]+|murine[\s-]+)?"
     r"(?:skin|epidermis|dermis)\b"),
    ("photoaging", r"\b(?:photo|pho[\s-]?to)[\s-]?ag(?:e|ing|eing)\w*\b"),
    ("photoaging_phenotype", r"\b(?:actinic[\s-]+lentigines?|solar[\s-]+elastosis)\b"),
    ("skin_appendage_aging_phenotype", r"\bhair[\s-]+(?:graying|greying|thinning)\b"),
    ("chronological_aging", r"\b(?:chronological|chronologic|intrinsic|extrinsic)"
     r"[\s-]+(?:skin[\s-]+)?ag(?:e|ing|eing)\w*\b"),
    ("age_related", r"\bage[\s-]+related\b|\bage[\s-]+associated\b"),
    ("aging_generic", r"\b(?:aging|ageing)\b"),
    ("aged", r"\baged\b"),
    ("young_vs_old", r"\b(?:young(?:er)?).{0,100}\b(?:old(?:er)?|aged)\b|"
     r"\b(?:old(?:er)?|aged).{0,100}\b(?:young(?:er)?)\b"),
    ("senescence", r"\b(?:senescen\w*|senenscen\w*|senescn\w*|senecen\w*|"
     r"sips|replicative[\s-]+lifespan|sasp)\b"),
    ("rejuvenation", r"\b(?:rejuvenat\w*|anti[\s-]?ag(?:e|ing|eing)\w*|senolytic\w*)\b"),
    ("premature_aging", r"\bpremature[\s-]+ag(?:e|ing|eing)\w*\b"),
)


SAMPLE_PATTERNS: Sequence[PatternSpec] = (
    ("skin_biopsy", r"\bskin[\s-]+biops(?:y|ies)\b"),
    ("skin_punch_biopsy", r"\bskin.{0,24}\bbiops(?:y|ies)\b|"
     r"\bbiops(?:y|ies).{0,80}\bskin\b"),
    ("skin_direct", r"\b(?:human|mouse|murine|dorsal|tail|facial|aged|young|"
     r"photoaged)[\s-]+skin\b|\b(?:back[\s-]?skin|skin[\s-]+(?:from|of))\b"),
    ("skin_tissue", r"\b(?:human|mouse|murine)?[\s-]*(?:dorsal|tail|facial|"
     r"sun[\s-]+exposed|sun[\s-]+protected|non[\s-]+sun[\s-]+exposed)?"
     r"[\s-]*skin[\s-]+(?:tissues?|samples?|sections?|cells?)\b"),
    ("epidermal_sample", r"\bepiderm(?:is|al)[\s-]+(?:tissues?|samples?|cells?|"
     r"stem[\s-]+cells?)\b"),
    ("dermal_sample", r"\bderm(?:is|al)[\s-]+(?:human[\s-]+)?(?:tissues?|samples?|cells?|"
     r"fibroblasts?|endothelial[\s-]+cells?)\b"),
    ("hdf", r"\bhdfs?\b"),
    ("bj5ta", r"\bbj[\s-]?5ta\b"),
    ("skin_fibroblast", r"\bskin[\s-]+fibroblasts?\b|"
     r"\bfibroblasts?[\s-]+(?:were[\s-]+)?isolated[\s-]+from.{0,40}\bskin\b"),
    ("keratinocyte_sample", r"\b(?:primary[\s-]+(?:human[\s-]+)?)?keratinocytes?\b"),
    ("melanocyte_sample", r"\b(?:primary[\s-]+(?:human[\s-]+)?)?melanocytes?\b"),
    ("skin_model", r"\b(?:skin[\s-]+equivalents?|skin[\s-]+organoids?|"
     r"full[\s-]+thickness[\s-]+skin|skin[\s-]+explants?)\b"),
    ("skin_appendage_sample", r"\b(?:hair[\s-]+follicle|sebaceous[\s-]+gland)"
     r"[\s-]+(?:cells?|stems?[\s-]+cells?|samples?|tissues?)\b"),
    ("dermal_papilla", r"\b(?:follicle[\s-]+)?dermal[\s-]+papilla[\s-]+cells?\b|"
     r"\bhfdpcs?\b"),
    ("dermal_adipose", r"\b(?:dermal[\s-]+white[\s-]+adipose|dwat)\b"),
)


AGE_CONTRAST_PATTERNS: Sequence[PatternSpec] = (
    ("young_vs_old", r"\b(?:young(?:er)?|adult).{0,80}\b(?:old(?:er)?|aged)\b|"
     r"\b(?:old(?:er)?|aged).{0,80}\b(?:young(?:er)?|adult)\b"),
    ("age_groups", r"\b(?:age[\s-]+groups?|donor[\s-]+ages?|different[\s-]+ages?|"
     r"across[\s-]+(?:the[\s-]+)?lifespan|age[\s-]+range)\b"),
    ("age_series", r"\b\d+(?:\s*,\s*\d+)+(?:\s*(?:,|and)\s*\d+)?"
     r"[\s-]+(?:months?|years?)[\s-]+of[\s-]+age\b"),
    ("serial_ages", r"\b(?:\d+(?:\.\d+)?[\s,-]+){2,}\d+(?:\.\d+)?"
     r"[\s-]*(?:months?|years?)(?:[\s-]+old)?\b"),
    ("age_time_course", r"\b\d+(?:\.\d+)?-.{0,120}\band[\s-]+"
     r"\d+(?:\.\d+)?[\s-]*months?[\s-]+old\b"),
    ("life_stage_contrast", r"\bnewborn.{0,100}\badults?\b|"
     r"\badults?.{0,100}\bnewborn\b"),
    ("senescent_control", r"\b(?:senescen\w*|senenscen\w*|senescn\w*|"
     r"senecen\w*|sips).{0,100}"
     r"\b(?:control|proliferat\w*|quiescent|non[\s-]?senescent|young)\b|"
     r"\b(?:control|proliferat\w*|quiescent|non[\s-]?senescent|young).{0,100}"
     r"\b(?:senescen\w*|senenscen\w*|senescn\w*|senecen\w*|sips)\b"),
    ("replicative_aging", r"\b(?:replicative[\s-]+senescence|serial[\s-]+passage|"
     r"population[\s-]+doublings?|replicative[\s-]+lifespan)\b"),
    ("photoaging_model", r"\b(?:(?:photo|pho[\s-]?to)[\s-]?ag(?:e|ing|eing)\w*|"
     r"chronic[\s-]+uv\w*|"
     r"repeated[\s-]+uv\w*|uv\w*[\s-]+induced[\s-]+(?:skin[\s-]+)?"
     r"(?:aging|ageing|senescence)|uv\w*.{0,60}\b(?:daily|"
     r"consecutive[\s-]+days?|(?:for|over)[\s-]+\d+[\s-]+days?))\b"),
)


INTERVENTION_PATTERNS: Sequence[PatternSpec] = (
    ("anti_aging_intervention", r"\b(?:anti[\s-]?(?:photo[\s-]?)?ag(?:e|ing|eing)\w*|"
     r"skin[\s-]+rejuvenat\w*|senolytic\w*)\b"),
    ("aged_skin_treatment", r"\b(?:treated|treatment|therapy|topical|application|"
     r"supplement\w*).{0,100}\b(?:aged[\s-]+skin|skin[\s-]+aging|"
     r"photoag(?:e|ing|eing)\w*)\b"),
)


INCIDENTAL_PATTERNS: Sequence[PatternSpec] = (
    ("fibroblast_reprogramming", r"\b(?:skin|dermal)[\s-]+fibroblasts?.{0,140}"
     r"\b(?:induced[\s-]+pluripotent|iPSCs?|reprogrammed[\s-]+into)\b|"
     r"\b(?:induced[\s-]+pluripotent|iPSCs?|reprogramming).{0,180}"
     r"\b(?:skin|dermal)[\s-]+fibroblasts?\b"),
    ("diagnostic_cell_source", r"\b(?:patient[\s-]+derived|skin)[\s-]+fibroblasts?"
     r".{0,160}\b(?:diagnos|neurolog|muscular|mitochondrial[\s-]+disease)\w*\b"),
    ("age_covariate_only", r"\bage[\s-]+(?:and|,)[\s-]+(?:sex|gender|batch)\b"),
)


OFF_TOPIC_PATTERNS: Sequence[PatternSpec] = (
    ("reproductive", r"\b(?:ovary|ovarian|oocyte|granulosa|cumulus|follicular[\s-]+fluid|"
     r"reproductive[\s-]+aging|primordial[\s-]+follicle|testis|sperm)\w*\b"),
    ("neurologic", r"\b(?:brain|neuron|neural|parkinson|alzheimer|hippocamp|glioma)\w*\b"),
    ("renal", r"\b(?:kidney|renal|nephro|tubular)\w*\b"),
    ("hepatic", r"\b(?:liver|hepatic|hepatocyte)\w*\b"),
    ("muscle", r"\b(?:skeletal[\s-]+muscle|myoblast|myotube|muscular)\w*\b"),
    ("skeletal_repair", r"\b(?:bone|cartilage|chondrocytes?|osteoarthritis|"
     r"osteogenic|chondrogenic|synovial)\b"),
    ("blood", r"\b(?:whole[\s-]+blood|pbmcs?|hematopoietic|leukocyte)\w*\b"),
    ("lung", r"\b(?:lung|pulmonary)\w*\b"),
    ("dental", r"\b(?:dental|tooth|odontogenic)\w*\b"),
    ("oral_mucosa", r"\b(?:oral[\s-]+(?:mucosa\w*|keratinocytes?|"
     r"fibroblasts?|epitheli\w*)|gingiv\w*|buccal\w*)\b"),
    ("cancer", r"\b(?:cancer|carcinoma|melanoma|tumou?r|sarcoma|leukemia|"
     r"braf\w*|nevi|nevus|dld[\s-]?1|mcf[\s-]?7)\w*\b"),
    ("other_disease", r"\b(?:diabetic[\s-]+foot|diabetes|psorias\w*|"
     r"alopecia[\s-]+areata|cole[\s-]+disease|epidermolysis[\s-]+bullosa|"
     r"trisom(?:y|ic)|hyaline[\s-]+fibromatosis)\w*\b"),
    ("pluripotent", r"\b(?:induced[\s-]+pluripotent|iPSCs?|"
     r"embryonic[\s-]+stem[\s-]+cells?)\b"),
    ("embryonic_development", r"\b(?:embryonic|embryo|e\d{1,2}\.\d|"
     r"skin[\s-]+development|epidermal[\s-]+development)\b"),
    ("systemic_premature_aging", r"\b(?:hutchinson[\s-]+gilford|progeria|"
     r"werner[\s-]+syndrome|cockayne[\s-]+syndrome(?![\s-]+group))\b"),
)


ASSAY_PATTERN = re.compile(
    r"\b(?:rna[\s-]?seq|single[\s-]+cell|single[\s-]+nucleus|scrna|snrna|"
    r"transcriptom\w*|profil\w*|microarray|sequenc\w*|atac|chip[\s-]?seq|"
    r"methyl\w*|epigen\w*|spatial|sample\w*|biops\w*|isolat\w*|expression)\b",
    re.IGNORECASE,
)
PRIMARY_PATTERN = re.compile(
    r"\b(?:we[\s-]+(?:profiled|analy[sz]ed|investigated|examined|compared|used)|"
    r"this[\s-]+study|aim(?:ed|s)?[\s-]+to|to[\s-]+investigate|"
    r"transcriptom\w*|profil\w*|single[\s-]+cell|rna[\s-]?seq)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RelevanceAssessment:
    decision: str
    score: int
    stage1_pass: bool
    reason: str
    scope_category: str
    skin_terms: list[str]
    aging_terms: list[str]
    sample_terms: list[str]
    age_contrast_terms: list[str]
    intervention_terms: list[str]
    incidental_signals: list[str]
    off_topic_signals: list[str]
    central_sentences: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text(record: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        if record.get(key) is not None:
            return str(record[key])
    return ""


def _matches(text: str, patterns: Iterable[PatternSpec]) -> list[str]:
    return [
        label
        for label, pattern in patterns
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    ]


def _sentences(text: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
        if part.strip()
    ]


def stage1_candidate(record: Mapping[str, Any]) -> bool:
    """High-recall gate: require both a skin subject and an aging concept."""

    combined = " ".join(
        (
            _text(record, "Title", "title"),
            _text(record, "Summary", "summary"),
            _text(record, "Overall_Design", "overall_design"),
            _text(record, "Sample_Titles", "sample_titles"),
        )
    )
    return bool(
        _matches(combined, SKIN_PATTERNS)
        and _matches(combined, AGING_PATTERNS)
    )


def _scope_category(combined: str) -> str:
    if re.search(
        r"\b(?:(?:photo|pho[\s-]?to)[\s-]?ag(?:e|ing|eing)\w*|"
        r"actinic[\s-]+lentigines?|solar[\s-]+elastosis)\b",
        combined,
        re.I,
    ):
        return "photoaging"
    if re.search(r"\b(?:senescen\w*|replicative[\s-]+lifespan|sasp)\b", combined, re.I):
        return "cellular_senescence"
    if re.search(r"\b(?:rejuvenat\w*|anti[\s-]?ag(?:e|ing|eing)\w*|senolytic)\w*\b", combined, re.I):
        return "rejuvenation_intervention"
    if re.search(r"\b(?:wound|healing|repair)\w*\b", combined, re.I):
        return "aged_skin_repair"
    if re.search(r"\b(?:hair[\s-]+follicle|sebaceous|pilosebaceous)\b", combined, re.I):
        return "skin_appendage_aging"
    return "intrinsic_skin_aging"


def assess_relevance(record: Mapping[str, Any]) -> RelevanceAssessment:
    """Validate whether skin aging is the actual omics subject."""

    title = _text(record, "Title", "title")
    summary = _text(record, "Summary", "summary")
    design = _text(record, "Overall_Design", "overall_design")
    sample_titles = _text(record, "Sample_Titles", "sample_titles")
    combined = " ".join((title, summary, design))

    skin_terms = _matches(combined, SKIN_PATTERNS)
    aging_terms = _matches(combined, AGING_PATTERNS)
    design_sample_terms = _matches(design, SAMPLE_PATTERNS)
    title_sample_terms = _matches(title, SAMPLE_PATTERNS)
    sample_title_terms = _matches(sample_titles, SAMPLE_PATTERNS)
    narrative_sample_terms = _matches(title + " " + summary, SAMPLE_PATTERNS)
    generic_design = not design.strip() or bool(
        re.fullmatch(
            r"(?:refer[\s-]+to[\s-]+individual[\s-]+series|"
            r"single[\s-]+end[\s-]+stranded[\s-]+rna[\s-]?seq|computed)[.]?",
            design.strip(),
            flags=re.IGNORECASE,
        )
    )
    if design_sample_terms:
        sample_terms = design_sample_terms
    elif generic_design:
        sample_terms = sample_title_terms or title_sample_terms
    elif sample_title_terms and not _matches(design, OFF_TOPIC_PATTERNS):
        # Sample titles can rescue a terse design, but a skin-aging title must
        # never override an explicit non-skin assay design.
        sample_terms = sample_title_terms
    else:
        sample_terms = []
    contrast_terms = _matches(title + " " + design, AGE_CONTRAST_PATTERNS)
    intervention_terms = _matches(combined, INTERVENTION_PATTERNS)
    incidental = _matches(combined, INCIDENTAL_PATTERNS)
    off_topic_title = _matches(title, OFF_TOPIC_PATTERNS)
    off_topic_design = _matches(design, OFF_TOPIC_PATTERNS)
    off_topic_summary = _matches(summary, OFF_TOPIC_PATTERNS)
    off_topic = sorted(set(off_topic_title + off_topic_design))
    if (
        not sample_terms
        and narrative_sample_terms
        and not off_topic_design
        and contrast_terms
    ):
        sample_terms = narrative_sample_terms
    stage1_pass = bool(skin_terms and aging_terms)

    central_sentences = 0
    for sentence in _sentences(title + ". " + summary):
        if (
            (
                _matches(sentence, SKIN_PATTERNS)
                or re.search(
                    r"\b(?:photo|pho[\s-]?to)[\s-]?ag(?:e|ing|eing)\w*\b",
                    sentence,
                    re.I,
                )
            )
            and _matches(sentence, AGING_PATTERNS)
            and (
                ASSAY_PATTERN.search(sentence)
                or PRIMARY_PATTERN.search(sentence)
            )
        ):
            central_sentences += 1

    explicit_photoaging_title = bool(
        re.search(
            r"\b(?:photo|pho[\s-]?to)[\s-]?ag(?:e|ing|eing)\w*\b",
            title,
            re.I,
        )
    )
    explicit_skin_aging_title = explicit_photoaging_title or bool(
        _matches(title, SKIN_PATTERNS)
        and _matches(title, AGING_PATTERNS)
    )
    aging_title_evidence = bool(_matches(title, AGING_PATTERNS))
    direct_sample = bool(sample_terms)
    design_contradiction = bool(off_topic_design) and not design_sample_terms
    developmental_only = (
        "embryonic_development" in off_topic_design
        and not aging_title_evidence
        and not contrast_terms
    )
    disease_central = (
        ("skeletal_repair" in off_topic_title and not direct_sample)
        or (
            "other_disease" in off_topic_title
            and not explicit_skin_aging_title
        )
    )
    generic_off_topic_series = (
        generic_design
        and bool(off_topic_summary)
        and not _matches(title, SKIN_PATTERNS)
    )
    aging_design = bool(_matches(design, AGING_PATTERNS))
    cancer_central = "cancer" in off_topic_title
    systemic_model = "systemic_premature_aging" in off_topic
    other_organ_central = bool(
        set(off_topic_title)
        & {"reproductive", "neurologic", "renal", "hepatic", "muscle", "blood", "dental"}
    )
    oral_central = (
        "oral_mucosa" in off_topic_title
        and not re.search(r"\b(?:skin|cutaneous|dermal|epiderm)\w*\b", title, re.I)
    )

    score = 0
    score += min(6, len(_matches(title, SKIN_PATTERNS)) * 2)
    score += min(6, len(_matches(title, AGING_PATTERNS)) * 2)
    score += min(8, len(sample_terms) * 3)
    score += min(6, len(contrast_terms) * 3)
    score += min(4, central_sentences * 2)
    score += min(3, len(intervention_terms) * 2)
    score -= min(6, len(incidental) * 3)
    score -= min(8, len(off_topic) * 3)

    if not stage1_pass:
        decision = "exclude"
        reason = "第一阶段未同时发现皮肤对象和老化概念"
    elif developmental_only:
        decision = "exclude"
        reason = "实验对象为胚胎皮肤发育，衰老程序仅为分子表型描述"
    elif disease_central:
        decision = "exclude"
        reason = "研究核心为特定疾病模型，未直接研究皮肤老化"
    elif oral_central:
        decision = "exclude"
        reason = "实际研究对象为口腔/黏膜细胞，而非皮肤组织或皮肤来源细胞"
    elif generic_off_topic_series:
        decision = "exclude"
        reason = "SuperSeries 的实际子研究指向非皮肤细胞，皮肤老化仅为背景"
    elif design_contradiction:
        decision = "exclude"
        reason = "Overall Design 的实际样本属于其他器官、肿瘤或非皮肤细胞"
    elif other_organ_central and not direct_sample:
        decision = "exclude"
        reason = "标题和实验设计指向非皮肤器官，皮肤/衰老仅为附带描述"
    elif incidental and not (contrast_terms or aging_design):
        decision = "exclude"
        reason = "皮肤细胞仅作为重编程或疾病诊断材料，并非皮肤老化研究对象"
    elif cancer_central and not (
        explicit_skin_aging_title and direct_sample and contrast_terms
    ):
        decision = "exclude"
        reason = "研究核心为肿瘤，缺少皮肤老化样本与年龄对照的共同证据"
    elif systemic_model:
        decision = "review"
        reason = "使用皮肤来源细胞研究系统性早老疾病，需确认是否属于皮肤老化范围"
    elif cancer_central:
        decision = "review"
        reason = "皮肤老化与肿瘤微环境同时为主题，需人工确认范围"
    elif direct_sample and contrast_terms:
        decision = "include"
        reason = "明确包含皮肤样本，并设置年龄、衰老或光老化对照"
    elif aging_title_evidence and direct_sample:
        decision = "include"
        reason = "标题明确以老化/细胞衰老为主题，Overall Design 验证了皮肤来源样本"
    elif explicit_skin_aging_title and direct_sample:
        decision = "include"
        reason = "标题以皮肤老化为核心，且存在直接皮肤样本证据"
    elif direct_sample and intervention_terms:
        decision = "include"
        reason = "皮肤样本用于验证抗衰老或年轻化干预"
    elif direct_sample and aging_design and central_sentences:
        decision = "include"
        reason = "实验设计和摘要共同表明皮肤老化是组学研究对象"
    elif explicit_skin_aging_title and not off_topic:
        decision = "include"
        reason = "标题明确以皮肤老化为研究主问题，实验设计未发现相反证据"
    elif direct_sample and central_sentences:
        decision = "include"
        reason = "摘要将皮肤老化作为组学实验的直接研究问题"
    else:
        decision = "exclude"
        reason = "同时命中皮肤和老化词，但缺少主研究问题与样本证据"

    return RelevanceAssessment(
        decision=decision,
        score=score,
        stage1_pass=stage1_pass,
        reason=reason,
        scope_category=classify_dimensions(record)["Primary_Scope_Category"],
        skin_terms=skin_terms,
        aging_terms=aging_terms,
        sample_terms=sample_terms,
        age_contrast_terms=contrast_terms,
        intervention_terms=intervention_terms,
        incidental_signals=incidental,
        off_topic_signals=off_topic,
        central_sentences=central_sentences,
    )


def with_relevance_metadata(
    record: Mapping[str, Any],
    assessment: RelevanceAssessment,
) -> dict[str, Any]:
    enriched = dict(record)
    enriched["Relevance_Decision"] = assessment.decision
    enriched["Relevance_Score"] = assessment.score
    enriched["Relevance_Reason"] = assessment.reason
    enriched["Scope_Category"] = assessment.scope_category
    enriched["Primary_Scope_Category"] = assessment.scope_category
    enriched["Relevance_Evidence"] = {
        "skin": assessment.skin_terms,
        "aging": assessment.aging_terms,
        "sample": assessment.sample_terms,
        "age_contrast": assessment.age_contrast_terms,
        "intervention": assessment.intervention_terms,
        "incidental": assessment.incidental_signals,
        "off_topic": assessment.off_topic_signals,
    }
    return enriched

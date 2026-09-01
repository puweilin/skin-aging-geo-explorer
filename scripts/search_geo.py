#!/usr/bin/env python3
"""Search, curate, and incrementally update the Skin Aging GEO corpus."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

import requests
from Bio import Entrez

from curation_model import (
    apply_corpus_model,
    classify_data_type,
    normalize_pubmed_ids,
)
from relevance_filter import (
    RelevanceAssessment,
    assess_relevance,
    stage1_candidate,
    with_relevance_metadata,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
REPORT_DIR = REPO_ROOT / "reports"
DATA_FILE = DATA_DIR / "geo_data.json"
PUBLIC_DATA_FILE = REPO_ROOT / "public" / "data" / "geo_data.json"
STUDY_FILE = DATA_DIR / "study_families.json"
PUBLIC_STUDY_FILE = REPO_ROOT / "public" / "data" / "study_families.json"
REVIEW_FILE = DATA_DIR / "relevance_review_queue.json"
DECISION_LOG_FILE = DATA_DIR / "relevance_decision_log.json"
MANUAL_OVERRIDES_FILE = DATA_DIR / "manual_curation_overrides.json"

ORGANISM_QUERY = (
    '("Homo sapiens"[Organism] OR "Mus musculus"[Organism])'
)
SEARCH_QUERIES = {
    "core_skin_aging": (
        '("skin aging" OR "skin ageing" OR "cutaneous aging" OR '
        '"cutaneous ageing" OR "dermal aging" OR "dermal ageing" OR '
        '"epidermal aging" OR "epidermal ageing" OR photoaging OR photoageing)'
    ),
    "aged_skin": (
        '("aged skin" OR "aging skin" OR "ageing skin" OR "old skin" OR '
        '"young skin" OR "chronologically aged skin" OR "intrinsically aged skin")'
    ),
    "skin_senescence": (
        '("skin senescence" OR "cutaneous senescence" OR "dermal senescence" OR '
        '"epidermal senescence" OR "senescent skin" OR "senescent dermis" OR '
        '"senescent epidermis" OR "senescent dermal fibroblasts" OR '
        '"replicative senescence" OR "stress induced premature senescence") '
        'AND (skin OR cutaneous OR epidermal OR dermal OR keratinocyte OR melanocyte)'
    ),
    "broad_skin_age_contrast": (
        '(skin OR cutaneous OR epidermis OR epidermal OR dermis OR dermal OR '
        'keratinocyte OR melanocyte OR "dermal fibroblast") AND '
        '(aging OR ageing OR aged OR senescence OR "young and old" OR '
        '"old and young" OR rejuvenation)'
    ),
    "skin_appendage_aging": (
        '("hair follicle aging" OR "hair follicle ageing" OR '
        '"aged hair follicle" OR "hair graying" OR "hair greying" OR '
        '"sebaceous gland aging" OR "dermal adipose aging")'
    ),
    "aging_intervention": (
        '(skin OR cutaneous OR epidermal OR dermal OR keratinocyte OR '
        '"dermal fibroblast") AND (rejuvenation OR senolytic OR '
        '"anti-aging" OR "anti-ageing")'
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full-history",
        action="store_true",
        help="Search the complete GEO history instead of the recent window.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Recent publication-date window used by daily updates.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="Optional development limit after the union search.",
    )
    parser.add_argument(
        "--soft-workers",
        type=int,
        default=3,
        help="Concurrent GEO SOFT page requests.",
    )
    return parser.parse_args()


def setup_entrez() -> None:
    email = os.environ.get("NCBI_EMAIL", "")
    if not email:
        raise RuntimeError("请先通过环境变量设置 NCBI_EMAIL")
    Entrez.email = email
    if os.environ.get("NCBI_API_KEY"):
        Entrez.api_key = os.environ["NCBI_API_KEY"]


def save_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_manual_overrides() -> dict[str, dict[str, str]]:
    raw = load_json(MANUAL_OVERRIDES_FILE, {})
    overrides: dict[str, dict[str, str]] = {}
    for decision in ("include", "exclude"):
        for accession, reason in raw.get(decision, {}).items():
            overrides[str(accession)] = {
                "decision": decision,
                "reason": str(reason),
            }
    return overrides


def merge_previous_raw_snapshots(
    current_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Union historical full-history snapshots so query drift cannot erase GSEs."""

    def merge_record(
        previous: Mapping[str, Any] | None,
        incoming: Mapping[str, Any],
    ) -> dict[str, Any]:
        combined = dict(previous or {})
        for key, value in incoming.items():
            if value not in (None, "", [], {}):
                combined[key] = value
            elif key not in combined:
                combined[key] = value
        return combined

    merged: dict[str, dict[str, Any]] = {}
    for path in sorted(DATA_DIR.glob("search_results_raw_*.json")):
        payload = load_json(path, [])
        if not isinstance(payload, list):
            continue
        for record in payload:
            accession = str(record.get("Accession", ""))
            if accession.startswith("GSE"):
                merged[accession] = merge_record(merged.get(accession), record)
    for record in current_records:
        accession = str(record["Accession"])
        merged[accession] = merge_record(merged.get(accession), record)
    print(
        f"历史 raw snapshots 并集: {len(current_records)} → {len(merged)} 个 GSE"
    )
    return list(merged.values())


def _search_one(
    label: str,
    query: str,
    *,
    full_history: bool,
    days: int,
) -> tuple[str, list[str], int]:
    kwargs: dict[str, Any] = {
        "db": "gds",
        "term": f"({query}) AND {ORGANISM_QUERY}",
        "retmax": 10000,
    }
    if not full_history:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        kwargs.update(
            mindate=start_date.strftime("%Y/%m/%d"),
            maxdate=end_date.strftime("%Y/%m/%d"),
            datetype="pdat",
        )
    with Entrez.esearch(**kwargs) as handle:
        result = Entrez.read(handle)
    return label, [str(item) for item in result.get("IdList", [])], int(result["Count"])


def search_geo(full_history: bool, days: int) -> tuple[list[str], dict[str, int]]:
    union_ids: set[str] = set()
    query_counts: dict[str, int] = {}
    for label, query in SEARCH_QUERIES.items():
        result_label, ids, count = _search_one(
            label,
            query,
            full_history=full_history,
            days=days,
        )
        union_ids.update(ids)
        query_counts[result_label] = count
        print(f"检索 {result_label}: {count} 条索引记录")
    return sorted(union_ids, key=int), query_counts


def fetch_summaries(ids: list[str]) -> list[Mapping[str, Any]]:
    records: list[Mapping[str, Any]] = []
    for offset in range(0, len(ids), 200):
        batch = ids[offset:offset + 200]
        for attempt in range(3):
            try:
                with Entrez.esummary(db="gds", id=",".join(batch)) as handle:
                    records.extend(Entrez.read(handle))
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        print(
            f"已获取 GEO 摘要: {min(offset + len(batch), len(ids))}/{len(ids)}"
        )
    return records


def _pubmed_ids(record: Mapping[str, Any]) -> str:
    return normalize_pubmed_ids(record.get("PubMedIds", []))


def _sample_titles(record: Mapping[str, Any]) -> str:
    values = []
    for item in record.get("Samples", []):
        title = str(item.get("Title", "")).strip()
        if title:
            values.append(title)
    return "; ".join(values)


def _classify_data_type(gds_type: str, title: str, summary: str) -> str:
    return classify_data_type(gds_type, title, summary)


def normalize_summary_record(record: Mapping[str, Any]) -> dict[str, Any] | None:
    accession = str(record.get("Accession", ""))
    if not accession.startswith("GSE"):
        return None
    title = str(record.get("title", ""))
    summary = str(record.get("summary", ""))
    gds_type = str(record.get("gdsType", ""))
    return {
        "Accession": accession,
        "Title": title,
        "Organism": str(record.get("taxon", "")),
        "Data_Type": _classify_data_type(gds_type, title, summary),
        "GEO_DataSet_Type": gds_type,
        "Sample_Count": int(record.get("n_samples", 0)),
        "Sample_Titles": _sample_titles(record),
        "Platform": str(record.get("GPL", "")),
        "Country": "",
        "Lab": "",
        "Institute": "",
        "Contributors": "",
        "PubMed_IDs": _pubmed_ids(record),
        "Supplementary_Size": "N/A",
        "Supplementary_Files": [],
        "Series_Relations": [],
        "Summary": summary,
        "Overall_Design": "",
        "AI_Summary_CN": "",
        "AI_Summary": "",
        "GEO_Link": (
            "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc="
            + accession
        ),
        "Submission_Date": str(record.get("PDAT", "")),
    }


def fetch_geo_soft(accession: str) -> dict[str, Any]:
    url = (
        "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?"
        f"acc={accession}&targ=self&form=text&view=full"
    )
    for attempt in range(3):
        try:
            response = requests.get(
                url,
                timeout=45,
                headers={"User-Agent": "SkinAgingGEOCurator/1.0"},
            )
            response.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 2:
                return {}
            time.sleep(2 ** attempt)
    info: dict[str, Any] = {
        "overall_design": "",
        "contributors": [],
        "lab": "",
        "institute": "",
        "country": "",
        "series_relations": [],
        "supplementary_files": [],
    }
    design_parts: list[str] = []
    for raw_line in response.text.splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if key == "!Series_overall_design":
            design_parts.append(value)
        elif key == "!Series_contributor":
            if value not in info["contributors"]:
                info["contributors"].append(value)
        elif key == "!Series_contact_laboratory":
            info["lab"] = value
        elif key == "!Series_contact_institute":
            info["institute"] = value
        elif key == "!Series_contact_country":
            info["country"] = value
        elif key == "!Series_relation":
            if value not in info["series_relations"]:
                info["series_relations"].append(value)
        elif key == "!Series_supplementary_file":
            if value not in info["supplementary_files"]:
                info["supplementary_files"].append(value)
    info["overall_design"] = " ".join(design_parts)
    return info


def enrich_soft_records(
    records: list[dict[str, Any]],
    workers: int,
) -> None:
    candidates = [record for record in records if stage1_candidate(record)]
    print(f"第一阶段候选: {len(candidates)}/{len(records)} 个 GSE")
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(fetch_geo_soft, record["Accession"]): record
            for record in candidates
        }
        for index, future in enumerate(as_completed(futures), 1):
            record = futures[future]
            info = future.result()
            record["Overall_Design"] = info.get("overall_design", "")
            record["Contributors"] = "; ".join(info.get("contributors", []))
            record["Lab"] = info.get("lab", "")
            record["Institute"] = info.get("institute", "")
            record["Country"] = info.get("country", "")
            record["Series_Relations"] = info.get("series_relations", [])
            record["Supplementary_Files"] = info.get("supplementary_files", [])
            if index % 25 == 0 or index == len(candidates):
                print(f"已获取实验设计: {index}/{len(candidates)}")


def _date_sort_key(record: Mapping[str, Any]) -> tuple[int, str]:
    value = str(record.get("Submission_Date", ""))
    return (1 if value else 0, value)


def _audit_row(
    record: Mapping[str, Any],
    assessment: RelevanceAssessment,
) -> dict[str, Any]:
    return {
        "Accession": record.get("Accession", ""),
        "Title": record.get("Title", ""),
        "Automated_Decision": assessment.decision,
        "Automated_Score": assessment.score,
        "Automated_Reason": assessment.reason,
        "Scope_Category": assessment.scope_category,
        "Stage1_Pass": assessment.stage1_pass,
        "Skin_Terms": assessment.skin_terms,
        "Aging_Terms": assessment.aging_terms,
        "Sample_Terms": assessment.sample_terms,
        "Age_Contrast_Terms": assessment.age_contrast_terms,
        "Intervention_Terms": assessment.intervention_terms,
        "Incidental_Signals": assessment.incidental_signals,
        "Off_Topic_Signals": assessment.off_topic_signals,
        "Central_Sentences": assessment.central_sentences,
        "Submission_Date": record.get("Submission_Date", ""),
        "GEO_Link": record.get("GEO_Link", ""),
    }


def save_audit_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    list_fields = {
        "Skin_Terms", "Aging_Terms", "Sample_Terms", "Age_Contrast_Terms",
        "Intervention_Terms", "Incidental_Signals", "Off_Topic_Signals",
    }
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            serialized = dict(row)
            for key in list_fields:
                serialized[key] = "; ".join(serialized.get(key, []))
            writer.writerow(serialized)


def save_markdown_report(
    path: Path,
    *,
    query_counts: Mapping[str, int],
    raw_count: int,
    audit_rows: list[Mapping[str, Any]],
    full_history: bool,
    days: int,
) -> None:
    decisions = Counter(row["Automated_Decision"] for row in audit_rows)
    candidates = [row for row in audit_rows if row["Stage1_Pass"]]
    candidate_decisions = Counter(
        row["Automated_Decision"] for row in candidates
    )
    categories = Counter(
        row["Scope_Category"]
        for row in audit_rows
        if row["Automated_Decision"] == "include"
    )
    lines = [
        "# Skin Aging GEO 两阶段检索与审计",
        "",
        f"- 运行日期：{date.today().isoformat()}",
        f"- 检索模式：{'完整历史' if full_history else f'最近 {days} 天'}",
        f"- 去重后 GSE：{raw_count}",
        f"- 第一阶段候选：{len(candidates)}",
        f"- 最终自动纳入：{decisions.get('include', 0)}",
        f"- 待人工复核：{decisions.get('review', 0)}",
        f"- 排除：{decisions.get('exclude', 0)}",
        "",
        "## 检索入口",
        "",
    ]
    for label, count in query_counts.items():
        lines.append(f"- `{label}`：{count} 条 GEO 索引记录")
    lines.extend([
        "",
        "## 第一阶段候选的第二阶段结果",
        "",
        f"- include：{candidate_decisions.get('include', 0)}",
        f"- review：{candidate_decisions.get('review', 0)}",
        f"- exclude：{candidate_decisions.get('exclude', 0)}",
        "",
        "## 正式纳入数据集的主题分层",
        "",
    ])
    for category, count in categories.most_common():
        lines.append(f"- `{category}`：{count}")
    lines.extend([
        "",
        "## 安全策略",
        "",
        "- 生产相关性判断不调用 AI。",
        "- 只有两阶段规则判定为 include 的新 accession 才会追加。",
        "- review 进入独立队列；exclude 进入可追溯日志。",
        "- Daily update 在保存前验证已有 accession 是最终集合的子集，禁止误删。",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def curate(
    records: list[dict[str, Any]],
    query_counts: Mapping[str, int],
    *,
    full_history: bool,
    days: int,
) -> None:
    existing = load_json(DATA_FILE, [])
    review_queue = load_json(REVIEW_FILE, [])
    decision_log = load_json(DECISION_LOG_FILE, [])
    overrides = load_manual_overrides()
    existing_ids = {item["Accession"] for item in existing}
    original_ids = set(existing_ids)
    review_by_id = {item["Accession"]: item for item in review_queue}
    logged_by_id = {item["Accession"]: item for item in decision_log}

    # Existing records may only be removed from the active corpus by an
    # explicit, versioned human override. Automated daily rules remain
    # append-only.
    explicitly_excluded = {
        accession
        for accession, override in overrides.items()
        if override["decision"] == "exclude"
    }
    retained: list[dict[str, Any]] = []
    for item in existing:
        accession = item["Accession"]
        if accession not in explicitly_excluded:
            retained.append(item)
            continue
        override = overrides[accession]
        logged_by_id[accession] = {
            **item,
            "Final_Decision": "exclude",
            "Final_Reason": override["reason"],
            "Decision_Source": "manual_override",
            "Decided_At": datetime.now().isoformat(timespec="seconds"),
        }
        review_by_id.pop(accession, None)
    existing = retained
    existing_ids = {item["Accession"] for item in existing}

    audit_rows: list[dict[str, Any]] = []
    added = 0
    for record in records:
        assessment = assess_relevance(record)
        audit_rows.append(_audit_row(record, assessment))
        accession = record["Accession"]
        override = overrides.get(accession)
        final_decision = override["decision"] if override else assessment.decision
        final_reason = override["reason"] if override else assessment.reason
        final_source = "manual_override" if override else "two_stage_rule"
        if accession in existing_ids:
            continue
        if final_decision == "include":
            enriched = with_relevance_metadata(record, assessment)
            enriched["Relevance_Final_Decision"] = "include"
            enriched["Relevance_Final_Source"] = final_source
            enriched["Relevance_Final_Reason"] = final_reason
            enriched["Curation_Status"] = "active"
            existing.append(enriched)
            existing_ids.add(accession)
            review_by_id.pop(accession, None)
            logged_by_id.pop(accession, None)
            added += 1
        elif final_decision == "review":
            if accession not in logged_by_id:
                review_by_id[accession] = {
                    **record,
                    "Assessment": assessment.to_dict(),
                    "Decision_Source": final_source,
                }
        elif (assessment.stage1_pass or override) and accession not in review_by_id:
            logged_by_id[accession] = {
                **record,
                "Final_Decision": "exclude",
                "Final_Reason": final_reason,
                "Decision_Source": final_source,
                "Assessment": assessment.to_dict(),
                "Decided_At": datetime.now().isoformat(timespec="seconds"),
            }

    final_ids = [item["Accession"] for item in existing]
    if len(final_ids) != len(set(final_ids)):
        raise RuntimeError("安全检查失败：生产数据出现重复 accession")
    protected_ids = original_ids - explicitly_excluded
    if not protected_ids.issubset(set(final_ids)):
        removed = sorted(protected_ids - set(final_ids))
        raise RuntimeError("安全检查失败：daily update 不得删除 " + ", ".join(removed))

    existing, study_families = apply_corpus_model(existing)
    review_values = sorted(
        review_by_id.values(), key=_date_sort_key, reverse=True
    )
    log_values = sorted(
        logged_by_id.values(), key=_date_sort_key, reverse=True
    )
    audit_rows.sort(key=_date_sort_key, reverse=True)

    save_json_atomic(DATA_FILE, existing)
    save_json_atomic(PUBLIC_DATA_FILE, existing)
    save_json_atomic(STUDY_FILE, study_families)
    save_json_atomic(PUBLIC_STUDY_FILE, study_families)
    save_json_atomic(REVIEW_FILE, review_values)
    save_json_atomic(DECISION_LOG_FILE, log_values)

    if full_history:
        stamp = date.today().strftime("%Y%m%d")
        raw_path = DATA_DIR / f"search_results_raw_{stamp}.json"
        save_json_atomic(raw_path, records)
        save_json_atomic(REPORT_DIR / f"relevance_audit_{stamp}.json", audit_rows)
        save_audit_csv(REPORT_DIR / f"relevance_audit_{stamp}.csv", audit_rows)
        save_markdown_report(
            REPORT_DIR / f"relevance_audit_{stamp}.md",
            query_counts=query_counts,
            raw_count=len(records),
            audit_rows=audit_rows,
            full_history=full_history,
            days=days,
        )
    print(
        f"策展完成：本次新增 {added}；生产数据 {len(existing)}；"
        f"独立研究 {len(study_families)}；复核队列 {len(review_values)}；"
        f"排除日志 {len(log_values)}"
    )


def main() -> int:
    args = parse_args()
    try:
        setup_entrez()
        ids, query_counts = search_geo(args.full_history, args.days)
        if args.max_records:
            ids = ids[:args.max_records]
        summaries = fetch_summaries(ids)
        records = [
            normalized
            for record in summaries
            if (normalized := normalize_summary_record(record)) is not None
        ]
        unique = {record["Accession"]: record for record in records}
        records = list(unique.values())
        enrich_soft_records(records, args.soft_workers)
        if args.full_history:
            records = merge_previous_raw_snapshots(records)
        curate(
            records,
            query_counts,
            full_history=args.full_history,
            days=args.days,
        )
        return 0
    except Exception as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

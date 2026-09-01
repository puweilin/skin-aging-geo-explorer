#!/usr/bin/env python3
"""Rebuild the curated Skin Aging corpus from a historical raw search snapshot."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from curation_model import apply_corpus_model
from relevance_filter import assess_relevance, with_relevance_metadata


REPO_ROOT = Path(__file__).resolve().parents[1]
STAMP = date.today().strftime("%Y%m%d")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=REPO_ROOT / "data" / f"search_results_raw_{STAMP}.json",
    )
    parser.add_argument(
        "--manual-review",
        type=Path,
        default=REPO_ROOT / "data" / "manual_curation_overrides.json",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


def load_overrides(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    raw = load_json(path)
    overrides: dict[str, dict[str, str]] = {}
    for decision in ("include", "exclude"):
        for accession, reason in raw.get(decision, {}).items():
            overrides[accession] = {
                "decision": decision,
                "reason": str(reason),
            }
    return overrides


def _sort_key(record: Mapping[str, Any]) -> tuple[int, str]:
    value = str(record.get("Submission_Date", ""))
    return (1 if value else 0, value)


def audit_record(
    record: Mapping[str, Any],
    overrides: Mapping[str, Mapping[str, str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    assessment = assess_relevance(record)
    accession = str(record.get("Accession", ""))
    override = overrides.get(accession)
    if override:
        final_decision = override["decision"]
        final_reason = override["reason"]
        source = "evidence_adjudication"
    else:
        final_decision = assessment.decision
        final_reason = assessment.reason
        source = "two_stage_rule"
    row = {
        "Accession": accession,
        "Title": record.get("Title", ""),
        "Automated_Decision": assessment.decision,
        "Automated_Score": assessment.score,
        "Automated_Reason": assessment.reason,
        "Final_Decision": final_decision,
        "Final_Reason": final_reason,
        "Decision_Source": source,
        "Stage1_Pass": assessment.stage1_pass,
        "Scope_Category": assessment.scope_category,
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
    context = {
        "assessment": assessment,
        "final_decision": final_decision,
        "final_reason": final_reason,
        "source": source,
    }
    return row, context


def save_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    fieldnames = list(rows[0]) if rows else []
    list_fields = {
        "Skin_Terms", "Aging_Terms", "Sample_Terms", "Age_Contrast_Terms",
        "Intervention_Terms", "Incidental_Signals", "Off_Topic_Signals",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            serialized = dict(row)
            for field in list_fields:
                serialized[field] = "; ".join(serialized.get(field, []))
            writer.writerow(serialized)


def save_markdown(
    path: Path,
    rows: list[Mapping[str, Any]],
    production: list[Mapping[str, Any]],
    review_queue: list[Mapping[str, Any]],
    decision_log: list[Mapping[str, Any]],
    study_families: list[Mapping[str, Any]],
) -> None:
    automated = Counter(row["Automated_Decision"] for row in rows)
    final = Counter(row["Final_Decision"] for row in rows)
    categories = Counter(
        item.get("Scope_Category", "unknown") for item in production
    )
    data_types = Counter(item.get("Data_Type", "Other") for item in production)
    organisms = Counter(item.get("Organism", "Unknown") for item in production)
    adjudicated = [
        row for row in rows if row["Decision_Source"] == "evidence_adjudication"
    ]
    lines = [
        "# Skin Aging GEO 完整历史回溯审计",
        "",
        f"- 审计日期：{date.today().isoformat()}",
        f"- GEO Series 原始检索结果：{len(rows)}",
        f"- 第一阶段候选：{sum(bool(row['Stage1_Pass']) for row in rows)}",
        f"- 自动规则：include {automated.get('include', 0)} / "
        f"review {automated.get('review', 0)} / exclude {automated.get('exclude', 0)}",
        f"- 最终整理：include {final.get('include', 0)} / "
        f"review {final.get('review', 0)} / exclude {final.get('exclude', 0)}",
        f"- 正式生产数据：{len(production)}",
        f"- 独立 Study Families：{len(study_families)}",
        f"- 未决复核队列：{len(review_queue)}",
        f"- 第一阶段候选排除日志：{len(decision_log)}",
        "",
        "## 主题分层",
        "",
    ]
    for category, count in categories.most_common():
        lines.append(f"- `{category}`：{count}")
    lines.extend(["", "## 数据类型", ""])
    for data_type, count in data_types.most_common():
        lines.append(f"- `{data_type}`：{count}")
    lines.extend(["", "## 物种", ""])
    for organism, count in organisms.most_common():
        lines.append(f"- `{organism}`：{count}")
    lines.extend(["", "## 证据裁决", ""])
    for row in adjudicated:
        lines.append(
            f"- {row['Accession']} → **{row['Final_Decision']}**："
            f"{row['Final_Reason']}"
        )
    lines.extend([
        "",
        "## 生产安全",
        "",
        "- 相关性判断不调用外部 AI。",
        "- Daily update 只追加规则确认的 include，不删除既有 accession。",
        "- review 不进入生产数据；exclude 留在可追溯日志中。",
        "- 原始检索快照与最终审计结果分开保存，可随时重跑。",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    raw_records = load_json(args.input)
    overrides = load_overrides(args.manual_review)
    existing_path = REPO_ROOT / "data" / "geo_data.json"
    existing_records = load_json(existing_path) if existing_path.exists() else []
    existing_by_id = {
        record.get("Accession"): record for record in existing_records
    }
    raw_ids = {record["Accession"] for record in raw_records}
    missing_overrides = sorted(set(overrides) - raw_ids)
    if missing_overrides:
        raise RuntimeError(
            "裁决文件包含原始快照中不存在的 accession: "
            + ", ".join(missing_overrides)
        )

    audit_rows: list[dict[str, Any]] = []
    production: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    decision_log: list[dict[str, Any]] = []
    excluded_report: list[dict[str, Any]] = []

    for record in raw_records:
        row, context = audit_record(record, overrides)
        audit_rows.append(row)
        accession = str(record.get("Accession", ""))
        assessment = context["assessment"]
        final_decision = context["final_decision"]
        source = context["source"]
        final_reason = context["final_reason"]
        if final_decision == "include":
            enriched = with_relevance_metadata(record, assessment)
            previous = existing_by_id.get(accession, {})
            for field in (
                "AI_Summary", "AI_Summary_CN", "AI_Summary_Generated_At",
                "AI_Summary_Model",
            ):
                if previous.get(field):
                    enriched[field] = previous[field]
            enriched["Relevance_Final_Decision"] = "include"
            enriched["Relevance_Final_Source"] = source
            enriched["Relevance_Final_Reason"] = final_reason
            enriched["Curation_Status"] = "active"
            production.append(enriched)
        elif final_decision == "review":
            review_queue.append({
                **record,
                "Assessment": assessment.to_dict(),
                "Decision_Source": source,
            })
        else:
            excluded_report.append(row)
            if assessment.stage1_pass:
                decision_log.append({
                    **record,
                    "Final_Decision": "exclude",
                    "Final_Reason": final_reason,
                    "Decision_Source": source,
                    "Assessment": assessment.to_dict(),
                    "Decided_At": datetime.now().isoformat(timespec="seconds"),
                })

    production, study_families = apply_corpus_model(production)
    review_queue.sort(key=_sort_key, reverse=True)
    decision_log.sort(key=_sort_key, reverse=True)
    audit_rows.sort(key=_sort_key, reverse=True)
    excluded_report.sort(key=_sort_key, reverse=True)

    production_ids = [item["Accession"] for item in production]
    if len(production_ids) != len(set(production_ids)):
        raise RuntimeError("正式数据出现重复 accession")
    if not set(production_ids).issubset(raw_ids):
        raise RuntimeError("正式数据不是原始检索快照的子集")

    data_dir = REPO_ROOT / "data"
    report_dir = REPO_ROOT / "reports"
    save_json_atomic(data_dir / "geo_data.json", production)
    save_json_atomic(
        REPO_ROOT / "public" / "data" / "geo_data.json",
        production,
    )
    save_json_atomic(data_dir / "study_families.json", study_families)
    save_json_atomic(
        REPO_ROOT / "public" / "data" / "study_families.json",
        study_families,
    )
    save_json_atomic(
        data_dir / f"geo_data_curated_{STAMP}.json",
        production,
    )
    save_json_atomic(data_dir / "relevance_review_queue.json", review_queue)
    save_json_atomic(data_dir / "relevance_decision_log.json", decision_log)
    save_json_atomic(report_dir / f"relevance_audit_{STAMP}.json", audit_rows)
    save_json_atomic(
        report_dir / f"relevance_excluded_{STAMP}.json",
        excluded_report,
    )
    save_csv(report_dir / f"relevance_audit_{STAMP}.csv", audit_rows)
    save_markdown(
        report_dir / f"relevance_audit_{STAMP}.md",
        audit_rows,
        production,
        review_queue,
        decision_log,
        study_families,
    )
    counts = Counter(row["Final_Decision"] for row in audit_rows)
    print(
        f"回溯完成：include {counts.get('include', 0)} / "
        f"review {counts.get('review', 0)} / "
        f"exclude {counts.get('exclude', 0)}；"
        f"独立研究 {len(study_families)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"错误: {error}", file=sys.stderr)
        raise

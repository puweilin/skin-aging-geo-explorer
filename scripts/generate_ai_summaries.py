#!/usr/bin/env python3
"""Generate Chinese summaries for rule-included Skin Aging GEO records.

This script deliberately does not make relevance decisions. It only fills the
AI summary fields of records that have already passed the two-stage rules.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = REPO_ROOT / "data" / "geo_data.json"
PUBLIC_DATA_FILE = REPO_ROOT / "public" / "data" / "geo_data.json"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"

SYSTEM_PROMPT = """你是一名严谨的生物信息学数据策展员。请只根据用户提供的 GEO 元数据，
为已经通过规则筛选的皮肤老化数据集撰写一段简洁中文摘要。

要求：
1. 用 80–160 个汉字概括研究目的、物种/样本、组学类型或实验设计，以及对皮肤老化研究的价值。
2. 明确区分“研究做了什么”和“研究发现了什么”；元数据没有结果时，不得虚构结果、结论或机制。
3. 不评价该数据集是否应该纳入，不输出相关性分数，也不补充输入中没有的信息。
4. 直接输出一段纯文本，不使用标题、列表、Markdown、引号或“摘要：”前缀。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-file",
        type=Path,
        default=DATA_FILE,
        help="Curated production JSON file.",
    )
    parser.add_argument(
        "--public-data-file",
        type=Path,
        default=PUBLIC_DATA_FILE,
        help="Frontend JSON mirror.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
        help="DeepSeek model name.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent API requests.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional maximum number of missing summaries to generate.",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=5,
        help="Atomically save after this many successful summaries.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate existing summaries. Not used by the daily workflow.",
    )
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path} 的顶层必须是 JSON 数组")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"{path} 包含非对象记录")
    return payload


def save_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


def accession_sequence(records: list[Mapping[str, Any]]) -> list[str]:
    accessions = [str(record.get("Accession", "")) for record in records]
    if any(not accession.startswith("GSE") for accession in accessions):
        raise ValueError("生产数据包含无效 accession")
    if len(accessions) != len(set(accessions)):
        raise ValueError("生产数据包含重复 accession")
    return accessions


def is_formally_included(record: Mapping[str, Any]) -> bool:
    return (
        record.get("Relevance_Final_Decision") == "include"
        and record.get("Curation_Status", "active") == "active"
    )


def needs_summary(record: Mapping[str, Any], *, force: bool = False) -> bool:
    if not is_formally_included(record):
        return False
    if force:
        return True
    return not str(
        record.get("AI_Summary_CN") or record.get("AI_Summary") or ""
    ).strip()


def _truncate(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def build_prompt(record: Mapping[str, Any]) -> str:
    metadata = {
        "GEO accession": record.get("Accession", ""),
        "题目": _truncate(record.get("Title"), 800),
        "物种": record.get("Organism", ""),
        "数据类型": record.get("Data_Type", ""),
        "样本数": record.get("Sample_Count", ""),
        "样本标题": _truncate(record.get("Sample_Titles"), 1800),
        "原始摘要": _truncate(record.get("Summary"), 5000),
        "Overall Design": _truncate(record.get("Overall_Design"), 4000),
        "规则主题分层": record.get("Scope_Category", ""),
        "老化情境": record.get("Aging_Contexts", []),
        "组织区室": record.get("Tissue_Compartments", []),
        "细胞类型": record.get("Cell_Types", []),
        "比较设计": record.get("Comparison_Designs", []),
        "数据集角色": record.get("Dataset_Role", ""),
    }
    return (
        "请为以下已经通过两阶段规则筛选的数据集生成中文摘要。"
        "规则主题分层只用于帮助理解，不要重新判断纳入或排除。\n"
        + json.dumps(metadata, ensure_ascii=False, indent=2)
    )


def clean_summary(value: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", value, flags=re.DOTALL | re.I)
    text = text.replace("```text", "").replace("```", "")
    text = re.sub(r"^\s*(?:中文)?摘要\s*[：:]\s*", "", text, flags=re.I)
    text = text.strip().strip("\"'“”")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 20:
        raise ValueError("模型返回的摘要过短")
    if len(text) > 800:
        raise ValueError("模型返回的摘要异常过长")
    return text


def request_summary(
    record: Mapping[str, Any],
    *,
    api_key: str,
    base_url: str,
    model: str,
    attempts: int = 3,
) -> str:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(record)},
        ],
        "thinking": {"type": "disabled"},
        "temperature": 0.2,
        "max_tokens": 400,
        "stream": False,
    }
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return clean_summary(str(content))
        except (requests.RequestException, KeyError, IndexError, TypeError,
                ValueError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"DeepSeek 请求失败：{last_error}")


def checkpoint(
    records: list[dict[str, Any]],
    *,
    data_file: Path,
    public_data_file: Path,
    expected_accessions: list[str],
) -> None:
    if accession_sequence(records) != expected_accessions:
        raise RuntimeError("安全检查失败：AI 摘要步骤不得增删或重排 accession")
    save_json_atomic(data_file, records)
    save_json_atomic(public_data_file, records)


def generate_missing_summaries(
    records: list[dict[str, Any]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    data_file: Path,
    public_data_file: Path,
    workers: int = 4,
    limit: int = 0,
    checkpoint_every: int = 5,
    force: bool = False,
) -> tuple[int, list[str]]:
    expected_accessions = accession_sequence(records)
    pending = [
        record for record in records if needs_summary(record, force=force)
    ]
    if limit > 0:
        pending = pending[:limit]
    if not pending:
        checkpoint(
            records,
            data_file=data_file,
            public_data_file=public_data_file,
            expected_accessions=expected_accessions,
        )
        return 0, []

    successes = 0
    failures: list[str] = []
    dirty_since_checkpoint = 0
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                request_summary,
                record,
                api_key=api_key,
                base_url=base_url,
                model=model,
            ): record
            for record in pending
        }
        for future in as_completed(futures):
            record = futures[future]
            accession = str(record["Accession"])
            try:
                summary = future.result()
            except Exception as error:
                failures.append(accession)
                print(f"警告: {accession} 摘要失败：{error}", file=sys.stderr)
                continue
            record["AI_Summary_CN"] = summary
            record["AI_Summary"] = summary
            record["AI_Summary_Model"] = model
            record["AI_Summary_Generated_At"] = generated_at
            successes += 1
            dirty_since_checkpoint += 1
            print(f"已生成摘要: {successes}/{len(pending)} ({accession})")
            if dirty_since_checkpoint >= max(1, checkpoint_every):
                checkpoint(
                    records,
                    data_file=data_file,
                    public_data_file=public_data_file,
                    expected_accessions=expected_accessions,
                )
                dirty_since_checkpoint = 0

    checkpoint(
        records,
        data_file=data_file,
        public_data_file=public_data_file,
        expected_accessions=expected_accessions,
    )
    return successes, failures


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("错误: 请通过环境变量设置 DEEPSEEK_API_KEY", file=sys.stderr)
        return 2
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip()
    try:
        records = load_records(args.data_file)
        pending_count = sum(
            needs_summary(record, force=args.force) for record in records
        )
        print(
            f"正式纳入记录 {len(records)}；待生成摘要 {pending_count}；"
            f"模型 {args.model}"
        )
        successes, failures = generate_missing_summaries(
            records,
            api_key=api_key,
            base_url=base_url,
            model=args.model,
            data_file=args.data_file,
            public_data_file=args.public_data_file,
            workers=args.workers,
            limit=args.limit,
            checkpoint_every=args.checkpoint_every,
            force=args.force,
        )
        print(f"AI 摘要完成：新增/更新 {successes}；失败 {len(failures)}")
        if failures and successes == 0:
            return 1
        return 0
    except Exception as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate production corpus, public mirrors, and Study Family integrity."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate() -> list[str]:
    errors: list[str] = []
    data = load_json(REPO_ROOT / "data" / "geo_data.json")
    public_data = load_json(REPO_ROOT / "public" / "data" / "geo_data.json")
    families = load_json(REPO_ROOT / "data" / "study_families.json")
    public_families = load_json(
        REPO_ROOT / "public" / "data" / "study_families.json"
    )
    overrides = load_json(
        REPO_ROOT / "data" / "manual_curation_overrides.json"
    )

    if data != public_data:
        errors.append("data/geo_data.json 与 public mirror 不一致")
    if families != public_families:
        errors.append("data/study_families.json 与 public mirror 不一致")

    accessions = [str(item.get("Accession", "")) for item in data]
    if len(accessions) != len(set(accessions)):
        errors.append("生产数据包含重复 accession")
    if any(not re.fullmatch(r"GSE\d+", accession) for accession in accessions):
        errors.append("生产数据包含无效 accession")

    family_ids = [str(item.get("Study_Family_ID", "")) for item in families]
    if len(family_ids) != len(set(family_ids)):
        errors.append("Study Family ID 重复")
    family_by_id = {item.get("Study_Family_ID"): item for item in families}

    excluded = set(overrides.get("exclude", {}))
    leaked = sorted(excluded.intersection(accessions))
    if leaked:
        errors.append("人工排除记录仍在生产数据: " + ", ".join(leaked))

    for item in data:
        accession = str(item.get("Accession", ""))
        if item.get("Schema_Version") != "2.0.0":
            errors.append(f"{accession}: Schema_Version 非 2.0.0")
        if item.get("Curation_Status") != "active":
            errors.append(f"{accession}: 非 active 记录进入生产数据")
        if item.get("Relevance_Final_Decision") != "include":
            errors.append(f"{accession}: 未正式 include")
        pubmed = str(item.get("PubMed_IDs", ""))
        if pubmed and not re.fullmatch(r"\d{5,9}(?:; \d{5,9})*", pubmed):
            errors.append(f"{accession}: PubMed_IDs 未规范化")
        family_id = item.get("Study_Family_ID")
        if family_id not in family_by_id:
            errors.append(f"{accession}: 缺少 Study Family")
            continue
        if accession not in family_by_id[family_id].get("Related_GSEs", []):
            errors.append(f"{accession}: Study Family 反向映射不一致")

    family_accessions = sorted({
        accession
        for family in families
        for accession in family.get("Related_GSEs", [])
    })
    if family_accessions != sorted(accessions):
        errors.append("Study Family 覆盖的 accession 与生产数据不一致")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("数据验证通过：dataset/public/study-family/override 均一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

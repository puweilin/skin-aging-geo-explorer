#!/usr/bin/env python3
"""Restore historical AI summaries from a git revision without changing IDs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = REPO_ROOT / "data" / "geo_data.json"
PUBLIC_DATA_FILE = REPO_ROOT / "public" / "data" / "geo_data.json"
SUMMARY_FIELDS = (
    "AI_Summary",
    "AI_Summary_CN",
    "AI_Summary_Generated_At",
    "AI_Summary_Model",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--git-ref",
        default="HEAD",
        help="Git revision containing the summary-bearing geo_data.json.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json_atomic(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    result = subprocess.run(
        ["git", "show", f"{args.git_ref}:data/geo_data.json"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    historical = json.loads(result.stdout)
    summaries = {
        record["Accession"]: record
        for record in historical
        if record.get("AI_Summary_CN") or record.get("AI_Summary")
    }
    current = load_json(DATA_FILE)
    expected_accessions = [record["Accession"] for record in current]
    restored = 0
    for record in current:
        source = summaries.get(record["Accession"])
        if not source:
            continue
        before = record.get("AI_Summary_CN") or record.get("AI_Summary")
        for field in SUMMARY_FIELDS:
            if source.get(field):
                record[field] = source[field]
        after = record.get("AI_Summary_CN") or record.get("AI_Summary")
        if not before and after:
            restored += 1
    if [record["Accession"] for record in current] != expected_accessions:
        raise RuntimeError("摘要恢复不得增删或重排 accession")
    save_json_atomic(DATA_FILE, current)
    save_json_atomic(PUBLIC_DATA_FILE, current)
    print(
        f"从 {args.git_ref} 读取 {len(summaries)} 条历史摘要；"
        f"本次恢复 {restored} 条"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

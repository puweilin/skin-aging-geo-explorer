#!/usr/bin/env python3
"""Build a stable 120-record relevance regression set from an audited snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = REPO_ROOT / "data" / "search_results_raw_20260901.json"
AUDIT_FILE = REPO_ROOT / "reports" / "relevance_audit_20260901.json"
OUTPUT_FILE = REPO_ROOT / "tests" / "fixtures" / "relevance_gold_set.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    raw_by_id = {item["Accession"]: item for item in load_json(RAW_FILE)}
    audit = load_json(AUDIT_FILE)
    includes = [row for row in audit if row["Final_Decision"] == "include"]
    hard_excludes = [
        row for row in audit
        if row["Final_Decision"] == "exclude" and row["Stage1_Pass"]
    ]
    includes.sort(
        key=lambda row: (row.get("Decision_Source") != "evidence_adjudication", -int(row.get("Automated_Score", 0)))
    )
    hard_excludes.sort(
        key=lambda row: (row.get("Decision_Source") != "evidence_adjudication", -int(row.get("Automated_Score", 0)))
    )
    selected = includes[:60] + hard_excludes[:60]
    payload = []
    for row in selected:
        raw = raw_by_id[row["Accession"]]
        payload.append({
            "Accession": row["Accession"],
            "Title": raw.get("Title", ""),
            "Summary": raw.get("Summary", ""),
            "Overall_Design": raw.get("Overall_Design", ""),
            "Sample_Titles": raw.get("Sample_Titles", ""),
            "Expected_Decision": row["Final_Decision"],
            "Expected_Reason": row["Final_Reason"],
            "Decision_Source": row["Decision_Source"],
        })
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_FILE.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temporary.replace(OUTPUT_FILE)
    print(f"已生成 {len(payload)} 条 relevance regression gold set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

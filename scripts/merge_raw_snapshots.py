#!/usr/bin/env python3
"""Merge saved full-history raw snapshots without calling NCBI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_DIR / "search_results_raw_20260901.json",
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


def merge_record(
    previous: dict[str, Any] | None,
    incoming: dict[str, Any],
) -> dict[str, Any]:
    combined = dict(previous or {})
    for key, value in incoming.items():
        if value not in (None, "", [], {}):
            combined[key] = value
        elif key not in combined:
            combined[key] = value
    return combined


def main() -> int:
    args = parse_args()
    output_resolved = args.output.resolve()
    paths = sorted(DATA_DIR.glob("search_results_raw_*.json"))
    merged: dict[str, dict[str, Any]] = {}
    for path in paths:
        payload = load_json(path)
        for record in payload:
            accession = str(record.get("Accession", ""))
            if accession.startswith("GSE"):
                merged[accession] = merge_record(merged.get(accession), record)
        print(f"读取 {path.name}: {len(payload)}")
    records = sorted(
        merged.values(),
        key=lambda item: str(item.get("Accession", "")),
    )
    save_json_atomic(output_resolved, records)
    print(f"合并完成: {len(records)} 个唯一 GSE → {output_resolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

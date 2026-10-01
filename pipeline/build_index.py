"""
Index generator for Mutual Fund Top-10 Holdings Tracker.
Scans data directory, aggregates metadata for all funds, and outputs data/index.json
for consumption by the Next.js frontend.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def build_index(
    data_dir: str = "data",
    config_path: str = "config/funds.json",
    out_path: str = "data/index.json",
) -> Dict[str, Any]:
    """
    Build index of all funds and their historical snapshots.
    """
    data_root = Path(data_dir)
    cfg_root = Path(config_path)

    if not cfg_root.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_root}")

    with open(cfg_root, "r", encoding="utf-8") as f:
        registered_funds = json.load(f)

    funds_summary: List[Dict[str, Any]] = []

    for fund in registered_funds:
        fund_id = fund["id"]
        fund_dir = data_root / fund_id

        if not fund_dir.exists():
            logger.info(f"No data directory yet for fund: {fund_id}")
            continue

        # Find all monthly snapshots (format: YYYY-MM.json, not YYYY-MM.diff.json)
        snapshot_files = sorted(
            [f for f in fund_dir.glob("*.json") if not f.name.endswith(".diff.json") and f.name != "index.json"],
            key=lambda x: x.stem,
            reverse=True,
        )

        if not snapshot_files:
            continue

        months_available = [f.stem for f in snapshot_files]
        latest_file = snapshot_files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            latest_snap = json.load(f)

        top_holding = None
        if latest_snap.get("holdings"):
            first = latest_snap["holdings"][0]
            top_holding = {
                "name": first["name"],
                "weight_pct": first["weight_pct"],
            }

        # Check for diff file for latest month
        diff_file = fund_dir / f"{latest_file.stem}.diff.json"
        latest_changes_count = 0
        latest_diff_summary = None

        if diff_file.exists():
            with open(diff_file, "r", encoding="utf-8") as f:
                diff_data = json.load(f)
                latest_diff_summary = diff_data.get("summary")
                latest_changes_count = (
                    diff_data.get("summary", {}).get("num_entered", 0)
                    + diff_data.get("summary", {}).get("num_exited", 0)
                )

        funds_summary.append({
            "id": fund_id,
            "name": fund.get("name", latest_snap.get("scheme_name")),
            "amc": fund.get("amc", "Mutual Fund AMC"),
            "category": fund.get("category", "Equity Fund"),
            "type": fund.get("type", "equity"),
            "latest_month": latest_snap["as_of"][:7],
            "latest_as_of": latest_snap["as_of"],
            "top10_total_pct": latest_snap.get("top10_total_pct"),
            "top_holding": top_holding,
            "months_available": months_available,
            "latest_changes_count": latest_changes_count,
            "latest_diff_summary": latest_diff_summary,
        })

    index_payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_funds": len(funds_summary),
        "funds": funds_summary,
    }

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(index_payload, f, indent=2)

    logger.info(f"Index successfully written to {out_file} ({len(funds_summary)} funds)")
    return index_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate data/index.json for tracked mutual funds")
    parser.add_argument("--data-dir", default="data", help="Root data directory")
    parser.add_argument("--config", default="config/funds.json", help="Path to funds.json config")
    parser.add_argument("--out", default="data/index.json", help="Path for output index JSON")
    args = parser.parse_args()

    build_index(data_dir=args.data_dir, config_path=args.config, out_path=args.out)


if __name__ == "__main__":
    main()

"""
Backfill script for Mutual Fund Top-10 Holdings Tracker.
Ingests historical factsheets/disclosures, generates monthly snapshots,
computes pairwise diffs, and updates the fund index.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.build_index import build_index
from pipeline.diff import DiffEngine
from pipeline.parse import ParserOrchestrator
from pipeline.scrape import Scraper

logger = logging.getLogger(__name__)


def run_fixtures_backfill(
    fund_id: str = "ppfas-flexicap",
    fixtures_dir: str = "pipeline/tests/fixtures/ppfas-flexicap",
    data_dir: str = "data",
    dry_run: bool = False,
) -> None:
    """
    Backfill using local fixture files (June, July, August 2026).
    """
    logger.info(f"Running fixtures backfill for fund '{fund_id}' from {fixtures_dir}")
    orchestrator = ParserOrchestrator()
    diff_engine = DiffEngine(significant_threshold_pp=0.5)

    fix_path = Path(fixtures_dir)
    target_data_dir = Path(data_dir) / fund_id
    if not dry_run:
        target_data_dir.mkdir(parents=True, exist_ok=True)

    # Process files in chronological order
    months_plan = [
        {"month": "2026-06", "pdf": fix_path / "factsheet-2026-06.pdf", "excel": None},
        {"month": "2026-07", "pdf": fix_path / "factsheet-2026-07.pdf", "excel": None},
        {
            "month": "2026-08",
            "pdf": fix_path / "factsheet-2026-08.pdf",
            "excel": fix_path / "portfolio-disclosure-2026-08.xls",
        },
    ]

    snapshots: Dict[str, Dict[str, Any]] = {}

    for item in months_plan:
        m = item["month"]
        logger.info(f"Processing month {m}...")
        snap = orchestrator.parse_with_fallback(
            fund_id=fund_id,
            excel_path=item["excel"],
            pdf_path=item["pdf"],
        )
        snapshots[m] = snap

        if not dry_run:
            snap_file = target_data_dir / f"{m}.json"
            with open(snap_file, "w", encoding="utf-8") as f:
                json.dump(snap, f, indent=2)
            logger.info(f"Saved snapshot: {snap_file}")

    # Compute diffs between consecutive months
    sorted_months = sorted(snapshots.keys())
    for i in range(1, len(sorted_months)):
        curr_m = sorted_months[i]
        prev_m = sorted_months[i - 1]
        logger.info(f"Computing diff: {curr_m} vs {prev_m}...")
        diff = diff_engine.compute_diff(snapshots[curr_m], snapshots[prev_m])

        if not dry_run:
            diff_file = target_data_dir / f"{curr_m}.diff.json"
            with open(diff_file, "w", encoding="utf-8") as f:
                json.dump(diff, f, indent=2)
            logger.info(f"Saved diff: {diff_file}")

    if not dry_run:
        build_index(data_dir=data_dir, out_path=f"{data_dir}/index.json")


def run_online_backfill(
    fund_id: str = "ppfas-flexicap",
    months_count: int = 12,
    data_dir: str = "data",
    cache_dir: str = "data/cache",
    dry_run: bool = False,
) -> None:
    """
    Backfill up to `months_count` months by scraping live download links.
    """
    logger.info(f"Starting online backfill for {fund_id} (target: {months_count} months)...")
    orchestrator = ParserOrchestrator()
    diff_engine = DiffEngine(significant_threshold_pp=0.5)
    fund = orchestrator.get_fund(fund_id)

    scraper = Scraper()
    html = scraper.fetch_page(fund["source_page"])
    discovered = scraper.discover_ppfas_links(html, fund["source_page"])

    targets = discovered[:months_count]
    logger.info(f"Discovered {len(targets)} months to process.")

    fund_cache_dir = Path(cache_dir) / fund_id
    target_data_dir = Path(data_dir) / fund_id
    if not dry_run:
        fund_cache_dir.mkdir(parents=True, exist_ok=True)
        target_data_dir.mkdir(parents=True, exist_ok=True)

    snapshots: Dict[str, Dict[str, Any]] = {}

    for item in targets:
        m = item["month"]
        logger.info(f"--- Processing {m} ---")
        excel_path = None
        pdf_path = None

        if item["excel_url"]:
            excel_path = fund_cache_dir / f"portfolio-disclosure-{m}.xls"
            if not dry_run:
                scraper.download_file(item["excel_url"], excel_path)

        if item["pdf_url"]:
            pdf_path = fund_cache_dir / f"factsheet-{m}.pdf"
            if not dry_run:
                scraper.download_file(item["pdf_url"], pdf_path)

        if not dry_run:
            try:
                snap = orchestrator.parse_with_fallback(
                    fund_id=fund_id,
                    excel_path=excel_path,
                    pdf_path=pdf_path,
                    source_url=item["excel_url"] or item["pdf_url"],
                )
                snapshots[m] = snap
                snap_file = target_data_dir / f"{m}.json"
                with open(snap_file, "w", encoding="utf-8") as f:
                    json.dump(snap, f, indent=2)
                logger.info(f"Saved snapshot {snap_file}")
            except Exception as e:
                logger.error(f"Failed to process month {m}: {e}")

    # Chronological diff generation
    sorted_months = sorted(snapshots.keys())
    for i in range(1, len(sorted_months)):
        curr_m = sorted_months[i]
        prev_m = sorted_months[i - 1]
        try:
            diff = diff_engine.compute_diff(snapshots[curr_m], snapshots[prev_m])
            diff_file = target_data_dir / f"{curr_m}.diff.json"
            with open(diff_file, "w", encoding="utf-8") as f:
                json.dump(diff, f, indent=2)
            logger.info(f"Saved diff: {diff_file}")
        except Exception as e:
            logger.error(f"Failed to compute diff for {curr_m} vs {prev_m}: {e}")

    if not dry_run:
        build_index(data_dir=data_dir, out_path=f"{data_dir}/index.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill mutual fund snapshots and diffs")
    parser.add_argument("--fund-id", default="ppfas-flexicap", help="Target fund ID")
    parser.add_argument("--months", type=int, default=12, help="Number of months to backfill")
    parser.add_argument("--fixtures-only", action="store_true", help="Use local test fixtures only")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files")
    parser.add_argument("--data-dir", default="data", help="Target data directory")
    args = parser.parse_args()

    if args.fixtures_only:
        run_fixtures_backfill(fund_id=args.fund_id, data_dir=args.data_dir, dry_run=args.dry_run)
    else:
        run_online_backfill(
            fund_id=args.fund_id,
            months_count=args.months,
            data_dir=args.data_dir,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()

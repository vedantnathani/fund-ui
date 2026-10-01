"""
Backfill script for Mutual Fund Top-10 Holdings Tracker.
Ingests historical factsheets/disclosures, generates monthly snapshots,
computes pairwise diffs, and updates the fund index.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, date
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

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def parse_month(value: str) -> str:
    """Validate and return a YYYY-MM string; raise ArgumentTypeError if invalid."""
    if not _MONTH_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"Invalid month format '{value}'. Expected YYYY-MM (e.g. 2026-08)."
        )
    return value


def month_range(start: str, end: str) -> List[str]:
    """Return a sorted list of YYYY-MM strings from start to end inclusive.

    Args:
        start: First month as YYYY-MM string.
        end: Last month as YYYY-MM string (inclusive).

    Returns:
        List of YYYY-MM strings in chronological order.

    Raises:
        ValueError: If start is after end.
    """
    s_year, s_month = int(start[:4]), int(start[5:])
    e_year, e_month = int(end[:4]), int(end[5:])

    if (s_year, s_month) > (e_year, e_month):
        raise ValueError(f"start '{start}' must not be after end '{end}'")

    months: List[str] = []
    cur_year, cur_month = s_year, s_month
    while (cur_year, cur_month) <= (e_year, e_month):
        months.append(f"{cur_year:04d}-{cur_month:02d}")
        cur_month += 1
        if cur_month > 12:
            cur_month = 1
            cur_year += 1
    return months


def _default_start_month(months_back: int) -> str:
    """Compute YYYY-MM for `months_back` months before today."""
    today = date.today()
    year = today.year
    month = today.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return f"{year:04d}-{month:02d}"


def _current_month() -> str:
    """Return current month as YYYY-MM."""
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def run_fixtures_backfill(
    fund_id: str = "all",
    fixtures_dir: str = "pipeline/tests/fixtures/ppfas-flexicap",
    data_dir: str = "data",
    dry_run: bool = False,
    config_path: str = "config/funds.json",
    start_month: str = "2026-06",
    end_month: str = "2026-08",
) -> None:
    """
    Backfill using local fixture files (June, July, August 2026).
    Supports backfilling a single fund or all enabled funds.
    Only processes months within [start_month, end_month].
    """
    with open(config_path, "r", encoding="utf-8") as f:
        funds = json.load(f)

    if fund_id and fund_id != "all":
        target_funds = [f for f in funds if f.get("id") == fund_id]
        if not target_funds:
            raise ValueError(f"No fund matched fund_id '{fund_id}'")
    else:
        target_funds = [f for f in funds if f.get("enabled", True)]

    orchestrator = ParserOrchestrator(config_path=config_path)
    diff_engine = DiffEngine(significant_threshold_pp=0.5)
    fix_path = Path(fixtures_dir)

    all_fixture_months = [
        {"month": "2026-06", "pdf": fix_path / "factsheet-2026-06.pdf", "excel": None},
        {"month": "2026-07", "pdf": fix_path / "factsheet-2026-07.pdf", "excel": None},
        {
            "month": "2026-08",
            "pdf": fix_path / "factsheet-2026-08.pdf",
            "excel": fix_path / "portfolio-disclosure-2026-08.xls",
        },
    ]

    # Filter fixture months to requested date range
    valid_months = set(month_range(start_month, end_month))
    months_plan = [item for item in all_fixture_months if item["month"] in valid_months]
    logger.info(
        f"Filtered fixture months to {len(months_plan)} in range [{start_month}, {end_month}]"
    )

    for fund in target_funds:
        fid = fund["id"]
        logger.info(f"Running fixtures backfill for fund '{fid}' ({fund.get('name')})")
        target_data_dir = Path(data_dir) / fid
        if not dry_run:
            target_data_dir.mkdir(parents=True, exist_ok=True)

        snapshots: Dict[str, Dict[str, Any]] = {}

        for item in months_plan:
            m = item["month"]
            # Idempotency: skip months already on disk
            snap_file = Path(data_dir) / fid / f"{m}.json"
            if not dry_run and snap_file.exists():
                logger.info(f"Snapshot {snap_file} already exists — loading from disk, skipping re-parse.")
                with open(snap_file, "r", encoding="utf-8") as f:
                    snapshots[m] = json.load(f)
                continue

            logger.info(f"Processing month {m} for {fid}...")
            snap = orchestrator.parse_with_fallback(
                fund_id=fid,
                excel_path=item["excel"],
                pdf_path=item["pdf"],
            )
            snapshots[m] = snap

            if not dry_run:
                with open(snap_file, "w", encoding="utf-8") as f:
                    json.dump(snap, f, indent=2)
                logger.info(f"Saved snapshot: {snap_file}")

        # Compute diffs between consecutive months
        sorted_months = sorted(snapshots.keys())
        for i in range(1, len(sorted_months)):
            curr_m = sorted_months[i]
            prev_m = sorted_months[i - 1]
            logger.info(f"Computing diff for {fid}: {curr_m} vs {prev_m}...")
            diff = diff_engine.compute_diff(
                snapshots[curr_m],
                snapshots[prev_m],
                significant_change_pp=fund.get("significant_change_pp", 0.5),
            )

            if not dry_run:
                diff_file = target_data_dir / f"{curr_m}.diff.json"
                with open(diff_file, "w", encoding="utf-8") as f:
                    json.dump(diff, f, indent=2)
                logger.info(f"Saved diff: {diff_file}")

    if not dry_run:
        build_index(data_dir=data_dir, config_path=config_path, out_path=f"{data_dir}/index.json")


def run_online_backfill(
    fund_id: str = "ppfas-flexicap",
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    # Legacy param kept for backwards compatibility; ignored when start_month is provided
    months_count: int = 12,
    data_dir: str = "data",
    cache_dir: str = "data/cache",
    dry_run: bool = False,
) -> None:
    """
    Backfill by scraping live download links, filtered to [start_month, end_month].

    Args:
        fund_id: Target fund ID.
        start_month: Earliest month to backfill (YYYY-MM, inclusive).
        end_month: Latest month to backfill (YYYY-MM, inclusive).
        months_count: Legacy — number of most recent months (ignored when start_month given).
        data_dir: Root data directory.
        cache_dir: Directory to cache downloaded files.
        dry_run: If True, simulate without writing files.
    """
    # Resolve date range
    resolved_end = end_month or _current_month()
    resolved_start = start_month or _default_start_month(months_count)

    logger.info(
        f"Starting online backfill for '{fund_id}' in range [{resolved_start}, {resolved_end}]..."
    )
    orchestrator = ParserOrchestrator()
    diff_engine = DiffEngine(significant_threshold_pp=0.5)
    fund = orchestrator.get_fund(fund_id)

    scraper = Scraper()
    html = scraper.fetch_page(fund["source_page"])
    discovered = scraper.discover_ppfas_links(html, fund["source_page"])

    # Filter discovered months to requested range
    valid_months = set(month_range(resolved_start, resolved_end))
    targets = [item for item in discovered if item["month"] in valid_months]
    logger.info(
        f"Filtered to {len(targets)} months in range [{resolved_start}, {resolved_end}] "
        f"(from {len(discovered)} discovered)"
    )

    fund_cache_dir = Path(cache_dir) / fund_id
    target_data_dir = Path(data_dir) / fund_id
    if not dry_run:
        fund_cache_dir.mkdir(parents=True, exist_ok=True)
        target_data_dir.mkdir(parents=True, exist_ok=True)

    snapshots: Dict[str, Dict[str, Any]] = {}

    for item in targets:
        m = item["month"]
        snap_file = target_data_dir / f"{m}.json"

        # Idempotency: load existing snapshots from disk instead of re-downloading
        if snap_file.exists():
            logger.info(f"Snapshot {snap_file} already exists — loading from disk, skipping re-download.")
            with open(snap_file, "r", encoding="utf-8") as f:
                snapshots[m] = json.load(f)
            continue

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
    parser.add_argument("--fund-id", default="all", help="Target fund ID (or 'all')")
    parser.add_argument(
        "--start",
        dest="start_month",
        type=parse_month,
        default=None,
        metavar="YYYY-MM",
        help="Earliest month to backfill (inclusive). Overrides --months.",
    )
    parser.add_argument(
        "--end",
        dest="end_month",
        type=parse_month,
        default=None,
        metavar="YYYY-MM",
        help="Latest month to backfill (inclusive). Defaults to current month.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=12,
        help="Number of most-recent months to backfill. Ignored when --start is provided.",
    )
    parser.add_argument("--fixtures-only", action="store_true", help="Use local test fixtures only")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files")
    parser.add_argument("--data-dir", default="data", help="Target data directory")
    args = parser.parse_args()

    # Warn if --months is given alongside --start (--start wins)
    if args.start_month and args.months != 12:
        logger.warning("--months is ignored when --start is provided. Using --start.")

    # Resolve start/end for fixtures mode
    resolved_start = args.start_month or "2026-06"
    resolved_end = args.end_month or "2026-08"

    if args.fixtures_only:
        run_fixtures_backfill(
            fund_id=args.fund_id,
            data_dir=args.data_dir,
            dry_run=args.dry_run,
            start_month=resolved_start,
            end_month=resolved_end,
        )
    else:
        run_online_backfill(
            fund_id=args.fund_id,
            start_month=args.start_month,
            end_month=args.end_month,
            months_count=args.months,
            data_dir=args.data_dir,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()

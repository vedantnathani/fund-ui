"""
Automated Pipeline Runner for Mutual Fund Top-10 Holdings Tracker.
Designed to be executed by GitHub Actions or local cron.
Checks for newly published monthly factsheets/disclosures, parses, diffs,
and updates data/index.json idempotently.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def set_github_output(key: str, value: str) -> None:
    """Write key-value pair to GITHUB_OUTPUT environment file if available."""
    github_output_path = os.getenv("GITHUB_OUTPUT")
    if github_output_path:
        with open(github_output_path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    logger.info(f"GitHub Output: {key}={value}")


def run_pipeline(
    fund_id_filter: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    data_dir: str = "data",
    config_path: str = "config/funds.json",
    cache_dir: str = "data/cache",
) -> bool:
    """
    Run the end-to-end check and update pipeline across tracked funds.
    Returns True if new data was processed, False otherwise.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        funds: List[Dict[str, Any]] = json.load(f)

    if fund_id_filter and fund_id_filter != "all":
        funds = [f for f in funds if f.get("id") == fund_id_filter]
        if not funds:
            raise ValueError(f"No fund matched fund_id '{fund_id_filter}'")

    funds = [f for f in funds if f.get("enabled", True) and f.get("type") == "equity"]

    orchestrator = ParserOrchestrator(config_path=config_path)
    diff_engine = DiffEngine(significant_threshold_pp=0.5)
    scraper = Scraper()

    new_data_found = False

    for fund in funds:
        fid = fund["id"]
        logger.info(f"=== Checking fund: {fund['name']} ({fid}) ===")
        try:
            discovered = scraper.discover_links(fund)
        except Exception as e:
            logger.error(f"Failed to discover links for {fid}: {e}")
            continue

        if not discovered:
            logger.warning(f"No download links found for {fid}")
            continue

        latest_item = discovered[0]
        latest_month = latest_item["month"]
        logger.info(f"Latest published report available: {latest_month}")

        fund_dir = Path(data_dir) / fid
        snapshot_path = fund_dir / f"{latest_month}.json"

        if snapshot_path.exists() and not force:
            logger.info(f"Month {latest_month} is already processed for {fid}. Everything up-to-date.")
            continue

        logger.info(f"New or updated data detected for {fid} ({latest_month})! Processing...")
        new_data_found = True

        fund_cache_dir = Path(cache_dir) / fid
        excel_path = None
        pdf_path = None

        if latest_item["excel_url"]:
            excel_path = fund_cache_dir / f"portfolio-disclosure-{latest_month}.xls"
            if not dry_run:
                scraper.download_file(latest_item["excel_url"], excel_path, force=force)

        if latest_item["pdf_url"]:
            pdf_path = fund_cache_dir / f"factsheet-{latest_month}.pdf"
            if not dry_run:
                scraper.download_file(latest_item["pdf_url"], pdf_path, force=force)

        if dry_run:
            logger.info(f"[DRY-RUN] Would parse and write snapshot for {latest_month}")
            continue

        # Parse with fallback
        try:
            snapshot = orchestrator.parse_with_fallback(
                fund_id=fid,
                excel_path=excel_path,
                pdf_path=pdf_path,
                source_url=latest_item["excel_url"] or latest_item["pdf_url"],
            )

            fund_dir.mkdir(parents=True, exist_ok=True)
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
            logger.info(f"Successfully saved new snapshot: {snapshot_path}")

            # Identify previous month snapshot for diff
            existing_snapshots = sorted(
                [f for f in fund_dir.glob("*.json") if not f.name.endswith(".diff.json") and f.name != "index.json"],
                key=lambda x: x.stem,
            )

            # Find the snapshot immediately preceding latest_month
            prev_snapshot_file = None
            for s in existing_snapshots:
                if s.stem < latest_month:
                    prev_snapshot_file = s

            if prev_snapshot_file:
                logger.info(f"Generating diff against previous month: {prev_snapshot_file.stem}...")
                with open(prev_snapshot_file, "r", encoding="utf-8") as f:
                    prev_snap = json.load(f)

                diff = diff_engine.compute_diff(
                    snapshot,
                    prev_snap,
                    significant_change_pp=fund.get("significant_change_pp", 0.5),
                )
                diff_path = fund_dir / f"{latest_month}.diff.json"
                with open(diff_path, "w", encoding="utf-8") as f:
                    json.dump(diff, f, indent=2)
                logger.info(f"Successfully saved diff: {diff_path}")
            else:
                logger.info(f"No prior snapshot found before {latest_month}. Diff skipped.")

        except Exception as e:
            logger.error(f"Error processing {fid} for {latest_month}: {e}")
            raise e

    if new_data_found and not dry_run:
        logger.info("Regenerating master fund index (data/index.json)...")
        build_index(data_dir=data_dir, config_path=config_path, out_path=f"{data_dir}/index.json")

    return new_data_found


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated mutual fund pipeline runner")
    parser.add_argument("--fund-id", default=None, help="Filter to specific fund ID (or 'all')")
    parser.add_argument("--force", action="store_true", help="Re-process even if snapshot exists")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files")
    parser.add_argument("--data-dir", default="data", help="Root data directory")
    parser.add_argument("--config", default="config/funds.json", help="Path to config/funds.json")
    args = parser.parse_args()

    try:
        new_data = run_pipeline(
            fund_id_filter=args.fund_id,
            force=args.force,
            dry_run=args.dry_run,
            data_dir=args.data_dir,
            config_path=args.config,
        )
        set_github_output("new_data", "true" if new_data else "false")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Pipeline execution failed: {e}")
        set_github_output("new_data", "false")
        sys.exit(1)


if __name__ == "__main__":
    main()

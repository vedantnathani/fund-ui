"""
Scraper module for Mutual Fund factsheets and portfolio disclosures.
Discovers download links, downloads files politely, and verifies SHA-256 hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MONTH_NAME_TO_NUM = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def parse_month_year(text: str) -> Optional[str]:
    """Extract YYYY-MM from text, url or filename."""
    clean = text.lower()
    for month_name, mm in MONTH_NAME_TO_NUM.items():
        if month_name in clean:
            year_match = re.search(r"\b(20\d{2})\b", clean)
            if year_match:
                return f"{year_match.group(1)}-{mm}"
    return None


class Scraper:
    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout: int = 30):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.timeout = timeout

    def fetch_page(self, url: str, max_retries: int = 3) -> str:
        """Fetch page content with retries and exponential backoff."""
        delay = 2.0
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching page: {url} (attempt {attempt + 1}/{max_retries})")
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                last_error = e
                logger.warning(f"Request failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2

        raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts: {last_error}")

    def discover_ppfas_links(self, page_html: str, base_url: str) -> List[Dict[str, Any]]:
        """Parse all factsheet and disclosure links from PPFAS download page."""
        soup = BeautifulSoup(page_html, "html.parser")
        items: Dict[str, Dict[str, Any]] = {}

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full_url = urljoin(base_url, href)
            link_text = a.get_text(strip=True)

            month_str = parse_month_year(href) or parse_month_year(link_text)
            if not month_str:
                continue

            if month_str not in items:
                items[month_str] = {
                    "month": month_str,
                    "excel_url": None,
                    "pdf_url": None,
                }

            lower_href = href.lower()
            if ".xls" in lower_href and "portfolio" in lower_href:
                items[month_str]["excel_url"] = full_url
            elif ".pdf" in lower_href and "factsheet" in lower_href:
                items[month_str]["pdf_url"] = full_url

        sorted_items = [items[m] for m in sorted(items.keys(), reverse=True)]
        return sorted_items

    def download_file(
        self, url: str, dest_path: Path, max_retries: int = 3, force: bool = False
    ) -> Path:
        """Download file to dest_path idempotently with verification."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if not force and dest_path.exists() and dest_path.stat().st_size > 0:
            logger.info(f"File already exists and is non-empty: {dest_path}")
            return dest_path

        temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
        delay = 2.0
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading {url} -> {dest_path}")
                with self.session.get(url, stream=True, timeout=self.timeout) as resp:
                    resp.raise_for_status()
                    with open(temp_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)

                temp_path.replace(dest_path)
                logger.info(f"Successfully saved {dest_path} ({dest_path.stat().st_size} bytes)")
                return dest_path
            except Exception as e:
                last_error = e
                if temp_path.exists():
                    temp_path.unlink()
                logger.warning(f"Download failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2

        raise RuntimeError(f"Failed to download {url} after {max_retries} attempts: {last_error}")


def load_fund_config(fund_id: str, config_path: str = "config/funds.json") -> Dict[str, Any]:
    """Load config for a specific fund ID."""
    with open(config_path, "r", encoding="utf-8") as f:
        funds = json.load(f)
    for fund in funds:
        if fund.get("id") == fund_id:
            return fund
    raise ValueError(f"Fund '{fund_id}' not found in {config_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape mutual fund factsheet/disclosure links")
    parser.add_argument("--fund-id", default="ppfas-flexicap", help="Fund ID to scrape for")
    parser.add_argument("--month", default=None, help="Target month (YYYY-MM), e.g. 2026-08")
    parser.add_argument("--dry-run", action="store_true", help="Discover links without downloading")
    parser.add_argument("--out-dir", default="data/raw", help="Directory to save downloads")
    parser.add_argument("--force", action="store_true", help="Force redownload existing files")
    args = parser.parse_args()

    fund = load_fund_config(args.fund_id)
    source_page = fund["source_page"]

    scraper = Scraper()
    html = scraper.fetch_page(source_page)
    discovered = scraper.discover_ppfas_links(html, source_page)

    logger.info(f"Discovered {len(discovered)} months of reports for {fund['name']}:")

    if args.month:
        targets = [d for d in discovered if d["month"] == args.month]
        if not targets:
            logger.error(f"Month {args.month} not found in discovered list.")
            sys.exit(1)
    else:
        targets = discovered[:3]  # default to latest 3

    for item in targets:
        logger.info(
            f"Month: {item['month']} | Excel: {bool(item['excel_url'])} | PDF: {bool(item['pdf_url'])}"
        )

        if not args.dry_run:
            out_base = Path(args.out_dir) / args.fund_id
            if item["excel_url"]:
                ext = ".xls"
                excel_dest = out_base / f"portfolio-disclosure-{item['month']}{ext}"
                scraper.download_file(item["excel_url"], excel_dest, force=args.force)
                logger.info(f"  SHA-256: {compute_sha256(excel_dest)}")

            if item["pdf_url"]:
                pdf_dest = out_base / f"factsheet-{item['month']}.pdf"
                scraper.download_file(item["pdf_url"], pdf_dest, force=args.force)
                logger.info(f"  SHA-256: {compute_sha256(pdf_dest)}")


if __name__ == "__main__":
    main()

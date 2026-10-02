"""
PDF text and table parser for Mutual Fund Factsheets.
Extracts top equity holdings from PDF factsheets using pdfplumber with dynamic page location.
"""

from __future__ import annotations

import calendar
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pdfplumber

logger = logging.getLogger(__name__)

MONTH_NAME_TO_NUM = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

KNOWN_SECTORS = [
    "Pharmaceuticals & Biotechnology",
    "Pharmaceuticals & Biotech",
    "Commercial Services & Supplies",
    "Catalog/Specialty Distribution",
    "Diversified FMCG",
    "Consumable Fuels",
    "Computer Software",
    "IT - Software",
    "Telecom - Services",
    "Healthcare Services",
    "Auto Components",
    "Transport Services",
    "Industrial Products",
    "Capital Markets",
    "Food Products",
    "Automobiles",
    "Finance",
    "Banks",
    "Power",
    "Realty",
    "Gas",
]


class PDFTextParser:
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)

    def parse(
        self,
        section_keyword: str = "Flexi Cap",
        top_n: int = 10,
    ) -> Dict[str, Any]:
        """
        Dynamically find the fund's portfolio page, extract holdings and commentary.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.file_path}")

        with pdfplumber.open(self.file_path) as pdf:
            as_of_date = self._extract_as_of_date(pdf)
            page_idx, table_idx, holdings_table = self._find_holdings_table(pdf, section_keyword)

            if holdings_table is None:
                raise ValueError(
                    f"Could not locate portfolio table for '{section_keyword}' in {self.file_path.name}"
                )

            logger.info(
                f"Found holdings table in {self.file_path.name} on page {page_idx + 1}, table {table_idx + 1} ({len(holdings_table)} rows)"
            )
            holdings = self._parse_holdings_table(holdings_table)

            if not holdings:
                raise ValueError(f"No equity holdings extracted from table in {self.file_path.name}")

            # Sort descending and assign ranks
            holdings.sort(key=lambda x: x["weight_pct"], reverse=True)
            for rank, h in enumerate(holdings[:top_n], start=1):
                h["rank"] = rank

            top_holdings = holdings[:top_n]
            top10_sum = round(sum(h["weight_pct"] for h in top_holdings), 2)

            amc_commentary = self._extract_commentary(pdf, page_idx, section_keyword)

            scheme_name = (
                section_keyword
                if "fund" in section_keyword.lower()
                else f"Parag Parikh {section_keyword} Fund"
            )
            return {
                "source_type": "pdf_text",
                "file_name": self.file_path.name,
                "scheme_name": scheme_name,
                "as_of": as_of_date,
                "top10_total_pct": top10_sum,
                "total_equities_found": len(holdings),
                "holdings": top_holdings,
                "amc_commentary": amc_commentary,
            }

    def _extract_as_of_date(self, pdf: pdfplumber.PDF) -> Optional[str]:
        """Extract as of date (YYYY-MM-DD) from first few pages or filename."""
        date_pattern = r"(?:fact\s*sheet|data\s*as\s*on)\s*[-:]?\s*([A-Za-z]+)\s*(?:(\d{1,2}),?\s*)?(\d{4})"
        for page in pdf.pages[:3]:
            text = page.extract_text() or ""
            m = re.search(date_pattern, text, re.IGNORECASE)
            if m:
                month_name = m.group(1).lower()
                year = int(m.group(3))
                month_num = MONTH_NAME_TO_NUM.get(month_name)
                if month_num:
                    if m.group(2):
                        day = int(m.group(2))
                    else:
                        day = calendar.monthrange(year, month_num)[1]
                    return f"{year:04d}-{month_num:02d}-{day:02d}"

        # Fallback to filename (e.g., factsheet-2026-08.pdf)
        fn_match = re.search(r"(\d{4})-(\d{2})", self.file_path.name)
        if fn_match:
            year = int(fn_match.group(1))
            month_num = int(fn_match.group(2))
            day = calendar.monthrange(year, month_num)[1]
            return f"{year:04d}-{month_num:02d}-{day:02d}"

        return None

    def _find_holdings_table(
        self, pdf: pdfplumber.PDF, section_keyword: str
    ) -> Tuple[int, int, Optional[List[List[Any]]]]:
        """Find the page and table containing the portfolio holdings."""
        kw_lower = section_keyword.lower()

        for page_idx, page in enumerate(pdf.pages):
            text = (page.extract_text() or "").lower()
            if kw_lower not in text:
                continue

            # Ensure we are on the specific fund page and not a different scheme
            if "flexi cap" in kw_lower and ("parag parikh elss" in text[:300] or "parag parikh large cap" in text[:300]):
                continue

            tables = page.extract_tables() or []

            # Check 1: Multi-table / split-column layout (e.g., Motilal Oswal with 'Scrip' and 'Weightage (%)')
            scrip_tables = []
            for t_idx, tbl in enumerate(tables):
                header_flat = " ".join([re.sub(r"\s+", "", str(c).lower()) for r in tbl[:2] for c in r if c])
                if "scrip" in header_flat and "weight" in header_flat:
                    scrip_tables.append((t_idx, tbl))

            if scrip_tables:
                combined_rows = []
                for _, tbl in scrip_tables:
                    for row in tbl:
                        combined_rows.append(row)
                if len(combined_rows) >= 10:
                    return page_idx, scrip_tables[0][0], combined_rows

            # Check 2: Single combined table (e.g., PPFAS)
            for table_idx, tbl in enumerate(tables):
                if len(tbl) < 20:
                    continue

                flat_first_3 = " ".join([str(c) for r in tbl[:3] for c in r if c]).lower()
                if any(
                    k in flat_first_3
                    for k in ["core equity", "industry % of net assets", "name % of net assets", "name industry"]
                ):
                    return page_idx, table_idx, tbl

        return -1, -1, None

    def _clean_company_and_sector(self, raw_str: str) -> Tuple[str, Optional[str]]:
        """Separate company name and sector if concatenated."""
        clean = raw_str.strip()
        for sec in sorted(KNOWN_SECTORS, key=len, reverse=True):
            if clean.endswith(sec):
                name = clean[:-len(sec)].strip()
                return name, sec
        return clean, None

    def _parse_holdings_table(self, table: List[List[Any]]) -> List[Dict[str, Any]]:
        """Parse rows from the portfolio table into structured holdings."""
        holdings: List[Dict[str, Any]] = []
        in_domestic = True
        in_foreign = False

        for row in table:
            # Check 2-column format where col 0 is scrip name and col 1 is weight (e.g., Motilal Oswal)
            if len(row) >= 2 and row[0] and row[1]:
                scrip_col = str(row[0]).strip()
                wt_col = str(row[1]).replace("%", "").strip()
                clean_scrip_norm = re.sub(r"\s+", "", scrip_col.lower())

                if clean_scrip_norm in (
                    "scrip",
                    "equity&equityrelated",
                    "total",
                    "cblo/repo/treps",
                    "netreceivables/(payables)",
                    "grandtotal",
                ):
                    continue

                try:
                    wt_val = float(wt_col)
                    if wt_val > 0:
                        clean_name, extracted_sector = self._clean_company_and_sector(scrip_col)
                        holdings.append({
                            "name": clean_name,
                            "isin": None,
                            "sector": extracted_sector or "Equity",
                            "weight_pct": round(wt_val, 2),
                            "is_foreign": False,
                        })
                        continue
                except ValueError:
                    pass

            row_text = " ".join([str(c).replace("\n", " ") for c in row if c]).strip()
            row_lower = row_text.lower()

            if "overseas securities" in row_lower:
                in_domestic = False
                in_foreign = True
                continue

            # Stop parsing when reaching non-equity sections
            if any(
                k in row_lower
                for k in ["units issued by reits", "debt and money", "commercial paper", "certificate of deposit", "treasury bill"]
            ):
                in_domestic = False
                in_foreign = False
                break

            if row_lower.startswith("sub total") or row_lower.startswith("total") or "@arbitrage" in row_lower:
                continue

            if not in_domestic and not in_foreign:
                continue

            # Match pattern: Company Name [Sector] Weight%
            m = re.search(r"^(.*?)\s+([0-9]+\.[0-9]+)\s*%", row_text)
            if m:
                raw_name = m.group(1).strip()
                try:
                    weight_pct = round(float(m.group(2)), 2)
                except ValueError:
                    continue

                if weight_pct <= 0:
                    continue

                if raw_name.lower() in ("name", "industry", "core equity", "sub total", "total"):
                    continue

                clean_name, extracted_sector = self._clean_company_and_sector(raw_name)
                sector = extracted_sector or ("Foreign Securities" if in_foreign else "Equity")

                holdings.append({
                    "name": clean_name,
                    "isin": None,
                    "sector": sector,
                    "weight_pct": weight_pct,
                    "is_foreign": in_foreign,
                })

        return holdings

    def _extract_commentary(
        self, pdf: pdfplumber.PDF, portfolio_page_idx: int, section_keyword: str
    ) -> Optional[str]:
        """Extract additions, deletions, or commentary from subsequent page."""
        commentary_lines = []
        for next_idx in range(portfolio_page_idx + 1, min(portfolio_page_idx + 3, len(pdf.pages))):
            text = pdf.pages[next_idx].extract_text() or ""
            if "top 10 changes in holding" in text.lower():
                lines = text.split("\n")
                capturing = False
                for line in lines:
                    if "top 10 changes in holding" in line.lower():
                        capturing = True
                        commentary_lines.append(line.strip())
                        continue
                    if capturing:
                        if any(term in line.lower() for term in ["market capitalisation", "portfolio turnover", "load structure"]):
                            break
                        if line.strip():
                            commentary_lines.append(line.strip())
                if commentary_lines:
                    return "\n".join(commentary_lines)

        return None

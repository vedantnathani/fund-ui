"""
Excel parser for mutual fund portfolio disclosures (e.g., PPFAS Monthly Portfolio Statement).
Extracts domestic and foreign equity holdings, ISINs, sectors, and weights.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

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


class ExcelParser:
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)

    def _load_excel_file(self) -> pd.ExcelFile:
        """Load ExcelFile using openpyxl, falling back to xlrd if binary format."""
        try:
            return pd.ExcelFile(self.file_path, engine="openpyxl")
        except Exception as e:
            logger.debug(f"openpyxl failed for {self.file_path}: {e}. Trying xlrd...")
            try:
                return pd.ExcelFile(self.file_path, engine="xlrd")
            except Exception as e_xlrd:
                raise ValueError(
                    f"Failed to open Excel file {self.file_path} with openpyxl or xlrd: {e_xlrd}"
                ) from e_xlrd

    def parse(self, sheet_name: str = "PPFCF", top_n: int = 10) -> Dict[str, Any]:
        """
        Parse target sheet from portfolio disclosure Excel file.
        Returns metadata and list of top holdings.
        """
        xls = self._load_excel_file()
        if sheet_name not in xls.sheet_names:
            # Try case-insensitive matching
            matched = [s for s in xls.sheet_names if s.strip().lower() == sheet_name.lower()]
            if matched:
                sheet_name = matched[0]
            else:
                raise ValueError(
                    f"Sheet '{sheet_name}' not found. Available sheets: {xls.sheet_names}"
                )

        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        as_of_date = self._extract_as_of_date(df)
        scheme_name = self._extract_scheme_name(df)

        holdings = self._extract_equities(df)
        holdings.sort(key=lambda x: x["weight_pct"], reverse=True)

        # Assign ranks
        for rank, h in enumerate(holdings[:top_n], start=1):
            h["rank"] = rank

        top_holdings = holdings[:top_n]
        top10_sum = round(sum(h["weight_pct"] for h in top_holdings), 2)

        return {
            "source_type": "excel",
            "file_name": self.file_path.name,
            "scheme_name": scheme_name,
            "as_of": as_of_date,
            "top10_total_pct": top10_sum,
            "total_equities_found": len(holdings),
            "holdings": top_holdings,
        }

    def _extract_as_of_date(self, df: pd.DataFrame) -> Optional[str]:
        """Extract as-of date (YYYY-MM-DD) from top rows of sheet or filename."""
        date_pattern = r"(?:as on|statement as on|portfolio as on)\s+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})"
        for i in range(min(10, len(df))):
            row_str = " ".join(str(val) for val in df.iloc[i].dropna().tolist())
            m = re.search(date_pattern, row_str, re.IGNORECASE)
            if m:
                month_name, day, year = m.group(1).lower(), int(m.group(2)), int(m.group(3))
                month_num = MONTH_NAME_TO_NUM.get(month_name)
                if month_num:
                    return f"{year:04d}-{month_num:02d}-{day:02d}"

        # Fallback to date in filename (e.g., August_31_2026 or 2026-08)
        fn_match = re.search(r"([A-Za-z]+)_(\d{1,2})_(\d{4})", self.file_path.name)
        if fn_match:
            month_name, day, year = fn_match.group(1).lower(), int(fn_match.group(2)), int(fn_match.group(3))
            month_num = MONTH_NAME_TO_NUM.get(month_name)
            if month_num:
                return f"{year:04d}-{month_num:02d}-{day:02d}"

        fn_match_ym = re.search(r"(\d{4})-(\d{2})", self.file_path.name)
        if fn_match_ym:
            return f"{fn_match_ym.group(1)}-{fn_match_ym.group(2)}-01"

        return None

    def _extract_scheme_name(self, df: pd.DataFrame) -> str:
        """Extract scheme name from first few rows."""
        for i in range(min(5, len(df))):
            vals = df.iloc[i].dropna().tolist()
            if vals:
                first_val = str(vals[0]).strip()
                if "fund" in first_val.lower():
                    # Strip parentheses explanation
                    return re.sub(r"\(.*?\)", "", first_val).strip()
        return "Mutual Fund Scheme"

    def _extract_equities(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Extract domestic listed equities and foreign listed equities.
        Columns in PPFAS format:
        0: Internal Code
        1: Name of the Instrument
        2: ISIN
        3: Industry / Rating / Sector
        4: Quantity
        5: Market/Fair Value (Rs. in Lakhs)
        6: % to Net Assets
        """
        equities: List[Dict[str, Any]] = []

        # Find section boundaries
        in_domestic_equity = False
        in_foreign_equity = False

        for idx, row in df.iterrows():
            col1 = str(row[1]).strip() if pd.notna(row[1]) else ""
            col1_lower = col1.lower()

            # Section entry points
            if "equity & equity related foreign investments" in col1_lower:
                in_domestic_equity = False
                in_foreign_equity = True
                continue
            elif "equity & equity related" in col1_lower:
                in_domestic_equity = True
                in_foreign_equity = False
                continue

            # Check for subtotal or exit boundaries
            if in_domestic_equity or in_foreign_equity:
                if col1_lower.startswith("sub total") or col1_lower.startswith("total"):
                    # End of the listed equities block
                    if in_domestic_equity:
                        in_domestic_equity = False
                    if in_foreign_equity:
                        in_foreign_equity = False
                    continue

                if col1_lower.startswith("(b)") or col1_lower.startswith("(c)") or "unlisted" in col1_lower:
                    continue

                # Ignore subheaders like '(a) Listed / awaiting listing on Stock Exchanges'
                if "(a) listed" in col1_lower or "name of the instrument" in col1_lower:
                    continue

                # Process holding row
                name = col1
                isin = str(row[2]).strip() if pd.notna(row[2]) else None
                sector = str(row[3]).strip() if pd.notna(row[3]) else None
                # Clean sector string (strip trailing ## or asterisks)
                if sector:
                    sector = re.sub(r"[#\*]+$", "", sector).strip()

                weight_raw = row[6]
                if pd.isna(weight_raw):
                    continue

                try:
                    weight_val = float(weight_raw)
                except (ValueError, TypeError):
                    continue

                if weight_val <= 0:
                    continue

                # Convert decimal weight (e.g. 0.0763 -> 7.63)
                weight_pct = round(weight_val * 100, 4) if weight_val <= 1.0 else round(weight_val, 4)
                weight_pct = round(weight_pct, 2)

                # Filter out obvious non-equity or invalid records
                if not name or len(name) < 3 or name.lower() in ("nil", "nan"):
                    continue

                is_foreign = in_foreign_equity or (isin and isin.startswith("US"))

                equities.append({
                    "name": name,
                    "isin": isin if (isin and len(isin) >= 10 and isin.isalnum()) else None,
                    "sector": sector or ("Foreign Securities" if is_foreign else "Equity"),
                    "weight_pct": weight_pct,
                    "is_foreign": is_foreign,
                })

        return equities

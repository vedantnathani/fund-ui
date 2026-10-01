"""
Parser orchestrator for mutual fund holdings.
Selects appropriate parser (Excel primary, PDF fallback, OCR last resort),
runs validation, and produces standard snapshot dictionaries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.parsers.excel import ExcelParser
from pipeline.parsers.ocr_fallback import OCRFallbackParser
from pipeline.parsers.pdf_text import PDFTextParser
from pipeline.validate import HoldingsValidator, ValidationError

logger = logging.getLogger(__name__)


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


class ParserOrchestrator:
    def __init__(
        self,
        config_path: str = "config/funds.json",
        aliases_path: str = "config/aliases.json",
    ):
        self.config_path = Path(config_path)
        self.aliases_path = Path(aliases_path)
        self.validator = HoldingsValidator()
        self.funds = self._load_funds()

    def _load_funds(self) -> Dict[str, Dict[str, Any]]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            funds_list = json.load(f)
        return {f["id"]: f for f in funds_list}

    def get_fund(self, fund_id: str) -> Dict[str, Any]:
        if fund_id not in self.funds:
            raise ValueError(f"Unknown fund_id: {fund_id}. Registered: {list(self.funds.keys())}")
        return self.funds[fund_id]

    def parse_file(
        self,
        fund_id: str,
        file_path: Union[str, Path],
        source_url: Optional[str] = None,
        as_of_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse a single file (either Excel or PDF) for a given fund.
        """
        path = Path(file_path)
        fund = self.get_fund(fund_id)
        suffix = path.suffix.lower()

        raw_result = None
        source_type = None

        if suffix in (".xls", ".xlsx"):
            source_type = "excel"
            logger.info(f"Parsing {path.name} with Excel parser for fund {fund_id}...")
            parser = ExcelParser(path)
            raw_result = parser.parse(sheet_name=fund.get("excel_sheet", "PPFCF"))

        elif suffix == ".pdf":
            source_type = "pdf_text"
            logger.info(f"Parsing {path.name} with PDF text parser for fund {fund_id}...")
            parser = PDFTextParser(path)
            raw_result = parser.parse(
                section_keyword=fund.get("pdf_section_keyword", fund.get("name", "Flexi Cap"))
            )
        else:
            raise ValueError(f"Unsupported file format: {suffix} for {path}")

        # Validate extracted holdings
        validated_holdings = self.validator.validate_and_normalize(
            raw_result["holdings"], expected_top10_total=raw_result.get("top10_total_pct")
        )

        as_of = as_of_override or raw_result.get("as_of")
        if not as_of:
            raise ValidationError(f"Could not determine as_of date from {path.name}")

        sha256 = compute_file_sha256(path)
        top10_sum = round(sum(h["weight_pct"] for h in validated_holdings), 2)

        return {
            "fund_id": fund_id,
            "as_of": as_of,
            "source_url": source_url or "",
            "source_type": source_type,
            "file_sha256": sha256,
            "top10_total_pct": top10_sum,
            "amc_commentary": raw_result.get("amc_commentary"),
            "holdings": validated_holdings,
        }

    def parse_with_fallback(
        self,
        fund_id: str,
        excel_path: Optional[Union[str, Path]] = None,
        pdf_path: Optional[Union[str, Path]] = None,
        source_url: Optional[str] = None,
        as_of_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Attempt parsing with configured preference (default: Excel then PDF fallback).
        """
        fund = self.get_fund(fund_id)
        preferences = fund.get("parser_preference", ["excel", "pdf_text"])
        errors: List[str] = []

        for pref in preferences:
            if pref == "excel" and excel_path and Path(excel_path).exists():
                try:
                    return self.parse_file(
                        fund_id, excel_path, source_url=source_url, as_of_override=as_of_override
                    )
                except Exception as e:
                    logger.warning(f"Excel parsing failed for {excel_path}: {e}. Trying fallback...")
                    errors.append(f"Excel: {e}")

            elif pref == "pdf_text" and pdf_path and Path(pdf_path).exists():
                try:
                    return self.parse_file(
                        fund_id, pdf_path, source_url=source_url, as_of_override=as_of_override
                    )
                except Exception as e:
                    logger.warning(f"PDF parsing failed for {pdf_path}: {e}.")
                    errors.append(f"PDF: {e}")

        # If OCR enabled and PDF exists
        if pdf_path and Path(pdf_path).exists():
            try:
                ocr = OCRFallbackParser(pdf_path)
                ocr.parse()
            except Exception as e:
                errors.append(f"OCR: {e}")

        raise RuntimeError(f"All parsers failed for fund {fund_id}. Errors: {'; '.join(errors)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse mutual fund portfolio disclosures/factsheets")
    parser.add_argument("--fund-id", default="ppfas-flexicap", help="Target fund ID")
    parser.add_argument("--file", help="Path to Excel or PDF file to parse")
    parser.add_argument("--excel", help="Path to Excel disclosure file")
    parser.add_argument("--pdf", help="Path to PDF factsheet file")
    parser.add_argument("--source-url", default="", help="Original download URL")
    parser.add_argument("--dry-run", action="store_true", help="Print result to stdout")
    parser.add_argument("--out", help="Save result snapshot JSON to path")
    args = parser.parse_args()

    orchestrator = ParserOrchestrator()

    try:
        if args.file:
            result = orchestrator.parse_file(args.fund_id, args.file, source_url=args.source_url)
        elif args.excel or args.pdf:
            result = orchestrator.parse_with_fallback(
                args.fund_id, excel_path=args.excel, pdf_path=args.pdf, source_url=args.source_url
            )
        else:
            parser.error("Must provide either --file or --excel/--pdf")

        if args.dry_run or not args.out:
            print(json.dumps(result, indent=2))
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            logger.info(f"Saved snapshot to {out_path}")

    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Phase 2: Scraper + Parser + Validator — Summary

## Execution Overview
Phase 2 delivered the core data extraction and validation pipeline for Mutual Fund Top-10 Holdings Tracker, targeting PPFAS Flexi Cap Fund and extensible to other funds via config.

## Deliverables Completed
1. **Config Registry**:
   - `config/funds.json`: Configuration for `ppfas-flexicap`, specifying source pages, sheets, section keywords, and parser preferences.
   - `config/aliases.json`: Canonical name mappings (e.g. "Google" / "Alphabet Inc A" -> "Alphabet Inc.").
   - `requirements.txt`: Specified all pipeline dependencies (`pandas`, `openpyxl`, `pdfplumber`, `requests`, `beautifulsoup4`, `pytest`).
2. **Scraper (`pipeline/scrape.py`)**:
   - Discovers monthly factsheet PDFs and portfolio disclosure XLS files via HTTP (`requests` + `BeautifulSoup`).
   - Computes SHA-256 hashes of downloaded assets and prevents redundant downloads.
   - Includes exponential backoff and polite scraping headers.
3. **Excel Parser (`pipeline/parsers/excel.py`)**:
   - Robustly parses OpenXML/ZIP formatted `.xls` files with `openpyxl` (with fallback to `xlrd`).
   - Extracts both domestic and foreign equity sections (`Equity & Equity related` + `Equity & Equity related Foreign Investments`).
   - Normalizes decimal weights to percentage values, associates ISINs and sector classifications, and ranks top 10.
4. **PDF Text Parser (`pipeline/parsers/pdf_text.py`)**:
   - Dynamically searches for scheme pages and holdings tables across changing factsheet layouts (e.g., page 3 in June/August, page 7 in July).
   - Accurately splits company names and attached sector strings.
   - Captures AMC commentary (additions and reductions in holding) from adjacent pages.
5. **OCR Fallback Stub (`pipeline/parsers/ocr_fallback.py`)**:
   - Feature-flagged stub (`ENABLE_OCR`) ready for image-only scans.
6. **Parser Orchestrator (`pipeline/parse.py`)**:
   - Coordinates multi-parser execution with fallback (Excel primary -> PDF fallback).
   - Produces standard JSON snapshot matching FR-5 schema.
7. **Validator & Normalizer (`pipeline/validate.py`)**:
   - Enforces exactly 10 holdings, descending weight order, weight range [0.1%, 30.0%], and total sum constraints.
   - Normalizes legal entity names and maps aliases.
   - Generates canonical keys (ISIN preferred, slug fallback).
8. **Test Suite (`pipeline/tests/`)**:
   - 18 automated unit and integration tests passing with 100% green status across all test fixtures.

## Requirements Verified
- **FR-1**: Config-driven fund registry & aliases.
- **FR-2**: HTTP scraper with SHA-256 and idempotency.
- **FR-3**: Excel and PDF parsers with foreign equity aggregation.
- **FR-4**: Strict validator enforcing 10 holdings and monotonic weights.
- **UAT Criteria 1**: August 2026 fixture parsed with exact top 10 and weights.
- **UAT Criteria 2**: Snapshot with 9 holdings rejected by validator.
- **UAT Criteria 4**: "Google" resolves to "Alphabet Inc." via alias map.

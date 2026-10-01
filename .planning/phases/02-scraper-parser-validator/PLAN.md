# Phase 2: Scraper + Parser + Validator — Plan

## Goal
Build the complete extraction pipeline for PPFAS Flexi Cap Fund (and extensible to future funds), capable of scraping monthly publication links, parsing holdings from Portfolio Disclosure Excel files (primary) and Factsheet PDFs (fallback), normalizing and resolving company names/aliases, and strictly validating the resulting top-10 holdings against schema invariants.

---

## Requirements Addressed
- **FR-1**: Fund Registry (`config/funds.json`, `config/aliases.json`)
- **FR-2**: Scraper (`pipeline/scrape.py` — HTTP, idempotent, SHA-256, polite backoff)
- **FR-3**: Parsers (`pipeline/parsers/excel.py`, `pipeline/parsers/pdf_text.py`, `pipeline/parsers/ocr_fallback.py`, `pipeline/parse.py`)
- **FR-4**: Validation (`pipeline/validate.py` — 10 holdings, weight ranges, sum check, rank monotonicity, normalization, alias mapping)
- **NFR-2, NFR-4, NFR-5**: Reliability, structured logging, dry-run mode, unit tests with real fixtures
- **UAT Criteria 1, 2, 4**: Top 10 extracted from August 2026 fixture, validation rejects invalid counts, alias resolves "Google" → "Alphabet Inc"

---

## Architecture & Technical Decisions

1. **Excel Engine Selection**:
   - The PPFAS monthly disclosure files have a `.xls` extension but contain an OpenXML/ZIP container (`openpyxl` engine).
   - Parser must auto-detect format: attempt `openpyxl` first, fall back to `xlrd` if binary Excel 97-2003 format is encountered.
2. **Equity Section Aggregation**:
   - In PPFAS files, domestic equities (`Equity & Equity related`) and foreign equities (`Equity & Equity related Foreign Investments`) are listed in distinct sub-tables.
   - Both sections must be parsed, filtered for equity status, weights converted from decimal (e.g. `0.0763` -> `7.63%`), combined, and ranked to determine the true Top 10.
3. **Dynamic PDF Page Finding**:
   - Factsheet PDF page locations shift (e.g., Flexi Cap is on Page 3 in June/August 2026, but Page 7 in July 2026).
   - `pdf_text.py` must scan pages for `scheme_name` + `Core Equity` table headers rather than relying on hardcoded page indices.
4. **Normalized Holdings Model**:
   - Standard output per holding:
     ```python
     {
         "rank": int,           # 1 to 10
         "key": str,            # ISIN if available, else normalized name
         "name": str,           # Normalized human-readable company name
         "isin": Optional[str], # 12-char alphanumeric ISIN (e.g. INE040A01034)
         "sector": str,         # Sector classification (e.g. Banks)
         "weight_pct": float    # Percentage points rounded to 2 decimal places (e.g. 7.63)
     }
     ```

---

## Detailed Task Breakdown

### Task 1: Dependencies & Configuration Setup
- **Files**:
  - `requirements.txt`: `pandas`, `openpyxl`, `xlrd`, `pdfplumber`, `requests`, `beautifulsoup4`, `pytest`
  - `config/funds.json`: Registry defining `ppfas-flexicap`:
    - `id`: `"ppfas-flexicap"`
    - `name`: `"Parag Parikh Flexi Cap Fund"`
    - `amc`: `"PPFAS Mutual Fund"`
    - `type`: `"equity"`
    - `source_page`: `"https://amc.ppfas.com/downloads/factsheet/"`
    - `url_pattern`: regex or glob matching disclosure/factsheet URLs
    - `excel_sheet`: `"PPFCF"`
    - `pdf_section_keyword`: `"Parag Parikh Flexi Cap Fund"`
    - `significant_change_pp`: `0.5`
  - `config/aliases.json`: Standardized canonical mappings (e.g., `"Alphabet Inc A"` -> `"Alphabet Inc."`, `"HDFC Bank Limited"` -> `"HDFC Bank Ltd."`, `"Google"` -> `"Alphabet Inc."`).

### Task 2: HTTP Scraper (`pipeline/scrape.py`)
- **Responsibilities**:
  - Fetch AMC factsheet page with customized User-Agent and exponential backoff retry.
  - Parse HTML via `BeautifulSoup` to find download links matching target years and months.
  - Detect month/year from anchor text or href attributes.
  - Download target file (Excel disclosure preferred, PDF factsheet fallback) into local storage/cache.
  - Compute SHA-256 hash of downloaded file.
  - Provide CLI flags: `--fund-id`, `--month`, `--dry-run`, `--out-dir`.

### Task 3: Excel Parser (`pipeline/parsers/excel.py`)
- **Responsibilities**:
  - Open Excel file (`openpyxl` with `xlrd` fallback).
  - Locate fund sheet (`PPFCF` from config).
  - Parse domestic equity rows: locate `Equity & Equity related`, collect rows until `Sub Total`, skipping headers.
  - Parse foreign equity rows: locate `Equity & Equity related Foreign Investments`, collect rows until `Sub Total`.
  - Extract: ISIN (col 2), Name (col 1), Sector (col 3), Weight (col 6).
  - Convert decimal weight to percentage (`weight * 100`).
  - Filter out debt, cash, TREPS, derivatives, or subtotal summary lines.
  - Aggregate, sort descending by weight, return Top 10.

### Task 4: PDF Text Parser (`pipeline/parsers/pdf_text.py`)
- **Responsibilities**:
  - Open PDF with `pdfplumber`.
  - Search pages dynamically for fund title (`"Parag Parikh Flexi Cap Fund"`) and portfolio tables.
  - Locate table containing `Core Equity` and `Overseas Securities, IDRs and ADRs`.
  - Parse holding name and percentage strings (e.g. `"HDFC Bank Limited 7.63%"`).
  - Extract weight as float, sanitize name string.
  - Combine domestic and overseas equities, sort descending, return Top 10.

### Task 5: OCR Fallback Stub (`pipeline/parsers/ocr_fallback.py`)
- **Responsibilities**:
  - Implement fallback interface matching parser signature.
  - Controlled by feature flag `ENABLE_OCR = False`.
  - Raise informative `RuntimeError("OCR parser disabled or not configured")`.

### Task 6: Parser Orchestrator (`pipeline/parse.py`)
- **Responsibilities**:
  - Orchestrate parsing based on fund configuration:
    1. If Excel disclosure available, run `excel.py`.
    2. If Excel missing or returns invalid data, fall back to `pdf_text.py`.
    3. If PDF has no text layer and OCR enabled, attempt OCR fallback.
  - Extract metadata: `as_of` date, `file_sha256`, AMC stated commentary / total if present.
  - Return structured dict ready for validation.

### Task 7: Validator & Normalizer (`pipeline/validate.py`)
- **Responsibilities**:
  - Validate count: exactly 10 holdings (`len(holdings) == 10`).
  - Validate weights: `0.1 <= weight <= 30.0` for all holdings.
  - Validate monotonicity: `holdings[i].weight_pct >= holdings[i+1].weight_pct`.
  - Validate sum: sum of top 10 weights must be between 30% and 80%.
  - Normalize names: strip trailing dots/spaces, normalize legal entity abbreviations ("Limited" vs "Ltd"), map through `config/aliases.json`.
  - Validate ISINs: 12 alphanumeric characters when present.
  - Assign sequential ranks 1 to 10.
  - Raise `ValidationError` with clear error reasons on any breach.

### Task 8: Unit & Integration Tests (`pipeline/tests/`)
- **Files**:
  - `pipeline/tests/test_excel_parser.py`: Verify August 2026 disclosure fixture produces exact top 10 (HDFC Bank 7.63%, ICICI Bank 5.67%, Alphabet 4.14%, etc.).
  - `pipeline/tests/test_pdf_parser.py`: Verify August, July, and June 2026 PDF fixtures extract top 10 correctly across different page numbers.
  - `pipeline/tests/test_validator.py`: Test rejection of <10 holdings, out-of-order weights, negative/extreme weights, and alias normalization.
  - `pipeline/tests/test_orchestrator.py`: Test fallback from Excel to PDF and end-to-end extraction.

---

## Verification & Acceptance Checklist
- [ ] `pytest pipeline/tests/` passes with 100% green tests.
- [ ] Excel parser extracts exact top 10 from August 2026 fixture matching manual audit.
- [ ] PDF parser extracts top 10 from June, July, and August 2026 factsheet PDFs.
- [ ] Validator strictly rejects corrupted payloads (9 holdings, invalid weights).
- [ ] Name normalizer cleanly resolves "Google" -> "Alphabet Inc." and standardizes entity suffixes.
- [ ] Dry-run command prints formatted top 10 table without file modifications.

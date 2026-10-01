# Phase 7: Scalability Proof — Second Fund — Plan

## Goal
Prove the zero-code multi-fund scalability of the architecture by configuring a second equity fund (`ppfas-taxsaver` / Parag Parikh ELSS Tax Saver Fund) strictly via `config/funds.json`. Verify that the scraping, parsing, diffing, AI summarization, index generation, and Next.js frontend seamlessly handle multiple funds without modifying engine code.

---

## Requirements Addressed
- **FR-8.1**: Adding a second fund requires only adding a new JSON object to `config/funds.json`.
- **FR-8.2**: The scraper, parser, validator, diff engine, and runner process all enabled funds in a single run.
- **FR-8.3**: Dashboard displays all funds in the catalog and supports fund switching via URL routing (`/fund/[id]`).
- **FR-8.4**: Zero regression across existing funds (`ppfas-flexicap`).
- **UAT Criteria 8**: Second fund added via config alone; pipeline extracts and diffs both funds; dashboard displays both funds.

---

## Architecture & Technical Decisions

1. **Fund Selection (`ppfas-taxsaver`)**:
   - AMC: PPFAS Mutual Fund
   - Scheme: Parag Parikh ELSS Tax Saver Fund
   - Sheet in disclosure workbook: `PPTSF`
   - Keyword in factsheet PDF: `Tax Saver`
   - Shares the same monthly disclosure files as Flexi Cap Fund, making historical fixture ingestion deterministic and reliable without requiring network mocking.

2. **Config-Driven Ingestion**:
   - `config/funds.json` will contain 2 enabled funds:
     - `ppfas-flexicap` (Parag Parikh Flexi Cap Fund)
     - `ppfas-taxsaver` (Parag Parikh ELSS Tax Saver Fund)
   - Adding fund configuration drives:
     - `pipeline/parse.py` (ParserOrchestrator picks up scheme sheet & section keyword)
     - `pipeline/run.py` (iterates over all enabled funds in config)
     - `pipeline/build_index.py` (aggregates both funds into `data/index.json`)
     - Next.js `generateStaticParams()` (statically prerenders both `/fund/ppfas-flexicap` and `/fund/ppfas-taxsaver`)

3. **Multi-Fund Index Structure**:
   - `data/index.json` will index both funds:
     ```json
     {
       "last_updated": "...",
       "total_funds": 2,
       "funds": [
         { "id": "ppfas-flexicap", ... },
         { "id": "ppfas-taxsaver", ... }
       ]
     }
     ```

4. **Zero Code Changes to Parsers or Pipeline Core**:
   - All parser selection, table detection, and normalizer logic are already parameterized by `fund_id` and `config/funds.json`.

---

## Detailed Task Breakdown

### Task 1: Configuration Addition
- Update `config/funds.json` with the second fund configuration:
  - `id`: `"ppfas-taxsaver"`
  - `name`: `"Parag Parikh ELSS Tax Saver Fund"`
  - `amc`: `"PPFAS Mutual Fund"`
  - `type`: `"equity"`
  - `excel_sheet`: `"PPTSF"`
  - `pdf_section_keyword`: `"Tax Saver"`
  - `parser_preference`: `["excel", "pdf_text"]`
  - `significant_change_pp`: 0.5
  - `enabled`: true
- Verify company alias mappings in `config/aliases.json` for new holdings (e.g. `Maharashtra Scooters Limited`).

### Task 2: Data Ingestion & Backfill for Second Fund
- Ingest snapshots for June 2026, July 2026, and August 2026 into `data/ppfas-taxsaver/`.
- Compute diffs `2026-07.diff.json` and `2026-08.diff.json` with AI summaries for `ppfas-taxsaver`.
- Regenerate master `data/index.json` containing both funds.

### Task 3: Pipeline Runner Multi-Fund Verification
- Test `pipeline/run.py` with `--dry-run` to ensure runner discovers and processes both funds.
- Verify fund filtering (`--fund-id ppfas-taxsaver` vs `--fund-id all`).

### Task 4: Dashboard Multi-Fund Verification
- Verify `FundCatalog.tsx` renders 2 fund cards, filterable by search query or category.
- Verify `generateStaticParams` statically prerenders both `/fund/ppfas-flexicap` and `/fund/ppfas-taxsaver`.
- Run `npm --prefix web run build` to confirm clean static build.

### Task 5: Integration Test Suite (`pipeline/tests/test_multi_fund.py`)
- Test 1: `config/funds.json` defines at least 2 active equity funds.
- Test 2: Ingested snapshots and diffs for both funds pass `HoldingsValidator`.
- Test 3: `build_index` produces index with `total_funds >= 2` and accurate latest month data for each.
- Test 4: `DiffEngine` computes distinct diffs for each fund.
- Run complete test suite (`pytest pipeline/tests/ -v`).

---

## Verification & Acceptance Checklist
- [ ] `config/funds.json` contains valid configuration for both `ppfas-flexicap` and `ppfas-taxsaver`.
- [ ] `data/ppfas-taxsaver/` contains valid snapshots (`2026-06.json`, `2026-07.json`, `2026-08.json`) and diffs (`2026-07.diff.json`, `2026-08.diff.json`).
- [ ] `data/index.json` lists both funds with `total_funds: 2`.
- [ ] `pipeline/run.py --dry-run` processes both funds without errors.
- [ ] `npm --prefix web run build` prerenders `/fund/ppfas-flexicap` and `/fund/ppfas-taxsaver` cleanly.
- [ ] `pipeline/tests/test_multi_fund.py` passes 100%.
- [ ] All 32+ tests in `pipeline/tests/` pass with zero regressions.

# Phase 14 Summary — Modular AMC Scraper & Multi-Fund Backfill

**Milestone**: v1.2  
**Status**: ✅ Completed  
**Completed**: 2026-10-02  

---

## What Was Done

1. **Polymorphic AMC Strategy Router (`pipeline/scrape.py`)**:
   - Added `discover_links(fund_config, start_month=None, end_month=None)` to dynamically route factsheet discovery.
   - Refined `parse_month_year()` with context-aware proximity matching to ensure years immediately adjacent to month names are matched accurately (preventing parent directory year bleeding).

2. **Native Motilal Oswal AEM Document Discovery (`discover_motilal_links`)**:
   - Implemented direct integration with Motilal Oswal's public AEM search API (`/content/aem-cloud-dept-backend-motilal-oswal/api/search-documents.json?searchQuery=factsheet&type=`).
   - Automatically filters active monthly factsheet PDFs and resolves full URLs without headless browser overhead or brittle DOM scraping.

3. **Direct URL / WAF Escape Hatch (`discover_custom_links`)**:
   - Supported `monthly_urls` in `config/funds.json` and `web/src/types/index.ts`.
   - Allows explicit month-to-URL mappings for AMCs protected by Akamai WAF/CAPTCHAs (e.g., HDFC).

4. **Runner Decoupling (`pipeline/backfill.py`, `pipeline/run.py`)**:
   - Replaced hardcoded `discover_ppfas_links` calls with `scraper.discover_links(fund, ...)`.
   - Updated CLI test mocks in `pipeline/tests/test_backfill_cli.py`.

5. **Multi-Month Backfill & MoM Diff Generation**:
   - Backfilled Motilal Oswal Midcap Fund for `2026-07` and `2026-08`.
   - Verified that `2026-08.diff.json` was generated with verified holding changes (e.g. One 97 Communications expanded from 8.1% to 9.1% [+1.0pp], Kalyan Jewellers decreased from 8.9% to 8.1% [-0.8pp]).
   - Updated `data/index.json` with 2 historical months for Motilal Oswal.

6. **Unit Tests & Verification**:
   - Created `pipeline/tests/test_amc_scraper.py` with 6 unit tests covering routing, API discovery, filtering, and error handling.
   - All 51 pytest tests pass in 11.6s.
   - Verified Next.js static site generation via `npm run build` in `web/`.

---

## Verification Results

- `python3 -m pytest pipeline/tests/ -v`: **51/51 passed**
- `npm run build`: **Compiled successfully, 13/13 static pages generated**
- `pipeline/backfill.py --fund-id motilal-oswal-midcap-fund --start 2026-07 --end 2026-08`: **Success, diff created**

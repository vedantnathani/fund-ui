# Phase 14 — Modular AMC Scraper & Multi-Fund Backfill

**Milestone**: v1.2 (Multi-AMC Architecture & Scalability)  
**Status**: ✅ Completed (2026-10-02)  
**Goal**: Decouple the scraping and discovery pipeline from PPFAS-specific assumptions, introduce an AMC strategy pattern in `pipeline/scrape.py`, implement automated factsheet discovery for Motilal Oswal via their public AEM document API, add a custom URL override escape hatch in `config/funds.json` for WAF-protected AMCs (like HDFC), and backfill historical months to produce active MoM diffs and trend charts.

---

## Context

### What exists today
- `Scraper` in `pipeline/scrape.py` only implements `discover_ppfas_links(page_html, base_url)`, expecting a static HTML page with anchor tags matching PPFAS URL patterns.
- `pipeline/backfill.py` (line 243) and `pipeline/run.py` (line 76) explicitly call `scraper.discover_ppfas_links(...)`.
- Non-PPFAS funds (like `motilal-oswal-midcap-fund`) discover 0 links during automated runs because their portals use client-side rendering (Adobe Experience Manager) where static HTML contains no links.
- `PDFTextParser` was already upgraded to handle 2-column split-table formats (`Scrip` + `Weightage (%)`) and dynamic scheme title resolution.
- `motilal-oswal-midcap-fund` currently has only 1 month (`2026-08`), meaning no month-over-month diffs or trend lines can be rendered yet on the UI.

### What Phase 14 adds
1. **Polymorphic Discovery Routing (`discover_links`)**: `Scraper.discover_links(fund_config, start_month=None, end_month=None)` inspects `fund["amc"]` or `fund.get("strategy")` and delegates to the appropriate discovery implementation.
2. **Motilal Oswal Discovery Strategy (`discover_motilal_links`)**: Queries Motilal Oswal's public AEM search API (`/content/aem-cloud-dept-backend-motilal-oswal/api/search-documents.json?searchQuery=factsheet&type=`) to retrieve active monthly factsheet PDFs without requiring headless browser automation.
3. **Custom URL & WAF Escape Hatch (`discover_custom_links`)**: Allows `config/funds.json` to specify `monthly_urls` (e.g. for HDFC or other AMCs protected by Akamai WAF/CAPTCHAs) so direct factsheet links can be supplied manually or via external mirrors.
4. **Decoupled Runners**: `pipeline/backfill.py` and `pipeline/run.py` call `scraper.discover_links(fund, start_month, end_month)` uniformly.
5. **Multi-Month Backfill for Motilal Oswal**: Backfills 2026-07 and 2026-08 to produce the first MoM holding delta (e.g. One 97 Communications increasing from 8.1% to 9.1%), verifying diff generation, charts, and table badges.
6. **Comprehensive Unit Tests**: Adds `pipeline/tests/test_amc_scraper.py` testing routing, Motilal JSON response parsing, date filtering, and fallback mechanisms.

---

## Tasks

### Task 14.1 — Implement AMC Strategy Dispatcher & Motilal Discovery
**File**: `pipeline/scrape.py`  
**What**:
1. Add `discover_links(fund_config: Dict[str, Any], start_month: Optional[str] = None, end_month: Optional[str] = None) -> List[Dict[str, Any]]`:
   - Checks `fund_config.get("monthly_urls")` first; if present, yields custom mapped URLs.
   - If AMC contains `"ppfas"`, calls `discover_ppfas_links`.
   - If AMC contains `"motilal"`, calls `discover_motilal_links`.
   - Otherwise, attempts `discover_ppfas_links` as generic fallback or logs an informative warning.
2. Implement `discover_motilal_links(fund_config: Dict[str, Any], start_month: Optional[str] = None, end_month: Optional[str] = None) -> List[Dict[str, Any]]`:
   - Queries `https://www.motilaloswalmf.com/content/aem-cloud-dept-backend-motilal-oswal/api/search-documents.json?searchQuery=factsheet&type=` using `self.session`.
   - Filters results where `category == "factsheet"`, `path.endswith(".pdf")`, and `active` is present in path or title.
   - Extracts `month_str` via `parse_month_year(path)` or `parse_month_year(title)`.
   - Filters by date window `[start_month, end_month]` if provided.
   - Yields dicts: `{"month": month_str, "excel_url": None, "pdf_url": full_url}`.
   - De-duplicates by `month` and sorts descending.
3. Implement `discover_custom_links(fund_config: Dict[str, Any], start_month: Optional[str] = None, end_month: Optional[str] = None) -> List[Dict[str, Any]]`:
   - Reads `fund_config.get("monthly_urls", {})` where keys are `YYYY-MM` and values are `{ "pdf": "...", "excel": "..." }` (or direct strings).

**Acceptance**: Running `python3 pipeline/scrape.py --fund-id motilal-oswal-midcap-fund --dry-run` discovers available factsheet months without error.

---

### Task 14.2 — Refactor Backfill CLI & Daily Pipeline Runner
**Files**: `pipeline/backfill.py`, `pipeline/run.py`  
**What**:
1. In `pipeline/backfill.py` (`run_online_backfill`):
   - Replace lines calling `scraper.fetch_page(...)` and `scraper.discover_ppfas_links(...)` with:
     ```python
     discovered = scraper.discover_links(fund, start_month=start_month, end_month=end_month)
     ```
2. In `pipeline/run.py` (`run_fund_pipeline`):
   - Replace `scraper.discover_ppfas_links(page_html, source_page)` with:
     ```python
     discovered = scraper.discover_links(fund)
     ```
3. Update `pipeline/tests/test_backfill_cli.py` to ensure mock expectations match `scraper.discover_links`.

**Acceptance**: `python3 pipeline/backfill.py --fund-id motilal-oswal-midcap-fund --start 2026-07 --end 2026-08 --dry-run` resolves both months cleanly.

---

### Task 14.3 — Add Direct URL Config Support to `config/funds.json`
**File**: `config/funds.json`  
**What**:
1. Document and enable `monthly_urls` optional property in fund schema.
2. Ensure existing funds (`ppfas-flexicap`, `ppfas-taxsaver`, `motilal-oswal-midcap-fund`) continue working smoothly without modification.
3. Validate format so that any new AMC added with WAF protection can supply `monthly_urls`.

**Acceptance**: Config loads cleanly in Python validator and Next.js data layer.

---

### Task 14.4 — Unit Tests for Modular AMC Scraper
**File**: `pipeline/tests/test_amc_scraper.py` (new file)  
**What**:
1. `test_discover_links_ppfas_routing`: Verifies that PPFAS fund routes to `discover_ppfas_links`.
2. `test_discover_links_motilal_routing`: Verifies that Motilal fund queries the AEM search documents endpoint and parses records correctly.
3. `test_discover_links_custom_urls`: Verifies that `monthly_urls` in `fund_config` are returned directly and filtered by date range.
4. `test_motilal_date_filtering`: Verifies that `start_month` and `end_month` filter Motilal API results properly.
5. `test_motilal_api_error_handling`: Verifies graceful failure (empty list + logged error) when API is unreachable or returns 500.

**Acceptance**: `python3 -m pytest pipeline/tests/test_amc_scraper.py -v` passes 100%.

---

### Task 14.5 — Backfill Motilal Historical Months & Verify Diff Engine
**Files**: `data/motilal-oswal-midcap-fund/`, `data/index.json`  
**What**:
1. Run backfill for `motilal-oswal-midcap-fund` for `2026-07` and `2026-08`:
   ```bash
   python3 pipeline/backfill.py --fund-id motilal-oswal-midcap-fund --start 2026-07 --end 2026-08
   ```
2. Verify:
   - `data/motilal-oswal-midcap-fund/2026-07.json` is generated (initial snapshot, no diff).
   - `data/motilal-oswal-midcap-fund/2026-08.json` is updated with `diff_from_previous` containing changes (e.g. One 97 Communications weight change, top 10 turnover).
   - `data/index.json` lists `2026-07` and `2026-08` for `motilal-oswal-midcap-fund`.
3. Run `npm run build` in `web/` to confirm static generation and TypeScript types succeed with multiple months.

**Acceptance**: Web dashboard displays 2-month history for Motilal Oswal Midcap Fund with working diff table and trend charts.

---

## Verification Checklist

- [ ] `python3 pipeline/scrape.py --fund-id motilal-oswal-midcap-fund --dry-run` discovers Motilal factsheet links
- [ ] `python3 pipeline/scrape.py --fund-id ppfas-flexicap --dry-run` still discovers PPFAS links (no regression)
- [ ] `python3 pipeline/backfill.py --fund-id motilal-oswal-midcap-fund --start 2026-07 --end 2026-08` backfills both months
- [ ] `data/motilal-oswal-midcap-fund/2026-08.json` contains valid `diff_from_previous`
- [ ] `python3 -m pytest pipeline/tests/ -v` all tests pass (≥ 50 tests)
- [ ] `npm run build` succeeds in `web/`

---

## Files Changed

| File | Change |
|------|--------|
| `pipeline/scrape.py` | Add `discover_links()`, `discover_motilal_links()`, `discover_custom_links()` |
| `pipeline/backfill.py` | Replace hardcoded `discover_ppfas_links` with `discover_links` |
| `pipeline/run.py` | Replace hardcoded `discover_ppfas_links` with `discover_links` |
| `config/funds.json` | Support optional `monthly_urls` |
| `pipeline/tests/test_amc_scraper.py` | New unit tests for multi-AMC discovery and routing |
| `pipeline/tests/test_backfill_cli.py` | Adapt mocks to `discover_links` |
| `data/motilal-oswal-midcap-fund/2026-07.json` | Generated July 2026 snapshot |
| `data/motilal-oswal-midcap-fund/2026-08.json` | Updated August 2026 snapshot with MoM diff |
| `data/index.json` | Updated fund index with multiple months for Motilal |

# Step 0 — PPFAS Factsheet Page Inspection Report

**Date**: 2026-10-02
**URL inspected**: https://amc.ppfas.com/downloads/factsheet/

---

## (a) How factsheet links are structured per month

The page uses a **two-level hierarchy**:

### Level 1: Year Tabs
A Bootstrap nav-pills tab bar across the top with tabs for each year (2026, 2025, 2024, ... back to 2013). Each tab shows a different year's worth of months.

### Level 2: Monthly Accordion Cards
Within each year tab, months are listed as Bootstrap accordion cards (newest first). Each card has:
- **Header**: "Factsheet - {Month} {Year}" (e.g., "Factsheet - August 2026")
- **Body** (3 links):
  1. **"View Digital Factsheet"** — Links to an interactive web page: `/downloads/digital-factsheet/2026/august-2026/`
  2. **"Download Factsheet"** — Direct PDF download: `/downloads/factsheet/2026/ppfas-mf-factsheet-for-August-2026.pdf?10092026`
  3. **"Detailed Portfolio Disclosure"** — XLS download: `/downloads/portfolio-disclosure/2026/PPFAS_Monthly_Portfolio_Report_August_31_2026.xls?10092026`

### URL Patterns
| Type | Pattern |
|------|---------|
| PDF Factsheet | `/downloads/factsheet/{YYYY}/ppfas-mf-factsheet-for-{Month}-{YYYY}.pdf?{cache_buster}` |
| Portfolio XLS | `/downloads/portfolio-disclosure/{YYYY}/PPFAS_Monthly_Portfolio_Report_{Month}_{DD}_{YYYY}.xls?{cache_buster}` |
| Digital Factsheet | `/downloads/digital-factsheet/{YYYY}/{month}-{YYYY}/` |

The `?DDMMYYYY` query parameter is a cache buster representing the publication date (e.g., `?10092026` = published on September 10, 2026).

---

## (b) Detailed Portfolio Disclosure — file type and availability

- **File type**: `.xls` (Excel 97-2003 format, NOT `.xlsx`)
- **Available per month**: Yes, every month has a "Detailed Portfolio Disclosure" link
- **Content**: Complete portfolio for ALL PPFAS funds in one file. Contains ISIN codes, sector classification, and exact weight percentages.
- **URL pattern**: `/downloads/portfolio-disclosure/{YYYY}/PPFAS_Monthly_Portfolio_Report_{Month}_{DD}_{YYYY}.xls`
- **Date in filename**: Uses the last calendar day of the month (e.g., `August_31_2026`, `February_28_2026`)

**This is the preferred parsing source** because:
1. Structured tabular data (no PDF parsing ambiguity)
2. Contains ISIN codes
3. Contains sector classifications
4. Exact decimal weight percentages

---

## (c) Does the page need JavaScript to render?

**No.** The page is server-side rendered HTML. All year tabs, month accordions, and download links are present in the initial HTML response. BeautifulSoup can parse all links without JavaScript execution.

Note: The page does include Cloudflare challenge scripts (`/cdn-cgi/challenge-platform/scripts/jsd/main.js`), but these are for bot protection, not for rendering content. Standard requests with a proper User-Agent header should work. If Cloudflare blocks us, we may need to use `cloudscraper` or set specific headers, but this is unlikely for a simple GET request.

---

## (d) How the page handles multiple funds in one factsheet

### PDF Factsheet
- **Single combined PDF** for all PPFAS funds (Flexi Cap, ELSS Tax Saver, Liquid)
- Each fund has its own section within the PDF
- The parser must locate the correct section using `section_keyword` from `config/funds.json` (e.g., `"Flexi Cap"`)
- The meta description confirms this: "Factsheets of Parag Parikh Flexi Cap Fund - An Open Ended Equity Scheme"

### Portfolio Disclosure Excel
- Single XLS file for all funds
- Likely uses separate sheets per fund, or separate sections within one sheet identified by fund name
- Parser filters by fund name to extract the correct top 10

### Website Navigation
The PPFAS site has separate navigation items for each fund:
- Parag Parikh Flexi Cap Fund
- Parag Parikh ELSS Tax Saver Fund  
- Parag Parikh Liquid Fund

But the factsheet download page serves ONE factsheet per month for ALL funds.

---

## (e) Fixture files downloaded

| File | Size | Month | Type |
|------|------|-------|------|
| `factsheet-2026-06.pdf` | 3.7 MB | June 2026 | Combined PDF factsheet |
| `factsheet-2026-07.pdf` | 19 MB | July 2026 | Combined PDF factsheet |
| `factsheet-2026-08.pdf` | 4.0 MB | August 2026 | Combined PDF factsheet |
| `portfolio-disclosure-2026-08.xls` | 395 KB | August 2026 | Portfolio disclosure Excel |

**Observation**: July 2026 factsheet is abnormally large (19 MB vs ~4 MB for others). May contain high-res images or additional content. Parser should handle this gracefully.

---

## (f) Proposed parser strategy

| Priority | Parser | Source | When to Use |
|----------|--------|--------|-------------|
| 1 (Primary) | `excel.py` | Portfolio Disclosure XLS | When XLS is available (most months) |
| 2 (Fallback) | `pdf_text.py` | Factsheet PDF | When XLS is unavailable or fails |
| 3 (Last resort) | `ocr_fallback.py` | Scanned PDF | Only if PDF has no text layer (not expected for PPFAS) |

### Parsing approach for each:

**Excel (`pandas`)**:
1. Read the XLS file with `pd.read_excel()` (engine `xlrd` for `.xls`)
2. Identify the sheet/section for the target fund
3. Filter to equity holdings only
4. Sort by weight descending
5. Take top 10
6. Extract: rank, name, ISIN, sector, weight_pct

**PDF (`pdfplumber`)**:
1. Open PDF, iterate pages
2. Search for `section_keyword` (e.g., "Flexi Cap") to find the right section
3. Look for "Top 10 Holdings" or similar table header
4. Extract table using pdfplumber's table extraction
5. Parse into structured holdings data

---

## Conclusion

The PPFAS site is straightforward to scrape:
- ✅ Server-rendered HTML, no JS needed
- ✅ Consistent URL patterns
- ✅ Both PDF and Excel available per month
- ✅ Excel is highly structured with ISIN
- ⚠️ Single factsheet per month for all funds — parser must section-filter
- ⚠️ Cloudflare is present — may need `cloudscraper` if basic requests are blocked

**Recommendation**: Proceed with Phase 2 (Scraper + Parser + Validator) using the Excel parser as primary.

# REQUIREMENTS: Mutual Fund Top-10 Holdings Tracker

## Functional Requirements

### FR-1: Fund Registry (Config-Driven)
- **FR-1.1**: A `config/funds.json` file defines all tracked funds with: id, amc, name, type, source_page URL, section matching rules, parser type, name aliases, and significant_change threshold.
- **FR-1.2**: Adding a new fund requires only adding a JSON entry (plus a custom parser only if the AMC layout is genuinely different).
- **FR-1.3**: Non-equity funds (e.g., Liquid) can be listed but are skipped by the pipeline when `type != "equity"`.

### FR-2: Scraper
- **FR-2.1**: Use plain HTTP (`requests` + `BeautifulSoup`) to scrape the AMC's factsheet download page. No Playwright unless page truly needs JavaScript.
- **FR-2.2**: Detect the reporting month from the link text or file contents, not from the download date.
- **FR-2.3**: Idempotent: if `data/{fund}/{YYYY-MM}.json` already exists, skip that month.
- **FR-2.4**: Store the source URL and a SHA-256 hash of the downloaded file in the snapshot.
- **FR-2.5**: Polite scraping: set a User-Agent header, add retries with exponential backoff, fetch only what's needed.
- **FR-2.6**: Prefer the "Detailed Portfolio Disclosure" Excel file when available; fall back to the PDF factsheet.

### FR-3: Parser
- **FR-3.1**: Excel parser (primary for PPFAS): Read XLS with pandas, identify fund sheet/section, sort by weight, extract top 10 with: rank, name, ISIN, sector, weight_pct.
- **FR-3.2**: PDF text parser (fallback): Use pdfplumber (fallback PyMuPDF) to extract tables. Locate the correct fund section via `section_keyword`. Extract top 10 holdings.
- **FR-3.3**: OCR fallback: Behind a flag, used ONLY if a PDF has no text layer. Not a default dependency.
- **FR-3.4**: Extract AMC commentary text if present: stated "top 10 holdings total %" and stated additions/exits (stored verbatim as `amc_commentary`).

### FR-4: Validation
- **FR-4.1**: Exactly 10 holdings extracted.
- **FR-4.2**: All weights are numbers between 0 and 30 (percentage points).
- **FR-4.3**: Ranks are consistent with descending weight order.
- **FR-4.4**: Sum of 10 weights matches AMC-stated "top 10 total" within ±0.1pp (when that statement exists).
- **FR-4.5**: Names are normalized (case, "Ltd/Limited", "&/and", punctuation) and mapped through `aliases`.
- **FR-4.6**: Prefer ISIN as the canonical key when available; otherwise use the normalized name.
- **FR-4.7**: On validation failure: do NOT commit a snapshot. Open a GitHub Issue or fail the workflow with the reason.

### FR-5: Snapshot Schema
Each `data/{fund_id}/{YYYY-MM}.json` contains:
```json
{
  "fund_id": "ppfas-flexicap",
  "as_of": "2026-08-31",
  "source_url": "https://...",
  "file_sha256": "abc123...",
  "top10_total_pct": 48.5,
  "amc_commentary": "...",
  "holdings": [
    { "rank": 1, "key": "INE...", "name": "...", "isin": "INE...", "sector": "...", "weight_pct": 8.2 }
  ]
}
```

### FR-6: Diff Engine
- **FR-6.1**: Pure Python, no LLM. Compare current month's snapshot against the previous month's snapshot.
- **FR-6.2**: Identify: `entered_top10` (holdings now in top 10 that weren't last month), `exited_top10` (holdings that left the top 10).
- **FR-6.3**: Label as "entered top 10" / "exited top 10", NOT as "newly bought" or "sold". Only say "added to portfolio" when AMC commentary explicitly says so.
- **FR-6.4**: For holdings in both months: calculate weight delta (in percentage points) and rank change.
- **FR-6.5**: Flag `significant` when |delta| >= fund's `significant_change_pp`.
- **FR-6.6**: Use wording "weight increased/decreased", never "bought more" — weight changes can come from price movement.
- **FR-6.7**: Output to `data/{fund_id}/{YYYY-MM}.diff.json`.

### FR-7: LLM Summary
- **FR-7.1**: Provider pluggable via env var (`LLM_PROVIDER`). Default: OpenRouter free models. Also support Gemini free tier, Groq.
- **FR-7.2**: Input: ONLY the diff JSON + AMC commentary. No external data.
- **FR-7.3**: Prompt: "Use only the numbers provided. Do not add outside facts, predictions or advice."
- **FR-7.4**: Output: 3-5 plain-language sentences summarizing the diff.
- **FR-7.5**: Post-check: Extract every number in the LLM output and confirm it exists in the diff JSON. If any fabricated number found, discard output.
- **FR-7.6**: Fallback: If API fails or post-check fails, generate a deterministic template summary.
- **FR-7.7**: Pipeline must NEVER fail just because the LLM did.

### FR-8: Dashboard
- **FR-8.1**: Home page: Grid of fund cards showing latest month, number of top-10 changes, biggest mover. Search/filter by AMC.
- **FR-8.2**: Fund page: Top 10 table with weight, delta vs last month (green/red arrows), rank change. "Changes" panel (entered/exited, significant moves). AI summary clearly labeled. AMC commentary. Link to source factsheet.
- **FR-8.3**: History chart: Weight over time for each current top-10 holding (Recharts line chart, selectable range).
- **FR-8.4**: Month selector to view past months.
- **FR-8.5**: Responsive, dark mode, fast.
- **FR-8.6**: Footer disclaimer: "Informational only. Not investment advice. Data from AMC factsheets; verify against the source."
- **FR-8.7**: "Last updated" timestamp and data source on every page.

### FR-9: GitHub Actions Workflow
- **FR-9.1**: Scheduled cron: Twice daily (6:00 AM IST / 00:30 UTC and 6:00 PM IST / 12:30 UTC) during days 3-20 of each month.
- **FR-9.2**: Manual `workflow_dispatch` trigger available.
- **FR-9.3**: A run with nothing new must exit cleanly with no commit.
- **FR-9.4**: On success with new data: commit snapshots and diffs to `/data`, which triggers Vercel redeploy.

### FR-10: Backfill
- **FR-10.1**: One-off script to ingest the last 12 months of factsheets.
- **FR-10.2**: Populates history so charts and diffs work from day one.

## Non-Functional Requirements

### NFR-1: Cost
- Everything must be 100% free: no paid APIs, no paid hosting, no credit card required.

### NFR-2: Reliability
- Validation-first: Reject bad data rather than store it.
- Idempotent: Re-running the pipeline produces the same result.
- Graceful degradation: LLM failures don't break the pipeline.

### NFR-3: Performance
- Dashboard loads fast (static generation from JSON at build time).
- Pipeline completes within GitHub Actions free-tier time limits.

### NFR-4: Observability
- Structured logs in the pipeline.
- `--dry-run` flag for local testing without writing or committing.

### NFR-5: Testing
- Unit tests for parser (using saved real fixtures), validator, and diff engine.
- Test cases for: Google→Alphabet rename alias, month with no changes.

### NFR-6: Documentation
- README with: setup instructions, how to add a fund, how to add secrets, how to run locally.

## UAT Criteria
1. ✅ PPFAS Flexi Cap Fund top 10 extracted correctly from August 2026 fixture
2. ✅ Validation rejects a snapshot with only 9 holdings
3. ✅ Diff engine correctly identifies holdings that entered/exited top 10
4. ✅ Alias mapping resolves "Google" → "Alphabet Inc"
5. ✅ LLM summary contains only numbers from the diff JSON
6. ✅ Fallback template summary generated when LLM fails
7. ✅ Dashboard displays fund card grid with correct data
8. ✅ History chart shows weight trends over multiple months
9. ✅ Adding a second fund via config only works without code changes
10. ✅ GitHub Actions workflow runs end-to-end and commits data

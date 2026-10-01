# PROJECT: Mutual Fund Top-10 Holdings Tracker

## Vision
A system that monitors mutual fund monthly factsheets, extracts each fund's TOP 10 equity holdings, compares them with the previous month, and shows everything on a premium dashboard. Starts with PPFAS Mutual Fund and scales to many funds/AMCs via a config file.

## Current State
- **Shipped Version**: v1.0 (2026-10-02) ✅
- **Active Milestone**: v1.1 — Fund Manager UI & Production Deployment (in planning)
- **Status**: v1.0 production-ready. v1.1 adds self-service fund management from the UI, parameterized backfill by period, and full Vercel deployment.
- **Milestone Archive**: [`.planning/milestones/v1.0-ROADMAP.md`](milestones/v1.0-ROADMAP.md) | [`.planning/v1.0-MILESTONE-AUDIT.md`](v1.0-MILESTONE-AUDIT.md)

## Architecture

```
GitHub Actions cron (daily, days 3-20)
    → scraper (find new factsheet on AMC page)
    → parser (extract top 10 from PDF/Excel)
    → validator (reject bad data loudly)
    → snapshot JSON committed to /data
    → diff engine (vs previous month, pure Python)
    → LLM summary (free tier, from diff only)
    → commit to repo
    → Vercel redeploys dashboard automatically
```

### Key Architectural Decisions
1. **Vercel is read-only**: No scraping, parsing, OCR, or heavy compute in Vercel functions. Vercel only serves the Next.js dashboard and reads pre-computed JSON from `/data` at build time.
2. **GitHub Actions is the compute engine**: All heavy work (HTTP scraping, PDF parsing, diffing, LLM calls) runs in scheduled GitHub Actions workflows (Python 3.11).
3. **JSON-as-database**: Storage is JSON files committed to the repo under `/data`. Each commit triggers a Vercel redeploy. No external database.
4. **LLM is narration only**: The LLM summarizes already-computed diffs. It never computes, extracts, or invents numbers. Code-based diff is the source of truth.
5. **Config-driven scalability**: Adding a new fund = adding a JSON entry to `config/funds.json`. No code changes unless the AMC has a genuinely different layout.

## Tech Stack
| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Pipeline | Python 3.11, pdfplumber, pandas, requests, BeautifulSoup | Runs in GitHub Actions, free |
| Dashboard | Next.js (App Router), TypeScript, Tailwind CSS, Recharts | Deploys on Vercel Hobby, free |
| CI/CD | GitHub Actions | Free for public repos |
| Hosting | Vercel Hobby | Free, auto-deploys on commit |
| LLM | OpenRouter free models (pluggable via env var) | Free tier, fallback to template |
| Storage | JSON files in repo `/data` | Zero cost, version-controlled |

## Hard Constraints
- **100% free stack**: No paid APIs, no paid hosting, no credit card required.
- **No heavy compute on Vercel**: No GPU, small function size, short timeouts.
- **Idempotent pipeline**: If data already exists for a month, skip it.
- **Validation-first**: Reject and fail loudly rather than store bad data.
- **No OCR by default**: PPFAS factsheets are digital PDFs with text layers. OCR is an optional fallback only.
- **Precise language**: "entered/exited top 10" ≠ "bought/sold". Weight changes ≠ trades.

## Scope
### In Scope
- PPFAS Flexi Cap Fund (initial), scalable to any equity fund
- Monthly factsheet scraping, parsing, validation
- Top-10 holdings extraction with rank, name, ISIN, sector, weight%
- Month-over-month diff engine
- AI-generated summaries with number verification
- Premium dark-mode dashboard with history charts
- Backfill script for 12 months of history
- GitHub Actions scheduled workflow

### Out of Scope
- Real-time or daily NAV tracking
- Full portfolio analysis (beyond top 10)
- Trading signals or investment advice
- Mobile app (web-responsive only)
- User accounts or authentication

## Target Users
- Individual investors tracking mutual fund portfolio changes
- Financial bloggers and analysts
- Fund comparison researchers

## Repository Structure
```
/config/funds.json            # Registry of funds
/pipeline/                    # Python pipeline
  scrape.py  parse.py  validate.py  diff.py  summarize.py  run.py
  parsers/  (pdf_text.py, excel.py, ocr_fallback.py)
  tests/ + tests/fixtures/    # Real sample files from AMC sites
/data/{fund_id}/{YYYY-MM}.json   # Monthly snapshots
/data/{fund_id}/{YYYY-MM}.diff.json  # Monthly diffs
/data/index.json              # Fund index for dashboard
/web/                         # Next.js app
/.github/workflows/pipeline.yml
```

## Research Findings (Step 0 Inspection)

### PPFAS Factsheet Page Analysis
- **URL**: https://amc.ppfas.com/downloads/factsheet/
- **Page rendering**: Server-side HTML. No JavaScript required to access links. Plain HTTP (requests + BeautifulSoup) works.
- **Structure**: Year tabs (2026, 2025, ... back to 2013) → Monthly accordion cards within each year tab.
- **Each month has 3 links**:
  1. "View Digital Factsheet" — interactive web page (not useful for parsing)
  2. "Download Factsheet" — PDF file, e.g. `/downloads/factsheet/2026/ppfas-mf-factsheet-for-August-2026.pdf?10092026`
  3. "Detailed Portfolio Disclosure" — XLS file, e.g. `/downloads/portfolio-disclosure/2026/PPFAS_Monthly_Portfolio_Report_August_31_2026.xls?10092026`
- **Month detection**: From the link text ("Factsheet - August 2026") and the URL path (`August-2026`).
- **Cache busters**: URLs have `?DDMMYYYY` query params (publication date).
- **Multiple funds in one factsheet**: The PDF factsheet is a single combined document covering ALL PPFAS funds (Flexi Cap, ELSS Tax Saver, Liquid). The parser must locate the correct section using `section_keyword` from config (e.g., "Flexi Cap").
- **Portfolio Disclosure Excel**: Contains the complete portfolio for all funds. One sheet per fund. Sorted by holding weight. Includes ISIN. **This is the preferred parsing source** (more structured, includes ISIN).

### Fixture Files Already Downloaded
| File | Size | Description |
|------|------|-------------|
| `factsheet-2026-06.pdf` | 3.7 MB | June 2026 combined factsheet |
| `factsheet-2026-07.pdf` | 19 MB | July 2026 combined factsheet |
| `factsheet-2026-08.pdf` | 4.0 MB | August 2026 combined factsheet |
| `portfolio-disclosure-2026-08.xls` | 395 KB | August 2026 full portfolio (Excel) |

### Parser Strategy
1. **Primary**: Excel parser (`excel.py`) — Parse the "Detailed Portfolio Disclosure" XLS with pandas. Filter to the relevant fund (via sheet name or fund name column), sort by weight descending, take top 10. This gives us ISIN, exact weights, and sector.
2. **Fallback**: PDF text parser (`pdf_text.py`) — Use pdfplumber to extract text/tables from the factsheet PDF. Locate the "Flexi Cap" section, find the "Top 10 Holdings" table. More fragile but available for months where Excel isn't present.
3. **OCR**: Not needed. PPFAS factsheets are digital PDFs with embedded text. OCR fallback exists behind a flag for future AMCs that might use scanned PDFs.

## Configuration
- **Cron schedule**: Twice daily (6:00 AM IST / 00:30 UTC and 6:00 PM IST / 12:30 UTC) during days 3-20 of each month, plus manual `workflow_dispatch`.
- **LLM provider**: OpenRouter free models (default), pluggable via `LLM_PROVIDER` env var. Gemini and Groq also supported.
- **Dashboard design**: Dark mode primary with glassmorphism cards, green/red accent colors for gains/losses, Inter font.

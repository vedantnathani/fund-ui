# ROADMAP: Mutual Fund Top-10 Holdings Tracker

## Milestone 1: Core Pipeline (v0.1)

### Phase 1: Step 0 — Live Site Inspection & Fixture Validation ✅
**Status**: DONE
**Goal**: Inspect the PPFAS factsheet page structure, download test fixtures, determine parser strategy.
**Deliverables**:
- Inspection report in PROJECT.md (page structure, link patterns, JS requirement, multi-fund handling)
- 3 factsheet PDFs + 1 portfolio disclosure XLS downloaded as fixtures
- Parser strategy determined: Excel primary, PDF fallback

### Phase 2: Scraper + Parser + Validator ✅
**Status**: DONE
**Goal**: Build the complete extraction pipeline for PPFAS Flexi Cap, validated against real fixtures.
**Deliverables**:
- `config/funds.json` — fund registry with PPFAS Flexi Cap entry
- `pipeline/scrape.py` — HTTP scraper with BeautifulSoup, idempotent, polite
- `pipeline/parsers/excel.py` — Excel parser using pandas (primary)
- `pipeline/parsers/pdf_text.py` — PDF text/table parser using pdfplumber (fallback)
- `pipeline/parsers/ocr_fallback.py` — Stub, behind feature flag
- `pipeline/parse.py` — Parser orchestrator (selects parser based on config)
- `pipeline/validate.py` — Validates extracted holdings (count, weights, ranks, sum check, name normalization, aliases)
- `pipeline/tests/` — Unit tests for parser (Excel + PDF), validator, alias resolution
- Passing tests against real fixture files

### Phase 3: Diff Engine + Snapshots + Backfill ✅
**Status**: DONE
**Goal**: Generate month-over-month diffs and backfill 12 months of history.
**Deliverables**:
- `pipeline/diff.py` — Pure Python diff engine (entered/exited top 10, weight deltas, rank changes, significant flags)
- Snapshot JSON files written to `data/ppfas-flexicap/{YYYY-MM}.json`
- Diff JSON files written to `data/ppfas-flexicap/{YYYY-MM}.diff.json`
- `data/index.json` — Fund index for dashboard consumption
- `pipeline/backfill.py` — One-off script for last 12 months
- Unit tests for diff engine (including no-changes month)
- `--dry-run` flag support

### Phase 4: GitHub Actions Workflow ✅
**Status**: DONE
**Goal**: Automate the pipeline with scheduled GitHub Actions.
**Deliverables**:
- `.github/workflows/pipeline.yml` — Scheduled cron (2x daily during days 3-20), manual dispatch
- Python dependency caching
- Commit + push of new data files
- Clean exit when nothing new
- Structured logging output

### Phase 5: Dashboard
**Status**: TODO
**Goal**: Build and deploy the premium Next.js dashboard on Vercel.
**Deliverables**:
- `web/` — Next.js app (App Router, TypeScript, Tailwind CSS, Recharts)
- Home page: Fund card grid with search/filter
- Fund detail page: Top 10 table, changes panel, month selector
- History chart: Weight trends over time
- Dark mode, glassmorphism design, Inter font, green/red accents
- Responsive layout, footer disclaimer, "last updated" timestamps
- Deployed on Vercel Hobby tier

### Phase 6: LLM Summary
**Status**: TODO
**Goal**: Add AI-generated summaries with number verification and fallback.
**Deliverables**:
- `pipeline/summarize.py` — Pluggable LLM provider (OpenRouter default, Gemini, Groq)
- Number extraction post-check (verify against diff JSON)
- Deterministic template fallback
- Summary stored in diff JSON, displayed on dashboard with "AI-generated" label
- Integration tests

### Phase 7: Scalability Proof — Second Fund
**Status**: TODO
**Goal**: Add a second fund via config only to prove the system scales.
**Deliverables**:
- New entry in `config/funds.json` for a second equity fund
- Pipeline processes both funds without code changes
- Dashboard displays both funds
- Documentation of the process

## Milestone 2: Polish & Documentation (v1.0)

### Phase 8: README & Documentation
**Status**: TODO
**Goal**: Complete project documentation.
**Deliverables**:
- README.md with setup, add-a-fund guide, secrets guide, local run guide
- Architecture diagram
- Contribution guide

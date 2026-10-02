# ROADMAP: Mutual Fund Top-10 Holdings Tracker

## Milestones

- **[Milestone v1.0 (Core Pipeline & Web Dashboard)](milestones/v1.0-ROADMAP.md)** — Shipped 2026-10-02 (8 phases, 37 tests, 2 funds live) ✅

---

## Milestone v1.1 — Fund Manager UI & Production Deployment

**Goal**: Self-service fund management from the UI + production deployment on Vercel.

### Phase 9 — Backfill CLI Enhancements
Make `pipeline/backfill.py` accept `--start`, `--end`, `--fund-id` CLI arguments. Update `backfill.yml` GitHub Actions workflow to accept `workflow_dispatch` inputs and pass them through. Add unit tests.

### Phase 10 — GitHub Actions: Backfill & Register-Fund Workflows
Create `backfill.yml` (period-aware, parameterized) and `register-fund.yml` (auto-triggered on `config/funds.json` changes) workflows. Wire up secrets (`GH_PAT`).

### Phase 11 — Fund Manager UI (Add / Edit / Remove Funds)
Build the `/manage` admin page in Next.js: fund list with status, "Add Fund" form (with GitHub API commit on submit), soft-delete toggle, and inline PAT setup guide when env var is missing.

### Phase 12 — Backfill Period Picker UI
Add "Fetch Data" button to fund cards and fund detail page. Implement month/year range picker modal. Wire up GitHub Actions `workflow_dispatch` API call. Show confirmation with Actions run link.

### Phase 13 — Vercel Production Deployment
Add `vercel.json`, document all env vars, connect repo to Vercel Hobby, validate Lighthouse scores ≥ 90, update README with full deploy guide.

---

## Milestone v1.2 — Multi-AMC Architecture & Historical Backfill

**Goal**: Decouple factsheet discovery from PPFAS, build a modular AMC scraper architecture with native Motilal Oswal AEM support and manual WAF overrides, and enable multi-month historical backfills.

### Phase 14 — Modular AMC Scraper & Multi-Fund Backfill
Implement `discover_links` router in `pipeline/scrape.py` delegating to PPFAS HTML parsing, Motilal Oswal AEM document search API, and manual `monthly_urls` overrides. Update `pipeline/backfill.py` and `pipeline/run.py` to use dynamic discovery. Add comprehensive unit tests and backfill Motilal Oswal historical months to populate MoM holding changes.


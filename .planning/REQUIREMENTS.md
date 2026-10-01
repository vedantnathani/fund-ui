# REQUIREMENTS: v1.1 — Fund Manager UI & Production Deployment

**Milestone**: v1.1  
**Goal**: Make the tracker self-service — users can add funds, trigger backfills, and fetch any period's data directly from the dashboard. Ship to production (Vercel + GitHub).

---

## Functional Requirements

### FR-1: Fund Manager UI (Add/Edit/Remove Funds)

- **FR-1.1**: Dashboard has a "Manage Funds" admin page accessible from the nav.
- **FR-1.2**: Admin page shows all currently tracked funds from `config/funds.json` with their status (active/paused, last scraped month, holdings count).
- **FR-1.3**: "Add Fund" form collects: Fund ID (slug), AMC name, Fund name, Source page URL, Parser type (excel/pdf), Section keyword (for PDF), Significant change threshold (pp).
- **FR-1.4**: On submit, the UI calls the GitHub Contents API to commit the updated `config/funds.json` to the repo (requires a GitHub PAT stored in Vercel env vars).
- **FR-1.5**: After committing `funds.json`, the UI automatically dispatches the `backfill` GitHub Actions workflow for the new fund + default period (last 12 months).
- **FR-1.6**: "Remove Fund" marks a fund as `"active": false` in config (soft delete — preserves historical data).
- **FR-1.7**: Validation: Fund ID must be lowercase-kebab-case, URL must be a valid HTTPS URL, threshold must be 0.1–5.0.
- **FR-1.8**: A GitHub PAT setup guide is shown inline if the PAT env var is missing (graceful degradation — UI is read-only without it).

### FR-2: Backfill Period Picker

- **FR-2.1**: Each fund card and the fund detail page have a "Fetch Data" / "Backfill" button.
- **FR-2.2**: Clicking opens a date range picker: Start Month/Year and End Month/Year (month-granularity).
- **FR-2.3**: On confirm, the UI dispatches a `workflow_dispatch` event to `backfill.yml` with inputs: `fund_id`, `start_month` (YYYY-MM), `end_month` (YYYY-MM).
- **FR-2.4**: The UI shows a "Backfill triggered ✓" confirmation with a link to the Actions run on GitHub.
- **FR-2.5**: `backfill.yml` must accept `fund_id`, `start_month`, `end_month` as `workflow_dispatch` inputs.
- **FR-2.6**: `pipeline/backfill.py` must support `--start YYYY-MM --end YYYY-MM --fund-id <id>` CLI args.

### FR-3: GitHub Actions Workflow Updates

- **FR-3.1**: New `backfill.yml` workflow that accepts `workflow_dispatch` inputs: `fund_id`, `start_month`, `end_month`.
- **FR-3.2**: New `register-fund.yml` workflow: triggered by push to `config/funds.json`; validates and backfills newly added fund.
- **FR-3.3**: Workflows use `GITHUB_TOKEN` or `GH_PAT` secret to commit data back.

### FR-4: Production Deployment (Vercel)

- **FR-4.1**: Next.js app deployed to Vercel with a live public URL.
- **FR-4.2**: Connected to GitHub repo; every push to `main` auto-deploys.
- **FR-4.3**: Required env vars documented: `GH_PAT`, `NEXT_PUBLIC_GITHUB_REPO`, `NEXT_PUBLIC_GITHUB_BRANCH`.
- **FR-4.4**: `vercel.json` present with correct build settings.
- **FR-4.5**: All pages pass Lighthouse score ≥ 90.

### FR-5: UI/UX Polish

- **FR-5.1**: Loading states on all async operations.
- **FR-5.2**: Error toasts with actionable messages.
- **FR-5.3**: Fund Manager shows last-updated status per fund and "No data yet" state for new funds.
- **FR-5.4**: Mobile-responsive: all new UI components work on phones.

---

## Non-Functional Requirements

- **NFR-1**: 100% free stack maintained.
- **NFR-2**: GitHub PAT stored in Vercel env vars only, never exposed client-side raw.
- **NFR-3**: Without PAT env var, dashboard is fully read-only — no crashes.
- **NFR-4**: Backfill workflow re-triggered for same period skips already-existing months.
- **NFR-5**: New GitHub API integration functions have unit tests (mocked). Target: ≥ 45 passing tests total.
- **NFR-6**: README updated with Vercel deploy guide, env var reference, and "Add a Fund" walkthrough.

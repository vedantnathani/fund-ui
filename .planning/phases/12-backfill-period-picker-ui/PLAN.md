# Phase 12 — Backfill Period Picker UI

**Milestone**: v1.1  
**Status**: ⬜ Not started  
**Goal**: Allow users to fetch historical portfolio disclosures for any fund and any date range directly from the web interface by triggering the parameterized `backfill.yml` GitHub Actions workflow via a secure server-side Next.js route handler.

---

## Context

### Existing Capabilities
- **Phase 9**: Added `--start YYYY-MM` and `--end YYYY-MM` date range filtering and idempotency to `pipeline/backfill.py`. 45/45 tests passing.
- **Phase 10**: Created `.github/workflows/backfill.yml` which accepts `workflow_dispatch` inputs: `fund_id`, `start_month`, `end_month`, `dry_run`. Commits data back with `[skip ci]`.
- **Phase 11**: Created `/manage` page, `Toast.tsx`, and `/api/github/update-fund` Route Handler pattern for secure server-side `GH_PAT` operations.

### What This Phase Adds
1. **Dispatch Route Handler** (`web/src/app/api/github/dispatch-backfill/route.ts`):
   - Secure server-side endpoint that reads `GH_PAT` (never exposed to browser)
   - Dispatches `backfill.yml` via GitHub Actions API: `POST /repos/{owner}/{repo}/actions/workflows/backfill.yml/dispatches`
   - Returns run URL so users can track execution live on GitHub Actions
2. **Client helper** (`web/src/lib/github.ts`):
   - Adds `triggerBackfill(params)` client function
3. **`BackfillModal` component** (`web/src/components/BackfillModal.tsx`):
   - Month & Year dropdown pickers (Start Month/Year → End Month/Year)
   - Quick date presets: "Last 6 Months", "Last 12 Months", "Last 3 Years", "Year-to-Date"
   - Scheme selector (supports individual funds or "All Tracked Schemes")
   - Dry run simulation toggle
   - Range validation (`start <= end`, not future beyond current month)
   - Real-time month count calculator and idempotency notice
4. **Integration into Fund Catalog** (`web/src/components/FundCatalog.tsx`):
   - "Fetch Data" button on every fund card
   - Global "Fetch Historical Data" button in catalog banner
5. **Integration into Fund Detail Page** (`web/src/app/fund/[id]/page.tsx` + `web/src/components/BackfillButton.tsx`):
   - "Fetch More Data" button alongside month selector
6. **Integration into Fund Manager** (`web/src/components/FundManager.tsx`):
   - "Fetch Data" quick action on fund table rows

---

## Architecture & Security Model

```
Browser UI (BackfillModal / FundCatalog / FundDetail)
   │
   │  POST /api/github/dispatch-backfill
   │  { fund_id, start_month, end_month, dry_run }
   ▼
Next.js Route Handler (Server-Side)
   │
   │  Reads process.env.GH_PAT (Never sent to client)
   │  Validates YYYY-MM regex, ranges, and fund_id
   │  POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/backfill.yml/dispatches
   ▼
GitHub Actions (backfill.yml)
   │
   │  Runs pipeline/backfill.py --fund-id ... --start ... --end ...
   │  Commits new snapshots with [skip ci]
   ▼
Vercel Auto-Deploy
   │  Pulls latest data on push to main
```

---

## Tasks

### Task 12.1 — Backfill Dispatch Route Handler
**File**: `web/src/app/api/github/dispatch-backfill/route.ts` (new)  
**What**: Next.js POST Route Handler that triggers GitHub Actions `backfill.yml`.

**Logic**:
1. Auth check: Read `GH_PAT` from `process.env`. If missing, return `401 Unauthorized` with clear message:
   `"GitHub PAT not configured. Set GH_PAT in your environment variables to trigger backfills."`
2. Repo check: Read `NEXT_PUBLIC_GITHUB_REPO`. If missing or invalid, return `500`.
3. Read branch from `NEXT_PUBLIC_GITHUB_BRANCH || 'main'`.
4. Parse and validate JSON payload:
   - `fund_id`: required string (`/^[a-z0-9-]+$/` or `'all'`)
   - `start_month`: required string (`/^\d{4}-(0[1-9]|1[0-2])$/`)
   - `end_month`: required string (`/^\d{4}-(0[1-9]|1[0-2])$/`)
   - `dry_run`: optional boolean (default `false`)
   - Validate `start_month <= end_month`
5. Call GitHub REST API:
   `POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/backfill.yml/dispatches`
   Headers:
   - `Authorization: Bearer ${token}`
   - `Accept: application/vnd.github+json`
   - `X-GitHub-Api-Version: 2022-11-28`
   Body:
   ```json
   {
     "ref": branch,
     "inputs": {
       "fund_id": fund_id,
       "start_month": start_month,
       "end_month": end_month,
       "dry_run": Boolean(dry_run)
     }
   }
   ```
6. Handle GitHub response:
   - `204 No Content` → Success! Return:
     ```json
     {
       "success": true,
       "run_url": "https://github.com/{owner}/{repo}/actions/workflows/backfill.yml"
     }
     ```
   - `404` → Return `404` with message that `backfill.yml` was not found on branch.
   - Other → Return `500` with GitHub error details.

**Acceptance**:
- Validates parameters strictly.
- Gracefully returns `401` when `GH_PAT` is missing without crashing.
- Returns `200` with `run_url` on GitHub API `204`.

---

### Task 12.2 — Client GitHub Helper Extension
**File**: `web/src/lib/github.ts` (edit)  
**What**: Add client-side wrapper function `triggerBackfill`:

```ts
export interface BackfillParams {
  fundId: string;
  startMonth: string;
  endMonth: string;
  dryRun?: boolean;
}

export interface BackfillResult {
  success: boolean;
  runUrl?: string;
  error?: string;
}

export async function triggerBackfill(params: BackfillParams): Promise<BackfillResult> {
  try {
    const res = await fetch('/api/github/dispatch-backfill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fund_id: params.fundId,
        start_month: params.startMonth,
        end_month: params.endMonth,
        dry_run: params.dryRun ?? false,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      return { success: false, error: data.error || `HTTP ${res.status}` };
    }
    return { success: true, runUrl: data.run_url };
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Network error occurred',
    };
  }
}
```

**Acceptance**: Types and function exported; calls `/api/github/dispatch-backfill` and normalizes response.

---

### Task 12.3 — `BackfillModal` Client Component
**File**: `web/src/components/BackfillModal.tsx` (new)  
**What**: Interactive modal dialog for configuring and launching a backfill job.

**Design & UI**:
- Dark glassmorphism modal matching existing style (`glass-panel`, rounded-2xl, border-white/10)
- Backdrop blur and click-outside/escape-to-close behavior
- Header: Title "Historical Data Backfill", fund indicator, and close button (X)
- Scheme picker: Dropdown to choose target scheme or "All Tracked Schemes (`all`)"
- Range pickers:
  - Start: Month selector (Jan–Dec) + Year selector (2013 to current year)
  - End: Month selector (Jan–Dec) + Year selector (2013 to current year)
- Quick Preset buttons:
  - "Last 6 Months"
  - "Last 12 Months"
  - "Last 3 Years"
  - "Year to Date (YTD)"
- Dynamic summary card:
  - Number of months in range (e.g. "12 Months: 2023-07 → 2024-06")
  - Informational pill: "Existing months are automatically skipped to avoid duplicate fetching"
- Dry Run switch / checkbox: "Dry run (simulate backfill without committing data)"
- Status & Action area:
  - Notice banner if `!isGitHubConfigured()`
  - "Cancel" button
  - "Dispatch Backfill" button (with spinner during submission)
- On success: Closes modal and fires `onSuccess(runUrl)` callback to show toast with link to GitHub Actions.

**Acceptance**:
- Range validation prevents start > end or future months beyond current month.
- Preset buttons correctly update start/end selections.
- Loading and disabled states are properly indicated.

---

### Task 12.4 — Wire Backfill Modal into `FundCatalog.tsx`
**File**: `web/src/components/FundCatalog.tsx` (edit)  
**What**:
1. Add a "Fetch Historical Data" button in the hero/banner area to open `BackfillModal` with "All Funds" default.
2. In each fund card's action row (next to "View Holdings & Diff"), add a "Fetch Data" button (with `CloudDownload` or `CalendarSearch` icon).
3. Clicking pre-selects that specific fund in `BackfillModal`.
4. Include `Toast` state for showing:
   - Green success toast: `"Backfill triggered! Track progress in GitHub Actions ↗"` with clickable link.
   - Red error toast if dispatch fails.

**Acceptance**:
- Every card has a functioning "Fetch Data" button.
- Hero has a global fetch button.
- Modal opens with appropriate preselected fund.
- Toast feedback appears upon submission.

---

### Task 12.5 — Wire Backfill into Fund Detail Page
**Files**:
- `web/src/components/BackfillButton.tsx` (new client component)
- `web/src/app/fund/[id]/page.tsx` (edit)

**What**:
1. Create `BackfillButton.tsx` as a client component that wraps the modal trigger for server components:
   - Accepts `fundId`, `fundName`, and available funds list
   - Renders a styled button: "Fetch Data Range" or "Backfill" with icon
   - Opens `BackfillModal` and handles toast notification
2. In `fund/[id]/page.tsx`:
   - Place `BackfillButton` in the header action area next to the reporting month pills.
   - Pass `id`, `fundSummary.name`, and all funds list.

**Acceptance**:
- Fund detail page shows "Fetch Data Range" button.
- Clicking opens the modal pre-filled with the current fund.
- Successful trigger shows toast notification with GitHub Actions link.

---

### Task 12.6 — Wire Backfill Action into `FundManager.tsx`
**File**: `web/src/components/FundManager.tsx` (edit)  
**What**:
1. Add a "Fetch Data" button in the action column of each fund in the `/manage` table.
2. Integrate `BackfillModal` so admins managing funds can immediately launch backfills right after enabling or adding a fund.
3. Show success toast with GitHub Actions link.

**Acceptance**:
- Fund table row has a "Fetch Data" action.
- Launches modal and executes backfill dispatch.

---

### Task 12.7 — Tests and Build Verification
**Files**:
- `pipeline/tests/test_backfill_cli.py` or new tests if applicable
- Validate Next.js build: `npm run build`
- Validate Python tests: `python3 -m pytest pipeline/tests/ -v`

**Acceptance**:
- `npm run build` succeeds with zero TypeScript or lint errors.
- 45/45 Python tests continue to pass.
- API route returns 401 when unauthenticated and handles invalid payloads gracefully.

---

## Verification Checklist

- [ ] `/api/github/dispatch-backfill` Route Handler rejects invalid JSON, missing months, and inverted date ranges with HTTP 400.
- [ ] `/api/github/dispatch-backfill` returns HTTP 401 when `GH_PAT` is not set.
- [ ] `triggerBackfill()` helper properly formats payload and communicates with route handler.
- [ ] `BackfillModal` renders month and year pickers with valid boundaries (2013 to current year).
- [ ] Date presets ("Last 6 Months", "Last 12 Months", "Last 3 Years", "YTD") accurately calculate month ranges.
- [ ] Fund cards on home catalog have "Fetch Data" buttons that open `BackfillModal` with that fund preselected.
- [ ] Fund detail page has a "Fetch Data Range" button that opens `BackfillModal`.
- [ ] Fund Manager page (`/manage`) has "Fetch Data" buttons for each fund.
- [ ] Successful dispatch triggers a toast notification containing a clickable link to GitHub Actions.
- [ ] Mobile responsive layout verified across modal and buttons.
- [ ] `npm run build` compiles cleanly (0 errors).
- [ ] 45/45 Python tests pass cleanly.

---

## Files Changed / Created

| File | Change |
|------|--------|
| `web/src/app/api/github/dispatch-backfill/route.ts` | New — Route Handler for GitHub Actions `workflow_dispatch` |
| `web/src/components/BackfillModal.tsx` | New — Month/year range picker modal with presets & validation |
| `web/src/components/BackfillButton.tsx` | New — Client wrapper button for server pages |
| `web/src/lib/github.ts` | Edit — Add `triggerBackfill()` and associated types |
| `web/src/components/FundCatalog.tsx` | Edit — Add "Fetch Data" button to cards + hero trigger + toast |
| `web/src/app/fund/[id]/page.tsx` | Edit — Add `BackfillButton` to header/selector area |
| `web/src/components/FundManager.tsx` | Edit — Add "Fetch Data" quick action to fund table rows |

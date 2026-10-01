# Phase 11 — Fund Manager UI (Add / Edit / Remove Funds)

**Milestone**: v1.1  
**Status**: ⬜ Not started  
**Goal**: Build a `/manage` admin page in Next.js where users can see all tracked funds, add new ones (committed to `config/funds.json` via GitHub Contents API), and soft-delete/disable existing funds — all without touching any files manually.

---

## Context

### Existing web app
- **Framework**: Next.js (App Router), TypeScript, Tailwind CSS
- **Design**: Dark mode `#0B0F17` bg, glassmorphism panels (`glass-panel`, `glass-card`), indigo/emerald accent palette
- **Nav**: `layout.tsx` has a sticky header with logo + GitHub link — we add a "Manage" nav link here
- **Data**: Loaded at build time from `/data/*.json` via `src/lib/data.ts` (fs reads)
- **Types**: Defined in `src/types/index.ts`

### What this phase adds
1. `/manage` page — fund list table with status badges + action buttons
2. "Add Fund" modal — form with all required fields, live validation, preview card
3. "Disable Fund" toggle — soft delete (sets `"enabled": false`)
4. GitHub API client (`src/lib/github.ts`) — encapsulates GitHub Contents API calls
5. Nav link "Manage" added to `layout.tsx`
6. Env var handling — `NEXT_PUBLIC_GITHUB_REPO`, `NEXT_PUBLIC_GITHUB_BRANCH`, `GH_PAT` (client env: only `NEXT_PUBLIC_*` safe, PAT is server-side only)
7. PAT setup guide shown inline when env var is missing

### Security model
- `GH_PAT` must be a **server-side env var only** (no `NEXT_PUBLIC_` prefix)
- The GitHub API call goes through a **Next.js Route Handler** (`/api/github/update-fund`) which reads `GH_PAT` server-side
- The client never sees the raw token
- Without `GH_PAT`, the UI renders in read-only mode (Add/Disable buttons disabled, setup guide shown)

---

## Tasks

### Task 11.1 — GitHub API Route Handler
**File**: `web/src/app/api/github/update-fund/route.ts` (new)  
**What**: A Next.js Route Handler (POST) that:
1. Reads `GH_PAT`, `NEXT_PUBLIC_GITHUB_REPO`, `NEXT_PUBLIC_GITHUB_BRANCH` from env
2. Fetches the current `config/funds.json` from the GitHub Contents API (gets current SHA)
3. Applies the change (add or update a fund entry)
4. Commits the updated file back via `PUT /repos/{owner}/{repo}/contents/{path}`
5. Returns `{ success: true, sha: "..." }` or `{ error: "..." }` with appropriate HTTP status

Request body schema:
```ts
{
  action: 'add' | 'disable' | 'enable';
  fund: FundConfig;  // full fund object for 'add'; { id } for 'disable'/'enable'
}
```

Response:
- `200` — success
- `400` — validation error (missing fields, bad format)
- `401` — `GH_PAT` not configured (read-only mode)
- `500` — GitHub API error

**Acceptance**: `curl -X POST /api/github/update-fund -d '{"action":"disable","fund":{"id":"ppfas-taxsaver"}}'` returns `401` in dev (PAT not set), no crash.

---

### Task 11.2 — GitHub API client utility
**File**: `web/src/lib/github.ts` (new)  
**What**: Client-side helper functions for calling our own Route Handler and (for non-sensitive operations) checking GitHub API status:

```ts
export interface FundConfig {
  id: string;
  name: string;
  amc: string;
  type: 'equity' | 'debt' | 'hybrid' | 'liquid';
  category?: string;
  source_page: string;
  excel_sheet?: string;
  pdf_section_keyword?: string;
  parser_preference: string[];
  significant_change_pp: number;
  enabled: boolean;
}

export async function addFund(fund: FundConfig): Promise<{ success: boolean; error?: string }>;
export async function disableFund(id: string): Promise<{ success: boolean; error?: string }>;
export async function enableFund(id: string): Promise<{ success: boolean; error?: string }>;
export function isGitHubConfigured(): boolean;  // checks NEXT_PUBLIC_GITHUB_REPO
```

All functions call `POST /api/github/update-fund` and return a normalized result.

**Acceptance**: Functions are exported and typed correctly; `isGitHubConfigured()` returns `false` when env var is not set.

---

### Task 11.3 — Fund Manager page (`/manage`)
**File**: `web/src/app/manage/page.tsx` (new)  
**What**: A server component that reads `config/funds.json` at build time and passes data to the client `FundManager` component.

```tsx
import { getFundsConfig } from '@/lib/data';
import FundManager from '@/components/FundManager';

export default async function ManagePage() {
  const funds = await getFundsConfig();
  return <FundManager initialFunds={funds} />;
}
```

Also add `getFundsConfig()` to `src/lib/data.ts` — reads `config/funds.json` from the repo root (not from `/data/`), returning a typed `FundConfig[]`.

**Acceptance**: Navigating to `/manage` renders without 404 or error.

---

### Task 11.4 — `FundManager` client component
**File**: `web/src/components/FundManager.tsx` (new)  
**What**: The main client component for the manage page. Contains:

**Layout sections:**
1. **Page header** — "Fund Manager" title + "Add New Fund" button (disabled if not configured)
2. **PAT setup banner** — shown when `isGitHubConfigured()` is false or PAT is missing; step-by-step instructions with code snippet
3. **Fund table** — card-based list of all funds (active + disabled) with:
   - Fund name, AMC, category, parser type badge
   - "Last data" date from index.json (or "No data yet" if new)
   - Status badge: 🟢 Active / 🔴 Disabled
   - "Enable" / "Disable" toggle button
4. **Add Fund modal** — see Task 11.5

**State management:**
- `funds` state initialized from `initialFunds` prop
- `isSubmitting` boolean for loading states
- `toast` state for success/error notifications
- `showAddModal` boolean

**Acceptance**: Page renders with all funds listed, status badges visible, buttons present.

---

### Task 11.5 — "Add Fund" modal
**File**: Part of `web/src/components/FundManager.tsx`  
**What**: A modal overlay with a multi-field form for adding a new fund:

**Form fields:**
| Field | Type | Validation |
|-------|------|-----------|
| Fund ID | text | required, `/^[a-z0-9-]+$/`, unique |
| Fund Name | text | required, non-empty |
| AMC Name | text | required, non-empty |
| Fund Type | select | equity / debt / hybrid / liquid |
| Category | text | optional (e.g. "Flexi Cap") |
| Source Page URL | url | required, must start with https:// |
| Parser Preference | multi-select | excel, pdf_text, ocr (at least 1) |
| Excel Sheet Name | text | optional (e.g. "PPFCF") |
| PDF Section Keyword | text | optional |
| Significant Change (pp) | number | 0.1–5.0, default 0.5 |

**UX:**
- Real-time inline validation (red border + error message per field on blur)
- "Preview Card" section below the form — shows what the fund card will look like on the home page (skeleton with fund name/AMC/type populated in real time)
- Submit button shows spinner during API call
- On success: modal closes, fund appears in table, green toast "Fund added — backfill triggered automatically"
- On error: red toast with message from API

**Acceptance**: Form validates all fields, disables submit when invalid, shows preview card.

---

### Task 11.6 — Toast notification component
**File**: `web/src/components/Toast.tsx` (new)  
**What**: A lightweight animated toast notification:
- Variants: `success` (emerald), `error` (rose), `info` (indigo)
- Auto-dismisses after 4 seconds
- Slide-in animation from top-right
- Close button
- Used by FundManager (and later by BackfillPicker in Phase 12)

```tsx
interface ToastProps {
  message: string;
  variant: 'success' | 'error' | 'info';
  onClose: () => void;
}
```

**Acceptance**: Toast renders with correct color, auto-dismisses after 4s, close button works.

---

### Task 11.7 — Add "Manage" nav link to layout
**File**: `web/src/app/layout.tsx` (edit)  
**What**: Add a "Manage" link to the nav header between the "Automated Pipeline Active" badge and the GitHub icon:

```tsx
<Link
  href="/manage"
  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-white/5 transition-colors border border-white/5"
>
  <Settings className="w-3.5 h-3.5" />
  Manage
</Link>
```

Import `Settings` from lucide-react.

**Acceptance**: "Manage" link visible in desktop nav, navigates to `/manage`.

---

### Task 11.8 — Update `getFundsConfig()` in `data.ts`
**File**: `web/src/lib/data.ts` (edit)  
**What**: Add a new export that reads from `config/funds.json` (repo root) rather than `/data/`:

```ts
export async function getFundsConfig(): Promise<FundConfig[]> {
  // Reads from ../../config/funds.json relative to web/
  const configPath = path.join(process.cwd(), '..', 'config', 'funds.json');
  // fallback: public/funds.json (for Vercel where root is not accessible)
  const fallbackPath = path.join(process.cwd(), 'public', 'funds.json');
  // ...
}
```

For Vercel deployment, `config/funds.json` must be copied to `web/public/funds.json` during prebuild. Update `web/package.json` prebuild script to also copy `config/funds.json → public/funds.json`.

**Acceptance**: `/manage` shows correct fund list; `npm run build` succeeds.

---

## Verification Checklist

- [ ] `/manage` route returns HTTP 200 (no 404)
- [ ] Fund list shows `ppfas-flexicap` and `ppfas-taxsaver` with Active badges
- [ ] "Add New Fund" button is visible
- [ ] When GitHub PAT is not configured: setup banner shown, buttons are disabled
- [ ] Add Fund form: invalid Fund ID (uppercase) shows inline error
- [ ] Add Fund form: missing required field blocks submit
- [ ] Add Fund form: valid data → POST to `/api/github/update-fund` (returns 401 in dev without PAT — that's expected)
- [ ] Toast component auto-dismisses in 4 seconds
- [ ] "Manage" nav link present in header, navigates correctly
- [ ] `npm run build` compiles without TypeScript errors
- [ ] 45/45 existing Python tests still pass (no regressions)

---

## Files Changed / Created

| File | Change |
|------|--------|
| `web/src/app/manage/page.tsx` | New — server component for manage route |
| `web/src/app/api/github/update-fund/route.ts` | New — Route Handler (server-side PAT handling) |
| `web/src/components/FundManager.tsx` | New — main manage page client component + Add modal |
| `web/src/components/Toast.tsx` | New — animated toast notification |
| `web/src/lib/github.ts` | New — client helper wrapping our Route Handler |
| `web/src/lib/data.ts` | Edit — add `getFundsConfig()` |
| `web/src/app/layout.tsx` | Edit — add "Manage" nav link |
| `web/src/types/index.ts` | Edit — add `FundConfig` interface |
| `web/package.json` | Edit — update prebuild to copy `config/funds.json` |

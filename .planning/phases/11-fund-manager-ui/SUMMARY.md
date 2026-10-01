# Phase 11 Summary — Fund Manager UI

**Status**: ✅ Complete  
**Commit**: `79fb307`

## What Was Built

### `/manage` route (new)
- `app/manage/page.tsx` — server component reads `config/funds.json` at build time via `getFundsConfig()`
- Static-rendered; 8/8 pages build successfully

### GitHub API Route Handler (new)
- `app/api/github/update-fund/route.ts` — server-side POST handler
- Reads `GH_PAT` from env (never in client bundle)
- Fetches current `config/funds.json` SHA from GitHub Contents API
- Applies `add` / `disable` / `enable` mutations and commits back
- Returns `401` when PAT unset (graceful read-only mode)
- Validates fund config before committing (same rules as `validate_fund_config.py`)

### `lib/github.ts` — Client helper (new)
- `addFund()`, `disableFund()`, `enableFund()` — all call the Route Handler
- `isGitHubConfigured()` — checks `NEXT_PUBLIC_GITHUB_REPO` env var
- Typed `GithubApiResult` response shape

### `FundManager.tsx` — Main manage page client (new)
- Fund list table with Active/Disabled status badges
- Enable/Disable toggle buttons with loading spinner + optimistic update
- **Add Fund modal**: 10-field form with:
  - Real-time validation (inline field errors on blur)
  - Live card preview (renders exactly how it will look on home page)
  - Parser preference multi-select buttons
  - Submit disabled until all required fields valid
- **PAT setup guide**: collapsible amber banner when not configured; copy-paste env snippet
- Toast integration for success/error feedback

### `Toast.tsx` — Animated notification (new)
- Auto-dismisses after 4s
- Variants: success (emerald), error (rose), info (indigo)
- Slide-in animation, close button

### Supporting changes
- `types/index.ts`: `FundConfig` interface added
- `lib/data.ts`: `getFundsConfig()` — reads from root or `public/funds.json`
- `app/layout.tsx`: "Manage" nav link with Settings icon
- `web/package.json`: prebuild copies `config/funds.json → public/funds.json`

## Verification Results
- ✅ `npm run build` — 8/8 pages, TypeScript clean
- ✅ `/manage` route returns 200
- ✅ Fund list shows ppfas-flexicap and ppfas-taxsaver
- ✅ Without PAT: PAT setup banner visible, buttons disabled
- ✅ 45/45 Python tests pass (no regressions)

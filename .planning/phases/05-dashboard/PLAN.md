# Phase 5: Dashboard — Plan

## Goal
Build and verify the premium Next.js dashboard application in `web/` deployed to Vercel Hobby tier. The dashboard reads pre-computed JSON snapshots and diffs from `data/`, presenting fund cards, top-10 equity holdings tables, month-over-month change panels, and historical weight trend charts in a sleek dark-mode glassmorphic interface.

---

## Requirements Addressed
- **FR-8.1**: Home page fund card grid with search, AMC filter, and highlights.
- **FR-8.2**: Fund detail page with Top 10 table, delta vs last month, rank changes, entered/exited panel, AMC commentary, and source links.
- **FR-8.3**: History chart displaying weight trends over time using Recharts.
- **FR-8.4**: Month selector to inspect past monthly snapshots and diffs.
- **FR-8.5**: Responsive layout, dark mode by default, glassmorphism design, fast static loads.
- **FR-8.6**: Footer disclaimer ("Informational only. Not investment advice. Data from AMC factsheets; verify against the source.").
- **FR-8.7**: "Last updated" timestamps and source metadata on every page.
- **NFR-1, NFR-3**: 100% free Vercel Hobby hosting, zero heavy runtime parsing, fast SSG/ISR rendering.
- **UAT Criteria 7 & 8**: Dashboard displays fund card grid with correct data, and history chart plots multi-month trends.

---

## Architecture & Technical Decisions

1. **Framework & Stack**:
   - Next.js 14+ (App Router, TypeScript, Tailwind CSS, Lucide icons, Recharts).
   - Zero database; pre-computed JSON from `data/` read at build/request time via server components.
2. **Design System & Aesthetics**:
   - Dark mode: deep charcoal/navy canvas (`#0B0F17`, `#111827`, `#1F2937`).
   - Glassmorphism: subtle backdrop blur (`backdrop-blur-md`), semitransparent borders (`border-white/10`).
   - Visual accents: Emerald green (`#10B981`) for weight increases and entering holdings, Rose red (`#F43F5E`) for reductions, Indigo/Violet for interactive highlights.
   - Clean typography with Inter font and tabular numbers for financial columns.
3. **Data Loading Architecture (`web/src/lib/data.ts`)**:
   - Resilient path resolution checking `../data`, `data`, and `public/data`.
   - Helper scripts copy `data/` to `web/public/data` during `prebuild` to ensure seamless zero-config Vercel deployments.
   - Pure typed interfaces matching `FR-5` and `FR-6` schemas.

---

## Detailed Task Breakdown

### Task 1: Next.js Project Scaffolding in `web/`
- Initialize Next.js project with App Router, TypeScript, and Tailwind CSS in `web/`.
- Install dependencies: `lucide-react`, `recharts`, `clsx`, `tailwind-merge`.
- Configure `tailwind.config.ts` and `next.config.mjs` for custom colors, font settings, and data bundling.
- Add `prebuild` script in `web/package.json` to mirror `../data` into `web/public/data`.

### Task 2: Data Types & Server-Side Loader (`web/src/lib/data.ts`)
- TypeScript models in `web/src/types/index.ts`:
  - `FundSummary`, `FundIndex`, `Holding`, `Snapshot`, `Diff`, `HistorySeries`.
- Implement `getFundIndex()`, `getFundSnapshot(id, month)`, `getFundDiff(id, month)`, and `getFundHistory(id)`.

### Task 3: Root Layout, Navigation & Global Aesthetics
- `web/src/app/layout.tsx`:
  - Navigation bar with logo, live tracker badge, and GitHub repository link.
  - Dark glassmorphism header and background gradient mesh.
  - Footer with mandatory regulatory disclaimer (`FR-8.6`) and data attribution.
- `web/src/app/globals.css`:
  - Custom scrollbar, glass card utility classes, glow effects, badge styling.

### Task 4: Home Page (`web/src/app/page.tsx`)
- High-level metric highlights (Tracked Schemes, Latest Ingestion Month, Top Monitored Holding, Total Equities Tracked).
- Live search bar and AMC filter pills.
- Interactive Fund Card Grid:
  - Fund name, AMC badge, category.
  - Latest reporting month and as-of date.
  - Top holding and top-10 total weight gauge.
  - Monthly change summary badge (e.g. "0 changes in Top 10", "6 increased, 4 decreased").
  - Click-through navigation to fund detail view.

### Task 5: Fund Detail Page (`web/src/app/fund/[id]/page.tsx`)
- Server component with dynamic routing for `fund/[id]`.
- Month Selector: Pill navigation across all available historical months (`FR-8.4`).
- Header info: AMC name, category, source factsheet URL link, as-of timestamp (`FR-8.7`).
- Changes & Highlights Panel (`FR-8.2`):
  - "Entered Top 10" and "Exited Top 10" cards.
  - Notable movers with delta badges ($\pm\text{pp}$).
  - Verbatim AMC commentary callout box.
- Top 10 Holdings Table (`FR-8.2`):
  - Columns: Rank, Instrument Name, ISIN (with one-click copy), Sector, Weight %, MoM Change (with colored trend arrows), Rank Change.
  - Responsive cards on mobile, structured data table on desktop.

### Task 6: Historical Weight Trend Chart (`web/src/components/HoldingHistoryChart.tsx`)
- Client component using Recharts (`FR-8.3`).
- Plots multi-month weight trajectories for current top-10 holdings.
- Interactive toggle to show/hide individual holdings.
- Custom tooltip with formatted percentages and month names.

### Task 7: Build Verification & Static Export Check
- Run `npm run build` inside `web/` to verify zero TypeScript errors, lint passes, and successful static generation.
- Test preview locally via Next.js dev server or production preview.

---

## Verification & Acceptance Checklist
- [ ] `web/` builds cleanly (`npm run build`) without errors.
- [ ] Home page renders fund cards reading directly from `data/index.json` (UAT Criteria #7).
- [ ] Fund detail page loads August 2026 PPFAS Flexi Cap snapshot with exact 10 holdings and deltas.
- [ ] Month selector toggles between 2026-08, 2026-07, and 2026-06.
- [ ] Recharts history chart plots weight series across the 3 historical months (UAT Criteria #8).
- [ ] Dark mode glassmorphic styling, footer disclaimer, and source links display properly.

# Phase 13 — Vercel Production Deployment & Documentation

**Milestone**: v1.1  
**Status**: ⬜ Not started  
**Goal**: Prepare, configure, optimize, and document the application for production deployment on the Vercel Hobby tier, ensuring seamless build configurations (both root and subdirectory modes), production security headers, accessibility/SEO compliance (Lighthouse score ≥ 90), and comprehensive documentation.

---

## Context

### Existing State
- **Phase 9**: Backfill CLI range parsing and idempotency (`pipeline/backfill.py`).
- **Phase 10**: GitHub Actions workflows (`backfill.yml`, `register-fund.yml`, `pipeline.yml`).
- **Phase 11**: `/manage` Fund Manager UI with Add Fund modal and server-side `GH_PAT` handling.
- **Phase 12**: Backfill Period Picker UI with date presets, range validation, and `workflow_dispatch` trigger.
- **Repository**: Connected to GitHub at `https://github.com/vedantnathani/fund-ui.git`.
- **Security & Roles**:
  - Regular users: Pure consumer financial dashboard with self-service historical backfill triggers.
  - Admin: Passcode-protected `/manage` area with `ADMIN_PASSWORD` verification. Zero developer token leakage in the UI.

### What This Phase Delivers
1. **`vercel.json` Configuration**:
   - Production security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
   - Caching policy for static data files and immutable assets.
   - Clean support for both root and `web/` deployment paths.
2. **Root Monorepo Build Support**:
   - Add root `package.json` with delegated scripts (`npm --prefix web run build`).
   - Ensures Vercel builds successfully regardless of whether the user sets "Root Directory" to `web` or leaves it as default `./`.
3. **SEO, Accessibility & Lighthouse Polish**:
   - Complete Open Graph, Twitter cards, and semantic meta tags in `web/src/app/layout.tsx`.
   - Ensure all interactive elements have accessible labels and ARIA attributes.
   - Audit color contrasts and responsive viewports.
4. **Comprehensive Production Documentation (`README.md`)**:
   - 1-Click / step-by-step Vercel deployment walkthrough.
   - Complete environment variable reference table (`GH_PAT`, `ADMIN_PASSWORD`, `NEXT_PUBLIC_GITHUB_REPO`, etc.).
   - Workflow architecture diagram and explanation.
   - Operational guide: Regular user data fetching vs Admin fund management.

---

## Tasks

### Task 13.1 — Vercel Configuration & Monorepo Delegation
**Files**:
- `vercel.json` (new, root)
- `web/vercel.json` (new, web app)
- `package.json` (new, root)

**What**:
1. Create `web/vercel.json` with security headers and caching configuration:
   - Security headers:
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `X-XSS-Protection: 1; mode=block`
     - `Referrer-Policy: strict-origin-when-cross-origin`
   - Cache control headers for static JSON snapshots (`/data/**` and `/public/**`).
2. Create root `package.json` delegating `build`, `start`, `dev`, and `lint` to `--prefix web`.
3. Create root `vercel.json` mapping framework `nextjs` and build commands to ensure zero-friction deployment.

**Acceptance**:
- Both root `npm run build` and `web` `npm run build` execute without error.
- Valid JSON format for both `vercel.json` files.

---

### Task 13.2 — Production SEO, Accessibility & Metadata Optimization
**Files**:
- `web/src/app/layout.tsx` (edit)
- `web/src/app/page.tsx` (edit if needed)

**What**:
1. Enhance metadata in `web/src/app/layout.tsx`:
   - Full OpenGraph metadata (`title`, `description`, `type: 'website'`, `locale: 'en_US'`).
   - Twitter card metadata (`summary_large_image`).
   - Semantic theme-color meta tag.
   - Favicon and icons link tags.
2. Verify accessibility:
   - Check all `<button>` elements have explicit `type` attributes and accessible labels/aria-labels.
   - Check all `<input>` elements have associated labels.
   - Verify semantic heading hierarchy (`h1` -> `h2` -> `h3`).

**Acceptance**:
- Page metadata is fully populated.
- TypeScript compile succeeds.
- No accessibility or missing tag warnings in build.

---

### Task 13.3 — Comprehensive Documentation in `README.md`
**File**: `README.md` (edit)  
**What**:
Update `README.md` into a complete, professional, production-ready guide:
1. Update test badge to `45/45 Passed`.
2. Add live deployment instructions for Vercel:
   - Fork/Clone instructions.
   - Vercel Project import settings (Root directory: `web` or `./`).
   - Required Environment Variables table:
     - `GH_PAT`: GitHub Personal Access Token (Server-side) for updating `config/funds.json` and triggering backfill.
     - `ADMIN_PASSWORD`: Administrator passcode to unlock `/manage`.
     - `NEXT_PUBLIC_GITHUB_REPO`: `vedantnathani/fund-ui`.
     - `NEXT_PUBLIC_GITHUB_BRANCH`: `main`.
     - Optional: `OPENROUTER_API_KEY` / `GEMINI_API_KEY` for LLM summaries.
   - GitHub Secrets setup for GitHub Actions (`GH_PAT`).
3. Add User Guides:
   - **For Users**: How to view funds, analyze month-over-month shifts, and fetch custom date ranges.
   - **For Admins**: How to access `/manage`, unlock with passcode, add a new mutual fund scheme, or pause an existing fund.
4. Add Architecture & Pipeline flow diagrams explaining scheduled runs, `[skip ci]` safety guards, and static generation.

**Acceptance**:
- README is comprehensive, accurate, formatted with clear markdown tables and code blocks.
- Contains exact environment variable specifications.

---

### Task 13.4 — End-to-End Build, Test & Deployment Verification
**What**:
1. Run root `npm run build` to verify monorepo build delegation.
2. Run `npm run build` inside `web/` directory.
3. Run `python3 -m pytest pipeline/tests/ -v` (confirm 45/45 tests pass).
4. Commit all files and push to `origin main` at `https://github.com/vedantnathani/fund-ui.git`.
5. Update `STATE.md` to mark Milestone v1.1 and Phase 13 as complete.

---

## Verification Checklist

- [ ] Root `vercel.json` and `web/vercel.json` exist with valid schemas and security headers.
- [ ] Root `package.json` delegates `build` and `dev` to `web/`.
- [ ] Root `npm run build` executes and succeeds.
- [ ] `web/` `npm run build` executes and succeeds with 10/10 routes static/dynamic.
- [ ] 45/45 Python tests pass without warnings or errors.
- [ ] `web/src/app/layout.tsx` contains complete OpenGraph, Twitter, and accessibility metadata.
- [ ] `README.md` thoroughly documents Vercel deployment, environment variables, GitHub Actions secrets, and admin usage.
- [ ] All changes committed and pushed to `main` branch on GitHub.

---

## Files Changed / Created

| File | Change |
|------|--------|
| `vercel.json` | New — Root Vercel configuration |
| `web/vercel.json` | New — Next.js Vercel headers and static asset config |
| `package.json` | New — Root package.json delegating scripts to `web/` |
| `web/src/app/layout.tsx` | Edit — OpenGraph, Twitter, and SEO metadata |
| `README.md` | Edit — Complete production deployment and usage documentation |
| `.planning/phases/13-vercel-production-deployment/PLAN.md` | New — Phase 13 execution plan |

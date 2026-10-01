# 📈 Mutual Fund Top-10 Holdings Tracker (FundLens)

[![Python Tests](https://img.shields.io/badge/Python%20Tests-45%2F45%20Passed-brightgreen?style=flat-square&logo=pytest)](pipeline/tests/)
[![Next.js](https://img.shields.io/badge/Next.js-16%20Turbopack-black?style=flat-square&logo=next.js)](web/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue?style=flat-square&logo=typescript)](web/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v4-38bdf8?style=flat-square&logo=tailwindcss)](web/)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Zero Cost](https://img.shields.io/badge/Stack-100%25%20Free-emerald?style=flat-square)](#-zero-cost-architecture)

An automated, **100% free stack** monitoring Indian mutual fund factsheets and monthly portfolio disclosures, extracting top-10 equity holdings, calculating month-over-month diffs, generating verified AI portfolio summaries, and presenting changes on a modern dark-mode glassmorphic dashboard.

---

## 🏛 Architecture & Philosophy

```
  [ AMC Source Page ] (e.g. PPFAS Monthly Disclosures & Factsheets)
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ GitHub Actions Automation Engine                            │
│                                                             │
│   • pipeline.yml      ── 2x daily automated cron ingestion  │
│   • backfill.yml      ── Parameterized period backfill      │
│   • register-fund.yml ── Ingests new funds from funds.json  │
│                                                             │
│   1. Scraper         ── Discovers latest XLS/PDF report     │
│   2. Parser Engine   ── Primary: Excel (OpenXML / xlrd)     │
│                         Fallback: PDF (dynamic table scan)  │
│   3. Validator       ── Enforces 10-holding monotonic rules │
│   4. Diff Engine     ── Computes MoM deltas & rank shifts   │
│   5. AI Summarizer   ── Strict number check: 0 hallucination│
│   6. Git Commit      ── Commits snapshots with [skip ci]    │
└──────────────────────────────┬──────────────────────────────┘
                               │ [git push to main]
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Vercel Hobby Tier (Production Web Application)              │
│                                                             │
│   • Prebuild Hook copies data/ to public/data               │
│   • Next.js App Router prerenders static pages              │
│   • Backfill Period Picker: Trigger custom period fetch     │
│   • Passcode-Protected Fund Manager (/manage)               │
│   • Recharts history trends & glassmorphic UI               │
│   • Zero runtime compute overhead                           │
└─────────────────────────────────────────────────────────────┘
```

### Core Design Principles
1. **100% Free Stack**: Zero paid APIs, zero paid hosting, zero cloud databases. GitHub Actions provides compute; the Git repository provides versioned storage; Vercel Hobby provides global static edge delivery.
2. **Role Separation & Clean User Experience**:
   - **Regular Users**: Experience a clean, noise-free financial dashboard. Users can inspect all funds, compare diffs, and fetch custom historical date ranges without seeing developer tokens or setup guides.
   - **Administrators**: Manage schemes via `/manage`, protected by an `ADMIN_PASSWORD` passcode.
3. **Validation-First**: If an AMC changes formatting or a holding table is missing, the validator rejects corrupted data loudly rather than storing corrupt state.
4. **Neutral Financial Terminology**: Diff comparisons strictly use objective phrasing (`entered/exited top 10`, `weight increased/decreased`). Speculative trading verbs (`bought`, `sold`) are strictly avoided.
5. **Zero-Hallucination AI Guard**: Every numerical metric, percentage, and basis-point change cited in AI commentary is verified against the raw diff JSON within $\pm 0.05$ tolerance. If any unverified number appears, output is rejected and replaced by a deterministic mathematical template.
6. **No Infinite Loops**: All automated pipeline commits include `[skip ci]` to ensure automated commits never trigger circular build pipelines.

---

## ✨ Features

- **Multi-Source Parser Engine**:
  - **Excel (Primary)**: Automatically extracts domestic and foreign equity sub-tables, ISINs, and percentage allocations from structured workbooks with automatic engine switching (`openpyxl` & `xlrd`).
  - **PDF Text (Fallback)**: Uses `pdfplumber` with dynamic page search and header matching to locate portfolio tables across variable-length monthly factsheets.
- **Strict Invariant Validation**:
  - Exactly 10 equity holdings per snapshot.
  - Monotonically decreasing weights ($W_1 \ge W_2 \ge \dots \ge W_{10}$).
  - Realistic weight bounds ($0.1\% \le W_i \le 30.0\%$, sum between $30.0\%$ and $85.0\%$).
  - Canonical company name resolution via `config/aliases.json`.
- **Month-Over-Month Diff Engine**:
  - Accurate tracking of newly entered and exited top-10 positions.
  - Weight deltas (basis points) and rank changes.
  - Highlighting of significant shifts ($\ge 0.50$ percentage points).
- **Pluggable AI Commentary with Number Verification**:
  - Compatible with OpenRouter (`google/gemini-2.0-flash-exp:free`), Google Gemini, and Groq (`llama-3.3-70b-versatile`).
  - Strict hallucination post-check extracts every number from generated text and verifies existence in diff JSON.
  - Deterministic template fallback ensures the pipeline never breaks if an API is unavailable or offline.
- **Backfill Period Picker UI (Self-Service Ingestion)**:
  - Users can select any custom range (from 2013 to current month) directly from scheme cards and detail views.
  - Presets: **Last 6 Months**, **Last 12 Months**, **Last 3 Years**, and **Year-to-Date (YTD)**.
  - Safe idempotency: automatically skips existing monthly snapshots to avoid duplicate work.
- **Passcode-Protected Fund Manager (`/manage`)**:
  - Self-service admin interface to add new mutual funds, validate configurations, and enable/disable schemes.
  - Protected with `ADMIN_PASSWORD` verification.
- **Glassmorphic Next.js Dashboard**:
  - Dark mode aesthetic (`#0B0F17`) with Inter typography, vibrant emerald/rose delta badges, and translucent glass panels.
  - Multi-fund catalog with real-time search, category filtering, and executive metrics.
  - Interactive multi-month holding history area chart powered by Recharts.
  - Fully mobile-responsive across all pages.

---

## 📁 Repository Structure

```
.
├── config/
│   ├── funds.json               # Registry of tracked mutual funds
│   └── aliases.json             # Normalization mappings for company names
├── data/
│   ├── index.json               # Master catalog consumed by dashboard
│   ├── ppfas-flexicap/          # Monthly snapshots and diffs
│   │   ├── 2026-06.json
│   │   ├── 2026-07.json
│   │   ├── 2026-07.diff.json
│   │   ├── 2026-08.json
│   │   └── 2026-08.diff.json
│   └── ppfas-taxsaver/          # Second fund snapshots and diffs
├── pipeline/
│   ├── scrape.py                # Plain HTTP factsheet discovery & download
│   ├── parsers/                 # Format-specific extraction modules
│   │   ├── excel.py             # OpenXML / xlrd Excel parser
│   │   └── pdf_text.py          # pdfplumber dynamic page parser
│   ├── parse.py                 # Multi-tier orchestrator
│   ├── validate.py              # Invariant validator & name normalizer
│   ├── validate_fund_config.py  # Standalone fund config validator
│   ├── diff.py                  # Month-over-month diff engine
│   ├── summarize.py             # Pluggable AI summarizer & hallucination guard
│   ├── build_index.py           # Master catalog generator
│   ├── backfill.py              # Parameterized historical backfill CLI
│   ├── run.py                   # Automated pipeline runner
│   └── tests/                   # 45 comprehensive unit & integration tests
├── web/                         # Next.js 16 App Router application
│   ├── src/
│   │   ├── app/                 # Routes: /, /fund/[id], /manage, /api/
│   │   ├── components/          # FundCatalog, BackfillModal, FundManager, Charts
│   │   ├── lib/                 # Precomputed data loaders & GitHub API client
│   │   └── types/               # TypeScript data definitions
│   ├── vercel.json              # Web app Vercel configuration & security headers
│   └── public/data/             # Mirrored data directory for static export
├── .github/workflows/
│   ├── pipeline.yml             # Scheduled twice-daily scraper & summarizer
│   ├── backfill.yml             # On-demand parameterized backfill workflow
│   └── register-fund.yml        # Auto-backfill for newly added funds
├── package.json                 # Monorepo root script delegation
├── vercel.json                  # Root Vercel deployment configuration
└── requirements.txt             # Python pipeline dependencies
```

---

## 🌐 Deploying to Vercel (Production)

Deploying FundLens to Vercel takes less than 3 minutes.

### Step 1: Import Project in Vercel
1. Go to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New > Project** and select your GitHub repository: `vedantnathani/fund-ui`.
3. Framework Preset: **Next.js** (detected automatically).
4. **Root Directory**:
   - You can either leave it as `./` (default) or set it to `web`. Both work out of the box because the root `package.json` delegates builds to `web/`.

### Step 2: Configure Environment Variables in Vercel
Add the following environment variables under **Project Settings > Environment Variables**:

| Variable | Required | Scope | Description |
|---|---|---|---|
| `GH_PAT` | **Yes** | Server-Only | GitHub Personal Access Token (Fine-grained or Classic) with `Contents: Read & Write` and `Actions: Read & Write` permissions. Used server-side to update `funds.json` and dispatch backfill workflows. |
| `ADMIN_PASSWORD` | Recommended | Server-Only | Passcode required to unlock the `/manage` scheme management interface. Choose any secure passphrase. |
| `NEXT_PUBLIC_GITHUB_REPO` | **Yes** | Public | Set to `vedantnathani/fund-ui` (or your repository in `owner/repo` format). |
| `NEXT_PUBLIC_GITHUB_BRANCH` | Optional | Public | Set to `main` (defaults to `main`). |
| `OPENROUTER_API_KEY` | Optional | Server-Only | API key from OpenRouter if you wish to generate AI summaries using external LLMs. |

> [!IMPORTANT]
> `GH_PAT` and `ADMIN_PASSWORD` are server-side environment variables and are **never** exposed to the client browser. All GitHub mutations and workflow dispatches proxy securely through Next.js server Route Handlers.

### Step 3: Configure GitHub Repository Secrets
To allow GitHub Actions scheduled workflows to commit updated data back to your repository:
1. In your GitHub repository, navigate to **Settings > Secrets and variables > Actions**.
2. Under **Repository secrets**, ensure `GH_PAT` or the default `GITHUB_TOKEN` has write permissions:
   - Under **Settings > Actions > General > Workflow permissions**, select **Read and write permissions**.
3. (Optional) If using LLM summaries in GitHub Actions, add `OPENROUTER_API_KEY` or `GEMINI_API_KEY` as an Action secret.

### Step 4: Click Deploy!
Vercel will build the Next.js application, sync the static portfolio snapshots, and assign your production URL (e.g. `https://fund-ui.vercel.app`).

---

## 🚀 Local Development

### 1. Prerequisites
- **Python**: 3.9, 3.10, or 3.11
- **Node.js**: v18.17+ or v20+
- **Git**

### 2. Python Pipeline Setup
```bash
# Clone the repository
git clone https://github.com/vedantnathani/fund-ui.git
cd fund-ui

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install pipeline dependencies
pip install -r requirements.txt
```

### 3. Run the Test Suite
Run all 45 unit and integration tests:
```bash
python3 -m pytest pipeline/tests/ -v
```
All tests should pass cleanly (100% green).

### 4. Run the Pipeline Locally
```bash
# Dry run: check AMC websites for new reports without writing files
python3 pipeline/run.py --dry-run

# Run for a specific fund
python3 pipeline/run.py --fund-id ppfas-flexicap --dry-run

# Backfill a specific date range
python3 pipeline/backfill.py --fund-id ppfas-flexicap --start 2024-01 --end 2024-06

# Backfill using local test fixtures
python3 pipeline/backfill.py --fixtures-only
```

### 5. Run the Next.js Dashboard
From the root directory:
```bash
npm run dev
```
(Or `cd web && npm run dev`)

Open [http://localhost:3000](http://localhost:3000) to view the live dashboard.

---

## ➕ Managing Funds

### From the Web UI (Admin)
1. Scroll to the site footer and click **Admin**.
2. Enter your `ADMIN_PASSWORD` to unlock the management portal.
3. Click **Add New Fund** to open the scheme wizard:
   - Fill in Scheme ID (slug), Fund Name, AMC Name, Category, and Source Page URL.
   - Select parser preferences (Excel / PDF) and delta threshold.
   - Inspect the live card preview.
4. Click **Add Fund**:
   - The server commits the new entry to `config/funds.json` via GitHub Contents API.
   - The `register-fund.yml` GitHub Actions workflow triggers automatically to validate and backfill the newly registered scheme!

### Manually via JSON
You can also add or modify funds directly by editing [`config/funds.json`](config/funds.json):
```json
{
  "id": "ppfas-taxsaver",
  "name": "Parag Parikh ELSS Tax Saver Fund",
  "amc": "PPFAS Mutual Fund",
  "type": "equity",
  "category": "ELSS / Tax Saver",
  "source_page": "https://amc.ppfas.com/downloads/factsheet/",
  "excel_sheet": "PPTSF",
  "pdf_section_keyword": "Tax Saver",
  "parser_preference": ["excel", "pdf_text"],
  "significant_change_pp": 0.5,
  "enabled": true
}
```

Validate your configuration before committing:
```bash
python3 pipeline/validate_fund_config.py
```

---

## 🔄 Fetching Historical Periods (Backfill)

Both regular visitors and administrators can fetch past disclosures for any time period:
1. Click **Fetch Data** on any scheme card or from the scheme detail page.
2. Select your desired period range using the Month/Year dropdowns or choose a quick preset (**Last 6 Months**, **Last 12 Months**, **Last 3 Years**, **YTD**).
3. Click **Fetch Portfolio History**.
4. The dashboard dispatches `backfill.yml` via GitHub Actions and displays a confirmation toast with a link to watch the job execute live in GitHub Actions.

---

## 🛡 Number Verification & Safety

Mutual fund holdings require absolute numerical precision. The summarizer enforces a strict two-stage verification barrier:

1. **System Prompt Constraint**: Pure diff numbers are fed to the model with an explicit instruction prohibiting outside market data, return projections, or unsolicited advice.
2. **Post-Check Regex Extractor (`verify_numbers_in_summary`)**:
   - Strips legitimate calendar years and month dates.
   - Extracts all remaining numerical figures and percentage changes.
   - Confirms that **every extracted number** exists in the raw diff JSON within a $\pm 0.05$ rounding tolerance.
   - **Rejection & Fallback**: If an unverified number appears, the response is rejected and replaced with a deterministic mathematical template.

---

## 🧪 Testing Summary

```
============================== 45 passed in 9.79s ==============================
```
- **CLI & Range Filtering**: `test_backfill_cli.py` (8 tests)
- **Excel Parser**: `test_excel_parser.py` (3 tests)
- **PDF Parser**: `test_pdf_parser.py` (4 tests)
- **Multi-Tier Orchestration**: `test_orchestrator.py` (3 tests)
- **Invariant Validation**: `test_validator.py` (7 tests)
- **Diff Engine**: `test_diff.py` (4 tests)
- **AI Summarization & Hallucination Guard**: `test_summarize.py` (6 tests)
- **Multi-Fund Scalability**: `test_multi_fund.py` (5 tests)
- **Automated Runner**: `test_run.py` (5 tests)

---

## 📜 Disclaimer

*This application is strictly for informational and educational purposes. Changes in portfolio weights or constituents do not constitute investment advice or recommendations to buy or sell any security. Data is sourced from publicly available AMC monthly factsheets and portfolio disclosures; verify directly against the AMC source before investing.*

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

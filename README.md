# 📈 Mutual Fund Top-10 Holdings Tracker

[![Python Tests](https://img.shields.io/badge/Python%20Tests-37%2F37%20Passed-brightgreen?style=flat-square&logo=pytest)](pipeline/tests/)
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
│ GitHub Actions Scheduled Workflow (Twice Daily, Days 3–20)  │
│                                                             │
│   1. Scraper         ── Discovers latest XLS/PDF report     │
│   2. Parser Engine   ── Primary: Excel (OpenXML / xlrd)     │
│                         Fallback: PDF (dynamic table scan)  │
│   3. Validator       ── Enforces 10-holding monotonic rules │
│   4. Diff Engine     ── Computes MoM deltas & rank shifts   │
│   5. AI Summarizer   ── Synthesizes commentary              │
│                         Strict number check: 0 hallucination│
│   6. Git Commit      ── Pushes new snapshots to data/       │
└──────────────────────────────┬──────────────────────────────┘
                               │ [git push to main]
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Vercel Hobby Tier (Read-Only Static Hosting)                │
│                                                             │
│   • Prebuild Hook copies data/ to public/data               │
│   • Next.js App Router prerenders static pages              │
│   • Recharts history trends & glassmorphic UI               │
│   • Zero runtime compute overhead                           │
└─────────────────────────────────────────────────────────────┘
```

### Core Design Principles
1. **100% Free Stack**: Zero paid APIs, zero paid hosting, zero cloud databases. GitHub Actions provides scheduled compute; Git repository provides versioned storage; Vercel Hobby provides global static edge delivery.
2. **Read-Only Frontend**: Vercel runs no scraping, OCR, or heavy parsing. The dashboard loads precomputed, validated JSON produced by GitHub Actions.
3. **Validation-First**: If an AMC changes formatting or a holding table is missing, the validator rejects bad data loudly rather than storing corrupted state.
4. **Neutral Financial Terminology**: Diff comparisons strictly use objective phrasing (`entered/exited top 10`, `weight increased/decreased`). Speculative or misleading trading verbs (`bought`, `sold`) are strictly avoided.
5. **Zero-Hallucination AI Guard**: Every numerical metric, percentage, and basis-point change cited in AI commentary is verified against the raw diff JSON within $\pm 0.05$ tolerance. If any unverified number appears, output is rejected and replaced by a deterministic mathematical template.
6. **Config-Driven Extensibility**: Adding an entirely new mutual fund requires only a JSON definition in `config/funds.json` without modifying engine code.

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
- **Glassmorphic Next.js Dashboard**:
  - Dark mode aesthetic tailored with Inter typography, vibrant emerald/rose delta badges, and translucent glass panels.
  - Multi-fund catalog with real-time search, category filtering, and executive metrics.
  - Interactive multi-month holding history area chart powered by Recharts.
  - Fully responsive on mobile, tablet, and desktop.

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
│   │   ├── pdf_text.py          # pdfplumber dynamic page parser
│   │   └── ocr_fallback.py      # Optional Tesseract OCR fallback
│   ├── parse.py                 # Multi-tier orchestrator
│   ├── validate.py              # Invariant validator & name normalizer
│   ├── diff.py                  # Month-over-month diff engine
│   ├── summarize.py             # Pluggable AI summarizer & hallucination guard
│   ├── build_index.py           # Master catalog generator
│   ├── backfill.py              # Historical backfill utility
│   ├── run.py                   # Automated pipeline runner
│   └── tests/                   # 37 comprehensive unit & integration tests
│       ├── fixtures/            # Real-world factsheet & disclosure samples
│       ├── test_excel_parser.py
│       ├── test_pdf_parser.py
│       ├── test_orchestrator.py
│       ├── test_validator.py
│       ├── test_diff.py
│       ├── test_summarize.py
│       ├── test_multi_fund.py
│       └── test_run.py
├── web/                         # Next.js 16 App Router application
│   ├── src/
│   │   ├── app/                 # Routes: / and /fund/[id]
│   │   ├── components/          # FundCatalog, HoldingHistoryChart
│   │   ├── lib/                 # Precomputed data loaders
│   │   └── types/               # TypeScript data definitions
│   └── public/data/             # Mirrored data directory for static export
├── .github/workflows/
│   └── pipeline.yml             # Scheduled GitHub Actions workflow
└── requirements.txt             # Python pipeline dependencies
```

---

## 🚀 Quickstart & Local Development

### 1. Prerequisites
- **Python**: 3.9, 3.10, or 3.11
- **Node.js**: v18.17+ or v20+
- **Git**

### 2. Python Pipeline Setup
```bash
# Clone the repository
git clone https://github.com/your-username/mutual-fund-tracker.git
cd mutual-fund-tracker

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install pipeline dependencies
pip install -r requirements.txt
```

### 3. Run the Test Suite
Run all 37 unit and integration tests:
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

# Backfill historical snapshots using local fixtures
python3 pipeline/backfill.py --fixtures-only
```

### 5. Run the Next.js Dashboard
```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Start local development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to explore the dashboard.

### 6. Build Production Bundle
```bash
npm --prefix web run build
```
This automatically runs the `prebuild` hook to sync `data/` to `web/public/data/` and statically compiles all fund pages.

---

## ➕ How to Add a New Mutual Fund

Adding a new fund requires **zero code modifications** to the parser or pipeline engine.

### Step 1: Add Fund Configuration to `config/funds.json`
Open [`config/funds.json`](config/funds.json) and add an entry:
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

| Config Key | Description |
|---|---|
| `id` | Unique URL-safe slug for the fund (creates `data/{id}/` and `/fund/{id}`). |
| `name` | Official scheme name displayed on cards and tables. |
| `amc` | Asset Management Company name. |
| `type` | Must be `"equity"` to be processed. |
| `category` | Scheme category (e.g. `"Flexi Cap"`, `"ELSS / Tax Saver"`, `"Large & Mid Cap"`). |
| `source_page` | URL of the AMC downloads page where disclosures are published. |
| `excel_sheet` | Exact sheet name inside the AMC's monthly portfolio disclosure workbook. |
| `pdf_section_keyword` | Text substring used to dynamically locate the scheme's portfolio page in the PDF factsheet. |
| `parser_preference` | Ordered preference list, typically `["excel", "pdf_text"]`. |
| `significant_change_pp` | Delta threshold in percentage points for highlighting significant moves (default: `0.5`). |
| `enabled` | Set to `true` to activate processing. |

### Step 2: Add Company Name Aliases (If Needed)
If the new fund holds stocks with naming variations (e.g., `"Maharashtra Scooters Limited"` vs `"Maharashtra Scooters Ltd."`), add them to [`config/aliases.json`](config/aliases.json):
```json
"maharashtra scooters limited": "Maharashtra Scooters Ltd.",
"maharashtra scooters": "Maharashtra Scooters Ltd."
```

### Step 3: Run Ingestion
```bash
python3 pipeline/backfill.py --fixtures-only
npm --prefix web run build
```
The new fund immediately appears in the dashboard catalog and generates its own `/fund/[id]` route!

---

## 🔒 Secrets & Environment Configuration

The pipeline runs completely without API keys by defaulting to its built-in **Deterministic Rules Engine**. To enable external LLM commentary, configure any of the following optional environment variables:

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | Selected provider: `auto`, `openrouter`, `gemini`, `groq`, or `template_fallback` | `auto` |
| `OPENROUTER_API_KEY` | API key from [OpenRouter](https://openrouter.ai/) (supports free models) | None |
| `OPENROUTER_MODEL` | Model ID on OpenRouter | `google/gemini-2.0-flash-exp:free` |
| `GEMINI_API_KEY` | Google AI Studio Gemini API Key | None |
| `GROQ_API_KEY` | Groq Cloud API Key | None |

### GitHub Actions Secrets Setup
1. Go to your repository on GitHub: **Settings > Secrets and variables > Actions**.
2. Click **New repository secret** and add your optional `OPENROUTER_API_KEY` or `GEMINI_API_KEY`.
3. Under **Settings > Actions > General > Workflow permissions**, select:
   - ✅ **Read and write permissions** (allows the workflow to commit updated `data/` snapshots).
   - ✅ **Allow GitHub Actions to create and approve pull requests**.

---

## 🛡 Number Verification & Safety

Mutual fund holdings require absolute numerical precision. The summarizer enforces a strict two-stage verification barrier:

1. **System Prompt Constraint**: Pure diff numbers are fed to the model with an explicit instruction prohibiting outside market data, return projections, or unsolicited advice.
2. **Post-Check Regex Extractor (`verify_numbers_in_summary`)**:
   - Strips legitimate calendar years and month dates.
   - Extracts all remaining numerical figures and percentage changes.
   - Confirms that **every extracted number** exists in the raw diff JSON within a $\pm 0.05$ rounding tolerance.
   - **Rejection & Fallback**: If an unverified number appears (e.g. an invented benchmark return or portfolio gain), the response is rejected and replaced with the deterministic template.

---

## 🌐 Deploying to Vercel

1. Push your repository to GitHub.
2. Go to [Vercel Dashboard](https://vercel.com/dashboard) and click **Add New > Project**.
3. Import your GitHub repository.
4. Set the **Root Directory** to `web`.
5. Keep default Framework Preset as **Next.js**.
6. Click **Deploy**.

Every time GitHub Actions detects a new month's disclosure and commits to `data/`, Vercel automatically triggers a redeployment and serves updated static assets worldwide.

---

## 🧪 Testing

The repository maintains **100% test pass rate** across all modules:
```bash
python3 -m pytest pipeline/tests/ -v
```
Test coverage spans:
- Excel OpenXML & xlrd parser extraction across domestic and foreign holdings
- Dynamic PDF table finding, header parsing, and AMC commentary extraction
- Multi-tier parser fallback behavior
- Strict invariant validation (bounds, monotonicity, exact 10 holdings, sum check)
- Canonical company key normalization
- Diff engine edge cases (zero churn, rank movements, entry/exit detection)
- Hallucination guard (number verification acceptance & rejection)
- Template fallback generation
- Multi-fund configuration integrity and catalog index generation
- Pipeline runner idempotency and CLI flags

---

## 📜 Disclaimer

*This application is strictly for informational and educational purposes. Changes in portfolio weights or constituents do not constitute investment advice or recommendations to buy or sell any security. Data is sourced from publicly available AMC monthly factsheets and portfolio disclosures.*

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

# Phase 4: GitHub Actions Workflow — Plan

## Goal
Automate the mutual fund data pipeline using scheduled and event-driven GitHub Actions workflows. The workflow will run unattended on GitHub's free tier, discover newly published monthly factsheets/disclosures during publishing windows (days 3–20), parse, validate, diff, and commit the updated data back to the repository—automatically triggering Vercel redeployment without human intervention.

---

## Requirements Addressed
- **FR-9.1**: Scheduled cron (twice daily at 6:00 AM IST / 00:30 UTC and 6:00 PM IST / 12:30 UTC on days 3–20 of each month).
- **FR-9.2**: Manual `workflow_dispatch` trigger with options (`force`, `fund_id`, `dry_run`).
- **FR-9.3**: Zero-diff clean exit when no new factsheet has been published.
- **FR-9.4**: Automated git commit and push of `/data` files on new data detection.
- **NFR-1**: 100% free stack running within GitHub Actions monthly free allowances.
- **NFR-2, NFR-4**: Pre-flight test suite execution, structured logging, and failure visibility.
- **UAT Criteria 10**: Pipeline automation workflow configured, validated, and executable end-to-end.

---

## Architecture & Technical Decisions

1. **Dedicated Automation Entrypoint (`pipeline/run.py`)**:
   - Rather than embedding bash script logic into the YAML workflow, provide a clean Python orchestrator `pipeline/run.py`.
   - Iterates through all active funds in `config/funds.json`.
   - Checks if the newest published report already exists in `data/{fund_id}/{YYYY-MM}.json`.
   - If already present, skips gracefully.
   - If new, downloads, parses, validates, writes snapshot, computes diff against previous month, and updates `data/index.json`.
   - Communicates state to GitHub Actions via `$GITHUB_OUTPUT` (`new_data=true/false`).
2. **Cron Schedule Tuning**:
   - Indian AMCs publish factsheets between the 5th and 15th calendar day of each month.
   - Cron: `30 0,12 3-20 * *` (00:30 UTC = 6:00 AM IST, 12:30 UTC = 6:00 PM IST, days 3 through 20).
   - Runs ~36 times a month; each execution takes under 15 seconds, well within GitHub Actions free tier (2,000 minutes/month).
3. **Bot Git Commit & Push**:
   - Commits as `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`.
   - Uses `[skip ci]` in the commit message to prevent recursive workflow triggers while still triggering Vercel deployment webhooks.
4. **Pre-commit Quality Gate**:
   - Every workflow run executes `pytest pipeline/tests/` before scraping/processing, ensuring broken code never runs against live data.

---

## Detailed Task Breakdown

### Task 1: Pipeline Orchestrator Entrypoint (`pipeline/run.py`)
- **Responsibilities**:
  - Load active funds from `config/funds.json`.
  - For each fund:
    - Scrape download page with `Scraper`.
    - Find the most recent available month.
    - Check if snapshot `data/{fund_id}/{month}.json` exists.
    - If missing or `--force`:
      - Download disclosure file (Excel preferred, PDF fallback).
      - Parse and validate using `ParserOrchestrator`.
      - Save snapshot JSON.
      - Find previous available month snapshot in `data/{fund_id}/`.
      - Compute diff with `DiffEngine` and save `{month}.diff.json`.
      - Flag `new_data_added = True`.
  - If `new_data_added`:
    - Rebuild `data/index.json`.
    - If in GitHub Actions environment, write `new_data=true` to `$GITHUB_OUTPUT`.
  - Else:
    - Log "No new publications found. Everything up-to-date."
    - Write `new_data=false` to `$GITHUB_OUTPUT`.
  - Support CLI arguments: `--fund-id`, `--force`, `--dry-run`.

### Task 2: GitHub Actions Workflow (`.github/workflows/pipeline.yml`)
- **Triggers**:
  - `schedule`: cron `30 0,12 3-20 * *`
  - `workflow_dispatch`:
    - `force`: boolean (default `false`)
    - `fund_id`: string (default `all`)
    - `dry_run`: boolean (default `false`)
  - `push`: branches `[main]`, paths `['pipeline/**', 'config/**', 'requirements.txt', '.github/workflows/**']`
- **Job Steps**:
  1. `actions/checkout@v4` with repository write permissions.
  2. `actions/setup-python@v5` with Python 3.11 and pip caching.
  3. Install dependencies from `requirements.txt`.
  4. Run tests: `pytest pipeline/tests/ -v`.
  5. Run pipeline: `python3 pipeline/run.py`.
  6. Commit & push changes:
     - Check if `steps.pipeline.outputs.new_data == 'true'`.
     - Git add `data/`.
     - Git commit: `chore(data): update mutual fund holdings [skip ci]`.
     - Git push.

### Task 3: Unit Tests for Pipeline Runner (`pipeline/tests/test_run.py`)
- **Scenarios**:
  - Test runner skips when snapshot already exists and `--force` is false.
  - Test runner processes new month and updates snapshot, diff, and index.
  - Test runner respects `--dry-run` flag.

### Task 4: Workflow Validation & Dry Run
- Test `pipeline/run.py` locally to verify clean zero-diff exit.
- Validate YAML structure and step sequence.

---

## Verification & Acceptance Checklist
- [ ] `pipeline/run.py` runs cleanly locally, detecting already existing snapshots without performing unnecessary writes.
- [ ] `.github/workflows/pipeline.yml` is valid YAML with correct cron, triggers, permissions, and steps.
- [ ] `pytest pipeline/tests/` passes with all tests green.
- [ ] Step outputs (`new_data=true/false`) are properly formatted for GitHub Actions runner.

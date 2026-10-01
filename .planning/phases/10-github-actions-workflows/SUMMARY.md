# Phase 10 Summary — GitHub Actions Workflows

**Status**: ✅ Complete  
**Commit**: `d4abdeb`

## What Was Built

### `.github/workflows/backfill.yml` (new)
On-demand backfill via `workflow_dispatch`. Accepts:
- `fund_id` (default: "all")
- `start_month` YYYY-MM (required)
- `end_month` YYYY-MM (required)
- `dry_run` boolean (default: false)

Inline Python validates YYYY-MM format and range before running. Commits data with `[skip ci]`. Generates a GitHub Step Summary.

### `.github/workflows/register-fund.yml` (new)
Auto-triggered on `push` to `config/funds.json`. Detects newly added enabled equity funds via Python set-diff vs `HEAD~1`. For each new fund:
1. Validates config with `validate_fund_config.py`
2. Runs 12-month online backfill
3. Commits data to repo with `[skip ci]`

Gracefully handles first-commit edge case (no HEAD~1).

### `pipeline/validate_fund_config.py` (new)
Standalone validator. Checks:
- Required fields (id, name, amc, type, source_page, parser_preference)
- `id` is `^[a-z0-9-]+$` kebab-case
- `source_page` is valid HTTPS URL
- `type` ∈ {equity, debt, hybrid, liquid}
- `parser_preference` entries ∈ {excel, pdf_text, ocr}
- `significant_change_pp` in [0.1, 5.0]
- Exit 0 = valid, exit 1 = invalid

### `.github/workflows/pipeline.yml` (patched)
Added `if: "!contains(github.event.head_commit.message, '[skip ci]')"` on `run-pipeline` job to prevent bot data commits from cascading into infinite pipeline runs.

## Verification Results
- ✅ All 3 workflow YAML files pass `yaml.safe_load()` parsing
- ✅ `validate_fund_config.py --fund-id ppfas-flexicap` exits 0
- ✅ `validate_fund_config.py --fund-id ppfas-taxsaver` exits 0
- ✅ `validate_fund_config.py --fund-id nonexistent` exits 1 with clear error
- ✅ 45/45 tests pass (no regressions)

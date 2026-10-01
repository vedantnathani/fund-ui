# Phase 10 — GitHub Actions: Backfill & Register-Fund Workflows

**Milestone**: v1.1  
**Status**: ⬜ Not started  
**Goal**: Create two new GitHub Actions workflow files that the UI (Phase 11/12) will dispatch via the GitHub API: `backfill.yml` for on-demand period backfills, and `register-fund.yml` for auto-validating and backfilling newly added funds.

---

## Context

### What exists today
- `.github/workflows/pipeline.yml` — the daily cron + `workflow_dispatch` runner (already has `fund_id`, `dry_run`, `force` inputs)
- `pipeline/backfill.py` — now accepts `--start YYYY-MM --end YYYY-MM --fund-id` (Phase 9)
- `pipeline/run.py` — the main pipeline runner (scrape → parse → diff → summarize → commit)
- `config/funds.json` — the fund registry

### What Phase 10 adds
1. **`backfill.yml`** — new workflow, `workflow_dispatch` only, accepts `fund_id` + `start_month` + `end_month`. Runs `pipeline/backfill.py` with those args. Commits resulting data back to repo, triggering Vercel redeploy.
2. **`register-fund.yml`** — new workflow, triggered on `push` to `config/funds.json`. Detects which fund IDs are newly added (compared to the previous commit), validates them, and runs a 12-month online backfill for each new fund.
3. **`pipeline.yml` patch** — add a `[skip ci]` guard so pushes from Actions bots don't cascade into infinite loops; also expose `start_month`/`end_month` inputs for power-user direct dispatch.

---

## Tasks

### Task 10.1 — Create `.github/workflows/backfill.yml`
**File**: `.github/workflows/backfill.yml` (new)  
**What**: A standalone GitHub Actions workflow for on-demand, date-range backfills.

```yaml
name: On-Demand Backfill

on:
  workflow_dispatch:
    inputs:
      fund_id:
        description: 'Fund ID to backfill (or "all")'
        required: false
        type: string
        default: 'all'
      start_month:
        description: 'Start month (YYYY-MM, inclusive)'
        required: true
        type: string
      end_month:
        description: 'End month (YYYY-MM, inclusive)'
        required: true
        type: string
      dry_run:
        description: 'Simulate without writing files'
        required: false
        type: boolean
        default: false
```

Steps:
1. Checkout repo with `token: ${{ secrets.GITHUB_TOKEN }}` and `fetch-depth: 0`
2. Set up Python 3.11 with pip cache
3. Install `requirements.txt`
4. Run test suite (`pytest pipeline/tests/ -v`)
5. Run backfill:
   ```bash
   python pipeline/backfill.py \
     --fund-id "${{ inputs.fund_id }}" \
     --start "${{ inputs.start_month }}" \
     --end "${{ inputs.end_month }}" \
     [--dry-run if inputs.dry_run == 'true']
   ```
6. Commit & push data: git add `data/`, commit with `[skip ci]` tag, push to main (only when `dry_run != 'true'`)

Permissions: `contents: write`  
Runner: `ubuntu-latest`

**Acceptance**: The workflow file is syntactically valid YAML; manual dispatch with `fund_id=ppfas-flexicap`, `start_month=2026-08`, `end_month=2026-08`, `dry_run=true` would succeed if triggered.

---

### Task 10.2 — Create `.github/workflows/register-fund.yml`
**File**: `.github/workflows/register-fund.yml` (new)  
**What**: Auto-triggered when `config/funds.json` changes on `main`. Detects newly added fund IDs and runs an initial 12-month online backfill for each.

Trigger:
```yaml
on:
  push:
    branches: [main]
    paths: ['config/funds.json']
```

Steps:
1. Checkout with full history (`fetch-depth: 2`)
2. Set up Python 3.11 + install dependencies
3. **Detect new funds** — Python inline script:
   ```python
   import json, subprocess, sys
   # Get funds.json from previous commit
   prev_raw = subprocess.check_output(["git", "show", "HEAD~1:config/funds.json"])
   curr_raw = open("config/funds.json").read()
   prev_ids = {f["id"] for f in json.loads(prev_raw)}
   curr_ids = {f["id"] for f in json.loads(curr_raw) if f.get("enabled", True)}
   new_ids = curr_ids - prev_ids
   print("NEW_FUND_IDS=" + ",".join(new_ids))
   # Write to GITHUB_OUTPUT
   with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
       fh.write(f"new_fund_ids={','.join(new_ids)}\n")
       fh.write(f"has_new_funds={'true' if new_ids else 'false'}\n")
   ```
4. Run test suite
5. **Backfill each new fund** (conditional on `has_new_funds == 'true'`):
   ```bash
   IFS=',' read -ra FUNDS <<< "${{ steps.detect.outputs.new_fund_ids }}"
   for fund_id in "${FUNDS[@]}"; do
     echo "Backfilling $fund_id (last 12 months)..."
     python pipeline/backfill.py \
       --fund-id "$fund_id" \
       --start "$(date -d '12 months ago' +%Y-%m)" \
       --end "$(date +%Y-%m)"
   done
   ```
6. Commit & push data with `[skip ci]` tag (only when new funds were processed)
7. Output a summary step listing which funds were backfilled

Permissions: `contents: write`  
Runner: `ubuntu-latest`

Edge cases:
- If `config/funds.json` is invalid JSON, the detect step fails loudly (Python will raise `json.JSONDecodeError`)
- If the push is the first commit (no `HEAD~1`), the detect step gracefully treats all current funds as "new"
- Funds with `"enabled": false` are skipped

**Acceptance**: The workflow file is syntactically valid YAML. The detect-new-funds logic correctly identifies the diff between two versions of `funds.json`.

---

### Task 10.3 — Patch `pipeline.yml`: add `[skip ci]` guard
**File**: `.github/workflows/pipeline.yml` (edit)  
**What**: The current `push` trigger fires whenever anything is pushed to `main`, including data commits from the pipeline bot itself. This creates an infinite loop risk. Fix by adding a commit message filter.

Change the `push` trigger from:
```yaml
push:
  branches:
    - main
  paths:
    - 'pipeline/**'
    - 'config/**'
    - 'requirements.txt'
    - '.github/workflows/pipeline.yml'
```

To — add a step condition at the top of `run-pipeline` job:
```yaml
jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    if: "!contains(github.event.head_commit.message, '[skip ci]')"
```

This is the idiomatic GitHub Actions guard. The `paths` filter already prevents data-only pushes from triggering this workflow, but the explicit `[skip ci]` guard future-proofs it.

Also ensure the data commit step in `pipeline.yml` uses `[skip ci]` in the commit message (it already does — verify it's present).

**Acceptance**: `pipeline.yml` has `if: "!contains(github.event.head_commit.message, '[skip ci]')"` on the `run-pipeline` job.

---

### Task 10.4 — Add `validate_fund_config.py` helper script
**File**: `pipeline/validate_fund_config.py` (new)  
**What**: A standalone Python script used by `register-fund.yml` to validate a newly added fund entry before committing a backfill. Checks:
- Required fields present: `id`, `name`, `amc`, `type`, `source_page`, `parser_preference`
- `type` is one of: `equity`, `debt`, `hybrid`, `liquid`
- `source_page` is a valid HTTPS URL
- `id` matches `^[a-z0-9-]+$`
- `parser_preference` is a list with at least one entry from `["excel", "pdf_text", "ocr"]`
- `significant_change_pp` is between 0.1 and 5.0 (if present)

Exit code 0 = valid, exit code 1 = invalid (with error messages to stderr).

Usage: `python pipeline/validate_fund_config.py --fund-id <id>`

**Acceptance**: `python pipeline/validate_fund_config.py --fund-id ppfas-flexicap` exits 0. `python pipeline/validate_fund_config.py --fund-id nonexistent-fund` exits 1 with a clear error.

---

## Verification Checklist

- [ ] `yamllint .github/workflows/backfill.yml` (or equivalent check) — valid YAML
- [ ] `yamllint .github/workflows/register-fund.yml` — valid YAML
- [ ] `backfill.yml` has all 4 inputs: `fund_id`, `start_month`, `end_month`, `dry_run`
- [ ] `backfill.yml` commit step uses `[skip ci]`
- [ ] `register-fund.yml` detect-new-funds step correctly computes set diff
- [ ] `register-fund.yml` skips disabled funds (`"enabled": false`)
- [ ] `pipeline.yml` has `[skip ci]` guard on `run-pipeline` job
- [ ] `validate_fund_config.py --fund-id ppfas-flexicap` exits 0
- [ ] `validate_fund_config.py --fund-id nonexistent` exits 1
- [ ] All 45 existing tests still pass (no regressions)

---

## Files Changed

| File | Change |
|------|--------|
| `.github/workflows/backfill.yml` | New — on-demand backfill via `workflow_dispatch` |
| `.github/workflows/register-fund.yml` | New — auto-triggered on `config/funds.json` push |
| `.github/workflows/pipeline.yml` | Edit — add `[skip ci]` guard on `run-pipeline` job |
| `pipeline/validate_fund_config.py` | New — fund config validator script |

# Phase 9 — Backfill CLI Enhancements

**Milestone**: v1.1  
**Status**: ⬜ Not started  
**Goal**: Make `pipeline/backfill.py` fully parameterizable by date range and fund, so GitHub Actions workflows (and the future UI) can dispatch targeted backfills for any `YYYY-MM` window.

---

## Context

### What exists today
- `backfill.py` accepts: `--fund-id` (default "all"), `--months` (integer count, default 12), `--fixtures-only`, `--dry-run`, `--data-dir`
- `--months` is a backwards count (e.g., last 12 months) — no way to say "give me Jan 2025 through Jun 2025"
- `run_online_backfill()` hardcodes `months_count` as a ceiling on `discovered[:months_count]`; month filtering is positional, not date-bounded
- `pipeline.yml` already accepts `fund_id` + `dry_run` inputs via `workflow_dispatch`
- No `backfill.yml` workflow exists yet (Phase 10 creates it, but it needs this CLI to be ready first)

### What Phase 9 adds
1. `--start YYYY-MM` and `--end YYYY-MM` args → explicit date-range backfill
2. `--months` stays as a shorthand (last N months from today), now computed as a date range internally
3. Both `run_fixtures_backfill` and `run_online_backfill` respect the date range, skipping months outside the window
4. Unit tests for the new CLI arg parsing and date-range filtering logic

---

## Tasks

### Task 9.1 — Add `--start` / `--end` args to `backfill.py` CLI
**File**: `pipeline/backfill.py`  
**What**: Extend `main()` argparse block with two new optional arguments:
```
--start YYYY-MM    Earliest month to backfill (inclusive). Defaults to 12 months ago.
--end YYYY-MM      Latest month to backfill (inclusive). Defaults to current month.
```
- Validate format with a helper `parse_month(s: str) -> str` that raises `argparse.ArgumentTypeError` if not matching `^\d{4}-(0[1-9]|1[0-2])$`
- If `--start` and `--months` are both given, `--start` wins (log a deprecation-style warning about `--months` being ignored)
- If only `--months` is given, compute `start = today minus N months` as `YYYY-MM`
- Compute `end` default as current month (`datetime.now().strftime("%Y-%m")`)

**Acceptance**: `python3 pipeline/backfill.py --help` shows `--start` and `--end` options.

---

### Task 9.2 — Refactor `run_online_backfill` to accept date-range params
**File**: `pipeline/backfill.py`  
**What**: Change signature from:
```python
def run_online_backfill(fund_id, months_count, data_dir, cache_dir, dry_run)
```
to:
```python
def run_online_backfill(fund_id, start_month, end_month, data_dir, cache_dir, dry_run)
```
- After discovering all available months via `scraper.discover_ppfas_links(...)`, filter to only those where `start_month <= month <= end_month`
- Log: `"Filtered to N months in range [start_month, end_month]"`
- Idempotency: before downloading/parsing a month, check if `data/{fund_id}/{YYYY-MM}.json` already exists; if so, load from disk and skip re-download
- `main()` passes `start_month` and `end_month` derived from the parsed args

**Acceptance**: `python3 pipeline/backfill.py --fund-id ppfas-flexicap --start 2026-06 --end 2026-08 --dry-run` logs exactly the 3 months in range without error.

---

### Task 9.3 — Refactor `run_fixtures_backfill` to respect date range
**File**: `pipeline/backfill.py`  
**What**: `run_fixtures_backfill` currently has a hardcoded `months_plan` list for 2026-06/07/08. Add `start_month: str = "2026-06"` and `end_month: str = "2026-08"` params and filter `months_plan` to only include months within the range.
- `main()` passes the resolved `start_month`/`end_month` to this function too

**Acceptance**: `python3 pipeline/backfill.py --fixtures-only --start 2026-07 --end 2026-08 --dry-run` processes only July and August fixture months.

---

### Task 9.4 — Add a helper: `month_range(start, end) -> List[str]`
**File**: `pipeline/backfill.py`  
**What**: Utility function that generates all `YYYY-MM` strings between start and end (inclusive):
```python
def month_range(start: str, end: str) -> List[str]:
    """Return sorted list of YYYY-MM strings from start to end inclusive."""
```
- Use `datetime` arithmetic (add months via `timedelta` or `relativedelta` if available, otherwise manual rollover)
- No external dependencies beyond stdlib (avoid requiring `python-dateutil`)

**Acceptance**: `month_range("2026-06", "2026-09")` returns `["2026-06", "2026-07", "2026-08", "2026-09"]`.

---

### Task 9.5 — Unit tests for CLI enhancements
**File**: `pipeline/tests/test_backfill_cli.py` (new file)  
**What**: Add tests covering:
1. `test_parse_month_valid` — `parse_month("2026-06")` returns `"2026-06"`
2. `test_parse_month_invalid` — `parse_month("06-2026")` raises `ArgumentTypeError`
3. `test_month_range_basic` — `month_range("2026-06", "2026-09")` → 4 months
4. `test_month_range_single` — `month_range("2026-08", "2026-08")` → `["2026-08"]`
5. `test_month_range_reversed` — `month_range("2026-09", "2026-06")` raises `ValueError`
6. `test_backfill_fixtures_date_filter` — mock `ParserOrchestrator` and `DiffEngine`; call `run_fixtures_backfill(start_month="2026-07", end_month="2026-08", dry_run=True)`; assert only 2 months processed
7. `test_backfill_online_date_filter` — mock `Scraper.discover_ppfas_links` returning 3 months; call `run_online_backfill(start_month="2026-07", end_month="2026-07", dry_run=True)`; assert only 1 month processed

**Acceptance**: All 7 new tests pass. Total test count ≥ 44.

---

## Verification Checklist

- [ ] `python3 pipeline/backfill.py --help` shows `--start` and `--end` options
- [ ] `python3 pipeline/backfill.py --fixtures-only --start 2026-06 --end 2026-08 --dry-run` runs without error, logs 3 months
- [ ] `python3 pipeline/backfill.py --fixtures-only --start 2026-07 --end 2026-08 --dry-run` runs without error, logs 2 months (June skipped)
- [ ] `python3 pipeline/backfill.py --fixtures-only --start 2026-08 --end 2026-08 --dry-run` runs without error, logs 1 month
- [ ] `python3 -m pytest pipeline/tests/test_backfill_cli.py -v` → 7/7 pass
- [ ] `python3 -m pytest pipeline/tests/ -v` → all existing tests still pass (no regressions)
- [ ] `--months 3` still works (no breaking change for existing callers)

---

## Files Changed

| File | Change |
|------|--------|
| `pipeline/backfill.py` | Add `--start`/`--end` args, `parse_month()`, `month_range()`, refactor both backfill functions |
| `pipeline/tests/test_backfill_cli.py` | New — 7 unit tests |

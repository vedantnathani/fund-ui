# Phase 3: Diff Engine + Snapshots + Backfill — Plan

## Goal
Build the pure Python diff engine, snapshot serialization system, fund index generator, and 12-month historical backfill utility. This populates `data/` with verified snapshots and month-over-month diffs required for the dashboard and LLM summary layers.

---

## Requirements Addressed
- **FR-5**: Snapshot Schema (`data/{fund_id}/{YYYY-MM}.json`)
- **FR-6**: Diff Engine (`pipeline/diff.py` — entered/exited top 10, weight deltas, rank moves, significant flags, strictly neutral financial wording)
- **FR-10**: Backfill Script (`pipeline/backfill.py` — historical data ingestion for past 12 months)
- **NFR-2, NFR-4, NFR-5**: Reliability, structured logging, `--dry-run` flag support, unit tests
- **UAT Criteria 3**: Diff engine correctly identifies holdings that entered/exited top 10.

---

## Architecture & Technical Decisions

1. **Pure Python Diff Logic (FR-6.1, FR-6.6)**:
   - Zero LLM dependencies.
   - Strict terminology compliance: "entered top 10" / "exited top 10" (never "newly bought" or "sold").
   - Weight changes labeled as "weight increased/decreased" because movements can result from relative stock price variation rather than manager transactions.
2. **Deterministic Canonical Identity Matching**:
   - Compares holdings by canonical `key` (preferring ISIN code e.g. `INE040A01034`, falling back to normalized company slug).
   - This ensures company renames or spelling variations (e.g. Google -> Alphabet) do not create false enter/exit signals.
3. **Threshold-Based Significance (FR-6.5)**:
   - Configurable per fund via `significant_change_pp` (default `0.5` percentage points).
   - Holdings with `abs(weight_delta_pp) >= significant_change_pp` receive `significant: true`.
4. **Fund Index Aggregation (`data/index.json`)**:
   - Single lightweight index file read by the Next.js dashboard at build/render time to discover all funds, available months, latest status, and highlights without traversing filesystem directories.

---

## Detailed Task Breakdown

### Task 1: Diff Engine (`pipeline/diff.py`)
- **Inputs**: Current snapshot dict, Previous snapshot dict, Fund configuration dict.
- **Calculations**:
  - `entered_top10`: Holdings present in current top 10 but absent in previous top 10.
  - `exited_top10`: Holdings present in previous top 10 but absent in current top 10.
  - `retained`: Holdings present in both months, with:
    - `weight_delta_pp = round(curr_weight - prev_weight, 2)`
    - `rank_change = prev_rank - curr_rank` (positive = moved up, negative = dropped)
    - `direction`: `"increased"` | `"decreased"` | `"unchanged"`
    - `significant`: `abs(weight_delta_pp) >= significant_change_pp`
  - `summary`:
    - Counts: `num_entered`, `num_exited`, `num_increased`, `num_decreased`, `num_unchanged`, `num_significant`.
    - `biggest_increase`: `{ "name": str, "weight_delta_pp": float }`
    - `biggest_decrease`: `{ "name": str, "weight_delta_pp": float }`
  - Carry forward AMC commentary and compute top 10 sum delta.
- **CLI Interface**:
  - `python3 pipeline/diff.py --current data/{fund}/{curr}.json --previous data/{fund}/{prev}.json --out data/{fund}/{curr}.diff.json`
  - Supports `--dry-run`.

### Task 2: Unit Tests for Diff Engine (`pipeline/tests/test_diff.py`)
- **Test Scenarios**:
  1. **Entered & Exited Detection (UAT 3)**: Verify simulated addition and deletion of holdings.
  2. **Consecutive Real Months**: Verify July 2026 vs August 2026 fixtures (stable membership with rank and weight shifts).
  3. **No-Changes Month**: Verify identical snapshots produce 0 entered, 0 exited, all deltas 0.00.
  4. **Significance Threshold**: Verify moves $\ge 0.5\text{pp}$ are flagged significant while $< 0.5\text{pp}$ are not.
  5. **Neutral Wording & Direction**: Confirm keys and values adhere to schema.

### Task 3: Fund Index Generator (`pipeline/build_index.py`)
- **Inputs**: Scans `data/` directory for all `{fund_id}` folders containing `{YYYY-MM}.json` snapshots.
- **Outputs**: `data/index.json` containing:
  - `last_updated`: ISO timestamp
  - `funds`: Array of fund summaries (id, name, amc, latest_month, latest_as_of, top10_total_pct, top_holding, months_available, latest_changes_count).
- Supports CLI `--out` and importable function `build_index()`.

### Task 4: Backfill Script (`pipeline/backfill.py`)
- **Workflow**:
  1. Inspects PPFAS factsheet page (using `Scraper`).
  2. Identifies the latest `N` months (default: 12 months) of available reports.
  3. For each month:
     - Downloads disclosure file (Excel preferred, PDF fallback) if not cached.
     - Parses using `ParserOrchestrator`.
     - Validates and saves snapshot to `data/{fund_id}/{YYYY-MM}.json`.
  4. Sorts snapshots chronologically and computes pairwise diffs:
     - Saves diff to `data/{fund_id}/{YYYY-MM}.diff.json`.
  5. Rebuilds `data/index.json`.
- Supports `--fund-id`, `--months N`, `--dry-run`, `--fixtures-only` (for offline runs using existing fixture files).

---

## Verification & Acceptance Checklist
- [ ] `pytest pipeline/tests/test_diff.py` passes with 100% green tests.
- [ ] Diff engine correctly identifies entered/exited holdings (UAT Criteria #3).
- [ ] Diff between July 2026 and August 2026 matches exact audited movements.
- [ ] Zero-changes test passes without errors.
- [ ] Backfill on fixtures creates snapshots for June, July, August 2026 and valid diffs.
- [ ] `data/index.json` is generated with valid structure and schema.

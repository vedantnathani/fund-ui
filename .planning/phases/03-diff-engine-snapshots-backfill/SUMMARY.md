# Phase 3: Diff Engine + Snapshots + Backfill — Summary

## Execution Overview
Phase 3 completed the pure Python diff engine, snapshot serialization, fund index generation, and historical backfill utility.

## Deliverables Completed
1. **Diff Engine (`pipeline/diff.py`)**:
   - Compares consecutive monthly snapshots without any LLM dependencies (`FR-6.1`).
   - Identifies holdings that `entered_top10` and `exited_top10` (`FR-6.2`, `FR-6.3`).
   - Uses cross-source match keys via `HoldingsNormalizer` to ensure consistent matching across PDF (no ISIN) and Excel (with ISIN) sources.
   - Calculates weight deltas (`weight_delta_pp`) and rank changes (`prev_rank - curr_rank`) for all retained holdings (`FR-6.4`).
   - Flags changes as `significant: true` when $| \Delta w | \ge 0.5\text{pp}$ (`FR-6.5`).
   - Strictly enforces neutral wording ("weight increased/decreased", "entered/exited top 10") rather than speculative transactional phrasing (`FR-6.6`).
   - Computes overall summary statistics (biggest increase, biggest decrease, counts).
2. **Fund Index Generator (`pipeline/build_index.py`)**:
   - Scans `data/` directory and compiles fund cards into `data/index.json`.
   - Includes latest month, top holding, available months list, and summary of latest top-10 changes for fast static ingestion by the Next.js frontend.
3. **Backfill Utility (`pipeline/backfill.py`)**:
   - Supports both online backfill (scraping and downloading past 12 months) and offline fixtures backfill (`--fixtures-only`).
   - Backfilled June 2026, July 2026, and August 2026 snapshots and pairwise diffs into `data/ppfas-flexicap/`.
4. **Data Artifacts**:
   - `data/ppfas-flexicap/2026-06.json`: June 2026 snapshot.
   - `data/ppfas-flexicap/2026-07.json`: July 2026 snapshot.
   - `data/ppfas-flexicap/2026-07.diff.json`: July 2026 vs June 2026 diff.
   - `data/ppfas-flexicap/2026-08.json`: August 2026 snapshot.
   - `data/ppfas-flexicap/2026-08.diff.json`: August 2026 vs July 2026 diff.
   - `data/index.json`: Master index for all tracked funds.
5. **Test Suite (`pipeline/tests/test_diff.py`)**:
   - 4 new unit tests covering:
     - Entered and exited holdings detection (UAT Criteria #3).
     - Retained holdings, rank changes, and weight deltas.
     - Significance threshold evaluation.
     - Zero-changes / identical snapshot diff.
   - Total test suite now at **22 / 22 passing tests**.

## Requirements Verified
- **FR-5**: Snapshot schema implemented and validated in JSON.
- **FR-6**: Pure Python diff engine with strict neutral terminology.
- **FR-10**: Backfill pipeline working end-to-end.
- **UAT Criteria 3**: Diff engine accurately isolates entered/exited holdings.

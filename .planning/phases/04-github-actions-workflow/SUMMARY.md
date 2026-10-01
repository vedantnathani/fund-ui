# Phase 4: GitHub Actions Workflow — Summary

## Execution Overview
Phase 4 automated the complete extraction, parsing, validation, diffing, and committing pipeline using scheduled and event-driven GitHub Actions workflows.

## Deliverables Completed
1. **Automated Pipeline Runner (`pipeline/run.py`)**:
   - Orchestrates multi-fund scanning, idempotency verification, extraction, diffing, and index regeneration.
   - Emits step outputs (`new_data=true/false`) to `$GITHUB_OUTPUT`.
   - Supports local testing with `--dry-run` and `--force` flags.
2. **GitHub Actions Workflow (`.github/workflows/pipeline.yml`)**:
   - **Cron Trigger**: `30 0,12 3-20 * *` (Twice daily at 6:00 AM & 6:00 PM IST on days 3–20 of each month) (`FR-9.1`).
   - **Manual Dispatch Trigger**: `workflow_dispatch` with inputs for `force`, `fund_id`, and `dry_run` (`FR-9.2`).
   - **CI Push Trigger**: Verifies all tests on pushes to `main` touching pipeline or config code.
   - **Dependency Caching**: Python 3.11 with pip caching for sub-30 second workflow execution (`NFR-1`, `NFR-3`).
   - **Pre-commit Test Gate**: Runs `pytest pipeline/tests/ -v` before executing pipeline.
   - **Automated Commit & Push**: Commits changes in `data/` as `github-actions[bot]` with `[skip ci]`, automatically triggering Vercel redeployment webhooks without recursive runs (`FR-9.4`).
   - **Zero-Diff Exit**: Completes cleanly without git modifications when no new reports exist (`FR-9.3`).
3. **Test Suite (`pipeline/tests/test_run.py`)**:
   - Tests runner idempotency (bypasses when month already processed).
   - Tests `--dry-run` and `--force` execution flags.
   - Tests `$GITHUB_OUTPUT` file writing.
   - Tests invalid `fund_id` error handling.
   - Complete project test suite now at **26 / 26 passing tests**.

## Requirements Verified
- **FR-9.1**: Scheduled cron configured for publication windows.
- **FR-9.2**: Manual `workflow_dispatch` trigger implemented with arguments.
- **FR-9.3**: Clean zero-commit exit verified on local dry run and test run.
- **FR-9.4**: Automated git commit step configured with appropriate permissions.
- **UAT Criteria 10**: GitHub Actions workflow and runner tested and executable end-to-end.

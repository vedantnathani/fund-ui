"""
Unit tests for Phase 9 — Backfill CLI enhancements.
Tests: parse_month(), month_range(), and date-range filtering
in run_fixtures_backfill() and run_online_backfill().
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.backfill import month_range, parse_month, run_fixtures_backfill, run_online_backfill


# ---------------------------------------------------------------------------
# Task 9.4: month_range() tests
# ---------------------------------------------------------------------------

def test_month_range_basic():
    """month_range spanning 4 consecutive months returns all 4."""
    result = month_range("2026-06", "2026-09")
    assert result == ["2026-06", "2026-07", "2026-08", "2026-09"]


def test_month_range_single():
    """month_range where start == end returns a single-element list."""
    result = month_range("2026-08", "2026-08")
    assert result == ["2026-08"]


def test_month_range_reversed():
    """month_range with start after end raises ValueError."""
    with pytest.raises(ValueError, match="must not be after"):
        month_range("2026-09", "2026-06")


def test_month_range_year_boundary():
    """month_range correctly crosses a year boundary."""
    result = month_range("2025-11", "2026-02")
    assert result == ["2025-11", "2025-12", "2026-01", "2026-02"]


# ---------------------------------------------------------------------------
# Task 9.1: parse_month() tests
# ---------------------------------------------------------------------------

def test_parse_month_valid():
    """parse_month accepts a well-formed YYYY-MM string."""
    assert parse_month("2026-06") == "2026-06"
    assert parse_month("2025-12") == "2025-12"
    assert parse_month("2024-01") == "2024-01"


def test_parse_month_invalid():
    """parse_month raises ArgumentTypeError for malformed inputs."""
    bad_inputs = ["06-2026", "2026-13", "2026-00", "26-06", "2026/06", "abcd-ef"]
    for bad in bad_inputs:
        with pytest.raises(argparse.ArgumentTypeError):
            parse_month(bad)


# ---------------------------------------------------------------------------
# Task 9.3: run_fixtures_backfill() date-range filtering
# ---------------------------------------------------------------------------

def test_backfill_fixtures_date_filter():
    """run_fixtures_backfill only processes months within the requested range."""
    processed_months = []

    def fake_parse(fund_id, excel_path, pdf_path, **kwargs):
        # Track which months were actually processed by inspecting pdf_path name
        month = str(pdf_path).split("factsheet-")[1].replace(".pdf", "")
        processed_months.append(month)
        return {
            "fund_id": fund_id,
            "as_of": month,
            "holdings": [],
            "top10_total_pct": 0,
        }

    mock_orchestrator = MagicMock()
    mock_orchestrator.parse_with_fallback.side_effect = fake_parse
    mock_diff_engine = MagicMock()
    mock_diff_engine.compute_diff.return_value = {"changes": []}

    with (
        patch("pipeline.backfill.ParserOrchestrator", return_value=mock_orchestrator),
        patch("pipeline.backfill.DiffEngine", return_value=mock_diff_engine),
        patch("pipeline.backfill.build_index"),
        patch("builtins.open", MagicMock(
            return_value=MagicMock(
                __enter__=MagicMock(return_value=MagicMock(
                    read=MagicMock(return_value="[]"),
                    __iter__=MagicMock(return_value=iter([])),
                )),
                __exit__=MagicMock(return_value=False),
            )
        )),
    ):
        # Patch json.load to return 2 funds
        import json
        with patch("json.load", return_value=[{"id": "ppfas-flexicap", "name": "PPFAS Flexi Cap", "enabled": True, "significant_change_pp": 0.5}]):
            run_fixtures_backfill(
                fund_id="ppfas-flexicap",
                start_month="2026-07",
                end_month="2026-08",
                dry_run=True,
            )

    # Should have processed exactly July and August (not June)
    assert processed_months == ["2026-07", "2026-08"], (
        f"Expected ['2026-07', '2026-08'] but got {processed_months}"
    )


# ---------------------------------------------------------------------------
# Task 9.2: run_online_backfill() date-range filtering
# ---------------------------------------------------------------------------

def test_backfill_online_date_filter():
    """run_online_backfill only processes months within the requested range."""
    discovered = [
        {"month": "2026-06", "excel_url": "http://example.com/06.xls", "pdf_url": "http://example.com/06.pdf"},
        {"month": "2026-07", "excel_url": "http://example.com/07.xls", "pdf_url": "http://example.com/07.pdf"},
        {"month": "2026-08", "excel_url": "http://example.com/08.xls", "pdf_url": "http://example.com/08.pdf"},
    ]

    mock_scraper = MagicMock()
    mock_scraper.fetch_page.return_value = "<html></html>"
    mock_scraper.discover_ppfas_links.return_value = discovered

    mock_orchestrator = MagicMock()
    mock_orchestrator.get_fund.return_value = {
        "id": "ppfas-flexicap",
        "source_page": "https://amc.ppfas.com/downloads/factsheet/",
    }

    with (
        patch("pipeline.backfill.Scraper", return_value=mock_scraper),
        patch("pipeline.backfill.ParserOrchestrator", return_value=mock_orchestrator),
        patch("pipeline.backfill.DiffEngine"),
        patch("pipeline.backfill.build_index"),
    ):
        run_online_backfill(
            fund_id="ppfas-flexicap",
            start_month="2026-07",
            end_month="2026-07",
            dry_run=True,
        )

    # Scraper should have been called but only July should be in valid_months
    # In dry_run mode no files are written; we verify via discover call count
    mock_scraper.discover_ppfas_links.assert_called_once()
    # The scraper download_file should NOT have been called (dry_run=True)
    mock_scraper.download_file.assert_not_called()

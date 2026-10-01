"""
Integration tests for multi-fund scalability proof (Phase 7).
Verifies that adding a second fund via config works seamlessly across the pipeline.
"""

import json
from pathlib import Path
import pytest

from pipeline.build_index import build_index
from pipeline.diff import DiffEngine
from pipeline.run import run_pipeline
from pipeline.validate import HoldingsValidator


def test_funds_config_contains_multiple_funds():
    """UAT Criteria #8: Multiple funds defined via config alone."""
    with open("config/funds.json", "r", encoding="utf-8") as f:
        funds = json.load(f)

    assert len(funds) >= 2
    fund_ids = {f["id"] for f in funds}
    assert "ppfas-flexicap" in fund_ids
    assert "ppfas-taxsaver" in fund_ids

    for f in funds:
        assert f.get("enabled") is True
        assert f.get("type") == "equity"
        assert f.get("source_page")
        assert f.get("excel_sheet")
        assert f.get("pdf_section_keyword")


def test_both_funds_snapshots_are_valid():
    """Verify that snapshots generated for both funds pass strict validation."""
    validator = HoldingsValidator()

    for fund_id in ["ppfas-flexicap", "ppfas-taxsaver"]:
        fund_dir = Path("data") / fund_id
        assert fund_dir.exists(), f"Directory missing for {fund_id}"

        for m in ["2026-06", "2026-07", "2026-08"]:
            snap_file = fund_dir / f"{m}.json"
            assert snap_file.exists(), f"Snapshot {m} missing for {fund_id}"

            with open(snap_file, "r", encoding="utf-8") as f:
                snap = json.load(f)

            assert snap["fund_id"] == fund_id
            assert len(snap["holdings"]) == 10
            # Validate holdings
            validated = validator.validate_and_normalize(snap["holdings"], expected_top10_total=snap["top10_total_pct"])
            assert len(validated) == 10


def test_both_funds_diffs_and_ai_summaries():
    """Verify diffs and AI summaries for both funds."""
    for fund_id in ["ppfas-flexicap", "ppfas-taxsaver"]:
        diff_file = Path("data") / fund_id / "2026-08.diff.json"
        assert diff_file.exists()

        with open(diff_file, "r", encoding="utf-8") as f:
            diff = json.load(f)

        assert diff["fund_id"] == fund_id
        assert diff["current_month"] == "2026-08"
        assert diff["previous_month"] == "2026-07"
        assert "ai_summary" in diff
        assert diff["ai_summary"]["verified"] is True

        if fund_id == "ppfas-taxsaver":
            assert "Parag Parikh ELSS Tax Saver Fund" in diff["ai_summary"]["text"]
        elif fund_id == "ppfas-flexicap":
            assert "Parag Parikh Flexi Cap Fund" in diff["ai_summary"]["text"]


def test_master_index_includes_both_funds():
    """Verify master index aggregates all funds correctly."""
    with open("data/index.json", "r", encoding="utf-8") as f:
        index_data = json.load(f)

    assert index_data["total_funds"] >= 2
    funds_by_id = {f["id"]: f for f in index_data["funds"]}

    assert "ppfas-flexicap" in funds_by_id
    assert "ppfas-taxsaver" in funds_by_id

    flexicap = funds_by_id["ppfas-flexicap"]
    taxsaver = funds_by_id["ppfas-taxsaver"]

    assert flexicap["name"] == "Parag Parikh Flexi Cap Fund"
    assert taxsaver["name"] == "Parag Parikh ELSS Tax Saver Fund"

    assert len(flexicap["months_available"]) >= 3
    assert len(taxsaver["months_available"]) >= 3

    assert flexicap["top_holding"]["name"] == "HDFC Bank Ltd."
    assert taxsaver["top_holding"]["name"] == "Bajaj Holdings & Investment Ltd."


def test_pipeline_runner_multi_fund_dry_run():
    """Verify automated pipeline runner processes both funds without error."""
    # Test dry run for all funds
    new_data = run_pipeline(fund_id_filter="all", dry_run=True)
    assert isinstance(new_data, bool)

    # Test targeted fund filter
    new_data_single = run_pipeline(fund_id_filter="ppfas-taxsaver", dry_run=True)
    assert isinstance(new_data_single, bool)

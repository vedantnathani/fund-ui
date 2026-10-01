"""Unit tests for Excel disclosure parser."""

from pathlib import Path
import pytest
from pipeline.parsers.excel import ExcelParser

FIXTURE_PATH = Path("pipeline/tests/fixtures/ppfas-flexicap/portfolio-disclosure-2026-08.xls")


def test_excel_fixture_exists():
    assert FIXTURE_PATH.exists(), f"Fixture file not found at {FIXTURE_PATH}"


def test_excel_parser_extracts_top_10():
    parser = ExcelParser(FIXTURE_PATH)
    result = parser.parse(sheet_name="PPFCF")

    assert result["source_type"] == "excel"
    assert result["as_of"] == "2026-08-31"
    assert result["scheme_name"] == "Parag Parikh Flexi Cap Fund"
    assert len(result["holdings"]) == 10

    # Validate ranks
    ranks = [h["rank"] for h in result["holdings"]]
    assert ranks == list(range(1, 11))

    # Top holding must be HDFC Bank
    top_holding = result["holdings"][0]
    assert "HDFC Bank" in top_holding["name"]
    assert top_holding["isin"] == "INE040A01034"
    assert top_holding["weight_pct"] == 7.63

    # Check that foreign equity (Alphabet) is included
    holding_names = [h["name"] for h in result["holdings"]]
    assert any("Alphabet" in name for name in holding_names)

    alphabet = next(h for h in result["holdings"] if "Alphabet" in h["name"])
    assert alphabet["isin"] == "US02079K3059"
    assert alphabet["weight_pct"] == 4.14
    assert alphabet["is_foreign"] is True

    # Check total sum
    assert result["top10_total_pct"] == 50.96


def test_excel_parser_invalid_sheet():
    parser = ExcelParser(FIXTURE_PATH)
    with pytest.raises(ValueError, match="Sheet 'NON_EXISTENT' not found"):
        parser.parse(sheet_name="NON_EXISTENT")

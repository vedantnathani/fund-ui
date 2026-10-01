"""Unit tests for PDF factsheet parser."""

from pathlib import Path
import pytest
from pipeline.parsers.pdf_text import PDFTextParser

FIXTURES_DIR = Path("pipeline/tests/fixtures/ppfas-flexicap")


@pytest.mark.parametrize(
    "filename,expected_as_of,expected_top_holding,expected_top_weight,expected_total",
    [
        ("factsheet-2026-06.pdf", "2026-06-30", "HDFC Bank Limited", 8.33, 51.82),
        ("factsheet-2026-07.pdf", "2026-07-31", "HDFC Bank Limited", 7.55, 51.02),
        ("factsheet-2026-08.pdf", "2026-08-31", "HDFC Bank Limited", 7.63, 50.96),
    ],
)
def test_pdf_parser_on_all_fixtures(
    filename, expected_as_of, expected_top_holding, expected_top_weight, expected_total
):
    pdf_path = FIXTURES_DIR / filename
    assert pdf_path.exists(), f"PDF fixture {filename} not found"

    parser = PDFTextParser(pdf_path)
    result = parser.parse(section_keyword="Flexi Cap")

    assert result["source_type"] == "pdf_text"
    assert result["as_of"] == expected_as_of
    assert len(result["holdings"]) == 10
    assert result["top10_total_pct"] == expected_total

    # Verify top holding
    top = result["holdings"][0]
    assert expected_top_holding in top["name"]
    assert top["weight_pct"] == expected_top_weight

    # Check foreign equity is captured in top 10
    names = [h["name"] for h in result["holdings"]]
    assert any("Alphabet" in n for n in names)


def test_pdf_parser_extracts_amc_commentary():
    pdf_path = FIXTURES_DIR / "factsheet-2026-08.pdf"
    parser = PDFTextParser(pdf_path)
    result = parser.parse(section_keyword="Flexi Cap")

    assert result["amc_commentary"] is not None
    assert "Top 10 changes in Holding" in result["amc_commentary"]
    assert "Knowledge Realty Trust" in result["amc_commentary"]

"""Integration tests for parser orchestrator."""

from pathlib import Path
import pytest
from pipeline.parse import ParserOrchestrator

FIXTURES_DIR = Path("pipeline/tests/fixtures/ppfas-flexicap")
EXCEL_PATH = FIXTURES_DIR / "portfolio-disclosure-2026-08.xls"
PDF_PATH = FIXTURES_DIR / "factsheet-2026-08.pdf"


@pytest.fixture
def orchestrator():
    return ParserOrchestrator()


def test_orchestrator_parse_excel(orchestrator):
    """UAT Criteria #1: PPFAS Flexi Cap Fund top 10 extracted correctly from August 2026 fixture."""
    snapshot = orchestrator.parse_file("ppfas-flexicap", EXCEL_PATH)

    assert snapshot["fund_id"] == "ppfas-flexicap"
    assert snapshot["as_of"] == "2026-08-31"
    assert snapshot["source_type"] == "excel"
    assert len(snapshot["file_sha256"]) == 64
    assert snapshot["top10_total_pct"] == 50.96
    assert len(snapshot["holdings"]) == 10

    # Top holding
    top = snapshot["holdings"][0]
    assert top["rank"] == 1
    assert top["name"] == "HDFC Bank Ltd."
    assert top["key"] == "INE040A01034"
    assert top["weight_pct"] == 7.63


def test_orchestrator_parse_pdf(orchestrator):
    snapshot = orchestrator.parse_file("ppfas-flexicap", PDF_PATH)

    assert snapshot["fund_id"] == "ppfas-flexicap"
    assert snapshot["as_of"] == "2026-08-31"
    assert snapshot["source_type"] == "pdf_text"
    assert snapshot["top10_total_pct"] == 50.96
    assert len(snapshot["holdings"]) == 10

    top = snapshot["holdings"][0]
    assert top["rank"] == 1
    assert top["name"] == "HDFC Bank Ltd."
    assert top["weight_pct"] == 7.63


def test_orchestrator_fallback_to_pdf_when_excel_missing(orchestrator):
    # Non-existent Excel path should gracefully fall back to PDF
    missing_excel = FIXTURES_DIR / "non_existent.xls"
    snapshot = orchestrator.parse_with_fallback(
        "ppfas-flexicap",
        excel_path=missing_excel,
        pdf_path=PDF_PATH,
    )

    assert snapshot["source_type"] == "pdf_text"
    assert snapshot["top10_total_pct"] == 50.96
    assert len(snapshot["holdings"]) == 10

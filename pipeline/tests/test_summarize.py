"""
Unit tests for AI summarization, strict number verification, and template fallback.
Verifies UAT Criteria #5 and #6.
"""

import json
from pathlib import Path
import pytest

from pipeline.diff import DiffEngine
from pipeline.summarize import (
    Summarizer,
    extract_numbers_from_diff,
    generate_template_summary,
    verify_numbers_in_summary,
)


@pytest.fixture
def sample_diff():
    return {
        "fund_id": "ppfas-flexicap",
        "current_month": "2026-08",
        "previous_month": "2026-07",
        "as_of": "2026-08-31",
        "prev_as_of": "2026-07-31",
        "top10_total_pct": 50.96,
        "prev_top10_total_pct": 51.02,
        "top10_total_delta_pp": -0.06,
        "entered_top10": [],
        "exited_top10": [],
        "retained": [
            {
                "key": "INE040A01034",
                "name": "HDFC Bank Ltd.",
                "rank": 1,
                "prev_rank": 1,
                "rank_change": 0,
                "weight_pct": 7.63,
                "prev_weight_pct": 7.55,
                "weight_delta_pp": 0.08,
                "direction": "increased",
                "significant": False,
            },
            {
                "key": "INE237A01036",
                "name": "Kotak Mahindra Bank Ltd.",
                "rank": 7,
                "prev_rank": 9,
                "rank_change": 2,
                "weight_pct": 4.40,
                "prev_weight_pct": 4.07,
                "weight_delta_pp": 0.33,
                "direction": "increased",
                "significant": False,
            },
            {
                "key": "INE154A01025",
                "name": "ITC Ltd.",
                "rank": 4,
                "prev_rank": 3,
                "rank_change": -1,
                "weight_pct": 5.26,
                "prev_weight_pct": 5.74,
                "weight_delta_pp": -0.48,
                "direction": "decreased",
                "significant": False,
            },
        ],
        "summary": {
            "num_entered": 0,
            "num_exited": 0,
            "num_increased": 2,
            "num_decreased": 1,
            "num_unchanged": 0,
            "num_significant": 0,
            "biggest_increase": {
                "name": "Kotak Mahindra Bank Ltd.",
                "weight_delta_pp": 0.33,
            },
            "biggest_decrease": {
                "name": "ITC Ltd.",
                "weight_delta_pp": -0.48,
            },
        },
        "amc_commentary": None,
    }


def test_extract_numbers_from_diff(sample_diff):
    numbers = extract_numbers_from_diff(sample_diff)
    # Check key figures are present
    assert 50.96 in numbers
    assert 51.02 in numbers
    assert 0.06 in numbers
    assert 7.63 in numbers
    assert 0.33 in numbers
    assert 0.48 in numbers


def test_template_summary_generation(sample_diff):
    """UAT Criteria #6: Fallback template summary generated cleanly without external LLM."""
    text = generate_template_summary(sample_diff, fund_name="Parag Parikh Flexi Cap Fund")
    
    assert "Parag Parikh Flexi Cap Fund" in text
    assert "2026-08" in text
    assert "51.02%" in text
    assert "50.96%" in text
    assert "0.06pp" in text
    assert "Kotak Mahindra Bank Ltd." in text
    assert "+0.33pp" in text
    assert "ITC Ltd." in text
    assert "-0.48pp" in text
    assert "HDFC Bank Ltd." in text
    assert "7.63%" in text


def test_verify_numbers_valid_summary(sample_diff):
    """UAT Criteria #5: Summary contains only verified numbers from diff JSON."""
    valid_text = (
        "In 2026-08, Parag Parikh Flexi Cap Fund held 10 companies. "
        "Top-10 concentration changed by 0.06pp from 51.02% to 50.96%. "
        "Kotak Mahindra Bank Ltd. expanded weight by 0.33pp. "
        "HDFC Bank Ltd. is at 7.63%."
    )
    is_valid, unverified = verify_numbers_in_summary(valid_text, sample_diff)
    assert is_valid is True
    assert unverified == []


def test_verify_numbers_rejects_hallucinations(sample_diff):
    """UAT Criteria #5: Rejects LLM summaries that fabricate numbers or returns."""
    hallucinated_text = (
        "In August 2026, the fund gained 15.4% while the benchmark fell 3.2%. "
        "HDFC Bank was maintained at 7.63%."
    )
    is_valid, unverified = verify_numbers_in_summary(hallucinated_text, sample_diff)
    assert is_valid is False
    assert "15.4" in unverified or 15.4 in [float(x) for x in unverified]


def test_summarizer_fallback_when_unconfigured(sample_diff, monkeypatch):
    """UAT Criteria #6: Summarizer defaults to verified template fallback in unconfigured environments."""
    # Ensure no API keys exist in test environment
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "auto")

    summarizer = Summarizer()
    res = summarizer.generate(sample_diff)

    assert res["provider"] == "template_fallback"
    assert res["verified"] is True
    assert len(res["text"]) > 50
    assert "50.96%" in res["text"]


def test_diff_engine_includes_ai_summary():
    """Verify DiffEngine automatically integrates Summarizer."""
    snap1 = {
        "fund_id": "ppfas-flexicap",
        "as_of": "2026-07-31",
        "holdings": [
            {"rank": 1, "key": "INE040A01034", "name": "HDFC Bank Ltd.", "weight_pct": 7.55},
        ],
    }
    snap2 = {
        "fund_id": "ppfas-flexicap",
        "as_of": "2026-08-31",
        "holdings": [
            {"rank": 1, "key": "INE040A01034", "name": "HDFC Bank Ltd.", "weight_pct": 7.63},
        ],
    }

    engine = DiffEngine()
    diff = engine.compute_diff(snap2, snap1)

    assert "ai_summary" in diff
    assert diff["ai_summary"]["verified"] is True
    assert diff["ai_summary"]["provider"] == "template_fallback"
    assert len(diff["ai_summary"]["text"]) > 20

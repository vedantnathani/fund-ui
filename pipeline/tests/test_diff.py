"""Unit tests for diff engine."""

import pytest
from pipeline.diff import DiffEngine


@pytest.fixture
def diff_engine():
    return DiffEngine(significant_threshold_pp=0.5)


@pytest.fixture
def month1_snapshot():
    return {
        "fund_id": "ppfas-flexicap",
        "as_of": "2026-07-31",
        "top10_total_pct": 51.02,
        "amc_commentary": None,
        "holdings": [
            {"rank": 1, "key": "INE040A01034", "name": "HDFC Bank Ltd.", "isin": "INE040A01034", "sector": "Banks", "weight_pct": 7.55},
            {"rank": 2, "key": "INE752E01010", "name": "Power Grid Corp of India Ltd.", "isin": "INE752E01010", "sector": "Power", "weight_pct": 5.98},
            {"rank": 3, "key": "INE154A01025", "name": "ITC Ltd.", "isin": "INE154A01025", "sector": "Diversified FMCG", "weight_pct": 5.74},
            {"rank": 4, "key": "INE090A01021", "name": "ICICI Bank Ltd.", "isin": "INE090A01021", "sector": "Banks", "weight_pct": 5.56},
            {"rank": 5, "key": "INE522F01014", "name": "Coal India Ltd.", "isin": "INE522F01014", "sector": "Consumable Fuels", "weight_pct": 4.91},
            {"rank": 6, "key": "INE118A01012", "name": "Bajaj Holdings & Investment Ltd.", "isin": "INE118A01012", "sector": "Finance", "weight_pct": 4.85},
            {"rank": 7, "key": "US02079K3059", "name": "Alphabet Inc.", "isin": "US02079K3059", "sector": "Foreign Securities", "weight_pct": 4.33},
            {"rank": 8, "key": "INE860A01027", "name": "HCL Technologies Ltd.", "isin": "INE860A01027", "sector": "IT - Software", "weight_pct": 4.23},
            {"rank": 9, "key": "INE237A01036", "name": "Kotak Mahindra Bank Ltd.", "isin": "INE237A01036", "sector": "Banks", "weight_pct": 4.07},
            {"rank": 10, "key": "INE101A01026", "name": "Mahindra & Mahindra Ltd.", "isin": "INE101A01026", "sector": "Automobiles", "weight_pct": 3.80},
        ],
    }


@pytest.fixture
def month2_snapshot():
    return {
        "fund_id": "ppfas-flexicap",
        "as_of": "2026-08-31",
        "top10_total_pct": 50.96,
        "amc_commentary": "Top 10 additions...",
        "holdings": [
            {"rank": 1, "key": "INE040A01034", "name": "HDFC Bank Ltd.", "isin": "INE040A01034", "sector": "Banks", "weight_pct": 7.63},
            {"rank": 2, "key": "INE090A01021", "name": "ICICI Bank Ltd.", "isin": "INE090A01021", "sector": "Banks", "weight_pct": 5.67},
            {"rank": 3, "key": "INE752E01010", "name": "Power Grid Corp of India Ltd.", "isin": "INE752E01010", "sector": "Power", "weight_pct": 5.58},
            {"rank": 4, "key": "INE154A01025", "name": "ITC Ltd.", "isin": "INE154A01025", "sector": "Diversified FMCG", "weight_pct": 5.26},
            {"rank": 5, "key": "INE118A01012", "name": "Bajaj Holdings & Investment Ltd.", "isin": "INE118A01012", "sector": "Finance", "weight_pct": 5.14},
            {"rank": 6, "key": "INE522F01014", "name": "Coal India Ltd.", "isin": "INE522F01014", "sector": "Consumable Fuels", "weight_pct": 5.02},
            {"rank": 7, "key": "INE237A01036", "name": "Kotak Mahindra Bank Ltd.", "isin": "INE237A01036", "sector": "Banks", "weight_pct": 4.40},
            {"rank": 8, "key": "INE860A01027", "name": "HCL Technologies Ltd.", "isin": "INE860A01027", "sector": "IT - Software", "weight_pct": 4.15},
            {"rank": 9, "key": "US02079K3059", "name": "Alphabet Inc.", "isin": "US02079K3059", "sector": "Foreign Securities", "weight_pct": 4.14},
            {"rank": 10, "key": "INE101A01026", "name": "Mahindra & Mahindra Ltd.", "isin": "INE101A01026", "sector": "Automobiles", "weight_pct": 3.97},
        ],
    }


def test_diff_engine_entered_and_exited(diff_engine, month1_snapshot):
    """UAT Criteria #3: Diff engine correctly identifies holdings that entered/exited top 10."""
    # Create month 2 where Mahindra & Mahindra exits, and Zydus Lifesciences enters
    month2_modified = dict(month1_snapshot)
    month2_modified["as_of"] = "2026-08-31"
    new_holdings = [dict(h) for h in month1_snapshot["holdings"][:9]]
    new_holdings.append({
        "rank": 10,
        "key": "INE010B01027",
        "name": "Zydus Lifesciences Ltd.",
        "isin": "INE010B01027",
        "sector": "Pharmaceuticals & Biotech",
        "weight_pct": 3.75,
    })
    month2_modified["holdings"] = new_holdings

    diff = diff_engine.compute_diff(month2_modified, month1_snapshot)

    assert len(diff["entered_top10"]) == 1
    assert diff["entered_top10"][0]["name"] == "Zydus Lifesciences Ltd."
    assert diff["entered_top10"][0]["key"] == "INE010B01027"
    assert diff["entered_top10"][0]["rank"] == 10

    assert len(diff["exited_top10"]) == 1
    assert diff["exited_top10"][0]["name"] == "Mahindra & Mahindra Ltd."
    assert diff["exited_top10"][0]["key"] == "INE101A01026"
    assert diff["exited_top10"][0]["prev_rank"] == 10

    assert diff["summary"]["num_entered"] == 1
    assert diff["summary"]["num_exited"] == 1


def test_diff_engine_retained_and_rank_changes(diff_engine, month1_snapshot, month2_snapshot):
    diff = diff_engine.compute_diff(month2_snapshot, month1_snapshot)

    assert diff["current_month"] == "2026-08"
    assert diff["previous_month"] == "2026-07"
    assert len(diff["entered_top10"]) == 0
    assert len(diff["exited_top10"]) == 0
    assert len(diff["retained"]) == 10

    # ICICI Bank moved from rank 4 to rank 2 (+2)
    icici = next(h for h in diff["retained"] if h["key"] == "INE090A01021")
    assert icici["rank"] == 2
    assert icici["prev_rank"] == 4
    assert icici["rank_change"] == 2
    assert icici["weight_delta_pp"] == 0.11
    assert icici["direction"] == "increased"

    # Alphabet moved from rank 7 to rank 9 (-2)
    alphabet = next(h for h in diff["retained"] if h["key"] == "US02079K3059")
    assert alphabet["rank"] == 9
    assert alphabet["prev_rank"] == 7
    assert alphabet["rank_change"] == -2
    assert alphabet["weight_delta_pp"] == -0.19
    assert alphabet["direction"] == "decreased"


def test_diff_engine_significance_flag(diff_engine, month1_snapshot):
    # Create month 2 with a >= 0.5pp move
    month2_sig = dict(month1_snapshot)
    month2_sig["as_of"] = "2026-08-31"
    modified_holdings = [dict(h) for h in month1_snapshot["holdings"]]
    # HDFC Bank moved +0.60pp (7.55 -> 8.15)
    modified_holdings[0]["weight_pct"] = 8.15
    month2_sig["holdings"] = modified_holdings

    diff = diff_engine.compute_diff(month2_sig, month1_snapshot, significant_change_pp=0.5)

    hdfc = next(h for h in diff["retained"] if h["key"] == "INE040A01034")
    assert hdfc["significant"] is True
    assert diff["summary"]["num_significant"] == 1


def test_diff_engine_no_changes_month(diff_engine, month1_snapshot):
    # Consecutive month with identical holdings
    month2_identical = dict(month1_snapshot)
    month2_identical["as_of"] = "2026-08-31"

    diff = diff_engine.compute_diff(month2_identical, month1_snapshot)

    assert diff["summary"]["num_entered"] == 0
    assert diff["summary"]["num_exited"] == 0
    assert diff["summary"]["num_increased"] == 0
    assert diff["summary"]["num_decreased"] == 0
    assert diff["summary"]["num_unchanged"] == 10
    assert diff["summary"]["num_significant"] == 0
    assert diff["top10_total_delta_pp"] == 0.0

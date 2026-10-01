"""Unit tests for validator and alias normalization."""

import pytest
from pipeline.validate import HoldingsNormalizer, HoldingsValidator, ValidationError


@pytest.fixture
def normalizer():
    return HoldingsNormalizer("config/aliases.json")


@pytest.fixture
def validator(normalizer):
    return HoldingsValidator(normalizer=normalizer)


@pytest.fixture
def valid_holdings():
    return [
        {"name": "HDFC Bank Limited", "isin": "INE040A01034", "sector": "Banks", "weight_pct": 7.63},
        {"name": "ICICI Bank Limited", "isin": "INE090A01021", "sector": "Banks", "weight_pct": 5.67},
        {"name": "Power Grid Corporation of India Limited", "isin": "INE752E01010", "sector": "Power", "weight_pct": 5.58},
        {"name": "ITC Limited", "isin": "INE154A01025", "sector": "Diversified FMCG", "weight_pct": 5.26},
        {"name": "Bajaj Holdings & Investment Limited", "isin": "INE118A01012", "sector": "Finance", "weight_pct": 5.14},
        {"name": "Coal India Limited", "isin": "INE522F01014", "sector": "Consumable Fuels", "weight_pct": 5.02},
        {"name": "Kotak Mahindra Bank Limited", "isin": "INE237A01036", "sector": "Banks", "weight_pct": 4.40},
        {"name": "HCL Technologies Limited", "isin": "INE860A01027", "sector": "IT - Software", "weight_pct": 4.15},
        {"name": "Alphabet Inc A", "isin": "US02079K3059", "sector": "Foreign Securities", "weight_pct": 4.14},
        {"name": "Mahindra & Mahindra Limited", "isin": "INE101A01026", "sector": "Automobiles", "weight_pct": 3.97},
    ]


def test_validation_passes_valid_holdings(validator, valid_holdings):
    result = validator.validate_and_normalize(valid_holdings, expected_top10_total=50.96)
    assert len(result) == 10
    assert result[0]["rank"] == 1
    assert result[0]["name"] == "HDFC Bank Ltd."
    assert result[0]["key"] == "INE040A01034"
    assert result[8]["name"] == "Alphabet Inc."
    assert result[8]["key"] == "US02079K3059"


def test_validation_rejects_9_holdings(validator, valid_holdings):
    """UAT Criteria #2: Validation rejects a snapshot with only 9 holdings."""
    nine_holdings = valid_holdings[:9]
    with pytest.raises(ValidationError, match="expected exactly 10, got 9"):
        validator.validate_and_normalize(nine_holdings)


def test_validation_rejects_11_holdings(validator, valid_holdings):
    extra = valid_holdings + [{"name": "Infosys Ltd.", "isin": "INE009A01021", "weight_pct": 3.0}]
    with pytest.raises(ValidationError, match="expected exactly 10, got 11"):
        validator.validate_and_normalize(extra)


def test_validation_rejects_non_monotonic_weights(validator, valid_holdings):
    # Swap rank 1 and 2 weights
    corrupted = [dict(h) for h in valid_holdings]
    corrupted[0]["weight_pct"] = 4.0
    corrupted[1]["weight_pct"] = 8.0

    with pytest.raises(ValidationError, match="Holdings not in descending weight order"):
        validator.validate_and_normalize(corrupted)


def test_validation_rejects_out_of_bounds_weights(validator, valid_holdings):
    corrupted = [dict(h) for h in valid_holdings]
    corrupted[0]["weight_pct"] = 35.0  # Max is 30%

    with pytest.raises(ValidationError, match="outside allowable range"):
        validator.validate_and_normalize(corrupted)


def test_validation_rejects_sum_mismatch(validator, valid_holdings):
    with pytest.raises(ValidationError, match="diverges from expected"):
        validator.validate_and_normalize(valid_holdings, expected_top10_total=60.0)


def test_alias_resolution(normalizer):
    """UAT Criteria #4: Alias mapping resolves 'Google' -> 'Alphabet Inc'."""
    assert normalizer.normalize_name("Google") == "Alphabet Inc."
    assert normalizer.normalize_name("Google Inc") == "Alphabet Inc."
    assert normalizer.normalize_name("Alphabet Inc A") == "Alphabet Inc."
    assert normalizer.normalize_name("Alphabet Inc Class A") == "Alphabet Inc."
    assert normalizer.normalize_name("HDFC Bank Limited") == "HDFC Bank Ltd."


def test_canonical_key_generation(normalizer):
    # Valid ISIN should be the key
    assert normalizer.generate_canonical_key("HDFC Bank Ltd.", "INE040A01034") == "INE040A01034"
    # Fallback to slug when no ISIN
    assert normalizer.generate_canonical_key("HDFC Bank Ltd.", None) == "hdfc-bank-ltd"
    assert normalizer.generate_canonical_key("Alphabet Inc.", "INVALID") == "alphabet-inc"

"""
Unit tests for modular AMC scraper routing, Motilal Oswal API discovery,
custom URL overrides, and date range filtering.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests

from pipeline.scrape import Scraper, parse_month_year


@pytest.fixture
def mock_scraper():
    return Scraper()


def test_parse_month_year_formats():
    """Verify parse_month_year correctly handles various AMC URL/filename conventions."""
    assert parse_month_year("https://amc.ppfas.com/downloads/factsheet/factsheet-2026-08.pdf") == "2026-08"
    assert parse_month_year("portfolio-disclosure-july-2026.xls") == "2026-07"
    assert parse_month_year("/content/dam/motilal-mf/downloads/mf/factsheet/2026/sep/Most Factsheet August 2026 Active.pdf") == "2026-08"
    assert parse_month_year("/content/dam/motilal-mf/downloads/mf/factsheet/2026/aug/factsheet-july-2026-active-funds.pdf") == "2026-07"
    # Ensure year near month name is picked, even if parent folder is next year
    assert parse_month_year("/2026/jan/67301-most-factsheet-december-2025-active.pdf") == "2025-12"
    assert parse_month_year("invalid-filename.pdf") is None


def test_discover_links_ppfas_routing(mock_scraper):
    """PPFAS fund routes to HTML page fetching and discover_ppfas_links."""
    sample_html = """
    <html>
      <a href="/downloads/factsheet/factsheet-2026-08.pdf">Factsheet August 2026</a>
      <a href="/downloads/portfolio-disclosure/portfolio-disclosure-august-2026.xls">Portfolio Aug 2026</a>
    </html>
    """
    fund_config = {
        "id": "ppfas-flexicap",
        "name": "Parag Parikh Flexi Cap Fund",
        "amc": "PPFAS Mutual Fund",
        "source_page": "https://amc.ppfas.com/downloads/factsheet/",
    }

    with patch.object(mock_scraper, "fetch_page", return_value=sample_html):
        discovered = mock_scraper.discover_links(fund_config)

    assert len(discovered) == 1
    assert discovered[0]["month"] == "2026-08"
    assert discovered[0]["pdf_url"] == "https://amc.ppfas.com/downloads/factsheet/factsheet-2026-08.pdf"
    assert discovered[0]["excel_url"] == "https://amc.ppfas.com/downloads/portfolio-disclosure/portfolio-disclosure-august-2026.xls"


def test_discover_links_motilal_routing(mock_scraper):
    """Motilal Oswal fund queries AEM search API and parses active factsheets."""
    mock_api_response = {
        "totalMatches": 2,
        "results": [
            {
                "path": "/content/dam/motilal-mf/downloads/mf/factsheet/2026/sep/Most Factsheet August 2026 Active.pdf",
                "title": "factsheet August 2026 active",
                "category": "factsheet",
            },
            {
                "path": "/content/dam/motilal-mf/downloads/mf/factsheet/2026/aug/factsheet-july-2026-active-funds.pdf",
                "title": "factsheet july 2026 active",
                "category": "factsheet",
            },
            {
                # Should be ignored (passive fund)
                "path": "/content/dam/motilal-mf/downloads/mf/factsheet/2026/sep/Most Factsheet August 2026 Passive.pdf",
                "title": "factsheet august 2026 passive",
                "category": "factsheet",
            },
        ],
    }

    fund_config = {
        "id": "motilal-oswal-midcap-fund",
        "name": "Motilal Oswal Midcap Fund",
        "amc": "Motilal Oswal",
        "source_page": "https://www.motilaloswalmf.com/downloads/factsheets",
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_api_response
    mock_resp.raise_for_status = MagicMock()

    with patch.object(mock_scraper.session, "get", return_value=mock_resp):
        discovered = mock_scraper.discover_links(fund_config)

    assert len(discovered) == 2
    assert discovered[0]["month"] == "2026-08"
    assert discovered[1]["month"] == "2026-07"
    assert "Most%20Factsheet%20August%202026%20Active.pdf" in discovered[0]["pdf_url"]
    assert discovered[0]["excel_url"] is None


def test_discover_links_custom_urls(mock_scraper):
    """Funds with custom monthly_urls bypass scraping and return configured URLs."""
    fund_config = {
        "id": "hdfc-top-100",
        "name": "HDFC Top 100 Fund",
        "amc": "HDFC Mutual Fund",
        "monthly_urls": {
            "2026-08": {
                "pdf": "https://mirror.example.com/hdfc-2026-08.pdf",
                "excel": "https://mirror.example.com/hdfc-2026-08.xls",
            },
            "2026-07": "https://mirror.example.com/hdfc-2026-07.pdf",
            "2026-06": "https://mirror.example.com/hdfc-2026-06.pdf",
        },
    }

    discovered = mock_scraper.discover_links(fund_config, start_month="2026-07", end_month="2026-08")
    assert len(discovered) == 2
    assert discovered[0]["month"] == "2026-08"
    assert discovered[0]["pdf_url"] == "https://mirror.example.com/hdfc-2026-08.pdf"
    assert discovered[0]["excel_url"] == "https://mirror.example.com/hdfc-2026-08.xls"
    assert discovered[1]["month"] == "2026-07"
    assert discovered[1]["pdf_url"] == "https://mirror.example.com/hdfc-2026-07.pdf"


def test_motilal_date_filtering(mock_scraper):
    """Motilal discovery filters results to given start_month and end_month."""
    mock_api_response = {
        "results": [
            {
                "path": "/content/dam/motilal-mf/downloads/mf/factsheet/2026/sep/Most Factsheet August 2026 Active.pdf",
                "title": "factsheet August 2026 active",
                "category": "factsheet",
            },
            {
                "path": "/content/dam/motilal-mf/downloads/mf/factsheet/2026/aug/factsheet-july-2026-active-funds.pdf",
                "title": "factsheet july 2026 active",
                "category": "factsheet",
            },
            {
                "path": "/content/dam/motilal-mf/downloads/mf/factsheet/2026/jul/most factsheet june 2026 active.pdf",
                "title": "factsheet june 2026 active",
                "category": "factsheet",
            },
        ],
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_api_response
    mock_resp.raise_for_status = MagicMock()

    with patch.object(mock_scraper.session, "get", return_value=mock_resp):
        discovered = mock_scraper.discover_motilal_links(
            {"amc": "Motilal Oswal"},
            start_month="2026-07",
            end_month="2026-07",
        )

    assert len(discovered) == 1
    assert discovered[0]["month"] == "2026-07"


def test_motilal_api_error_handling(mock_scraper):
    """Gracefully handle HTTP or JSON errors when querying Motilal API."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.RequestException("Connection timeout")

    with patch.object(mock_scraper.session, "get", return_value=mock_resp):
        discovered = mock_scraper.discover_motilal_links({"amc": "Motilal Oswal"})

    assert discovered == []

"""Unit tests for the automated pipeline runner."""

from pathlib import Path
import pytest
from pipeline.run import run_pipeline, set_github_output


def test_set_github_output(tmp_path, monkeypatch):
    out_file = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))

    set_github_output("new_data", "true")
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "new_data=true\n" in content


def test_run_pipeline_skips_when_already_processed(tmp_path):
    # Running against current data/ where 2026-08 is already processed
    result = run_pipeline(
        fund_id_filter="ppfas-flexicap",
        force=False,
        dry_run=False,
        data_dir="data",
    )
    assert result is False


def test_run_pipeline_dry_run_force():
    # With force=True and dry_run=True, detects update without performing file writes
    result = run_pipeline(
        fund_id_filter="ppfas-flexicap",
        force=True,
        dry_run=True,
        data_dir="data",
    )
    assert result is True


def test_run_pipeline_invalid_fund_id():
    with pytest.raises(ValueError, match="No fund matched fund_id 'unknown-fund'"):
        run_pipeline(fund_id_filter="unknown-fund")

"""
validate_fund_config.py — Standalone validator for a fund entry in config/funds.json.

Usage:
    python pipeline/validate_fund_config.py --fund-id <id> [--config config/funds.json]

Exit codes:
    0 — fund entry is valid
    1 — fund entry is invalid or not found (errors written to stderr)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Required fields and their expected types
REQUIRED_FIELDS: dict[str, type] = {
    "id": str,
    "name": str,
    "amc": str,
    "type": str,
    "source_page": str,
    "parser_preference": list,
}

VALID_TYPES = {"equity", "debt", "hybrid", "liquid"}
VALID_PARSERS = {"excel", "pdf_text", "ocr"}
ID_RE = re.compile(r"^[a-z0-9-]+$")


def validate_fund(fund: dict, errors: list[str]) -> None:
    """Validate a single fund config dict; append error messages to `errors`."""
    fund_id = fund.get("id", "<unknown>")

    # Check required fields
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in fund:
            errors.append(f"[{fund_id}] Missing required field: '{field}'")
        elif not isinstance(fund[field], expected_type):
            errors.append(
                f"[{fund_id}] Field '{field}' must be {expected_type.__name__}, "
                f"got {type(fund[field]).__name__}"
            )

    # Validate 'id' format
    if "id" in fund and isinstance(fund["id"], str):
        if not ID_RE.match(fund["id"]):
            errors.append(
                f"[{fund_id}] 'id' must match ^[a-z0-9-]+$ (lowercase kebab-case). "
                f"Got: '{fund['id']}'"
            )

    # Validate 'type'
    if "type" in fund and fund["type"] not in VALID_TYPES:
        errors.append(
            f"[{fund_id}] 'type' must be one of {sorted(VALID_TYPES)}. Got: '{fund['type']}'"
        )

    # Validate 'source_page' is a valid HTTPS URL
    if "source_page" in fund and isinstance(fund["source_page"], str):
        parsed = urlparse(fund["source_page"])
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(
                f"[{fund_id}] 'source_page' must be a valid HTTPS URL. Got: '{fund['source_page']}'"
            )

    # Validate 'parser_preference'
    if "parser_preference" in fund and isinstance(fund["parser_preference"], list):
        if len(fund["parser_preference"]) == 0:
            errors.append(f"[{fund_id}] 'parser_preference' must have at least one entry.")
        for p in fund["parser_preference"]:
            if p not in VALID_PARSERS:
                errors.append(
                    f"[{fund_id}] Unknown parser '{p}' in 'parser_preference'. "
                    f"Valid values: {sorted(VALID_PARSERS)}"
                )

    # Validate 'significant_change_pp' (optional)
    if "significant_change_pp" in fund:
        val = fund["significant_change_pp"]
        if not isinstance(val, (int, float)) or not (0.1 <= val <= 5.0):
            errors.append(
                f"[{fund_id}] 'significant_change_pp' must be a number between 0.1 and 5.0. Got: {val}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a fund entry in config/funds.json"
    )
    parser.add_argument(
        "--fund-id",
        required=True,
        help="The fund ID to validate (must exist in the config file)",
    )
    parser.add_argument(
        "--config",
        default="config/funds.json",
        help="Path to the funds config JSON (default: config/funds.json)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            funds = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {config_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Find the fund
    matched = [f for f in funds if f.get("id") == args.fund_id]
    if not matched:
        print(
            f"ERROR: Fund ID '{args.fund_id}' not found in {config_path}.",
            file=sys.stderr,
        )
        print(f"Available IDs: {[f.get('id') for f in funds]}", file=sys.stderr)
        sys.exit(1)

    fund = matched[0]
    errors: list[str] = []
    validate_fund(fund, errors)

    if errors:
        print(f"INVALID fund config for '{args.fund_id}':", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"✓ Fund config for '{args.fund_id}' is valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()

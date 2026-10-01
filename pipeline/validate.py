"""
Validation and normalization module for mutual fund holdings.
Enforces schema invariants, weights monotonicity, bounds, and alias resolution.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Raised when holdings payload fails validation rules."""
    pass


class HoldingsNormalizer:
    def __init__(self, aliases_path: Optional[str] = "config/aliases.json"):
        self.aliases: Dict[str, str] = {}
        if aliases_path and Path(aliases_path).exists():
            with open(aliases_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.aliases = {k.lower().strip(): v for k, v in data.get("aliases", {}).items()}

    def normalize_name(self, name: str) -> str:
        """
        Normalize company name:
        1. Clean whitespace and unwanted characters
        2. Check alias map
        3. Standardize legal suffixes (Limited -> Ltd., etc.)
        """
        if not name:
            return ""

        clean = re.sub(r"\s+", " ", name).strip()
        lookup_key = clean.lower()

        # Direct alias lookup
        if lookup_key in self.aliases:
            return self.aliases[lookup_key]

        # Normalized lookup (strip trailing dots, commas)
        lookup_key_stripped = re.sub(r"[.,]+$", "", lookup_key)
        if lookup_key_stripped in self.aliases:
            return self.aliases[lookup_key_stripped]

        # Standard legal suffix normalization
        clean = re.sub(r"\bLimited\b\.?", "Ltd.", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\bCorporation\b\.?", "Corp.", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\bIncorporated\b\.?", "Inc.", clean, flags=re.IGNORECASE)

        return clean.strip()

    def generate_canonical_key(self, name: str, isin: Optional[str] = None) -> str:
        """
        Generate canonical key: prefer valid ISIN, otherwise normalized slug.
        """
        if isin and self.is_valid_isin(isin):
            return isin.upper().strip()

        norm_name = self.normalize_name(name)
        # Slugify
        slug = re.sub(r"[^\w\s-]", "", norm_name.lower())
        return re.sub(r"[-\s]+", "-", slug).strip("-")

    @staticmethod
    def is_valid_isin(isin: str) -> bool:
        """Check if ISIN is 12 alphanumeric characters."""
        if not isin or not isinstance(isin, str):
            return False
        isin = isin.strip().upper()
        return bool(re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", isin))


class HoldingsValidator:
    def __init__(
        self,
        normalizer: Optional[HoldingsNormalizer] = None,
        min_weight_pct: float = 0.1,
        max_weight_pct: float = 30.0,
        min_top10_sum_pct: float = 30.0,
        max_top10_sum_pct: float = 85.0,
    ):
        self.normalizer = normalizer or HoldingsNormalizer()
        self.min_weight_pct = min_weight_pct
        self.max_weight_pct = max_weight_pct
        self.min_top10_sum_pct = min_top10_sum_pct
        self.max_top10_sum_pct = max_top10_sum_pct

    def validate_and_normalize(
        self,
        holdings: List[Dict[str, Any]],
        expected_top10_total: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Validate holdings and return normalized records.
        Raises ValidationError if any check fails.
        """
        # Rule FR-4.1: Exactly 10 holdings
        if len(holdings) != 10:
            raise ValidationError(
                f"Invalid holdings count: expected exactly 10, got {len(holdings)}"
            )

        normalized_holdings: List[Dict[str, Any]] = []
        prev_weight = float("inf")

        for idx, h in enumerate(holdings):
            raw_name = h.get("name")
            if not raw_name or not str(raw_name).strip():
                raise ValidationError(f"Holding at index {idx} has missing or empty name")

            raw_weight = h.get("weight_pct")
            if raw_weight is None:
                raise ValidationError(f"Holding '{raw_name}' has no weight_pct")

            try:
                weight = round(float(raw_weight), 2)
            except (ValueError, TypeError) as e:
                raise ValidationError(f"Holding '{raw_name}' has non-numeric weight: {raw_weight}") from e

            # Rule FR-4.2: Weight bounds
            if not (self.min_weight_pct <= weight <= self.max_weight_pct):
                raise ValidationError(
                    f"Holding '{raw_name}' weight {weight}% is outside allowable range "
                    f"[{self.min_weight_pct}%, {self.max_weight_pct}%]"
                )

            # Rule FR-4.3: Monotonic descending weight order
            # Allow tiny float rounding tolerance of 0.01
            if weight > prev_weight + 0.01:
                raise ValidationError(
                    f"Holdings not in descending weight order: rank {idx+1} ({weight}%) "
                    f"> rank {idx} ({prev_weight}%)"
                )
            prev_weight = weight

            # Normalize name & alias mapping (FR-4.5)
            norm_name = self.normalizer.normalize_name(str(raw_name))

            # Canonical key & ISIN validation (FR-4.6)
            raw_isin = h.get("isin")
            valid_isin = str(raw_isin).strip().upper() if self.normalizer.is_valid_isin(str(raw_isin or "")) else None
            key = self.normalizer.generate_canonical_key(norm_name, valid_isin)

            sector = h.get("sector") or "Equity"
            rank = idx + 1

            normalized_holdings.append({
                "rank": rank,
                "key": key,
                "name": norm_name,
                "isin": valid_isin,
                "sector": sector,
                "weight_pct": weight,
            })

        # Calculate sum
        total_sum = round(sum(h["weight_pct"] for h in normalized_holdings), 2)

        # Sum bounds check
        if not (self.min_top10_sum_pct <= total_sum <= self.max_top10_sum_pct):
            raise ValidationError(
                f"Top 10 total sum {total_sum}% is outside allowable bounds "
                f"[{self.min_top10_sum_pct}%, {self.max_top10_sum_pct}%]"
            )

        # Rule FR-4.4: Stated top 10 total match within ±0.15pp if expected total provided
        if expected_top10_total is not None:
            diff = abs(total_sum - expected_top10_total)
            if diff > 0.15:
                raise ValidationError(
                    f"Sum of top 10 ({total_sum}%) diverges from expected ({expected_top10_total}%) "
                    f"by {diff:.2f}pp (allowed tolerance: ±0.15pp)"
                )

        # Check for duplicate keys
        keys = [h["key"] for h in normalized_holdings]
        if len(keys) != len(set(keys)):
            raise ValidationError(f"Duplicate holdings detected in top 10: {keys}")

        return normalized_holdings

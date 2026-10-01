"""
Pure Python Diff Engine for Mutual Fund Top-10 Holdings Tracker.
Compares consecutive monthly snapshots, calculates weight and rank deltas,
identifies entered/exited holdings, and determines significant changes.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.validate import HoldingsNormalizer

logger = logging.getLogger(__name__)


class DiffEngine:
    def __init__(
        self,
        significant_threshold_pp: float = 0.5,
        aliases_path: str = "config/aliases.json",
    ):
        self.significant_threshold_pp = significant_threshold_pp
        self.normalizer = HoldingsNormalizer(aliases_path)

    def _match_key(self, holding: Dict[str, Any]) -> str:
        """
        Generate a robust cross-source match key.
        Uses normalized name slug so PDF snapshots (without ISIN) and Excel
        snapshots (with ISIN) match identically.
        """
        raw_key = holding.get("key")
        # If raw_key is a slug (not an ISIN), use it
        if raw_key and not self.normalizer.is_valid_isin(raw_key):
            return raw_key.lower().strip()
        # Otherwise compute canonical slug from normalized name
        return self.normalizer.generate_canonical_key(holding["name"])

    def compute_diff(
        self,
        current_snapshot: Dict[str, Any],
        previous_snapshot: Dict[str, Any],
        significant_change_pp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compare current snapshot against previous snapshot.
        Both inputs must follow the FR-5 snapshot schema.
        """
        threshold = (
            significant_change_pp
            if significant_change_pp is not None
            else self.significant_threshold_pp
        )

        fund_id = current_snapshot.get("fund_id") or previous_snapshot.get("fund_id")
        curr_as_of = current_snapshot["as_of"]
        prev_as_of = previous_snapshot["as_of"]

        curr_month = curr_as_of[:7]
        prev_month = prev_as_of[:7]

        curr_holdings = current_snapshot.get("holdings", [])
        prev_holdings = previous_snapshot.get("holdings", [])

        curr_by_key = {self._match_key(h): h for h in curr_holdings}
        prev_by_key = {self._match_key(h): h for h in prev_holdings}

        # 1. Entered top 10 (FR-6.2, FR-6.3)
        entered: List[Dict[str, Any]] = []
        for h in curr_holdings:
            m_key = self._match_key(h)
            if m_key not in prev_by_key:
                entered.append({
                    "key": h["key"],
                    "name": h["name"],
                    "isin": h.get("isin"),
                    "sector": h.get("sector", "Equity"),
                    "rank": h["rank"],
                    "weight_pct": h["weight_pct"],
                })

        # 2. Exited top 10 (FR-6.2, FR-6.3)
        exited: List[Dict[str, Any]] = []
        for h in prev_holdings:
            m_key = self._match_key(h)
            if m_key not in curr_by_key:
                exited.append({
                    "key": h["key"],
                    "name": h["name"],
                    "isin": h.get("isin"),
                    "sector": h.get("sector", "Equity"),
                    "prev_rank": h["rank"],
                    "prev_weight_pct": h["weight_pct"],
                })

        # 3. Retained holdings (in both months)
        retained: List[Dict[str, Any]] = []
        num_increased = 0
        num_decreased = 0
        num_unchanged = 0
        num_significant = 0

        biggest_inc: Optional[Dict[str, Any]] = None
        biggest_dec: Optional[Dict[str, Any]] = None

        for h in curr_holdings:
            m_key = self._match_key(h)
            if m_key in prev_by_key:
                prev_h = prev_by_key[m_key]
                curr_w = h["weight_pct"]
                prev_w = prev_h["weight_pct"]
                delta_w = round(curr_w - prev_w, 2)
                rank_change = prev_h["rank"] - h["rank"]  # +2 means moved up 2 ranks

                if delta_w > 0.005:
                    direction = "increased"
                    num_increased += 1
                elif delta_w < -0.005:
                    direction = "decreased"
                    num_decreased += 1
                else:
                    direction = "unchanged"
                    num_unchanged += 1

                is_sig = abs(delta_w) >= threshold
                if is_sig:
                    num_significant += 1

                if delta_w > 0:
                    if biggest_inc is None or delta_w > biggest_inc["weight_delta_pp"]:
                        biggest_inc = {"name": h["name"], "weight_delta_pp": delta_w}
                elif delta_w < 0:
                    if biggest_dec is None or delta_w < biggest_dec["weight_delta_pp"]:
                        biggest_dec = {"name": h["name"], "weight_delta_pp": delta_w}

                retained.append({
                    "key": h["key"],
                    "name": h["name"],
                    "isin": h.get("isin"),
                    "sector": h.get("sector", "Equity"),
                    "rank": h["rank"],
                    "prev_rank": prev_h["rank"],
                    "rank_change": rank_change,
                    "weight_pct": curr_w,
                    "prev_weight_pct": prev_w,
                    "weight_delta_pp": delta_w,
                    "direction": direction,
                    "significant": is_sig,
                })

        curr_total = round(current_snapshot.get("top10_total_pct", sum(h["weight_pct"] for h in curr_holdings)), 2)
        prev_total = round(previous_snapshot.get("top10_total_pct", sum(h["weight_pct"] for h in prev_holdings)), 2)
        total_delta = round(curr_total - prev_total, 2)

        return {
            "fund_id": fund_id,
            "current_month": curr_month,
            "previous_month": prev_month,
            "as_of": curr_as_of,
            "prev_as_of": prev_as_of,
            "top10_total_pct": curr_total,
            "prev_top10_total_pct": prev_total,
            "top10_total_delta_pp": total_delta,
            "entered_top10": entered,
            "exited_top10": exited,
            "retained": retained,
            "summary": {
                "num_entered": len(entered),
                "num_exited": len(exited),
                "num_increased": num_increased,
                "num_decreased": num_decreased,
                "num_unchanged": num_unchanged,
                "num_significant": num_significant,
                "biggest_increase": biggest_inc,
                "biggest_decrease": biggest_dec,
            },
            "amc_commentary": current_snapshot.get("amc_commentary"),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute month-over-month diff for mutual fund holdings")
    parser.add_argument("--current", required=True, help="Path to current month snapshot JSON")
    parser.add_argument("--previous", required=True, help="Path to previous month snapshot JSON")
    parser.add_argument("--significant-pp", type=float, default=0.5, help="Threshold for significant changes (pp)")
    parser.add_argument("--out", help="Output path for diff JSON")
    parser.add_argument("--dry-run", action="store_true", help="Print diff to stdout")
    args = parser.parse_args()

    with open(args.current, "r", encoding="utf-8") as f:
        curr_snap = json.load(f)
    with open(args.previous, "r", encoding="utf-8") as f:
        prev_snap = json.load(f)

    engine = DiffEngine(significant_threshold_pp=args.significant_pp)
    diff = engine.compute_diff(curr_snap, prev_snap)

    if args.dry_run or not args.out:
        print(json.dumps(diff, indent=2))

    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(diff, f, indent=2)
        logger.info(f"Diff written to {out_p}")


if __name__ == "__main__":
    main()

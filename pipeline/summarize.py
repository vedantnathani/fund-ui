"""
AI Summarization module with strict number verification post-check
and deterministic template fallback for mutual fund diffs.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def extract_numbers_from_diff(diff: Dict[str, Any]) -> Set[float]:
    """Extract all valid numbers (weights, deltas, ranks, totals) from diff JSON."""
    numbers: Set[float] = set()

    def add_val(v: Any) -> None:
        if v is not None:
            try:
                num = round(float(v), 2)
                numbers.add(num)
                numbers.add(abs(num))
            except (ValueError, TypeError):
                pass

    add_val(diff.get("top10_total_pct"))
    add_val(diff.get("prev_top10_total_pct"))
    add_val(diff.get("top10_total_delta_pp"))

    for section in ["entered_top10", "exited_top10", "retained"]:
        for h in diff.get(section, []):
            add_val(h.get("rank"))
            add_val(h.get("prev_rank"))
            add_val(h.get("rank_change"))
            add_val(h.get("weight_pct"))
            add_val(h.get("prev_weight_pct"))
            add_val(h.get("weight_delta_pp"))

    summary = diff.get("summary", {})
    for k in ["num_entered", "num_exited", "num_increased", "num_decreased", "num_unchanged", "num_significant"]:
        add_val(summary.get(k))

    if summary.get("biggest_increase"):
        add_val(summary["biggest_increase"].get("weight_delta_pp"))
    if summary.get("biggest_decrease"):
        add_val(summary["biggest_decrease"].get("weight_delta_pp"))

    # Also extract numbers from commentary if present
    commentary = diff.get("amc_commentary") or ""
    for match in re.findall(r"\b\d+(?:\.\d+)?\b", commentary):
        add_val(match)

    return numbers


def verify_numbers_in_summary(summary_text: str, diff: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    FR-7.5: Post-check: Extract every number in the LLM output and confirm it exists in the diff JSON.
    Returns (True, []) if verified, or (False, [unverified_numbers]) if invalid.
    """
    valid_numbers = extract_numbers_from_diff(diff)

    # 1. Strip full dates (e.g. 2026-08, 2026-08-31) and calendar years (2020-2035)
    cleaned_text = re.sub(r"\b\d{4}-\d{2}(?:-\d{2})?\b", " ", summary_text)
    cleaned_text = re.sub(r"\b20[2-3]\d\b", " ", cleaned_text)

    # 2. Extract numbers even when followed by units like pp, %, bps
    tokens = re.findall(r"(?<![a-zA-Z])[-+]?\d*\.?\d+", cleaned_text)
    unverified: List[str] = []

    # Common ordinal/cardinal counts to ignore (e.g., top 10, month days)
    ignore_set = {
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "11", "12", "15", "20", "28", "30", "31",
    }

    for token in tokens:
        stripped = token.lstrip("+-")
        if stripped in ignore_set or token in ignore_set:
            continue
        try:
            val = round(float(token), 2)
            # Check within ±0.05 tolerance against both positive and absolute values
            matched = any(
                abs(val - v) <= 0.05 or abs(abs(val) - abs(v)) <= 0.05
                for v in valid_numbers
            )
            if not matched:
                unverified.append(token)
        except ValueError:
            unverified.append(token)

    is_valid = len(unverified) == 0
    return is_valid, unverified


def generate_template_summary(diff: Dict[str, Any], fund_name: str = "Parag Parikh Flexi Cap Fund") -> str:
    """
    FR-7.6: Generate deterministic template summary when LLM fails or is disabled.
    Guarantees crisp, neutral financial phrasing without external calls.
    """
    curr_m = diff.get("current_month", "")
    prev_m = diff.get("previous_month", "")
    curr_total = diff.get("top10_total_pct", 0.0)
    prev_total = diff.get("prev_top10_total_pct", 0.0)
    delta_total = diff.get("top10_total_delta_pp", 0.0)

    entered = diff.get("entered_top10", [])
    exited = diff.get("exited_top10", [])
    summary = diff.get("summary", {})
    biggest_inc = summary.get("biggest_increase")
    biggest_dec = summary.get("biggest_decrease")

    sentences: List[str] = []

    # 1. Churn sentence
    if not entered and not exited:
        sentences.append(
            f"In {curr_m}, {fund_name} maintained all 10 constituent companies in its top holdings with zero member churn."
        )
    else:
        entered_names = ", ".join(e["name"] for e in entered) if entered else "no new companies"
        exited_names = ", ".join(e["name"] for e in exited) if exited else "none"
        sentences.append(
            f"In {curr_m}, {fund_name} saw {len(entered)} holdings enter the top 10 ({entered_names}), while {exited_names} exited."
        )

    # 2. Total concentration sentence
    direction_word = "increased" if delta_total > 0 else ("decreased" if delta_total < 0 else "remained flat")
    sentences.append(
        f"Total top-10 concentration {direction_word} by {abs(delta_total):.2f}pp from {prev_total:.2f}% to {curr_total:.2f}%."
    )

    # 3. Movers sentence
    if biggest_inc and biggest_dec:
        sentences.append(
            f"{biggest_inc['name']} recorded the largest weight expansion (+{biggest_inc['weight_delta_pp']:.2f}pp), "
            f"while {biggest_dec['name']} saw the largest reduction ({biggest_dec['weight_delta_pp']:.2f}pp)."
        )
    elif biggest_inc:
        sentences.append(
            f"{biggest_inc['name']} recorded the largest weight expansion (+{biggest_inc['weight_delta_pp']:.2f}pp)."
        )
    elif biggest_dec:
        sentences.append(
            f"{biggest_dec['name']} saw the largest reduction ({biggest_dec['weight_delta_pp']:.2f}pp)."
        )

    # 4. Top holding anchor
    retained = sorted(diff.get("retained", []), key=lambda x: x["rank"])
    top_h = retained[0] if retained else (entered[0] if entered else None)
    if top_h:
        sentences.append(
            f"{top_h['name']} remained the portfolio's largest single position at {top_h['weight_pct']:.2f}%."
        )

    return " ".join(sentences)


class Summarizer:
    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER") or "auto").lower()

    def generate(self, diff: Dict[str, Any], fund_name: str = "Parag Parikh Flexi Cap Fund") -> Dict[str, Any]:
        """
        Generate AI summary with strict verification and automatic template fallback.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check API keys
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

        chosen_provider = self.provider
        if chosen_provider == "auto":
            if openrouter_key:
                chosen_provider = "openrouter"
            elif gemini_key:
                chosen_provider = "gemini"
            elif groq_key:
                chosen_provider = "groq"
            else:
                chosen_provider = "template_fallback"

        if chosen_provider == "template_fallback" or not any([openrouter_key, gemini_key, groq_key]):
            logger.info("Using deterministic template summary (no external LLM API key configured).")
            text = generate_template_summary(diff, fund_name=fund_name)
            return {
                "text": text,
                "provider": "template_fallback",
                "verified": True,
                "generated_at": now_iso,
            }

        # Attempt LLM call
        raw_text = None
        try:
            if chosen_provider == "openrouter" and openrouter_key:
                raw_text = self._call_openrouter(diff, fund_name, openrouter_key)
            elif chosen_provider == "groq" and groq_key:
                raw_text = self._call_groq(diff, fund_name, groq_key)
            elif chosen_provider == "gemini" and gemini_key:
                raw_text = self._call_gemini(diff, fund_name, gemini_key)
        except Exception as e:
            logger.warning(f"LLM API call failed ({chosen_provider}): {e}. Falling back to template.")

        # Post-check verification
        if raw_text:
            is_valid, unverified = verify_numbers_in_summary(raw_text, diff)
            if is_valid:
                logger.info(f"LLM summary successfully verified against diff JSON numbers ({chosen_provider}).")
                return {
                    "text": raw_text.strip(),
                    "provider": chosen_provider,
                    "verified": True,
                    "generated_at": now_iso,
                }
            else:
                logger.warning(
                    f"LLM summary rejected due to unverified numbers: {unverified}. Falling back to template."
                )

        # Fallback
        fallback_text = generate_template_summary(diff, fund_name=fund_name)
        return {
            "text": fallback_text,
            "provider": "template_fallback",
            "verified": True,
            "generated_at": now_iso,
        }

    def _build_prompt(self, diff: Dict[str, Any], fund_name: str) -> str:
        prompt_data = {
            "fund_name": fund_name,
            "current_month": diff.get("current_month"),
            "previous_month": diff.get("previous_month"),
            "top10_total_pct": diff.get("top10_total_pct"),
            "prev_top10_total_pct": diff.get("prev_top10_total_pct"),
            "top10_total_delta_pp": diff.get("top10_total_delta_pp"),
            "entered_top10": diff.get("entered_top10", []),
            "exited_top10": diff.get("exited_top10", []),
            "summary": diff.get("summary", {}),
            "retained_top_movers": diff.get("retained", [])[:4],
        }
        return (
            "You are an institutional financial portfolio analyst.\n"
            "Summarize the month-over-month mutual fund top-10 equity holdings changes in 3 to 4 plain-language sentences.\n"
            "STRICT RULES:\n"
            "1. Use ONLY the numbers provided in the JSON data below. DO NOT invent, estimate, or extrapolate any numbers.\n"
            "2. Mention top-10 concentration, entering/exiting stocks, and the biggest gainers/reducers.\n"
            "3. Use neutral language ('weight increased/decreased', 'entered/exited'). Never say 'bought' or 'sold'.\n"
            "4. Do NOT give investment recommendations or outside market commentary.\n\n"
            f"DATA:\n{json.dumps(prompt_data, indent=2)}"
        )

    def _call_openrouter(self, diff: Dict[str, Any], fund_name: str, api_key: str) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
            "X-Title": "Mutual Fund Tracker",
        }
        payload = {
            "model": os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free"),
            "messages": [
                {"role": "user", "content": self._build_prompt(diff, fund_name)},
            ],
            "temperature": 0.1,
            "max_tokens": 250,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_groq(self, diff: Dict[str, Any], fund_name: str, api_key: str) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "user", "content": self._build_prompt(diff, fund_name)},
            ],
            "temperature": 0.1,
            "max_tokens": 250,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_gemini(self, diff: Dict[str, Any], fund_name: str, api_key: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {"parts": [{"text": self._build_prompt(diff, fund_name)}]}
            ],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 250},
        }
        resp = requests.post(url, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AI summary for mutual fund diff JSON")
    parser.add_argument("--diff", required=True, help="Path to diff JSON file")
    parser.add_argument("--provider", default=None, help="LLM provider override")
    args = parser.parse_args()

    with open(args.diff, "r", encoding="utf-8") as f:
        diff_data = json.load(f)

    summarizer = Summarizer(provider=args.provider)
    result = summarizer.generate(diff_data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

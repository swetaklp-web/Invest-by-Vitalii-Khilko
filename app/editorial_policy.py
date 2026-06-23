from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import ROOT_DIR


POLICY_PATH = ROOT_DIR / "data" / "editorial_policy.json"


def load_editorial_policy(path: Path | None = None) -> dict[str, Any]:
    policy_path = path or POLICY_PATH
    return json.loads(policy_path.read_text(encoding="utf-8"))


def _source_family(source: str) -> str:
    if source.startswith("Telegram/"):
        return "Telegram"
    if source.startswith("X/"):
        return "X"
    return source


def _keyword_score(text: str, keyword_weights: dict[str, int]) -> int:
    lowered = text.lower()
    score = 0
    for keyword, weight in keyword_weights.items():
        if re.search(rf"(?<![a-z]){re.escape(keyword.lower())}(?![a-z])", lowered):
            score += int(weight)
    return score


def score_signal(signal: dict[str, Any], policy: dict[str, Any] | None = None) -> int:
    policy = policy or load_editorial_policy()
    tickers = [str(ticker).upper().replace("$", "") for ticker in signal.get("tickers", [])]
    source = _source_family(str(signal.get("source", "")))
    catalyst = str(signal.get("catalyst_type", "")).lower()
    strength = str(signal.get("strength", "low")).lower()
    text = " ".join(
        str(signal.get(key, "")) for key in ("summary", "source", "discovery_query", "impact")
    )

    score = int(policy.get("source_weights", {}).get(source, 0))
    score += int(policy.get("strength_weights", {}).get(strength, 0))
    score += int(policy.get("catalyst_weights", {}).get(catalyst, 0))
    score += _keyword_score(text, policy.get("market_impact_keywords", {}))

    broad_tickers = set(policy.get("broad_market_tickers", []))
    if broad_tickers.intersection(tickers):
        score += int(policy.get("broad_market_bonus", 0))
    if len(tickers) >= 3:
        score += int(policy.get("multi_ticker_bonus", 0))
    if len(tickers) == 1 and tickers[0] not in broad_tickers:
        score += int(policy.get("single_company_penalty", 0))

    for ticker in tickers:
        score += int(policy.get("overused_tickers", {}).get(ticker, 0))

    return score

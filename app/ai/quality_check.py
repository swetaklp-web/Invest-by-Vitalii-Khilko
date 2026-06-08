from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.sources.freshness import today_moscow


FORBIDDEN_PATTERNS = [
    r"\bпокупать\b",
    r"\bпродавать\b",
    r"\bнадо брать\b",
    r"\bточно вырастет\b",
    r"\bгарантированн\w*\b",
    r"\bбез риска\b",
    r"\bсрочно покупать\b",
    r"\bиксы\b",
    r"\bракета\b",
]
PROMISE_PATTERNS = [r"\bдоходност\w* гарантирован\w*\b", r"\bгарантия доходност\w*\b"]
DIRECT_RECOMMENDATIONS = [r"\bвам стоит\b", r"\bрекомендуем купить\b", r"\bследует купить\b"]
COMPANY_HINTS = ["компания", "акции", "эмитент", "корпорац"]
APPROVED_SOURCE_DOMAINS = {
    "x.com",
    "t.me",
    "finance.yahoo.com",
    "www.barchart.com",
    "barchart.com",
    "oninvest.com",
    "www.oninvest.com",
}


def _approved_source_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname in APPROVED_SOURCE_DOMAINS


def check_post(post: dict[str, Any], allowed_source_urls: set[str] | None = None) -> dict[str, Any]:
    text = str(post.get("telegram_text", ""))
    lowered = text.lower()
    issues: list[str] = []

    if not text:
        issues.append("telegram_text is empty")
    if len(text) > 1000:
        issues.append(f"telegram_text exceeds 1000 characters: {len(text)}")
    if not post.get("date") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(post.get("date"))):
        issues.append("date is missing or invalid")
    elif str(post.get("date")) != today_moscow():
        issues.append("post date is not current Moscow date")
    if any(re.search(pattern, lowered) for pattern in FORBIDDEN_PATTERNS):
        issues.append("forbidden wording detected")
    if any(re.search(pattern, lowered) for pattern in DIRECT_RECOMMENDATIONS):
        issues.append("direct personal investment recommendation detected")
    if any(re.search(pattern, lowered) for pattern in PROMISE_PATTERNS):
        issues.append("return promise detected")
    if any(hint in lowered for hint in COMPANY_HINTS) and not post.get("tickers"):
        issues.append("company-related post has no tickers")
    if post.get("catalyst_type") == "rumor" and "слух" not in lowered:
        issues.append('rumor is not marked as "СЛУХ"')
    post_type = post.get("post_type")
    if post_type == "morning_brief":
        if post.get("title") != "Что важно перед открытием США":
            issues.append("morning_brief title is invalid")
        if not 5 <= len(post.get("tickers") or []) <= 10:
            issues.append("morning_brief must contain 5-10 tickers")
    elif post_type == "evening_theme" and post.get("title") != "Главная тема дня на рынке":
        issues.append("evening_theme title is invalid")
    sources = post.get("sources") or []
    if not sources:
        issues.append("sources are missing")
    elif any(not source.get("url") for source in sources):
        issues.append("one or more sources have no URL")
    elif any(not _approved_source_url(str(source.get("url"))) for source in sources):
        issues.append("one or more sources are outside the approved source list")
    elif allowed_source_urls is not None and any(
        str(source.get("url")) not in allowed_source_urls for source in sources
    ):
        issues.append("one or more sources were not present in the fresh input data")

    risk_flags = list(post.get("risk_flags") or [])
    return {
        "passed": not issues,
        "issues": issues,
        "risk_flags": risk_flags,
        "requires_manual_review": bool(issues or risk_flags),
    }

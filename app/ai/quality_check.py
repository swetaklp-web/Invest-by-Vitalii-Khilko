import re
from typing import Any


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


def check_post(post: dict[str, Any]) -> dict[str, Any]:
    text = str(post.get("telegram_text", ""))
    lowered = text.lower()
    issues: list[str] = []

    if not text:
        issues.append("telegram_text is empty")
    if len(text) > 3500:
        issues.append(f"telegram_text exceeds 3500 characters: {len(text)}")
    if not post.get("date") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(post.get("date"))):
        issues.append("date is missing or invalid")
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

    risk_flags = list(post.get("risk_flags") or [])
    return {
        "passed": not issues,
        "issues": issues,
        "risk_flags": risk_flags,
        "requires_manual_review": bool(issues or risk_flags),
    }


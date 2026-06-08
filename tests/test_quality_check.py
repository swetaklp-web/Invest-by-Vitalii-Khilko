from app.ai.quality_check import check_post
from app.sources.freshness import today_moscow


def base_post() -> dict:
    return {
        "date": today_moscow(),
        "post_type": "evening_theme",
        "title": "Главная тема дня на рынке",
        "telegram_text": "AI-инфраструктура остаётся на радаре. Акции $NVDA могут получить импульс.",
        "tickers": ["NVDA"],
        "catalyst_type": "narrative",
        "sources": [{"name": "Yahoo Finance", "url": "https://finance.yahoo.com/"}],
        "risk_flags": [],
    }


def test_valid_post_passes() -> None:
    assert check_post(base_post())["passed"] is True


def test_forbidden_word_fails() -> None:
    post = base_post()
    post["telegram_text"] = "Эти акции надо покупать."
    assert check_post(post)["passed"] is False


def test_rumor_requires_label() -> None:
    post = base_post()
    post["catalyst_type"] = "rumor"
    assert any('СЛУХ' in issue for issue in check_post(post)["issues"])


def test_risk_flags_require_manual_review_but_do_not_fail_quality() -> None:
    post = base_post()
    post["risk_flags"] = ["Источник требует дополнительной проверки"]
    result = check_post(post)
    assert result["passed"] is True
    assert result["requires_manual_review"] is True


def test_caption_over_1000_characters_fails() -> None:
    post = base_post()
    post["telegram_text"] = "$NVDA " + ("а" * 1000)
    assert check_post(post)["passed"] is False

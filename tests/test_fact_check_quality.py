from app.ai.quality_check import check_post
from app.sources.freshness import today_moscow


def valid_post() -> dict:
    return {
        "date": today_moscow(),
        "post_type": "evening_theme",
        "title": "Главная тема дня на рынке",
        "telegram_text": "Энергетический сектор показывает относительную силу.",
        "tickers": ["XLE"],
        "catalyst_type": "technical",
        "sources": [{"name": "Yahoo Finance", "url": "https://finance.yahoo.com/"}],
        "risk_flags": [],
    }


def test_unsupported_factual_claim_fails_quality() -> None:
    result = check_post(
        valid_post(),
        {"https://finance.yahoo.com/"},
        {"passed": False, "unsupported_claims": ["Неподтверждённая цифра"], "notes": []},
    )

    assert result["passed"] is False
    assert result["fact_check"]["unsupported_claims"] == ["Неподтверждённая цифра"]

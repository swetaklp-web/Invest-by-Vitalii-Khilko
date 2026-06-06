from app.ai.quality_check import check_post


def base_post() -> dict:
    return {
        "date": "2026-06-06",
        "telegram_text": "AI-инфраструктура остаётся на радаре. Акции $NVDA могут получить импульс.",
        "tickers": ["NVDA"],
        "catalyst_type": "narrative",
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
    assert 'СЛУХ' in check_post(post)["issues"][0]


def test_risk_flags_require_manual_review_but_do_not_fail_quality() -> None:
    post = base_post()
    post["risk_flags"] = ["Источник требует дополнительной проверки"]
    result = check_post(post)
    assert result["passed"] is True
    assert result["requires_manual_review"] is True


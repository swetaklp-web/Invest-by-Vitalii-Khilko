import pytest

from app import workflow


def test_generate_grounded_post_retries_with_fact_check_feedback(monkeypatch) -> None:
    feedback_calls = []

    def fake_generate_post(*_args, grounding_feedback=None, **_kwargs):
        feedback_calls.append(grounding_feedback)
        return {
            "telegram_text": "Текст",
            "sources": [{"url": "https://finance.yahoo.com/news/test"}],
        }

    fact_checks = iter(
        [
            {"passed": False, "unsupported_claims": ["лишняя цифра"], "notes": []},
            {"passed": True, "unsupported_claims": [], "notes": []},
        ]
    )

    monkeypatch.setattr(workflow, "generate_post", fake_generate_post)
    monkeypatch.setattr(workflow, "verify_post_grounding", lambda *_: next(fact_checks))
    monkeypatch.setattr(workflow, "write_log", lambda *_: None)

    post, fact_check = workflow.generate_grounded_post(
        {"signals": [{"url": "https://finance.yahoo.com/news/test"}], "market_snapshot": {}},
        "evening_theme",
    )

    assert post["telegram_text"] == "Текст"
    assert fact_check["passed"] is True
    assert feedback_calls[0] is None
    assert feedback_calls[1]["unsupported_claims"] == ["лишняя цифра"]


def test_generate_grounded_post_stops_after_repeated_fact_check_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        workflow,
        "generate_post",
        lambda *_args, **_kwargs: {"telegram_text": "Текст"},
    )
    monkeypatch.setattr(
        workflow,
        "verify_post_grounding",
        lambda *_: {"passed": False, "unsupported_claims": ["не подтверждено"], "notes": []},
    )
    monkeypatch.setattr(workflow, "write_log", lambda *_: None)

    with pytest.raises(workflow.FactCheckFailed) as error:
        workflow.generate_grounded_post({"signals": [{}], "market_snapshot": {}}, "evening_theme")

    assert error.value.fact_check["unsupported_claims"] == ["не подтверждено"]

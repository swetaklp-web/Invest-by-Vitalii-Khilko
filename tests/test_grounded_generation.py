import pytest

from app import workflow
from app.sources.freshness import today_moscow
from app.storage import drafts as draft_storage


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


def test_source_anchored_fallback_builds_publishable_fact_checked_post(monkeypatch) -> None:
    monkeypatch.setattr(workflow, "load_editorial_policy", lambda: {})
    monkeypatch.setattr(workflow, "score_signal", lambda signal, _policy: 10)
    today = today_moscow()

    post, fact_check = workflow.build_source_anchored_post(
        {
            "date": today,
            "signals": [
                {
                    "source": "Yahoo Finance",
                    "url": "https://finance.yahoo.com/news/test",
                    "summary": "Reuters: Banks rise as yields move lower",
                    "tickers": ["JPM", "XLF"],
                    "impact": "[Watch]",
                    "strength": "medium",
                    "horizon": "short",
                    "catalyst_type": "event",
                    "date": today,
                }
            ],
            "market_snapshot": {"quotes": []},
        },
        "evening_theme",
        {"unsupported_claims": ["AI added unsupported detail"]},
    )

    assert post["telegram_text"].startswith("Banks rise as yields move lower")
    assert "$JPM $XLF" in post["telegram_text"]
    assert post["sources"] == [
        {
            "name": "Yahoo Finance",
            "url": "https://finance.yahoo.com/news/test",
            "summary": "Banks rise as yields move lower",
        }
    ]
    assert fact_check["passed"] is True
    assert fact_check["unsupported_claims"] == []


def test_build_draft_uses_source_anchored_fallback_when_ai_fact_check_fails(monkeypatch, tmp_path) -> None:
    today = today_moscow()
    inputs = {
        "date": today,
        "signals": [
            {
                "source": "Yahoo Finance",
                "url": "https://finance.yahoo.com/news/test",
                "summary": "Yahoo Finance: Energy shares move after oil update",
                "tickers": ["XLE"],
                "impact": "[Watch]",
                "strength": "medium",
                "horizon": "short",
                "catalyst_type": "event",
                "date": today,
            }
        ],
        "market_snapshot": {"quotes": []},
        "source_quality": {},
    }
    events = []
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"png")

    monkeypatch.setattr(draft_storage, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(workflow, "load_source_inputs", lambda _post_type: inputs)
    monkeypatch.setattr(
        workflow,
        "generate_grounded_post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            workflow.FactCheckFailed({"unsupported_claims": ["лишний вывод"]})
        ),
    )
    monkeypatch.setattr(workflow, "write_log", events.append)
    monkeypatch.setattr(workflow, "load_editorial_policy", lambda: {})
    monkeypatch.setattr(workflow, "score_signal", lambda signal, _policy: 10)
    monkeypatch.setattr(workflow, "create_news_image", lambda *_: (image_path, "test"))

    draft = workflow.build_draft("evening_theme")

    assert draft["quality"]["passed"] is True
    assert draft["quality"]["fact_check"]["passed"] is True
    assert "Energy shares move after oil update" in draft["post"]["telegram_text"]
    assert any(event["status"] == "source_anchored_fallback" for event in events)


def test_build_draft_does_not_block_on_technical_quality_warnings(monkeypatch, tmp_path) -> None:
    today = today_moscow()
    inputs = {
        "date": today,
        "signals": [
            {
                "source": "Yahoo Finance",
                "url": "https://finance.yahoo.com/news/test",
                "summary": "Yahoo Finance: Test source",
                "tickers": ["XLF"],
                "date": today,
            }
        ],
        "market_snapshot": {"quotes": []},
        "source_quality": {},
    }
    post = {
        "post_type": "evening_theme",
        "date": today,
        "title": "Главная тема дня на рынке",
        "telegram_text": "Технически длинный текст " + ("x" * 1100),
        "tickers": ["XLF"],
        "sources": [{"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/test"}],
        "catalyst_type": "event",
        "risk_flags": [],
    }
    fact_check = {
        "passed": True,
        "unsupported_claims": [],
        "notes": [],
        "fresh_signals_checked": 1,
        "market_quotes_checked": 0,
    }
    events = []
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"png")

    monkeypatch.setattr(draft_storage, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(workflow, "load_source_inputs", lambda _post_type: inputs)
    monkeypatch.setattr(workflow, "generate_grounded_post", lambda *_args, **_kwargs: (post, fact_check))
    monkeypatch.setattr(workflow, "write_log", events.append)
    monkeypatch.setattr(workflow, "create_news_image", lambda *_: (image_path, "test"))

    draft = workflow.build_draft("evening_theme")

    assert draft["quality"]["fact_check"]["passed"] is True
    assert draft["quality"]["technical_passed"] is False
    assert any(event["status"] == "technical_quality_warning" for event in events)

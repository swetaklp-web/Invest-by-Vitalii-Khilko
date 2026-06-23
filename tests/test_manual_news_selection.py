from hashlib import sha256

from app import workflow
from app.storage import news_selections


def test_discover_news_candidates_removes_duplicates(monkeypatch) -> None:
    signals = [
        {
            "source": "Yahoo Finance",
            "url": "https://a",
            "summary": "Apple product update",
            "tickers": ["AAPL"],
            "strength": "low",
            "catalyst_type": "event",
        },
        {
            "source": "Yahoo Finance",
            "url": "https://b",
            "summary": "Apple earnings guidance changes",
            "tickers": ["AAPL"],
            "strength": "high",
            "catalyst_type": "fundamental",
        },
        {
            "source": "X/@source",
            "url": "https://c",
            "summary": "Banks react to Treasury yield and Fed repricing",
            "tickers": ["JPM", "XLF", "TLT"],
            "strength": "medium",
            "catalyst_type": "macro",
        },
    ]
    monkeypatch.setattr(
        workflow, "load_source_inputs_with_retries", lambda _post_type: {"signals": signals}
    )

    result = workflow.discover_news_candidates("evening_theme")

    assert [item["url"] for item in result] == ["https://c", "https://b"]


def test_discover_news_candidates_penalizes_overused_nvda_story(monkeypatch) -> None:
    signals = [
        {
            "source": "Yahoo Finance",
            "url": "https://nvda",
            "summary": "Nvidia rises on AI chip narrative",
            "tickers": ["NVDA"],
            "strength": "high",
            "catalyst_type": "narrative",
        },
        {
            "source": "Yahoo Finance",
            "url": "https://macro",
            "summary": "Fed rate expectations move Treasury yields and dollar",
            "tickers": ["SPY", "TLT", "XLF"],
            "strength": "medium",
            "catalyst_type": "macro",
        },
    ]
    monkeypatch.setattr(
        workflow, "load_source_inputs_with_retries", lambda _post_type: {"signals": signals}
    )

    result = workflow.discover_news_candidates("evening_theme")

    assert result[0]["url"] == "https://macro"


def test_news_selection_survives_callback_restart(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(news_selections, "SELECTIONS_DIR", tmp_path)
    signal = {"source": "Yahoo Finance", "url": "https://example.com", "summary": "News"}

    selection_id = news_selections.save_news_selection(signal, "evening_theme")
    restored = news_selections.load_news_selection(selection_id)

    assert restored["signal"] == signal
    assert restored["post_type"] == "evening_theme"


def test_recover_news_signal_after_worker_restart(monkeypatch) -> None:
    signal = {"url": "https://example.com/news", "summary": "Verified story"}
    monkeypatch.setattr(
        workflow, "discover_news_candidates", lambda _post_type, limit=30: [signal]
    )
    selection_id = sha256(
        f"evening_theme:{signal['url']}:{signal['summary']}".encode("utf-8")
    ).hexdigest()[:12]

    assert workflow.recover_news_signal(selection_id, "evening_theme") == signal

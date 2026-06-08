from app.sources.freshness import filter_fresh_signals


def test_filter_fresh_signals_drops_stale_and_undated_items() -> None:
    fresh, stale = filter_fresh_signals(
        [
            {"summary": "today", "date": "2026-06-08"},
            {"summary": "old", "date": "2026-06-06"},
            {"summary": "unknown", "date": ""},
        ],
        "2026-06-08",
    )

    assert [item["summary"] for item in fresh] == ["today"]
    assert [item["summary"] for item in stale] == ["old", "unknown"]

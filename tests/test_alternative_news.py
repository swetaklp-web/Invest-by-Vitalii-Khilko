from app.workflow import select_alternative_signals


def test_alternative_news_prefers_signals_with_different_tickers() -> None:
    inputs = {
        "signals": [
            {"summary": "AI", "tickers": ["NVDA"]},
            {"summary": "Banks", "tickers": ["JPM", "BAC"]},
            {"summary": "Energy", "tickers": ["XOM", "CVX"]},
            {"summary": "Health", "tickers": ["LLY", "UNH"]},
            {"summary": "Retail", "tickers": ["WMT", "COST"]},
            {"summary": "Industry", "tickers": ["CAT", "GE"]},
        ],
        "source_quality": {},
    }

    result = select_alternative_signals(inputs, {"telegram_text": "Фокус на $NVDA"})

    assert all("NVDA" not in signal["tickers"] for signal in result["signals"])
    assert result["source_quality"]["alternative_candidates"] == 5

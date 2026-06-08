from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


WATCHLIST = ("SPY", "QQQ", "NVDA", "AMD", "TSLA", "AAPL", "MSFT")


def fetch_yahoo_signals() -> list[dict]:
    signals: list[dict] = []
    for ticker in WATCHLIST:
        query = urlencode({"q": ticker, "quotesCount": 1, "newsCount": 2})
        request = Request(
            f"https://query1.finance.yahoo.com/v1/finance/search?{query}",
            headers={"User-Agent": "Mozilla/5.0 InvestByVitaliiKhilko/1.0"},
        )
        with urlopen(request, timeout=12) as response:
            payload = json.load(response)
        for item in payload.get("news", [])[:2]:
            signals.append(
                {
                    "source": "Yahoo Finance",
                    "url": item.get("link", ""),
                    "summary": item.get("title", ""),
                    "tickers": [ticker],
                    "impact": "[Watch]",
                    "strength": "low",
                    "horizon": "short",
                    "catalyst_type": "event",
                    "date": "",
                }
            )
    return signals

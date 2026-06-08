from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings
from app.sources.freshness import today_moscow


WATCHLIST = (
    "SPY", "QQQ", "IWM", "DIA",
    "XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLRE", "XLB", "XLC",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    "JPM", "BAC", "GS", "V", "BRK.B",
    "LLY", "UNH", "JNJ", "PFE",
    "XOM", "CVX", "COP",
    "WMT", "COST", "HD", "MCD",
    "CAT", "GE", "BA", "RTX", "LMT",
)


def fetch_barchart_signals() -> list[dict]:
    if not settings.barchart_api_key:
        return []

    query = urlencode(
        {
            "apikey": settings.barchart_api_key,
            "symbols": ",".join(WATCHLIST),
            "fields": "percentChange,netChange,lastPrice,tradeTimestamp",
        }
    )
    request = Request(
        f"https://marketdata.websol.barchart.com/getQuote.json?{query}",
        headers={"User-Agent": "InvestByVitaliiKhilko/1.0"},
    )
    with urlopen(request, timeout=15) as response:
        payload = json.load(response)

    signals: list[dict] = []
    for quote in payload.get("results", []) or []:
        symbol = quote.get("symbol")
        if not symbol:
            continue
        percent = quote.get("percentChange")
        impact = "[Watch]"
        try:
            if float(percent) >= 1:
                impact = "[Bullish]"
            elif float(percent) <= -1:
                impact = "[Bearish]"
        except (TypeError, ValueError):
            pass
        signals.append(
            {
                "source": "Barchart OnDemand",
                "url": f"https://www.barchart.com/stocks/quotes/{symbol}/overview",
                "summary": (
                    f"{symbol}: price={quote.get('lastPrice')}, "
                    f"change={quote.get('netChange')}, percentChange={percent}"
                ),
                "tickers": [symbol],
                "impact": impact,
                "strength": "medium",
                "horizon": "short",
                "catalyst_type": "technical",
                "date": today_moscow(),
            }
        )
    return signals

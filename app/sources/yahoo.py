from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


WATCHLIST = ("SPY", "QQQ", "NVDA", "AMD", "TSLA", "AAPL", "MSFT")
MARKET_SYMBOLS = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq Composite",
    "^DJI": "Dow Jones",
    "ES=F": "S&P 500 futures",
    "NQ=F": "Nasdaq futures",
    "^TNX": "US 10Y yield",
    "DX-Y.NYB": "US Dollar Index",
    "CL=F": "WTI oil",
    "GC=F": "Gold",
}


def _get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 InvestByVitaliiKhilko/1.0"})
    with urlopen(request, timeout=12) as response:
        return json.load(response)


def _provider_date(item: dict) -> str:
    timestamp = item.get("providerPublishTime")
    if not timestamp:
        return ""
    return datetime.fromtimestamp(int(timestamp), ZoneInfo("Europe/Moscow")).date().isoformat()


def fetch_yahoo_signals() -> list[dict]:
    signals: list[dict] = []
    for ticker in WATCHLIST:
        query = urlencode({"q": ticker, "quotesCount": 1, "newsCount": 2})
        payload = _get_json(f"https://query1.finance.yahoo.com/v1/finance/search?{query}")
        for item in payload.get("news", [])[:2]:
            signals.append(
                {
                    "source": "Yahoo Finance",
                    "url": item.get("link", ""),
                    "summary": f"{item.get('publisher', 'Yahoo Finance')}: {item.get('title', '')}",
                    "tickers": [ticker],
                    "impact": "[Watch]",
                    "strength": "low",
                    "horizon": "short",
                    "catalyst_type": "event",
                    "date": _provider_date(item),
                }
            )
    return signals


def fetch_yahoo_market_snapshot() -> dict:
    quotes = []
    for symbol, name in MARKET_SYMBOLS.items():
        encoded_symbol = quote(symbol, safe="")
        try:
            payload = _get_json(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_symbol}"
                "?range=1d&interval=5m"
            )
        except Exception:
            continue
        result = payload.get("chart", {}).get("result", [])
        if not result:
            continue
        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        previous_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        change_percent = None
        if price is not None and previous_close:
            change_percent = (float(price) - float(previous_close)) / float(previous_close) * 100
        quotes.append(
            {
                "symbol": symbol,
                "name": name,
                "price": price,
                "change_percent": change_percent,
                "market_state": meta.get("marketState"),
                "source": "Yahoo Finance quote",
                "date": datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat(),
            }
        )
    if not quotes:
        raise RuntimeError("Yahoo Finance market snapshot returned no quotes")
    return {"date": datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat(), "quotes": quotes}

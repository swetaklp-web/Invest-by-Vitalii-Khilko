from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DISCOVERY_QUERIES = (
    "US stock market",
    "Federal Reserve interest rates Treasury yields",
    "US inflation jobs economy",
    "earnings stocks",
    "mergers acquisitions stocks",
    "insider trading stocks",
    "options market stocks",
    "bank financial stocks",
    "healthcare biotech stocks",
    "energy oil stocks",
    "industrial aerospace defense stocks",
    "consumer retail stocks",
    "materials mining gold stocks",
    "real estate utilities stocks",
    "technology semiconductor stocks",
    "small cap stocks",
)
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
    "BTC-USD": "Bitcoin",
    "IWM": "Russell 2000 ETF",
    "XLF": "Financials sector ETF",
    "XLV": "Health Care sector ETF",
    "XLE": "Energy sector ETF",
    "XLI": "Industrials sector ETF",
    "XLY": "Consumer Discretionary sector ETF",
    "XLP": "Consumer Staples sector ETF",
    "XLU": "Utilities sector ETF",
    "XLRE": "Real Estate sector ETF",
    "XLB": "Materials sector ETF",
    "XLK": "Technology sector ETF",
    "XLC": "Communication Services sector ETF",
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
    seen_urls: set[str] = set()
    for discovery_query in DISCOVERY_QUERIES:
        query = urlencode({"q": discovery_query, "quotesCount": 0, "newsCount": 5})
        payload = _get_json(f"https://query1.finance.yahoo.com/v1/finance/search?{query}")
        for item in payload.get("news", [])[:5]:
            url = item.get("link", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            tickers = [
                ticker
                for ticker in item.get("relatedTickers", [])
                if isinstance(ticker, str) and ticker and not ticker.startswith("^")
            ][:10]
            signals.append(
                {
                    "source": "Yahoo Finance",
                    "url": url,
                    "summary": f"{item.get('publisher', 'Yahoo Finance')}: {item.get('title', '')}",
                    "tickers": tickers,
                    "impact": "[Watch]",
                    "strength": "low",
                    "horizon": "short",
                    "catalyst_type": "event",
                    "date": _provider_date(item),
                    "discovery_query": discovery_query,
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

from __future__ import annotations

import asyncio
import re
from zoneinfo import ZoneInfo

from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config import settings
from app.sources.freshness import today_moscow


CHANNELS = ("krasilnikovbroker", "utexplatform")
TICKER_RE = re.compile(r"(?<![A-ZА-Я])\$?([A-Z]{1,6})(?![A-ZА-Я])")


def _extract_tickers(text: str) -> list[str]:
    ignored = {"USA", "USD", "ETF", "CEO", "IPO", "AI", "GDP", "CPI", "PPI", "FOMC"}
    tickers = []
    for match in TICKER_RE.findall(text):
        ticker = match.upper()
        if ticker not in ignored and ticker not in tickers:
            tickers.append(ticker)
    return tickers[:8]


async def _fetch_telegram_signals_async() -> list[dict]:
    if not (
        settings.telegram_api_id
        and settings.telegram_api_hash
        and settings.telegram_session_string
    ):
        return []

    current_date = today_moscow()
    signals: list[dict] = []
    async with TelegramClient(
        StringSession(settings.telegram_session_string),
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    ) as client:
        for channel in CHANNELS:
            async for message in client.iter_messages(channel, limit=10):
                text = (message.message or "").strip()
                message_date = message.date.astimezone(ZoneInfo("Europe/Moscow")).date().isoformat()
                if not text or message_date != current_date:
                    continue
                signals.append(
                    {
                        "source": f"Telegram/{channel}",
                        "url": f"https://t.me/{channel}/{message.id}",
                        "summary": text[:700],
                        "tickers": _extract_tickers(text),
                        "impact": "[Watch]",
                        "strength": "medium",
                        "horizon": "short",
                        "catalyst_type": "narrative",
                        "date": current_date,
                    }
                )
    return signals


def fetch_telegram_signals() -> list[dict]:
    return asyncio.run(_fetch_telegram_signals_async())

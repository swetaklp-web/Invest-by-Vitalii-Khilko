from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def today_moscow() -> str:
    return datetime.now(MOSCOW_TZ).date().isoformat()


def signal_date(signal: dict[str, Any]) -> str:
    value = str(signal.get("date") or "").strip()
    if len(value) >= 10:
        return value[:10]
    return ""


def filter_fresh_signals(signals: list[dict[str, Any]], current_date: str | None = None) -> tuple[list[dict], list[dict]]:
    date = current_date or today_moscow()
    fresh: list[dict] = []
    stale: list[dict] = []
    for signal in signals:
        if signal_date(signal) == date:
            fresh.append(signal)
        else:
            stale.append(signal)
    return fresh, stale

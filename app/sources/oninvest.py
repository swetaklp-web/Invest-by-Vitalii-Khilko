"""Oninvest adapter placeholder.

Oninvest does not expose a stable public API URL in this project yet. Keep this
adapter disabled until ONINVEST_API_KEY is paired with official endpoint docs.
"""

from app.config import settings


def fetch_oninvest_signals() -> list[dict]:
    if not settings.oninvest_api_key:
        return []
    return []

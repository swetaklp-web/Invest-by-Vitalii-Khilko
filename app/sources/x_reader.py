from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings


PRIORITY_ACCOUNTS = (
    "trendspider",
    "mr_derivatives",
    "thetechinvest",
    "stocksavvyshay",
    "wallstengine",
)


def _get(url: str) -> dict:
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {settings.x_bearer_token}",
            "User-Agent": "InvestByVitaliiKhilko/1.0",
        },
    )
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def fetch_x_signals() -> list[dict]:
    if not settings.x_bearer_token:
        return []

    signals: list[dict] = []
    for username in PRIORITY_ACCOUNTS:
        user = _get(f"https://api.x.com/2/users/by/username/{username}")
        user_id = user["data"]["id"]
        query = urlencode(
            {
                "max_results": 5,
                "exclude": "retweets,replies",
                "tweet.fields": "created_at",
            }
        )
        tweets = _get(f"https://api.x.com/2/users/{user_id}/tweets?{query}")
        for tweet in tweets.get("data", [])[:2]:
            signals.append(
                {
                    "source": f"X/@{username}",
                    "url": f"https://x.com/{username}/status/{tweet['id']}",
                    "summary": tweet["text"],
                    "tickers": [],
                    "impact": "[Watch]",
                    "strength": "low",
                    "horizon": "short",
                    "catalyst_type": "narrative",
                    "date": tweet.get("created_at", "")[:10],
                }
            )
    return signals

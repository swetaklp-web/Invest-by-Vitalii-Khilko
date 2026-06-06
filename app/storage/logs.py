import json
from datetime import datetime, timezone
import os
from typing import Any

from app.config import ROOT_DIR


SECRET_NAMES = [
    "OPENAI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_SESSION_STRING",
    "X_API_KEY",
    "BARCHART_API_KEY",
]


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        for name in SECRET_NAMES:
            secret = os.getenv(name)
            if secret:
                value = value.replace(secret, "[REDACTED]")
    return value


def write_log(event: dict[str, Any]) -> None:
    path = ROOT_DIR / "data" / "logs" / f"{datetime.now(timezone.utc):%Y-%m}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _redact({"logged_at": datetime.now(timezone.utc).isoformat(), **event})
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")

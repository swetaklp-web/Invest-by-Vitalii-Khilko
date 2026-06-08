from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

REQUIRED_ENV_VARS = (
    "OPENAI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_REVIEW_CHAT_ID",
    "TELEGRAM_CHANNEL_ID",
)
OPTIONAL_ENV_VARS = (
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_SESSION_STRING",
    "X_BEARER_TOKEN",
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
    "BARCHART_API_KEY",
    "ONINVEST_API_KEY",
    "YAHOO_FINANCE_API_KEY",
)


def _env(name: str, default: str = ""):
    def load() -> str:
        value = os.getenv(name, default).strip()
        prefix = f"{name}="
        if value.startswith(prefix):
            return value[len(prefix):].strip()
        return value

    return field(default_factory=load)


def _credential(name: str):
    return field(default_factory=lambda: "".join(os.getenv(name, "").split()))


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = _credential("OPENAI_API_KEY")
    telegram_bot_token: str = _credential("TELEGRAM_BOT_TOKEN")
    telegram_review_chat_id: str = _env("TELEGRAM_REVIEW_CHAT_ID")
    telegram_channel_id: str = _env("TELEGRAM_CHANNEL_ID")
    telegram_api_id: str = _credential("TELEGRAM_API_ID")
    telegram_api_hash: str = _credential("TELEGRAM_API_HASH")
    telegram_session_string: str = _credential("TELEGRAM_SESSION_STRING")
    x_bearer_token: str = _credential("X_BEARER_TOKEN")
    x_api_key: str = _credential("X_API_KEY")
    x_api_secret: str = _credential("X_API_SECRET")
    x_access_token: str = _credential("X_ACCESS_TOKEN")
    x_access_token_secret: str = _credential("X_ACCESS_TOKEN_SECRET")
    barchart_api_key: str = _credential("BARCHART_API_KEY")
    oninvest_api_key: str = _credential("ONINVEST_API_KEY")
    yahoo_finance_api_key: str = _credential("YAHOO_FINANCE_API_KEY")
    openai_model: str = _env("OPENAI_MODEL", "gpt-4.1-mini")

    def require(self, *names: str) -> None:
        missing = [name for name in names if not getattr(self, name)]
        if missing:
            variables = ", ".join(name.upper() for name in missing)
            raise RuntimeError(f"Missing required environment variables: {variables}")

    def missing_optional_env_vars(self) -> list[str]:
        return [name for name in OPTIONAL_ENV_VARS if not os.getenv(name)]

    def require_mvp(self) -> None:
        self.require(
            "openai_api_key",
            "telegram_bot_token",
            "telegram_review_chat_id",
            "telegram_channel_id",
        )


settings = Settings()

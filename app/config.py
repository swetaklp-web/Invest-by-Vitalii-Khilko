from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_review_chat_id: str = os.getenv("TELEGRAM_REVIEW_CHAT_ID", "-5253592951")
    telegram_channel_id: str = os.getenv("TELEGRAM_CHANNEL_ID", "@Financebks")
    telegram_api_id: str = os.getenv("TELEGRAM_API_ID", "")
    telegram_api_hash: str = os.getenv("TELEGRAM_API_HASH", "")
    telegram_session_string: str = os.getenv("TELEGRAM_SESSION_STRING", "")
    x_api_key: str = os.getenv("X_API_KEY", "")
    barchart_api_key: str = os.getenv("BARCHART_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def require(self, *names: str) -> None:
        missing = [name for name in names if not getattr(self, name)]
        if missing:
            variables = ", ".join(name.upper() for name in missing)
            raise RuntimeError(f"Missing required environment variables: {variables}")


settings = Settings()

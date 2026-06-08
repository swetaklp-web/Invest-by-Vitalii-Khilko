from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession


async def main() -> None:
    load_dotenv()
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    if not api_id or not api_hash:
        raise RuntimeError("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env first.")

    async with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        session = client.session.save()
        print("TELEGRAM_SESSION_STRING:")
        print(session)


if __name__ == "__main__":
    asyncio.run(main())

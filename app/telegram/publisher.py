from pathlib import Path

from telegram import Bot

from app.config import settings
from app.telegram.formatting import sanitize_telegram_html


async def publish_draft(bot: Bot, draft: dict) -> tuple[int]:
    with Path(draft["image_path"]).open("rb") as image:
        photo_message = await bot.send_photo(
            chat_id=settings.telegram_channel_id,
            photo=image,
            caption=sanitize_telegram_html(draft["post"]["telegram_text"]),
            parse_mode="HTML",
        )
    return (photo_message.message_id,)

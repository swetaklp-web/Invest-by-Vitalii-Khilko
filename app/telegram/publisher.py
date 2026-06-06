from pathlib import Path

from telegram import Bot

from app.config import settings


async def publish_draft(bot: Bot, draft: dict) -> tuple[int, int]:
    with Path(draft["image_path"]).open("rb") as image:
        photo_message = await bot.send_photo(chat_id=settings.telegram_channel_id, photo=image)
    text_message = await bot.send_message(
        chat_id=settings.telegram_channel_id,
        text=draft["post"]["telegram_text"],
        disable_web_page_preview=True,
    )
    return photo_message.message_id, text_message.message_id


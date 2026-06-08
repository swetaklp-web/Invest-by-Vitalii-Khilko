from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler

from app.config import settings
from app.storage.drafts import save_draft
from app.storage.logs import write_log
from app.telegram.callbacks import handle_callback


def review_keyboard(post_type: str, message_id: int) -> InlineKeyboardMarkup:
    suffix = f"{post_type}:{message_id}"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Опубликовать", callback_data=f"publish:{suffix}"),
                InlineKeyboardButton("🔁 Новый вариант текста", callback_data=f"rewrite:{suffix}"),
            ],
            [
                InlineKeyboardButton("🖼 Новый вариант картинки", callback_data=f"image:{suffix}:1"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{suffix}"),
            ],
            [InlineKeyboardButton("📰 Другая новость", callback_data=f"other_news:{suffix}")],
        ]
    )


def image_review_keyboard(post_type: str, main_message_id: int, variant_number: int) -> InlineKeyboardMarkup:
    suffix = f"{post_type}:{main_message_id}"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Принять картинку", callback_data=f"accept_image:{suffix}"),
                InlineKeyboardButton("🖼 Ещё вариант", callback_data=f"image:{suffix}:{variant_number + 1}"),
            ],
            [InlineKeyboardButton("❌ Отклонить картинку", callback_data=f"reject_image:{suffix}")],
        ]
    )


def service_block(draft: dict) -> str:
    quality = draft["quality"]
    issues = "\n".join(f"• {item}" for item in quality["issues"]) or "• нет"
    risks = "\n".join(f"• {item}" for item in quality["risk_flags"]) or "• нет"
    return (
        f"\n\n———\nСлужебный блок\n"
        f"Draft ID: {draft['id']}\nQuality passed: {quality['passed']}\n"
        f"Проблемы:\n{issues}\nRisk flags:\n{risks}"
    )


async def send_review_draft(bot, draft: dict) -> None:
    with Path(draft["image_path"]).open("rb") as image:
        photo_message = await bot.send_photo(
            chat_id=settings.telegram_review_chat_id,
            photo=image,
            caption=draft["post"]["telegram_text"],
            parse_mode="HTML",
        )
    await bot.edit_message_reply_markup(
        chat_id=settings.telegram_review_chat_id,
        message_id=photo_message.message_id,
        reply_markup=review_keyboard(draft["post"]["post_type"], photo_message.message_id),
    )
    message = await bot.send_message(
        chat_id=settings.telegram_review_chat_id,
        text=service_block(draft).lstrip(),
    )
    draft["telegram_message_id"] = photo_message.message_id
    draft["telegram_service_message_id"] = message.message_id
    draft["telegram_photo_message_id"] = photo_message.message_id
    save_draft(draft)
    write_log(
        {
            "date": draft["post"].get("date"),
            "post_type": draft["post"].get("post_type"),
            "sources": draft["post"].get("sources", []),
            "tickers": draft["post"].get("tickers", []),
            "status": "pending_review",
            "telegram_message_id": message.message_id,
            "error": None,
        }
    )


async def log_bot_error(update: object, context) -> None:
    write_log({"status": "bot_error", "error": str(context.error)})


def run_bot() -> None:
    settings.require_mvp()
    application = Application.builder().token(settings.telegram_bot_token).build()
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(log_bot_error)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

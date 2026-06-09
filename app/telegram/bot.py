from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler

from app.config import settings
from app.storage.drafts import save_draft
from app.storage.logs import write_log
from app.telegram.callbacks import handle_callback
from app.telegram.formatting import sanitize_telegram_html


def review_keyboard(
    post_type: str, message_id: int, publish_allowed: bool = True
) -> InlineKeyboardMarkup:
    suffix = f"{post_type}:{message_id}"
    publish_button = InlineKeyboardButton(
        "✅ Опубликовать" if publish_allowed else "⛔ Факты не подтверждены",
        callback_data=f"{'publish' if publish_allowed else 'blocked_publish'}:{suffix}",
    )
    return InlineKeyboardMarkup(
        [
            [
                publish_button,
                InlineKeyboardButton("🔁 Новый вариант текста", callback_data=f"rewrite:{suffix}"),
            ],
            [
                InlineKeyboardButton(
                    "🖼 Новый вариант картинки",
                    callback_data=f"image:{suffix}:1:{1 if publish_allowed else 0}",
                ),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{suffix}"),
            ],
            [InlineKeyboardButton("📰 Другая новость", callback_data=f"other_news:{suffix}")],
        ]
    )


def image_review_keyboard(
    post_type: str,
    main_message_id: int,
    variant_number: int,
    publish_allowed: bool = True,
) -> InlineKeyboardMarkup:
    suffix = f"{post_type}:{main_message_id}"
    publish_flag = 1 if publish_allowed else 0
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Принять картинку",
                    callback_data=f"accept_image:{suffix}:1:{publish_flag}",
                ),
                InlineKeyboardButton(
                    "🖼 Ещё вариант",
                    callback_data=f"image:{suffix}:{variant_number + 1}:{publish_flag}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ Отклонить картинку",
                    callback_data=f"reject_image:{suffix}:1:{publish_flag}",
                )
            ],
        ]
    )


def service_block(draft: dict) -> str:
    quality = draft["quality"]
    issues = "\n".join(f"• {item}" for item in quality["issues"]) or "• нет"
    risks = "\n".join(f"• {item}" for item in quality["risk_flags"]) or "• нет"
    fact_check = quality.get("fact_check", {})
    unsupported = (
        "\n".join(f"• {item}" for item in fact_check.get("unsupported_claims", []))
        or "• нет"
    )
    fact_status = "ПРОЙДЕНА" if fact_check.get("passed") else "НЕ ПРОЙДЕНА"
    return (
        f"\n\n———\nСлужебный блок\n"
        f"Draft ID: {draft['id']}\n"
        f"Техническая проверка: "
        f"{'ПРОЙДЕНА' if quality.get('technical_passed', quality['passed']) else 'НЕ ПРОЙДЕНА'}\n"
        f"Проверка фактов по свежим источникам: {fact_status}\n"
        f"Проверено свежих сигналов: {fact_check.get('fresh_signals_checked', 0)}\n"
        f"Проверено рыночных показателей: {fact_check.get('market_quotes_checked', 0)}\n"
        f"Технические проблемы:\n{issues}\n"
        f"Неподтверждённые утверждения:\n{unsupported}\n"
        f"Risk flags:\n{risks}"
    )


async def send_review_draft(bot, draft: dict) -> None:
    draft["post"]["telegram_text"] = sanitize_telegram_html(draft["post"]["telegram_text"])
    publish_allowed = bool(
        draft["quality"]["passed"]
        and draft["quality"].get("fact_check", {}).get("passed")
    )
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
        reply_markup=review_keyboard(
            draft["post"]["post_type"], photo_message.message_id, publish_allowed
        ),
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

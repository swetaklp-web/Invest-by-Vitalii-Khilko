import asyncio

from telegram import Bot, CallbackQuery, Update
from telegram.ext import ContextTypes

from app.config import settings
from app.storage.logs import write_log


async def handle_query(query: CallbackQuery, bot: Bot) -> None:
    if not query or not query.data or not query.message:
        return
    if str(query.message.chat_id) != str(settings.telegram_review_chat_id):
        await query.answer("Эта кнопка доступна только в чате согласования.", show_alert=True)
        return

    parts = query.data.split(":", 2)
    if len(parts) != 3:
        await query.answer("Это кнопка старого черновика. Создайте новый.", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=None)
        return
    action, post_type, photo_message_id = parts
    await query.answer("Команда принята")

    if action == "publish":
        if not query.message.text:
            await query.message.reply_text("Не удалось прочитать текст черновика.")
            return
        photo = await bot.copy_message(
            chat_id=settings.telegram_channel_id,
            from_chat_id=settings.telegram_review_chat_id,
            message_id=int(photo_message_id),
        )
        text = await bot.send_message(
            chat_id=settings.telegram_channel_id,
            text=query.message.text,
            disable_web_page_preview=True,
        )
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ Опубликовано в основном канале.")
        status = "published"
        extra = {"channel_message_ids": [photo.message_id, text.message_id]}
    elif action == "reject":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ Черновик отклонён.")
        status = "rejected"
        extra = {}
    elif action in {"shorter", "deeper"}:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Готовлю новую версию…")
        from app.telegram.bot import send_review_draft
        from app.workflow import build_draft

        previous_post = {"post_type": post_type, "telegram_text": query.message.text or ""}
        new_draft = await asyncio.to_thread(build_draft, post_type, action, previous_post)
        await send_review_draft(bot, new_draft)
        status = f"revision_{action}"
        extra = {}
    else:
        return

    write_log(
        {
            "post_type": post_type,
            "status": status,
            "telegram_message_id": query.message.message_id,
            "error": None,
            **extra,
        }
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await handle_query(update.callback_query, context.bot)


async def process_callbacks_once(bot: Bot) -> int:
    updates = await bot.get_updates(timeout=10, allowed_updates=["callback_query"])
    processed = 0
    for update in updates:
        if update.callback_query:
            await handle_query(update.callback_query, bot)
            processed += 1
    if updates:
        await bot.get_updates(offset=updates[-1].update_id + 1, timeout=0)
    return processed

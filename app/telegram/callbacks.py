import asyncio
from datetime import datetime
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

from telegram import Bot, CallbackQuery, InputMediaPhoto, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from app.config import settings
from app.storage.logs import write_log


async def handle_query(query: CallbackQuery, bot: Bot) -> None:
    if not query or not query.data or not query.message:
        return
    if str(query.message.chat_id) != str(settings.telegram_review_chat_id):
        await query.answer("Эта кнопка доступна только в чате согласования.", show_alert=True)
        return

    parts = query.data.split(":")
    if len(parts) not in {3, 4}:
        await query.answer("Это кнопка старого черновика. Создайте новый.", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=None)
        return
    action, post_type, photo_message_id = parts[:3]
    variant_number = int(parts[3]) if len(parts) == 4 and parts[3].isdigit() else 1
    await query.answer("Команда принята")

    if action == "publish":
        try:
            published = await bot.copy_message(
                chat_id=settings.telegram_channel_id,
                from_chat_id=settings.telegram_review_chat_id,
                message_id=query.message.message_id,
            )
        except TelegramError as error:
            await query.message.reply_text(
                "Не удалось опубликовать. Проверьте, что бот добавлен администратором "
                f"в канал/группу публикации и что TELEGRAM_CHANNEL_ID задан верно. Ошибка: {error}"
            )
            raise
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ Опубликовано в основном канале.")
        status = "published"
        extra = {"channel_message_ids": [published.message_id]}
    elif action == "reject":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ Черновик отклонён.")
        status = "rejected"
        extra = {}
    elif action == "rewrite":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Готовлю новую версию…")
        from app.telegram.bot import send_review_draft
        from app.workflow import build_draft

        previous_post = {"post_type": post_type, "telegram_text": query.message.caption_html or ""}
        new_draft = await asyncio.to_thread(build_draft, post_type, "shorter", previous_post)
        await send_review_draft(bot, new_draft)
        status = "revision_text"
        extra = {}
    elif action == "image":
        from app.design.render_image import render_market_card
        from app.telegram.bot import image_review_keyboard

        plain_text = query.message.caption or ""
        tickers = list(dict.fromkeys(re.findall(r"\$[A-Z]{1,6}", plain_text)))[:6]
        post = {
            "date": datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat(),
            "image_sentence": plain_text,
            "image_tickers": tickers,
            "market_direction": "[Watch]",
            "signal_strength": "medium",
            "catalyst_type": "narrative",
        }
        image_path = await asyncio.to_thread(
            render_market_card, post, f"image-{uuid4().hex[:10]}", str(variant_number)
        )
        main_message_id = int(photo_message_id)
        with image_path.open("rb") as image:
            if query.message.message_id == main_message_id:
                photo = await bot.send_photo(
                    chat_id=settings.telegram_review_chat_id,
                    photo=image,
                    caption=query.message.caption_html or "",
                    parse_mode="HTML",
                    reply_markup=image_review_keyboard(post_type, main_message_id, variant_number),
                )
            else:
                await bot.edit_message_media(
                    chat_id=settings.telegram_review_chat_id,
                    message_id=query.message.message_id,
                    media=InputMediaPhoto(
                        media=image,
                        caption=query.message.caption_html or "",
                        parse_mode="HTML",
                    ),
                    reply_markup=image_review_keyboard(post_type, main_message_id, variant_number),
                )
                photo = query.message
        status = "image_variant"
        extra = {"telegram_photo_message_id": photo.message_id, "image_variant": variant_number}
    elif action == "accept_image":
        if not query.message.photo:
            await query.message.reply_text("Не удалось прочитать новую картинку.")
            return
        from app.telegram.bot import review_keyboard

        main_message_id = int(photo_message_id)
        main_keyboard = review_keyboard(post_type, main_message_id)
        try:
            main_message = await bot.edit_message_media(
                chat_id=settings.telegram_review_chat_id,
                message_id=main_message_id,
                media=InputMediaPhoto(
                    media=query.message.photo[-1].file_id,
                    caption=query.message.caption_html or "",
                    parse_mode="HTML",
                ),
            )
            # Telegram may drop inline buttons when media is replaced.
            await bot.edit_message_reply_markup(
                chat_id=settings.telegram_review_chat_id,
                message_id=main_message_id,
                reply_markup=main_keyboard,
            )
        except TelegramError as error:
            await query.message.reply_text(
                "Не удалось полностью обновить основной черновик и восстановить кнопки. "
                f"Предпросмотр оставлен на месте. Ошибка: {error}"
            )
            raise
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"✅ Картинка принята. Основной черновик выше обновлён: message_id {main_message.message_id}."
        )
        status = "image_accepted"
        extra = {"telegram_photo_message_id": main_message_id}
    elif action == "reject_image":
        await query.message.delete()
        status = "image_rejected"
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

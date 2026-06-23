from __future__ import annotations

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
from app.telegram.formatting import ensure_subscription_link, sanitize_telegram_html


async def answer_callback_safely(query: CallbackQuery, text: str, show_alert: bool = False) -> None:
    try:
        await query.answer(text, show_alert=show_alert)
    except TelegramError as error:
        write_log(
            {
                "status": "callback_answer_warning",
                "telegram_message_id": query.message.message_id if query.message else None,
                "error": str(error),
            }
        )


async def restore_review_keyboard(query: CallbackQuery, bot: Bot, post_type: str) -> None:
    from app.telegram.bot import review_keyboard

    await bot.edit_message_reply_markup(
        chat_id=settings.telegram_review_chat_id,
        message_id=query.message.message_id,
        reply_markup=review_keyboard(post_type, query.message.message_id),
    )


async def generate_replacement_draft(
    query: CallbackQuery,
    bot: Bot,
    post_type: str,
    revision: str,
    progress_message: str,
    failure_message: str,
) -> dict | None:
    from app.telegram.bot import send_review_draft
    from app.workflow import build_draft

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(progress_message)
    previous_post = {"post_type": post_type, "telegram_text": query.message.caption_html or ""}
    try:
        new_draft = await asyncio.to_thread(build_draft, post_type, revision, previous_post)
        await send_review_draft(bot, new_draft)
        return new_draft
    except Exception as error:
        await restore_review_keyboard(query, bot, post_type)
        error_type = type(error).__name__
        await query.message.reply_text(
            f"{failure_message}\nПричина: {error_type}.\n"
            "Кнопки исходного черновика восстановлены."
        )
        print(f"Callback action {revision} failed: {error_type}: {error}", flush=True)
        write_log(
            {
                "post_type": post_type,
                "status": "callback_error",
                "action": revision,
                "telegram_message_id": query.message.message_id,
                "error": str(error),
            }
        )
        return None


async def handle_query(query: CallbackQuery, bot: Bot) -> None:
    if not query or not query.data or not query.message:
        return
    if str(query.message.chat_id) != str(settings.telegram_review_chat_id):
        await answer_callback_safely(
            query, "Эта кнопка доступна только в чате согласования.", show_alert=True
        )
        return

    parts = query.data.split(":")
    if parts[0] == "news_menu" and len(parts) == 2:
        from app.telegram.bot import news_menu_keyboard, send_news_candidates

        await answer_callback_safely(query, "Ищу свежие подтверждённые новости")
        await query.edit_message_reply_markup(reply_markup=None)
        try:
            count = await send_news_candidates(bot, parts[1], query.message)
            await query.message.reply_text(
                f"Подборка готова: {count} сюжетов.",
                reply_markup=news_menu_keyboard(),
            )
        except Exception as error:
            await query.message.reply_text(
                f"⚠️ Не удалось собрать подборку: {type(error).__name__}.",
                reply_markup=news_menu_keyboard(),
            )
            write_log({"status": "news_discovery_error", "error": str(error)})
        return
    if parts[0] == "accept_news" and len(parts) == 3:
        from app.storage.news_selections import load_news_selection
        from app.telegram.bot import accept_news_keyboard, send_review_draft
        from app.workflow import build_draft_from_signal, recover_news_signal

        selection_id, post_type = parts[1], parts[2]
        await answer_callback_safely(query, "Новость принята, готовлю пост и картинку")
        await query.edit_message_reply_markup(reply_markup=None)
        progress = await query.message.reply_text(
            "Готовлю публикацию по выбранной новости и генерирую новую тематическую картинку…"
        )
        try:
            try:
                signal = load_news_selection(selection_id)["signal"]
            except FileNotFoundError:
                signal = await asyncio.to_thread(
                    recover_news_signal, selection_id, post_type
                )
            draft = await asyncio.to_thread(
                build_draft_from_signal, post_type, signal
            )
            await send_review_draft(bot, draft)
            await progress.edit_text("✅ Готовый пост отправлен на согласование.")
        except Exception as error:
            await query.edit_message_reply_markup(
                reply_markup=accept_news_keyboard(selection_id, post_type)
            )
            await progress.edit_text(
                f"⚠️ Не удалось подготовить пост: {type(error).__name__}. "
                "Кнопка выбора восстановлена."
            )
            write_log(
                {
                    "post_type": post_type,
                    "status": "accept_news_error",
                    "selection_id": selection_id,
                    "error": str(error),
                }
            )
        return
    if len(parts) not in {3, 4, 5}:
        await answer_callback_safely(query, "Это кнопка старого черновика. Создайте новый.", True)
        await query.edit_message_reply_markup(reply_markup=None)
        return
    action, post_type, photo_message_id = parts[:3]
    variant_number = int(parts[3]) if len(parts) == 4 and parts[3].isdigit() else 1
    if len(parts) >= 4 and parts[3].isdigit():
        variant_number = int(parts[3])
    publish_allowed = not (len(parts) == 5 and parts[4] == "0")
    await answer_callback_safely(query, "Команда принята")

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
    elif action == "blocked_publish":
        await query.message.reply_text(
            "⛔ Публикация заблокирована: проверка фактов по свежим источникам не пройдена. "
            "Создайте другую новость или новую редакцию."
        )
        return
    elif action == "reject":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ Черновик отклонён.")
        status = "rejected"
        extra = {}
    elif action == "rewrite":
        new_draft = await generate_replacement_draft(
            query,
            bot,
            post_type,
            "shorter",
            "Готовлю новую версию…",
            "⚠️ Не удалось создать новую редакцию.",
        )
        if new_draft is None:
            return
        status = "revision_text"
        extra = {}
    elif action == "other_news":
        new_draft = await generate_replacement_draft(
            query,
            bot,
            post_type,
            "different_news",
            "Ищу другую новость и готовлю новый сюжет…",
            "⚠️ Не удалось создать другой подтверждённый сюжет на текущую дату.",
        )
        if new_draft is None:
            return
        status = "different_news"
        extra = {}
    elif action == "image":
        from app.design.generate_ai_image import generate_ai_news_image
        from app.design.render_image import render_market_card
        from app.telegram.bot import image_review_keyboard

        plain_text = query.message.caption or ""
        clean_caption = ensure_subscription_link(
            sanitize_telegram_html(query.message.caption_html or plain_text)
        )
        tickers = list(dict.fromkeys(re.findall(r"\$[A-Z]{1,6}", plain_text)))[:6]
        post = {
            "date": datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat(),
            "image_sentence": plain_text,
            "image_tickers": tickers,
            "market_direction": "[Watch]",
            "signal_strength": "medium",
            "catalyst_type": "narrative",
        }
        image_id = f"image-{uuid4().hex[:10]}"
        try:
            image_path = await asyncio.to_thread(
                generate_ai_news_image, post, image_id, variant_number
            )
        except Exception as error:
            image_path = await asyncio.to_thread(
                render_market_card, post, image_id, str(variant_number)
            )
            write_log(
                {
                    "post_type": post_type,
                    "status": "image_generation_warning",
                    "error": str(error),
                    "fallback": "html_market_card",
                }
            )
        main_message_id = int(photo_message_id)
        with image_path.open("rb") as image:
            if query.message.message_id == main_message_id:
                photo = await bot.send_photo(
                    chat_id=settings.telegram_review_chat_id,
                    photo=image,
                    caption=clean_caption,
                    parse_mode="HTML",
                    reply_markup=image_review_keyboard(
                        post_type, main_message_id, variant_number, publish_allowed
                    ),
                )
            else:
                await bot.edit_message_media(
                    chat_id=settings.telegram_review_chat_id,
                    message_id=query.message.message_id,
                    media=InputMediaPhoto(
                        media=image,
                        caption=clean_caption,
                        parse_mode="HTML",
                    ),
                    reply_markup=image_review_keyboard(
                        post_type, main_message_id, variant_number, publish_allowed
                    ),
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
        main_keyboard = review_keyboard(post_type, main_message_id, publish_allowed)
        clean_caption = ensure_subscription_link(
            sanitize_telegram_html(query.message.caption_html or "")
        )
        try:
            main_message = await bot.edit_message_media(
                chat_id=settings.telegram_review_chat_id,
                message_id=main_message_id,
                media=InputMediaPhoto(
                    media=query.message.photo[-1].file_id,
                    caption=clean_caption,
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

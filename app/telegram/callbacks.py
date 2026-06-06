import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.storage.drafts import load_draft, mark_published, save_draft
from app.storage.logs import write_log
from app.telegram.publisher import publish_draft


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not query.message:
        return
    if str(query.message.chat_id) != str(settings.telegram_review_chat_id):
        await query.answer("Эта кнопка доступна только в чате согласования.", show_alert=True)
        return
    await query.answer()

    action, draft_id = query.data.split(":", 1)
    draft = load_draft(draft_id)
    if draft["status"] not in {"pending_review", "revision_requested"}:
        await query.edit_message_reply_markup(reply_markup=None)
        return

    if action == "publish":
        photo_id, text_id = await publish_draft(context.bot, draft)
        draft["channel_message_ids"] = [photo_id, text_id]
        mark_published(draft)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Опубликовано: {draft_id}")
        status = "published"
    elif action == "reject":
        draft["status"] = "rejected"
        save_draft(draft)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Отклонено: {draft_id}")
        status = "rejected"
    elif action in {"shorter", "deeper"}:
        draft["status"] = "revision_requested"
        save_draft(draft)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Готовлю новую версию: {action}")
        from app.telegram.bot import send_review_draft
        from app.workflow import build_draft

        new_draft = await asyncio.to_thread(
            build_draft, draft["post"]["post_type"], action, draft["post"]
        )
        await send_review_draft(context.bot, new_draft)
        status = f"revision_{action}"
    else:
        return

    write_log(
        {
            "date": draft["post"].get("date"),
            "post_type": draft["post"].get("post_type"),
            "sources": draft["post"].get("sources", []),
            "tickers": draft["post"].get("tickers", []),
            "status": status,
            "telegram_message_id": draft.get("telegram_message_id"),
            "error": None,
        }
    )

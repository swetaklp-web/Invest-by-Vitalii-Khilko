import argparse
import asyncio

from telegram import Bot

from app.config import settings
from app.storage.logs import write_log
from app.telegram.bot import run_bot, send_review_draft
from app.workflow import build_draft


async def generate_and_send(post_type: str) -> None:
    settings.require_mvp()
    try:
        draft = await asyncio.to_thread(build_draft, post_type)  # type: ignore[arg-type]
        async with Bot(settings.telegram_bot_token) as bot:
            await send_review_draft(bot, draft)
    except Exception as error:
        write_log({"post_type": post_type, "status": "error", "error": str(error)})
        raise


async def discover_chats() -> None:
    settings.require("telegram_bot_token")
    async with Bot(settings.telegram_bot_token) as bot:
        updates = await bot.get_updates(timeout=10, allowed_updates=["message"])

    chats: dict[int, tuple[str, str]] = {}
    for update in updates:
        if not update.effective_chat:
            continue
        chat = update.effective_chat
        name = chat.title or chat.full_name or chat.username or "unnamed"
        chats[chat.id] = (chat.type, name)

    if not chats:
        print("No recent chats found. Send /start to the bot in the review group and retry.")
        return

    print("Recent Telegram chats:")
    for chat_id, (chat_type, name) in chats.items():
        print(f"- type={chat_type} name={name!r} id={chat_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Invest by Vitalii Khilko automation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="Generate and send a review draft")
    generate.add_argument("--type", choices=["morning_brief", "evening_theme"], required=True)
    subparsers.add_parser("bot", help="Run the persistent Telegram approval bot")
    subparsers.add_parser("discover-chats", help="List recent Telegram chat IDs")
    args = parser.parse_args()

    if args.command == "bot":
        run_bot()
    elif args.command == "discover-chats":
        asyncio.run(discover_chats())
    else:
        asyncio.run(generate_and_send(args.type))


if __name__ == "__main__":
    main()

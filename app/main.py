import argparse
import asyncio

from telegram import Bot

from app.config import settings
from app.storage.logs import write_log
from app.telegram.bot import run_bot, send_review_draft
from app.workflow import build_draft


async def generate_and_send(post_type: str) -> None:
    settings.require(
        "telegram_bot_token", "openai_api_key", "telegram_review_chat_id", "telegram_channel_id"
    )
    try:
        draft = await asyncio.to_thread(build_draft, post_type)  # type: ignore[arg-type]
        async with Bot(settings.telegram_bot_token) as bot:
            await send_review_draft(bot, draft)
    except Exception as error:
        write_log({"post_type": post_type, "status": "error", "error": str(error)})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Invest by Vitalii Khilko automation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="Generate and send a review draft")
    generate.add_argument("--type", choices=["morning_brief", "evening_theme"], required=True)
    subparsers.add_parser("bot", help="Run the persistent Telegram approval bot")
    args = parser.parse_args()

    if args.command == "bot":
        run_bot()
    else:
        asyncio.run(generate_and_send(args.type))


if __name__ == "__main__":
    main()

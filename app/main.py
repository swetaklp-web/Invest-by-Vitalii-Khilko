import argparse
import asyncio

from telegram import Bot

from app.config import settings
from app.storage.logs import write_log
from app.telegram.bot import news_menu_keyboard, run_bot, send_review_draft
from app.telegram.callbacks import process_callbacks_once
from app.workflow import DraftQualityFailed, FactCheckFailed, FreshSourceDataUnavailable, build_draft
from app.sources.barchart import fetch_barchart_signals
from app.sources.freshness import filter_fresh_signals, today_moscow
from app.sources.oninvest import fetch_oninvest_signals
from app.sources.telegram_reader import fetch_telegram_signals
from app.sources.x_reader import fetch_x_signals
from app.sources.yahoo import fetch_yahoo_market_snapshot, fetch_yahoo_signals


async def generate_and_send(post_type: str) -> None:
    settings.require_mvp()
    try:
        draft = await asyncio.to_thread(build_draft, post_type)  # type: ignore[arg-type]
        async with Bot(settings.telegram_bot_token) as bot:
            await send_review_draft(bot, draft)
    except FreshSourceDataUnavailable as error:
        write_log({"post_type": post_type, "status": "fresh_data_unavailable", "error": str(error)})
        async with Bot(settings.telegram_bot_token) as bot:
            await bot.send_message(
                chat_id=settings.telegram_review_chat_id,
                text=(
                    "⚠️ Черновик не создан: на текущую дату не найдено достаточно "
                    "свежих подтверждённых сигналов из разрешённых источников. "
                    "Система остановила генерацию, чтобы не публиковать недостоверную новость."
                ),
            )
    except FactCheckFailed as error:
        write_log(
            {
                "post_type": post_type,
                "status": "fact_check_failed",
                "error": str(error),
                "unsupported_claims": error.fact_check.get("unsupported_claims", []),
            }
        )
        unsupported = "\n".join(
            f"• {item}" for item in error.fact_check.get("unsupported_claims", [])[:8]
        ) or "• факт-чек не вернул конкретный список"
        async with Bot(settings.telegram_bot_token) as bot:
            await bot.send_message(
                chat_id=settings.telegram_review_chat_id,
                text=(
                    "⚠️ Черновик не отправлен: проверка фактов по свежим источникам "
                    "не прошла после нескольких попыток.\n\n"
                    f"Неподтверждённые утверждения:\n{unsupported}\n\n"
                    "Система остановила публикационный черновик, чтобы не отправлять "
                    "в согласование недостоверный материал."
                ),
            )
    except DraftQualityFailed as error:
        write_log(
            {
                "post_type": post_type,
                "status": "quality_failed",
                "error": str(error),
                "issues": error.quality.get("issues", []),
            }
        )
        issues = "\n".join(f"• {item}" for item in error.quality.get("issues", [])[:8]) or "• нет"
        async with Bot(settings.telegram_bot_token) as bot:
            await bot.send_message(
                chat_id=settings.telegram_review_chat_id,
                text=(
                    "⚠️ Черновик не отправлен: техническая проверка качества не прошла.\n\n"
                    f"Проблемы:\n{issues}\n\n"
                    "Нужно сгенерировать новый вариант по более строгим входным данным."
                ),
            )
    except Exception as error:
        write_log({"post_type": post_type, "status": "error", "error": str(error)})
        raise


async def discover_chats() -> None:
    settings.require("telegram_bot_token")
    async with Bot(settings.telegram_bot_token) as bot:
        updates = await bot.get_updates(
            timeout=10,
            allowed_updates=["message", "channel_post", "my_chat_member"],
        )

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


async def check_publish_target() -> None:
    settings.require("telegram_bot_token", "telegram_channel_id")
    async with Bot(settings.telegram_bot_token) as bot:
        identity = await bot.get_me()
        print(f"Bot identity: username=@{identity.username} id={identity.id}")
        chat = await bot.get_chat(settings.telegram_channel_id)
    print(f"Publish target: type={chat.type} title={chat.title or chat.username!r} id={chat.id}")


async def process_callbacks() -> None:
    settings.require_mvp()
    async with Bot(settings.telegram_bot_token) as bot:
        processed = await process_callbacks_once(bot)
    print(f"Processed callback queries: {processed}")


async def send_news_menu() -> None:
    settings.require("telegram_bot_token", "telegram_review_chat_id")
    async with Bot(settings.telegram_bot_token) as bot:
        await bot.send_message(
            chat_id=settings.telegram_review_chat_id,
            text=(
                "Ручной отбор новостей готов. Выберите подборку, затем нажмите "
                "«Принять новость» под подходящим сюжетом."
            ),
            reply_markup=news_menu_keyboard(),
        )


def source_health() -> None:
    print("Source health report:")
    for name, fetcher in (
        ("x", fetch_x_signals),
        ("yahoo", fetch_yahoo_signals),
        ("barchart", fetch_barchart_signals),
        ("telegram", fetch_telegram_signals),
        ("oninvest", fetch_oninvest_signals),
    ):
        try:
            signals = fetcher()
            fresh, stale = filter_fresh_signals(signals, today_moscow())
            print(f"- {name}: ok, fresh_signals={len(fresh)}, stale_or_undated={len(stale)}")
        except Exception as error:
            print(f"- {name}: unavailable, fallback=manual_inputs, error={error}")
    try:
        snapshot = fetch_yahoo_market_snapshot()
        print(f"- yahoo_market_snapshot: ok, quotes={len(snapshot['quotes'])}")
    except Exception as error:
        print(f"- yahoo_market_snapshot: unavailable, error={error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Invest by Vitalii Khilko automation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="Generate and send a review draft")
    generate.add_argument("--type", choices=["morning_brief", "evening_theme"], required=True)
    subparsers.add_parser("bot", help="Run the persistent Telegram approval bot")
    subparsers.add_parser("discover-chats", help="List recent Telegram chat IDs")
    subparsers.add_parser("check-publish-target", help="Validate Telegram publish target")
    subparsers.add_parser("process-callbacks", help="Process pending Telegram buttons once")
    subparsers.add_parser("send-news-menu", help="Send the manual news selection menu")
    subparsers.add_parser("source-health", help="Check external source availability")
    args = parser.parse_args()

    if args.command == "bot":
        run_bot()
    elif args.command == "discover-chats":
        asyncio.run(discover_chats())
    elif args.command == "check-publish-target":
        asyncio.run(check_publish_target())
    elif args.command == "process-callbacks":
        asyncio.run(process_callbacks())
    elif args.command == "send-news-menu":
        asyncio.run(send_news_menu())
    elif args.command == "source-health":
        source_health()
    else:
        asyncio.run(generate_and_send(args.type))


if __name__ == "__main__":
    main()

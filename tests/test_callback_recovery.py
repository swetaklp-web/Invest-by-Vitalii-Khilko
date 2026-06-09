import asyncio

from app.telegram import callbacks
from telegram.error import BadRequest


class FakeMessage:
    message_id = 321
    caption_html = "Исходный пост"

    def __init__(self) -> None:
        self.replies = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class FakeQuery:
    def __init__(self) -> None:
        self.message = FakeMessage()
        self.markups = []

    async def edit_message_reply_markup(self, reply_markup=None) -> None:
        self.markups.append(reply_markup)


class FakeBot:
    def __init__(self) -> None:
        self.restored = []

    async def edit_message_reply_markup(self, **kwargs) -> None:
        self.restored.append(kwargs)


class FakeSettings:
    telegram_review_chat_id = "-1"


def test_failed_other_news_restores_original_buttons(monkeypatch) -> None:
    query = FakeQuery()
    bot = FakeBot()

    def fail_build(*_):
        raise RuntimeError("temporary failure")

    monkeypatch.setattr("app.workflow.build_draft", fail_build)
    monkeypatch.setattr(callbacks, "write_log", lambda *_: None)
    monkeypatch.setattr(callbacks, "settings", FakeSettings())

    result = asyncio.run(
        callbacks.generate_replacement_draft(
            query, bot, "morning_brief", "different_news", "working", "failed"
        )
    )

    assert result is None
    assert bot.restored
    assert "восстановлены" in query.message.replies[-1]


def test_expired_callback_answer_does_not_stop_action(monkeypatch) -> None:
    events = []

    class ExpiredQuery:
        message = FakeMessage()

        async def answer(self, *_args, **_kwargs):
            raise BadRequest("Query is too old")

    monkeypatch.setattr(callbacks, "write_log", events.append)

    asyncio.run(callbacks.answer_callback_safely(ExpiredQuery(), "accepted"))

    assert events[0]["status"] == "callback_answer_warning"

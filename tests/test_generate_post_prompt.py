from app.ai import generate_post


class FakeMessage:
    content = '{"telegram_text":"Тест"}'


class FakeChoice:
    message = FakeMessage()


class FakeResponse:
    choices = [FakeChoice()]


class FakeCompletions:
    def __init__(self) -> None:
        self.kwargs = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeResponse()


class FakeClient:
    def __init__(self) -> None:
        self.chat = type("Chat", (), {"completions": FakeCompletions()})()


class FakeSettings:
    openai_api_key = "test"
    openai_model = "gpt-test"

    def require(self, *_):
        return None


def test_different_news_prompt_requires_a_new_story(monkeypatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(generate_post, "settings", FakeSettings())
    monkeypatch.setattr(generate_post, "OpenAI", lambda **_: client)
    monkeypatch.setattr(generate_post, "_prompt", lambda _: "")

    generate_post.generate_post(
        {"signals": [{"summary": "Новая тема"}]},
        "evening_theme",
        "different_news",
        {"telegram_text": "Старый сюжет"},
    )

    user_message = client.chat.completions.kwargs["messages"][-1]["content"]
    assert "совершенно другой новости" in user_message
    assert "Не редактируй и не пересказывай предыдущий пост" in user_message

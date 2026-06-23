from app.telegram.bot import (
    accept_news_keyboard,
    image_review_keyboard,
    news_menu_keyboard,
    review_keyboard,
    service_block,
)


def button_labels(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_review_keyboard_has_all_review_actions() -> None:
    assert button_labels(review_keyboard("morning_brief", 123)) == [
        "✅ Опубликовать",
        "🔁 Новый вариант текста",
        "🖼 Новый вариант картинки",
        "❌ Отклонить",
        "📰 Другая новость",
    ]


def test_image_review_keyboard_accepts_retries_or_rejects_variant() -> None:
    assert button_labels(image_review_keyboard("morning_brief", 123, 2)) == [
        "✅ Принять картинку",
        "🖼 Ещё вариант",
        "❌ Отклонить картинку",
    ]


def test_review_keyboard_blocks_publish_when_fact_check_fails() -> None:
    labels = button_labels(review_keyboard("evening_theme", 123, publish_allowed=False))

    assert labels[0] == "⛔ Факты не подтверждены"


def test_news_menu_has_manual_editorial_choices() -> None:
    assert button_labels(news_menu_keyboard()) == [
        "🌅 Новости для утреннего поста",
        "🌆 Новости для вечернего поста",
        "🔄 Обновить общую подборку",
    ]


def test_news_card_can_be_accepted() -> None:
    markup = accept_news_keyboard("abc123", "evening_theme")

    assert button_labels(markup) == ["✅ Принять новость"]
    assert markup.inline_keyboard[0][0].callback_data == "accept_news:abc123:evening_theme"


def test_service_block_marks_technical_issues_as_non_blocking() -> None:
    text = service_block(
        {
            "id": "draft1",
            "post": {
                "sources": [
                    {
                        "name": "Yahoo Finance",
                        "url": "https://finance.yahoo.com/news/test",
                        "summary": "Banks move after Fed update",
                    }
                ]
            },
            "quality": {
                "passed": False,
                "technical_passed": False,
                "issues": ["telegram_text exceeds 1000 characters"],
                "risk_flags": [],
                "fact_check": {
                    "passed": True,
                    "fresh_signals_checked": 3,
                    "market_quotes_checked": 2,
                    "unsupported_claims": [],
                },
            },
        }
    )

    assert "Технические замечания: есть, не блокируют" in text
    assert "Проверка фактов по свежим источникам: ПРОЙДЕНА" in text
    assert "Источники фактов:" in text
    assert '<a href="https://finance.yahoo.com/news/test">Yahoo Finance: Banks move after Fed update</a>' in text
    assert "Техническая проверка: НЕ ПРОЙДЕНА" not in text


def test_service_block_deduplicates_and_escapes_source_links() -> None:
    text = service_block(
        {
            "id": "draft2",
            "post": {
                "sources": [
                    {
                        "name": "Yahoo <Finance>",
                        "url": "https://finance.yahoo.com/news/test?a=1&b=2",
                        "summary": "A < B & C",
                    },
                    {
                        "name": "Duplicate",
                        "url": "https://finance.yahoo.com/news/test?a=1&b=2",
                        "summary": "duplicate",
                    },
                ]
            },
            "quality": {
                "passed": True,
                "technical_passed": True,
                "issues": [],
                "risk_flags": [],
                "fact_check": {
                    "passed": True,
                    "fresh_signals_checked": 1,
                    "market_quotes_checked": 0,
                    "unsupported_claims": [],
                },
            },
        }
    )

    assert text.count("https://finance.yahoo.com/news/test") == 1
    assert "Yahoo &lt;Finance&gt;: A &lt; B &amp; C" in text

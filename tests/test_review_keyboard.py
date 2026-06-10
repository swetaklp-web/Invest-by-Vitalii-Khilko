from app.telegram.bot import (
    accept_news_keyboard,
    image_review_keyboard,
    news_menu_keyboard,
    review_keyboard,
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

from app.telegram.bot import image_review_keyboard, review_keyboard


def button_labels(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_review_keyboard_has_four_actions() -> None:
    assert button_labels(review_keyboard("morning_brief", 123)) == [
        "✅ Опубликовать",
        "🔁 Новый вариант текста",
        "🖼 Новый вариант картинки",
        "❌ Отклонить",
    ]


def test_image_review_keyboard_accepts_or_rejects_variant() -> None:
    assert button_labels(image_review_keyboard("morning_brief", 123)) == [
        "✅ Принять картинку",
        "❌ Отклонить картинку",
    ]

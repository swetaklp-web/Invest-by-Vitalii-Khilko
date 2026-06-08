from app.telegram.bot import review_keyboard


def test_restored_main_keyboard_contains_publish_action() -> None:
    markup = review_keyboard("morning_brief", 321)
    callback_data = [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
    ]

    assert "publish:morning_brief:321" in callback_data
    assert len(callback_data) == 4

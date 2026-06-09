from app.telegram.formatting import sanitize_telegram_html


def test_sanitize_telegram_html_keeps_supported_tags_and_escapes_other_markup():
    text = "<b>Вывод</b> AT&T <i>важно</i> <blockquote>Риск</blockquote>"

    assert sanitize_telegram_html(text) == (
        "<b>Вывод</b> AT&amp;T &lt;i&gt;важно&lt;/i&gt; "
        "<blockquote>Риск</blockquote>"
    )


def test_sanitize_telegram_html_converts_br_tags_to_paragraph_breaks():
    text = "Первый абзац.<br><br>Второй абзац.&lt;br /&gt;Третья строка."

    assert sanitize_telegram_html(text) == "Первый абзац.\n\nВторой абзац.\nТретья строка."


def test_sanitize_telegram_html_is_idempotent():
    text = "<b>AT&amp;T</b>\n\nТекст"

    once = sanitize_telegram_html(text)
    twice = sanitize_telegram_html(once)

    assert twice == once

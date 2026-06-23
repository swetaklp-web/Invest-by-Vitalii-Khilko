from app.telegram.formatting import (
    PHOTO_CAPTION_LIMIT,
    SUBSCRIPTION_LABEL,
    SUBSCRIPTION_URL,
    ensure_subscription_link,
    sanitize_telegram_html,
)


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


def test_sanitize_telegram_html_keeps_safe_links():
    text = '<a href="https://t.me/Financebks">Подписаться</a> <a href="javascript:bad">bad</a>'

    assert sanitize_telegram_html(text) == (
        '<a href="https://t.me/Financebks">Подписаться</a> '
        '&lt;a href=&quot;javascript:bad&quot;&gt;bad&lt;/a&gt;'
    )


def test_ensure_subscription_link_appends_once():
    text = ensure_subscription_link("Пост")

    assert f'<a href="{SUBSCRIPTION_URL}">{SUBSCRIPTION_LABEL}</a>' in text
    assert ensure_subscription_link(text) == text


def test_ensure_subscription_link_keeps_caption_within_telegram_limit():
    text = ensure_subscription_link("<b>" + ("длинный текст " * 120) + "</b>")

    assert len(text) <= PHOTO_CAPTION_LIMIT
    assert f'<a href="{SUBSCRIPTION_URL}">{SUBSCRIPTION_LABEL}</a>' in text
    assert text.endswith(f'<a href="{SUBSCRIPTION_URL}">{SUBSCRIPTION_LABEL}</a>')

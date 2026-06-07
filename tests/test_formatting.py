from app.telegram.formatting import sanitize_telegram_html


def test_sanitize_telegram_html_keeps_supported_tags_and_escapes_other_markup():
    text = "<b>Вывод</b> AT&T <i>важно</i> <blockquote>Риск</blockquote>"

    assert sanitize_telegram_html(text) == (
        "<b>Вывод</b> AT&amp;T &lt;i&gt;важно&lt;/i&gt; "
        "<blockquote>Риск</blockquote>"
    )

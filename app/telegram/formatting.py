import html
import re


ALLOWED_TAGS = ("<b>", "</b>", "<blockquote>", "</blockquote>")


def sanitize_telegram_html(text: str) -> str:
    normalized = html.unescape(text)
    normalized = re.sub(r"<br\s*/?>", "\n", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", normalized)
    parts = re.split(r"(<\/?(?:b|blockquote)>)", normalized, flags=re.IGNORECASE)
    return "".join(
        part.lower() if part.lower() in ALLOWED_TAGS else html.escape(part)
        for part in parts
    )

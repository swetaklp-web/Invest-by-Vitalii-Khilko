import html
import re


ALLOWED_TAGS = ("<b>", "</b>", "<blockquote>", "</blockquote>")


def sanitize_telegram_html(text: str) -> str:
    parts = re.split(r"(<\/?(?:b|blockquote)>)", text, flags=re.IGNORECASE)
    return "".join(part.lower() if part.lower() in ALLOWED_TAGS else html.escape(part) for part in parts)

import html
import re
from urllib.parse import urlparse


ALLOWED_TAGS = ("<b>", "</b>", "<blockquote>", "</blockquote>")
SUBSCRIPTION_URL = "https://t.me/Financebks"
SUBSCRIPTION_LABEL = "🔋 Инвестиции | Технологии - подписаться"


def _safe_href(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return url


def sanitize_telegram_html(text: str) -> str:
    normalized = html.unescape(text)
    normalized = re.sub(r"<br\s*/?>", "\n", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", normalized)
    token_pattern = re.compile(
        r"(<\/?(?:b|blockquote)>|<a\s+href=[\"']([^\"']+)[\"']>|</a>)",
        flags=re.IGNORECASE,
    )
    result: list[str] = []
    position = 0
    safe_link_depth = 0
    for match in token_pattern.finditer(normalized):
        result.append(html.escape(normalized[position:match.start()]))
        token = match.group(1)
        token_lower = token.lower()
        if token_lower in ALLOWED_TAGS:
            result.append(token_lower)
        elif token_lower == "</a>":
            if safe_link_depth:
                result.append("</a>")
                safe_link_depth -= 1
            else:
                result.append(html.escape(token))
        elif token_lower.startswith("<a "):
            href = _safe_href(match.group(2) or "")
            if href:
                result.append(f'<a href="{html.escape(href, quote=True)}">')
                safe_link_depth += 1
            else:
                result.append(html.escape(token))
        position = match.end()
    result.append(html.escape(normalized[position:]))
    return "".join(result)


def ensure_subscription_link(text: str) -> str:
    clean = text.rstrip()
    if SUBSCRIPTION_URL in clean or SUBSCRIPTION_LABEL in clean:
        return clean
    return (
        f'{clean}\n\n<a href="{SUBSCRIPTION_URL}">{html.escape(SUBSCRIPTION_LABEL)}</a>'
        if clean
        else f'<a href="{SUBSCRIPTION_URL}">{html.escape(SUBSCRIPTION_LABEL)}</a>'
    )

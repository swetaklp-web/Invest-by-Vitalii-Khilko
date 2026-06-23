import html
import re
from urllib.parse import urlparse


ALLOWED_TAGS = ("<b>", "</b>", "<blockquote>", "</blockquote>")
SUBSCRIPTION_URL = "https://t.me/Financebks"
SUBSCRIPTION_LABEL = "🔋 Инвестиции | Технологии - подписаться"
SUBSCRIPTION_HTML = f'<a href="{SUBSCRIPTION_URL}">{html.escape(SUBSCRIPTION_LABEL)}</a>'
PHOTO_CAPTION_LIMIT = 1024


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
    suffix = f"\n\n{SUBSCRIPTION_HTML}"
    clean = text.rstrip()
    clean = re.sub(
        rf"\s*<a\s+href=[\"']{re.escape(SUBSCRIPTION_URL)}[\"']>"
        rf"{re.escape(SUBSCRIPTION_LABEL)}</a>\s*$",
        "",
        clean,
        flags=re.IGNORECASE,
    ).rstrip()
    body_limit = PHOTO_CAPTION_LIMIT - len(suffix)
    if len(clean) > body_limit:
        plain = re.sub(r"<\/?(?:b|blockquote)>|<a\s+href=[\"'][^\"']+[\"']>|</a>", "", clean)
        plain = html.unescape(plain)
        clean = html.escape(plain[: max(body_limit - 1, 0)].rstrip()) + "…"
    result = f"{clean}{suffix}" if clean else SUBSCRIPTION_HTML
    if len(result) <= PHOTO_CAPTION_LIMIT:
        return result
    # Last-resort guard for Telegram's hard caption limit.
    if len(SUBSCRIPTION_HTML) >= PHOTO_CAPTION_LIMIT:
        return SUBSCRIPTION_HTML[:PHOTO_CAPTION_LIMIT]
    body_limit = PHOTO_CAPTION_LIMIT - len(suffix)
    plain = html.unescape(re.sub(r"<[^>]+>", "", clean))
    clean = html.escape(plain[: max(body_limit - 1, 0)].rstrip()) + "…"
    return f"{clean}{suffix}" if clean else SUBSCRIPTION_HTML

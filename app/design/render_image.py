from pathlib import Path
from typing import Any
import colorsys
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from app.config import ROOT_DIR


FORBIDDEN_IMAGE_PHRASES = ("на радаре", "альтернативный вариант обложки")


def _sentence_from_text(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    parts = re.split(r"(?<=[.!?])\s+", clean)
    sentence = next((part.strip() for part in parts if part.strip()), "Главная тема рынка США получает новый импульс.")
    sentence = re.sub(r"^[^\w$А-Яа-яЁё]+", "", sentence).strip()
    words = sentence.split()
    while len(" ".join(words)) > 92 and len(words) > 4:
        words.pop()
    sentence = " ".join(words).rstrip(",:;—- ")
    if sentence and sentence[-1] not in ".!?":
        sentence += "."
    lowered = sentence.lower()
    if any(phrase in lowered for phrase in FORBIDDEN_IMAGE_PHRASES):
        return "Главная тема рынка США получает новый импульс."
    return sentence


def render_market_card(post: dict[str, Any], draft_id: str, variant: str = "default") -> Path:
    template_dir = ROOT_DIR / "app" / "design" / "templates"
    output_path = ROOT_DIR / "data" / "drafts" / f"{draft_id}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape())
    variant_number = int(variant) if variant.isdigit() else 0
    variant_templates = (
        "market_card_chart.html",
        "market_card_partnership.html",
        "market_card_ranking.html",
        "market_card_ecosystem.html",
        "market_card_variant.html",
    )
    template_name = (
        variant_templates[(variant_number - 1) % len(variant_templates)]
        if variant_number
        else "market_card.html"
    )
    hue = ((variant_number * 0.173) % 1.0) if variant_number else 0.6

    def color(lightness: float, saturation: float = 0.72) -> str:
        red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
        return f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"

    html = env.get_template(template_name).render(
        date=post.get("date", ""),
        sentence=_sentence_from_text(
            post.get("image_sentence")
            or post.get("image_title")
            or post.get("title")
            or post.get("telegram_text", "")
        ),
        tickers=post.get("image_tickers") or [f"${ticker}" for ticker in post.get("tickers", [])],
        variant_number=variant_number,
        layout=variant_number % 3,
        accent=color(0.52),
        accent_dark=color(0.30),
        accent_soft=color(0.93, 0.45),
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page.set_content(html, wait_until="networkidle")
        forbidden = page.locator("body").inner_text().lower()
        if any(phrase in forbidden for phrase in FORBIDDEN_IMAGE_PHRASES):
            browser.close()
            raise ValueError("Image contains a forbidden service phrase")
        text_overflows = page.locator("h1, .title").evaluate_all(
            """elements => elements.some(el =>
                el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1 ||
                el.getBoundingClientRect().right > 1279 || el.getBoundingClientRect().bottom > 719
            )"""
        )
        if text_overflows:
            browser.close()
            raise ValueError("Image sentence does not fit inside the template")
        page.screenshot(path=str(output_path))
        browser.close()
    return output_path

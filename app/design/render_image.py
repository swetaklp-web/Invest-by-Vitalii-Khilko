from pathlib import Path
from typing import Any
import colorsys

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from app.config import ROOT_DIR


def render_market_card(post: dict[str, Any], draft_id: str, variant: str = "default") -> Path:
    template_dir = ROOT_DIR / "app" / "design" / "templates"
    output_path = ROOT_DIR / "data" / "drafts" / f"{draft_id}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape())
    direction = {
        "[Bullish]": "Позитивный импульс",
        "[Bearish]": "Негативный импульс",
        "[Watch]": "На радаре",
        "[Volatile]": "Высокая волатильность",
    }.get(post.get("market_direction"), "На радаре")
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
        title=post.get("image_title") or post.get("title", ""),
        subtitle=post.get("image_subtitle", ""),
        tickers=post.get("image_tickers") or [f"${ticker}" for ticker in post.get("tickers", [])],
        direction=direction,
        strength=post.get("signal_strength", "medium"),
        catalyst=post.get("catalyst_type", "narrative"),
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
        page.screenshot(path=str(output_path))
        browser.close()
    return output_path

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from app.config import ROOT_DIR


def render_market_card(post: dict[str, Any], draft_id: str) -> Path:
    template_dir = ROOT_DIR / "app" / "design" / "templates"
    output_path = ROOT_DIR / "data" / "drafts" / f"{draft_id}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape())
    html = env.get_template("market_card.html").render(
        date=post.get("date", ""),
        title=post.get("image_title") or post.get("title", ""),
        subtitle=post.get("image_subtitle", ""),
        tickers=post.get("image_tickers") or [f"${ticker}" for ticker in post.get("tickers", [])],
        direction=post.get("market_direction", "[Watch]").strip("[]"),
        strength=post.get("signal_strength", "medium").upper(),
        catalyst=post.get("catalyst_type", "narrative").upper(),
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=str(output_path))
        browser.close()
    return output_path

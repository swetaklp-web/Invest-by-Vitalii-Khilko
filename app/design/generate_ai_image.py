from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.config import ROOT_DIR, settings


def _image_prompt(post: dict[str, Any], variant_number: int) -> str:
    tickers = ", ".join(post.get("tickers", [])[:5]) or "US market"
    source_context = " ".join(
        str(source.get("summary", "")) for source in post.get("sources", [])[:3]
    )
    styles = (
        "editorial financial illustration with cinematic depth and a clear central metaphor",
        "premium magazine collage with market infrastructure, companies and macro forces",
        "clean isometric financial ecosystem illustration with distinct connected elements",
        "photorealistic institutional trading desk scene blended with the news subject",
        "bold modern data-art composition with an unmistakable visual narrative",
    )
    style = styles[(max(variant_number, 1) - 1) % len(styles)]
    return (
        f"Create a unique 16:9 cover image for a Russian-language investment Telegram post. "
        f"News topic: {post.get('image_title') or post.get('title')}. "
        f"Verified context: {source_context}. Related tickers: {tickers}. "
        f"Visual direction: {style}. Premium fintech editorial quality, light balanced palette, "
        f"high visual hierarchy, sophisticated and credible, meaningfully different from prior variants. "
        f"Do not include any words, letters, numbers, captions, charts with labels, watermarks, "
        f"or invented company logos. If a brand is relevant, communicate it through recognizable "
        f"products or industry imagery without fabricating its logo."
    )


def generate_ai_news_image(
    post: dict[str, Any], draft_id: str, variant_number: int = 1
) -> Path:
    settings.require("openai_api_key")
    output_path = ROOT_DIR / "data" / "drafts" / f"{draft_id}-ai-{variant_number}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.images.generate(
        model=settings.openai_image_model,
        prompt=_image_prompt(post, variant_number),
        size="1536x1024",
        quality="medium",
        n=1,
    )
    image = response.data[0]
    if not image.b64_json:
        raise RuntimeError("OpenAI image generation returned no image data")
    output_path.write_bytes(base64.b64decode(image.b64_json))
    return output_path
